from functools import wraps
import secrets

from django.contrib.auth.decorators import login_required
from django.core import signing
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from syh.models import Area, Cliente
from utiles.alertas_hallazgos import (
    SeleccionEmpresaAreaInvalida,
    construir_resumen_hallazgos_whatsapp,
)
from utiles.models import AreaWhatsAppContacto
from utiles.notificaciones import WhatsAppClient, WhatsAppError


PREVIEW_SALT = "utiles.whatsapp_hallazgos.preview"
PREVIEW_MAX_AGE = 300


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

    try:
        contacto = AreaWhatsAppContacto.objects.get(area_id=area_id)
    except AreaWhatsAppContacto.DoesNotExist:
        return JsonResponse({
            "error": "Esta área no tiene un WhatsApp configurado en Django Admin.",
            "hay_novedades": True,
        }, status=404)

    data = {
        "cliente_id": str(cliente_id),
        "area_id": str(area_id),
        "mensaje": resumen.mensaje,
        "nonce": secrets.token_urlsafe(18),
    }
    response["telefono"] = contacto.telefono
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
        contacto = AreaWhatsAppContacto.objects.get(area_id=preview.get("area_id", ""))
    except (SeleccionEmpresaAreaInvalida, AreaWhatsAppContacto.DoesNotExist):
        return JsonResponse({"error": "La empresa, el área o su contacto ya no están disponibles."}, status=400)

    if not resumen.hay_novedades:
        return JsonResponse({"error": "Ya no hay hallazgos vencidos o próximos a vencer para enviar."}, status=409)
    if resumen.mensaje != preview.get("mensaje"):
        return JsonResponse({"error": "Los hallazgos cambiaron desde la vista previa. Actualizá el resumen antes de enviar."}, status=409)

    cliente = WhatsAppClient()
    try:
        telefono_destino = cliente.normalizar_telefono(telefono)
    except WhatsAppError:
        return JsonResponse({
            "error": "El número debe incluir código de país, por ejemplo 5493764000000."
        }, status=400)
    if len(telefono_destino) < 10 or len(telefono_destino) > 15:
        return JsonResponse({"error": "El número internacional tiene una longitud inválida."}, status=400)

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

