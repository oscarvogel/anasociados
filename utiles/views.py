from functools import wraps
import hashlib
import secrets
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core import signing
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from syh.models import Area, Cliente, Movimientos
from syh.models import Evidencia
from utiles.alertas_hallazgos import (
    SeleccionEmpresaAreaInvalida,
    construir_resumen_hallazgos_whatsapp,
    notificar_admin_evidencia,
)
from utiles.models import EnlacePublicoHallazgos
from utiles.notificaciones import WhatsAppClient, WhatsAppError
from usuarios.models import AreasProfile

MAX_ARCHIVOS_POR_ENVIO = 5
MAX_BYTES_POR_ARCHIVO = 8 * 1024 * 1024  # 8 MB
# El iPhone manda HEIC/HEIF al sacar foto desde la camara. Si no se aceptan,
# el usuario saca la foto y el servidor la rechaza.
TIPOS_IMAGEN = {
    "image/jpeg", "image/jpg", "image/pjpeg",
    "image/png", "image/webp", "image/gif",
    "image/heic", "image/heif", "image/heic-sequence", "image/heif-sequence",
}


PREVIEW_SALT = "utiles.whatsapp_hallazgos.preview"
PREVIEW_MAX_AGE = 300
ENLACE_PUBLICO_DIAS = 14


def _url_hallazgos_publicos(token):
    ruta = reverse("utiles:hallazgos_publicos")
    base = settings.WHATSAPP_PUBLIC_BASE_URL.rstrip("/")
    return f"{base}{ruta}#{token}"


def _respuesta_publica(response):
    response["Cache-Control"] = "private, no-store, max-age=0"
    response["Pragma"] = "no-cache"
    response["Referrer-Policy"] = "no-referrer"
    response["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    return response


def superusuario_requerido(view):
    """Devuelve 403 a quien no sea superusuario, también en las APIs."""
    @wraps(view)
    @login_required
    def wrapped(request, *args, **kwargs):
        if not request.user.is_superuser:
            return HttpResponseForbidden("Acceso restringido a superusuarios.")
        return view(request, *args, **kwargs)
    return wrapped


@superusuario_requerido
@require_GET
def whatsapp_hallazgos_page(request):
    return render(
        request,
        "pages/utiles/whatsapp_hallazgos.html",
        {"empresas": Cliente.objects.all()},
    )


@superusuario_requerido
@require_GET
def whatsapp_hallazgos_areas(request):
    cliente_id = request.GET.get("cliente_id", "").strip()
    if not cliente_id:
        return JsonResponse({"error": "Seleccioná una empresa."}, status=400)
    if not Cliente.objects.filter(pk=cliente_id).exists():
        return JsonResponse({"error": "La empresa seleccionada no existe."}, status=404)
    areas = Area.objects.filter(cliente_id=cliente_id).order_by("detalle")
    return JsonResponse({
        "areas": [{"id": area.pk, "nombre": area.detalle} for area in areas]
    })


@superusuario_requerido
@require_GET
def whatsapp_hallazgos_preview(request):
    cliente_id = request.GET.get("cliente_id", "").strip()
    area_id = request.GET.get("area_id", "").strip()
    try:
        resumen = construir_resumen_hallazgos_whatsapp(cliente_id, area_id)
    except SeleccionEmpresaAreaInvalida as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    response = {
        "empresa": resumen.cliente,
        "area": resumen.area,
        "mensaje": resumen.mensaje,
        "total_vencidos": resumen.total_vencidos,
        "total_por_vencer": resumen.total_por_vencer,
        "hay_novedades": resumen.hay_novedades,
    }
    if not resumen.hay_novedades:
        return JsonResponse(response)

    asignaciones = list(
        AreasProfile.objects.filter(
            area_id=area_id,
            area__cliente_id=cliente_id,
            user__profile__cliente_id=cliente_id,
        ).select_related("user")[:2]
    )
    asignacion = asignaciones[0] if len(asignaciones) == 1 else None
    telefono = asignacion.telefono_whatsapp if asignacion else ""

    public_token = secrets.token_urlsafe(32)
    public_url = _url_hallazgos_publicos(public_token)
    mensaje = f"{resumen.mensaje}\n\nVer todos los hallazgos: {public_url}"
    data = {
        "cliente_id": str(cliente_id),
        "area_id": str(area_id),
        "mensaje_resumen": resumen.mensaje,
        "mensaje": mensaje,
        "public_token": public_token,
        "nonce": secrets.token_urlsafe(18),
    }
    response["telefono"] = telefono
    response["contacto_configurado"] = bool(telefono)
    response["contacto_ambiguo"] = len(asignaciones) > 1
    response["mensaje"] = mensaje
    response["enlace_publico"] = public_url
    response["preview_token"] = signing.dumps(data, salt=PREVIEW_SALT)
    return JsonResponse(response)


@superusuario_requerido
@require_POST
def whatsapp_hallazgos_send(request):
    token = request.POST.get("preview_token", "")
    telefono = request.POST.get("telefono", "")
    if not token or not telefono.strip():
        return JsonResponse({"error": "Falta la confirmación o el número de destino."}, status=400)

    try:
        preview = signing.loads(token, salt=PREVIEW_SALT, max_age=PREVIEW_MAX_AGE)
    except signing.SignatureExpired:
        return JsonResponse({"error": "La vista previa venció. Volvé a seleccionar el área."}, status=400)
    except signing.BadSignature:
        return JsonResponse({"error": "La vista previa no es válida. Volvé a seleccionar el área."}, status=400)

    try:
        resumen = construir_resumen_hallazgos_whatsapp(
            preview.get("cliente_id", ""), preview.get("area_id", "")
        )
    except SeleccionEmpresaAreaInvalida:
        return JsonResponse({"error": "La empresa o el área ya no están disponibles."}, status=400)

    if not resumen.hay_novedades:
        return JsonResponse({"error": "Ya no hay hallazgos vencidos o próximos a vencer para enviar."}, status=409)
    if resumen.mensaje != preview.get("mensaje_resumen"):
        return JsonResponse({"error": "Los hallazgos cambiaron desde la vista previa. Actualizá el resumen antes de enviar."}, status=409)

    public_token = preview.get("public_token", "")
    if not public_token or preview.get("mensaje") != (
        f"{resumen.mensaje}\n\nVer todos los hallazgos: {_url_hallazgos_publicos(public_token)}"
    ):
        return JsonResponse({"error": "El enlace de consulta no es válido. Volvé a preparar el resumen."}, status=400)

    cliente = WhatsAppClient()
    try:
        telefono_destino = cliente.normalizar_telefono(telefono)
    except WhatsAppError:
        return JsonResponse({
            "error": "El número debe incluir código de país, por ejemplo 5493764000000."
        }, status=400)
    if len(telefono_destino) < 10 or len(telefono_destino) > 15:
        return JsonResponse({"error": "El número internacional tiene una longitud inválida."}, status=400)

    token_hash = hashlib.sha256(public_token.encode("utf-8")).hexdigest()
    enlace, _ = EnlacePublicoHallazgos.objects.get_or_create(
        token_hash=token_hash,
        defaults={
            "area_id": preview["area_id"],
            "cliente_id": preview["cliente_id"],
            "expires_at": timezone.now() + timedelta(days=ENLACE_PUBLICO_DIAS),
        },
    )
    if (
        enlace.area_id != preview["area_id"]
        or enlace.cliente_id != preview["cliente_id"]
        or enlace.revoked_at is not None
        or enlace.expires_at <= timezone.now()
    ):
        return JsonResponse({"error": "El enlace venció o fue revocado. Volvé a preparar el resumen."}, status=409)

    try:
        resultado = cliente.enviar_texto(
            telefono_destino,
            preview["mensaje"],
            external_ref=f"an:hallazgos:{preview['nonce']}",
            actor=request.user.get_full_name() or request.user.get_username(),
        )
    except WhatsAppError:
        # El detalle del gateway/red puede incluir información sensible; no lo
        # devolvemos ni lo registramos desde esta vista.
        return JsonResponse({"error": "No se pudo enviar el mensaje. Revisá la conexión con WhatsApp e intentá nuevamente."}, status=502)
    except Exception:
        return JsonResponse({"error": "Ocurrió un error al enviar el mensaje."}, status=502)

    return JsonResponse({
        "ok": True,
        "aceptado": True,
        "message_id": resultado.get("messageId"),
        "mensaje": "WhatsApp aceptó el mensaje. Esto no confirma que el destinatario lo haya leído.",
    })


@never_cache
@require_POST
def hallazgos_publicos_subir(request):
    """
    Sube evidencia para un hallazgo, desde el enlace publico del area.

    El token va en el header Authorization, igual que el endpoint de datos:
    el fragmento (#) de la URL nunca viaja al servidor, asi que tampoco
    viaja en el cuerpo de este POST.

    Regla que no se negocia: el hallazgo TIENE que pertenecer al area del
    enlace. Sin esto, un enlace del area A permitiria colgar evidencia falsa
    de un hallazgo del area B.
    """
    authorization = request.headers.get("Authorization", "")
    esquema, _, token = authorization.partition(" ")
    if esquema.lower() != "bearer" or not token.strip():
        return _respuesta_publica(JsonResponse(
            {"error": "El enlace no es válido o ya venció."}, status=404
        ))

    enlace = _enlace_valido(token.strip())
    if enlace is None:
        return _respuesta_publica(JsonResponse(
            {"error": "El enlace no es válido o ya venció."}, status=404
        ))

    movimiento_id = request.POST.get("movimiento_id", "").strip()
    detalle = request.POST.get("detalle", "").strip()[:500]

    # El hallazgo tiene que ser de esta empresa Y de este area.
    movimiento = Movimientos.objects.filter(
        pk=movimiento_id,
        cliente_id=enlace.cliente_id,
        area_id=enlace.area_id,
    ).first()
    if movimiento is None:
        return _respuesta_publica(JsonResponse(
            {"error": "Ese hallazgo no pertenece a esta área."}, status=400
        ))

    archivos = [f for f in request.FILES.getlist("archivos") if f]
    if not archivos:
        return _respuesta_publica(JsonResponse(
            {"error": "Adjuntá al menos una foto."}, status=400
        ))
    if len(archivos) > MAX_ARCHIVOS_POR_ENVIO:
        return _respuesta_publica(JsonResponse(
            {"error": f"Se permiten hasta {MAX_ARCHIVOS_POR_ENVIO} fotos por envío."},
            status=400,
        ))

    for archivo in archivos:
        if archivo.size > MAX_BYTES_POR_ARCHIVO:
            return _respuesta_publica(JsonResponse(
                {"error": "Cada foto puede pesar hasta 8 MB."}, status=400
            ))
        if archivo.content_type not in TIPOS_IMAGEN:
            return _respuesta_publica(JsonResponse(
                {"error": "Solo se aceptan imágenes (JPG, PNG, WEBP)."}, status=400
            ))

    area = Area.objects.filter(pk=enlace.area_id).select_related("cliente").first()
    cliente_nombre = area.cliente.nombre if area and area.cliente else enlace.cliente_id
    area_detalle = area.detalle if area else enlace.area_id

    # Telefono del responsable, si se conoce: sirve para saber de quien vino.
    asignaciones = AreasProfile.objects.filter(
        area_id=enlace.area_id,
        area__cliente_id=enlace.cliente_id,
    ).exclude(telefono_whatsapp="").values_list("telefono_whatsapp", flat=True)
    telefono_origen = sorted(set(asignaciones))[0] if asignaciones else ""

    guardadas = []
    for archivo in archivos:
        evidencia = Evidencia.objects.create(
            movimiento=movimiento,
            fecha=timezone.localdate(),
            detalle=detalle,
            origen="enlace_publico",
            subido_por=telefono_origen,
        )
        evidencia.archivo.save(archivo.name, archivo, save=True)
        guardadas.append(evidencia)

    # Avisar a los administradores. Si falla, la evidencia ya quedo guardada
    # y el admin la ve igual en el panel: el aviso es una comodidad, no un
    # requisito para que la evidencia exista.
    aviso = notificar_admin_evidencia(
        guardadas[0], movimiento, cliente_nombre, area_detalle
    )

    return _respuesta_publica(JsonResponse({
        "ok": True,
        "guardadas": len(guardadas),
        "mensaje": (
            "Se recibieron tus fotos. El hallazgo queda pendiente de validación "
            "por el equipo de AN & Asociados; no se cerró automáticamente."
        ),
        "aviso_admin": aviso.get("detalle", ""),
    }, status=201))


def _enlace_valido(token):
    """Enlace vigente para ese token, o None."""
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return EnlacePublicoHallazgos.objects.filter(
        token_hash=token_hash,
        revoked_at__isnull=True,
        expires_at__gt=timezone.now(),
    ).first()


@never_cache
@require_GET
def hallazgos_publicos_page(request):
    response = render(
        request,
        "pages/utiles/hallazgos_publicos.html",
        {
            "datos_url": reverse("utiles:hallazgos_publicos_datos"),
            "subir_url": reverse("utiles:hallazgos_publicos_subir"),
        },
    )
    return _respuesta_publica(response)


@never_cache
@require_GET
def hallazgos_publicos_datos(request):
    authorization = request.headers.get("Authorization", "")
    esquema, _, token = authorization.partition(" ")
    if esquema.lower() != "bearer" or not token.strip():
        return _respuesta_publica(JsonResponse({"error": "El enlace no es válido o ya venció."}, status=404))

    token_hash = hashlib.sha256(token.strip().encode("utf-8")).hexdigest()
    enlace = EnlacePublicoHallazgos.objects.filter(
        token_hash=token_hash,
        revoked_at__isnull=True,
        expires_at__gt=timezone.now(),
    ).select_related("area", "area__cliente").first()
    if enlace is None:
        return _respuesta_publica(JsonResponse({"error": "El enlace no es válido o ya venció."}, status=404))

    try:
        resumen = construir_resumen_hallazgos_whatsapp(enlace.cliente_id, enlace.area_id)
    except SeleccionEmpresaAreaInvalida:
        return _respuesta_publica(JsonResponse({"error": "El enlace no es válido o ya venció."}, status=404))

    def serializar(movimientos):
        return [
            {
                # El id va en el payload para que el formulario de subida sepa a
                # que hallazgo pertenece la foto. El pk es un uuid de 20
                # caracteres, no es enumerable.
                "id": movimiento.pk,
                "fecha": movimiento.fecha_cumplimiento.isoformat(),
                "estado": movimiento.estado,
                "descripcion": movimiento.hallazgo or "Sin descripción",
            }
            for movimiento in movimientos
        ]

    payload = {
        "empresa": resumen.cliente,
        "area": resumen.area,
        "actualizado": timezone.localtime().strftime("%d/%m/%Y %H:%M"),
        "vence": timezone.localtime(enlace.expires_at).strftime("%d/%m/%Y"),
        "total_vencidos": resumen.total_vencidos,
        "total_por_vencer": resumen.total_por_vencer,
        "vencidos": serializar(resumen.vencidos),
        "por_vencer": serializar(resumen.por_vencer),
    }
    return _respuesta_publica(JsonResponse(payload))
