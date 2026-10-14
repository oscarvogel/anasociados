import hashlib
import logging
import secrets
from dataclasses import dataclass
from datetime import date, timedelta

from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from syh.models import Area, Cliente, Movimientos
from utiles.models import EnlacePublicoHallazgos

logger = logging.getLogger(__name__)


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


def notificar_admin_evidencia(evidencia, movimiento, cliente_nombre, area_detalle,
                              enlaces=None):
    """
    Avisa a los administradores que se subio una evidencia.

    Subir una foto NO cierra el hallazgo: el cierre lo hace un administrador
    revisando la evidencia. Por eso el mensaje lo dice explicitamente, para
    que nadie asuma que el hallazgo ya quedo resuelto.

    `enlaces` es una lista de (telefono, url). Cada administrador recibe SU
    link, asi que queda registrado quien aprobo o rechazo. Sin `enlaces` se
    cae a la lista del .env y el aviso sale sin link de revision.

    Nunca levanta excepcion: si el gateway esta caido, la evidencia ya esta
    guardada y el admin la va a ver igual en el panel.
    """
    from utiles.notificaciones import WhatsAppClient, WhatsAppError, _destinatarios_admin

    if enlaces:
        destinos = list(dict(enlaces).items())
    else:
        destinos = [(numero, "") for numero in _destinatarios_admin()]

    if not destinos:
        return {"ok": False, "detalle": "sin numeros de administracion configurados"}

    cliente = WhatsAppClient()
    if not cliente.habilitado:
        return {"ok": False, "detalle": "WhatsApp deshabilitado o sin API key"}

    fecha_vencimiento = getattr(movimiento, "fecha_cumplimiento", None)
    vencimiento = (
        fecha_vencimiento.strftime("%d/%m/%Y") if fecha_vencimiento else "sin fecha"
    )

    base = [
        "*AN & Asociados | Evidencia nueva*",
        "",
        f"Empresa: {cliente_nombre}",
        f"Area: {area_detalle}",
        f"Hallazgo: {_descripcion_breve(movimiento.hallazgo or '', 120)}",
        f"Vencia: {vencimiento}",
        f"Subida por: {evidencia.subido_por or 'no identificado'}",
    ]
    if evidencia.detalle:
        base.append(f"Comentario: {_descripcion_breve(evidencia.detalle, 140)}")

    enviados, errores = [], []
    for numero, url in destinos:
        lineas = list(base)
        if url:
            lineas += ["", f"Ver la foto y decidir: {url}"]
        lineas += ["", "_Queda pendiente de validacion: el hallazgo NO se cerro._"]

        try:
            cliente.enviar_texto(
                numero,
                "\n".join(lineas),
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


def url_revision_evidencias(token):
    """URL de la bandeja de revision para un token."""
    ruta = reverse("utiles:evidencias_revision_page")
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
            "puede_revisar": False,
        },
    )
    return enlace, token, url_hallazgos_publicos(token)


def crear_enlace_revision(cliente_id, area_id, contacto=None, token=None,
                          dias=DIAS_ENLACE_PUBLICO):
    """
    Enlace de la bandeja de revision para una empresa+area.

    Mismo modelo y mismo alcance que el del responsable, pero con
    `puede_revisar=True`: ese es el unico permiso que habilita a ver las fotos
    y a cerrar hallazgos. Son tokens distintos a proposito.

    Se crea POR CONTACTO: cada administrador recibe el suyo y queda registrado
    quien aprobo o rechazo cada evidencia. Si se llama sin contacto, el enlace
    queda sin dueno y `revisado_por` cae en "sin identificar".
    """
    token = token or secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    enlace, _creado = EnlacePublicoHallazgos.objects.get_or_create(
        token_hash=token_hash,
        defaults={
            "area_id": str(area_id),
            "cliente_id": str(cliente_id),
            "expires_at": timezone.now() + timedelta(days=dias),
            "puede_revisar": True,
            "contacto_id": getattr(contacto, "pk", None),
        },
    )
    return enlace, token, url_revision_evidencias(token)


def crear_enlaces_revision_admin(cliente_id, area_id):
    """
    Un enlace de revision por cada administrador que recibe avisos de evidencia.

    Devuelve [(contacto, url), ...]. Los contactos que no tienen el rol
    `recibe_evidencias` o estan desactivados no entran: si alguien lo desactivo
    a proposito, mandarle igual seria mandarle a alguien que dijo que no.

    Un contacto que falla (telefono raro, gateway caido) no impide que los
    demas reciban el suyo: cada uno va en su propio try.
    """
    from utiles.models import ContactoNotificacion

    resultado = []
    for contacto in ContactoNotificacion.objects.filter(
        activo=True, recibe_evidencias=True
    ):
        try:
            _enlace, _token, url = crear_enlace_revision(
                cliente_id, area_id, contacto=contacto
            )
            resultado.append((contacto, url))
        except Exception:  # noqa: BLE001
            logger.exception("No se pudo crear el enlace de revisión para %s", contacto)
    return resultado


def notificar_responsable_rechazo(evidencia, movimiento):
    """
    Le avisa al responsable del area que la evidencia fue rechazada.

    El motivo es lo importante: sin el, el responsable no sabe que corregir y
    vuelve a subir la misma foto. Por eso el endpoint de revision exige el
    motivo antes de rechazar.

    A diferencia de la subida, aca no hay un link de reintento: el responsable
    ya tiene el enlace de su area, que sigue siendo el mismo. Solo se le dice
    que resubita.

    Nunca levanta excepcion: si el gateway esta caido, el rechazo ya quedo
    registrado y el administrador lo ve en la bandeja igual.
    """
    from utiles.notificaciones import WhatsAppClient, WhatsAppError

    try:
        from usuarios.models import AreasProfile

        numeros = sorted(set(
            AreasProfile.objects.filter(
                area_id=movimiento.area_id,
                area__cliente_id=movimiento.cliente_id,
            ).exclude(telefono_whatsapp="")
            .values_list("telefono_whatsapp", flat=True)
        ))
    except Exception:  # noqa: BLE001
        numeros = []

    if not numeros:
        return {"ok": False, "detalle": "el área no tiene teléfono de responsable cargado"}

    cliente = WhatsAppClient()
    if not cliente.habilitado:
        return {"ok": False, "detalle": "WhatsApp deshabilitado o sin API key"}

    vencimiento = (
        movimiento.fecha_cumplimiento.strftime("%d/%m/%Y")
        if movimiento.fecha_cumplimiento else "sin fecha"
    )

    lineas = [
        "*AN & Asociados | Evidencia rechazada*",
        "",
        f"Hallazgo: {_descripcion_breve(movimiento.hallazgo or '', 120)}",
        f"Vencia: {vencimiento}",
        "",
        f"Motivo: {evidencia.motivo_rechazo}",
        "",
        "El hallazgo sigue pendiente. Volvé al enlace que te enviamos y subí la foto de nuevo.",
    ]

    enviados, errores = [], []
    for numero in numeros:
        try:
            cliente.enviar_texto(
                numero,
                "\n".join(lineas),
                external_ref=f"an:rechazo:{evidencia.pk}",
            )
            enviados.append(numero)
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
