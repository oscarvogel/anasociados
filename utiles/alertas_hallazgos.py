import hashlib
import secrets
from dataclasses import dataclass
from datetime import date, timedelta

from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from syh.models import Area, Cliente, Movimientos
from utiles.models import EnlacePublicoHallazgos


ESTADOS_ABIERTOS = ("Gestión en Curso", "Incumplido")
DIAS_POR_VENCER = 5
MAX_EJEMPLOS = 3
MAX_CARACTERES_HALLAZGO = 100
DIAS_ENLACE_PUBLICO = 14


class SeleccionEmpresaAreaInvalida(ValueError):
    """La empresa o el área seleccionada no existe o no coincide."""


@dataclass(frozen=True)
class ResumenHallazgosWhatsApp:
    cliente: str
    area: str
    vencidos: list[Movimientos]
    por_vencer: list[Movimientos]
    total_vencidos: int
    total_por_vencer: int
    mensaje: str
    hay_novedades: bool


def construir_resumen_hallazgos_whatsapp(
    cliente_id: str,
    area_id: str,
    hoy: date | None = None,
) -> ResumenHallazgosWhatsApp:
    """Construye el resumen de hallazgos abiertos para una empresa y área."""
    try:
        cliente = Cliente.objects.get(pk=cliente_id)
    except Cliente.DoesNotExist as exc:
        raise SeleccionEmpresaAreaInvalida("La empresa seleccionada no existe.") from exc

    try:
        area = Area.objects.get(pk=area_id, cliente_id=cliente.pk)
    except Area.DoesNotExist as exc:
        raise SeleccionEmpresaAreaInvalida(
            "El área seleccionada no pertenece a la empresa indicada."
        ) from exc

    fecha_actual = hoy or timezone.localdate()
    fecha_limite = fecha_actual + timedelta(days=DIAS_POR_VENCER)
    movimientos_abiertos = Movimientos.objects.filter(
        cliente_id=cliente.pk,
        area_id=area.pk,
        estado__in=ESTADOS_ABIERTOS,
        fecha_cumplimiento__isnull=False,
    )

    vencidos = list(
        movimientos_abiertos.filter(fecha_cumplimiento__lt=fecha_actual).order_by(
            "fecha_cumplimiento", "pk"
        )
    )
    por_vencer = list(
        movimientos_abiertos.filter(
            fecha_cumplimiento__gte=fecha_actual,
            fecha_cumplimiento__lte=fecha_limite,
        ).order_by("fecha_cumplimiento", "pk")
    )

    mensaje = _formatear_mensaje(cliente.nombre, area.detalle, vencidos, por_vencer)
    return ResumenHallazgosWhatsApp(
        cliente=cliente.nombre,
        area=area.detalle,
        vencidos=vencidos,
        por_vencer=por_vencer,
        total_vencidos=len(vencidos),
        total_por_vencer=len(por_vencer),
        mensaje=mensaje,
        hay_novedades=bool(vencidos or por_vencer),
    )


def _formatear_mensaje(
    cliente: str,
    area: str,
    vencidos: list[Movimientos],
    por_vencer: list[Movimientos],
) -> str:
    lineas = [
        f"*AN & Asociados | {cliente} - {area}*",
        f"Vencidos: {len(vencidos)} | Por vencer en {DIAS_POR_VENCER} días: {len(por_vencer)}",
    ]
    if not vencidos and not por_vencer:
        lineas.append("No hay hallazgos abiertos con vencimiento en este período.")
        return "\n".join(lineas)

    ejemplos = []
    # Si hay hallazgos de ambas categorías, reservar un ejemplo de cada una.
    if vencidos:
        ejemplos.append(("VENCIDO", vencidos[0]))
    if por_vencer and len(ejemplos) < MAX_EJEMPLOS:
        ejemplos.append(("POR VENCER", por_vencer[0]))

    restantes = (
        [("VENCIDO", movimiento) for movimiento in vencidos[1:]]
        + [("POR VENCER", movimiento) for movimiento in por_vencer[1:]]
    )
    ejemplos.extend(restantes[: MAX_EJEMPLOS - len(ejemplos)])

    for etiqueta, movimiento in ejemplos:
        descripcion = _descripcion_breve(movimiento.hallazgo)
        fecha = movimiento.fecha_cumplimiento.strftime("%d/%m")
        lineas.append(f"- {etiqueta} ({fecha}): {descripcion}")

    omitidos = len(vencidos) + len(por_vencer) - len(ejemplos)
    if omitidos:
        lineas.append(f"… y {omitidos} más.")
    return "\n".join(lineas)


def _descripcion_breve(hallazgo: str, limite: int = MAX_CARACTERES_HALLAZGO) -> str:
    descripcion = " ".join((hallazgo or "").split())
    if len(descripcion) <= limite:
        return descripcion
    return f"{descripcion[:limite - 3].rstrip()}..."


def notificar_admin_evidencia(evidencia, movimiento, cliente_nombre, area_detalle):
    """
    Avisa a los administradores que se subio una evidencia.

    Subir una foto NO cierra el hallazgo: el cierre lo hace un administrador
    revisando la evidencia. Por eso el mensaje lo dice explicitamente, para
    que nadie asuma que el hallazgo ya quedo resuelto.

    Nunca levanta excepcion: si el gateway esta caido, la evidencia ya esta
    guardada y el admin la va a ver igual en el panel.
    """
    from utiles.notificaciones import WhatsAppClient, WhatsAppError, _destinatarios_whatsapp

    numeros = _destinatarios_whatsapp()
    if not numeros:
        return {"ok": False, "detalle": "sin numeros de administracion configurados"}

    cliente = WhatsAppClient()
    if not cliente.habilitado:
        return {"ok": False, "detalle": "WhatsApp deshabilitado o sin API key"}

    fecha_vencimiento = getattr(movimiento, "fecha_cumplimiento", None)
    vencimiento = (
        fecha_vencimiento.strftime("%d/%m/%Y") if fecha_vencimiento else "sin fecha"
    )

    lineas = [
        "*AN & Asociados | Evidencia nueva*",
        "",
        f"Empresa: {cliente_nombre}",
        f"Area: {area_detalle}",
        f"Hallazgo: {_descripcion_breve(movimiento.hallazgo or '', 120)}",
        f"Vencia: {vencimiento}",
        f"Subida por: {evidencia.subido_por or 'no identificado'}",
    ]
    if evidencia.detalle:
        lineas.append(f"Comentario: {_descripcion_breve(evidencia.detalle, 140)}")
    lineas += [
        "",
        "_Queda pendiente de validacion: el hallazgo NO se cerro._",
    ]
    mensaje = "\n".join(lineas)

    enviados, errores = [], []
    for numero in numeros:
        try:
            cliente.enviar_texto(
                numero,
                mensaje,
                external_ref=f"an:evidencia:{evidencia.pk}",
            )
            enviados.append(numero)
        except WhatsAppError as exc:
            errores.append(f"{numero}: {exc}")
        except Exception as exc:  # noqa: BLE001
            errores.append(f"{numero}: {exc}")

    return {
        "ok": not errores,
        "enviados": enviados,
        "errores": errores,
        "detalle": (
            f"notificado a {len(enviados)}" if not errores
            else f"{len(enviados)} ok, {len(errores)} con error"
        ),
    }


def url_hallazgos_publicos(token):
    """URL publica de detalle de hallazgos para un token."""
    ruta = reverse("utiles:hallazgos_publicos")
    base = settings.WHATSAPP_PUBLIC_BASE_URL.rstrip("/")
    return f"{base}{ruta}#{token}"


def crear_enlace_hallazgos(cliente_id, area_id, token=None, dias=DIAS_ENLACE_PUBLICO):
    """
    Registra el enlace publico de una empresa+area y devuelve (token, url).

    El token viaja en el fragmento (#) de la URL y la pagina lo pasa como
    Bearer al endpoint de datos; en la base solo queda su hash.

    Se reutiliza si el token ya existe: asi, si el comando corre dos veces con
    el mismo token, no se crea un enlace duplicado.
    """
    token = token or secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    enlace, _creado = EnlacePublicoHallazgos.objects.get_or_create(
        token_hash=token_hash,
        defaults={
            "area_id": str(area_id),
            "cliente_id": str(cliente_id),
            "expires_at": timezone.now() + timedelta(days=dias),
        },
    )
    return enlace, token, url_hallazgos_publicos(token)
