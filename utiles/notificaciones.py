"""
Canal de WhatsApp para las alertas del sistema, sobre Vogel WhatsApp API.

Contrato: https://github.com/oscarvogel/vogel_whatsapp_api (docs/INTEGRACION_SISTEMAS.md)

Principio de diseno importante:

    WhatsApp es un canal SECUNDARIO. Si esta caido, se rompe o no esta
    configurado, la alerta sigue saliendo por mail y el fallo queda
    registrado. Un sistema de alertas que depende de que todos sus canales
    funcionen no sirve para avisar justamente cuando algo se rompio.

Por eso este modulo nunca levanta la excepcion hacia el llamador: devuelve
un resultado y sigue. Los errores se registran, no se propagan.
"""

import logging
import re

import requests
from django.conf import settings
from django.core.mail import EmailMessage

logger = logging.getLogger(__name__)

SOURCE_APP = "an_asociados"


class WhatsAppError(Exception):
    """Error al hablar con el gateway de WhatsApp."""


class WhatsAppClient:
    """
    Cliente HTTP del gateway. Es sin estado: se instancia por envio.

    No loguea la API key en ningun camino.
    """

    def __init__(self, api_url=None, api_key=None, instance_id=None, timeout=None):
        self.api_url = (api_url or settings.WHATSAPP_API_URL or "").rstrip("/")
        self.api_key = api_key or settings.WHATSAPP_API_KEY or ""
        self.instance_id = instance_id or settings.WHATSAPP_INSTANCE_ID or "default"
        self.timeout = timeout or settings.WHATSAPP_API_TIMEOUT
        # sourceApp se manda en cada envio para que quede en la auditoria
        # del gateway de que sistema salio el mensaje.
        self.source_app = SOURCE_APP

    @property
    def habilitado(self):
        return bool(settings.WHATSAPP_ENABLED and self.api_key and self.api_url)

    @property
    def _headers(self):
        return {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        }

    def normalizar_telefono(self, telefono):
        """
        Deja solo digitos y quita el 0 inicial del prefijo local.

        Argentina: '+54 9 3764-00-0000' -> '5493764000000'
        El gateway exige internacional y solo digitos: sin +, sin espacios,
        sin guiones. Si se le pasa '5493764...' ya normalizado, no lo toca.
        """
        if telefono is None:
            raise WhatsAppError("telefono vacio")

        digitos = re.sub(r"\D", "", str(telefono))

        if digitos.startswith("54"):
            pais = digitos[:2]
            resto = digitos[2:]
            # 54911... es movil con 9; 5411... es fijo
            return pais + resto

        if digitos.startswith("0"):
            digitos = digitos.lstrip("0")

        raise WhatsAppError(
            f"telefono '{telefono}' no parece internacional. "
            "Hace falta codigo de pais (ej: 5493764000000)."
        )

    def enviar_texto(self, telefono, mensaje, external_ref=None, actor=None):
        """
        POST /api/v1/instances/:instanceId/messages

        Devuelve el dict de la API. Levanta WhatsAppError si algo sale mal.
        """
        if not self.habilitado:
            raise WhatsAppError("WhatsApp deshabilitado o sin configurar")

        phone = self.normalizar_telefono(telefono)
        url = f"{self.api_url}/api/v1/instances/{self.instance_id}/messages"

        payload = {
            "phone": phone,
            "message": mensaje,
            "sourceApp": self.source_app,
        }
        if external_ref:
            payload["externalRef"] = external_ref
        if actor:
            payload["actorName"] = actor

        try:
            r = requests.post(url, headers=self._headers, json=payload, timeout=self.timeout)
        except requests.RequestException as e:
            raise WhatsAppError(f"no se pudo conectar al gateway: {e}") from e

        if r.status_code not in (200, 202):
            # El cuerpo puede traer detalle del error; no incluimos la key.
            raise WhatsAppError(
                f"HTTP {r.status_code} al enviar a {phone}: {r.text[:300]}"
            )

        try:
            data = r.json()
        except ValueError as e:
            raise WhatsAppError("el gateway devolvio una respuesta ilegible") from e

        if not data.get("success"):
            raise WhatsAppError(f"el gateway no acepto el mensaje: {data}")

        return data.get("data", {})

    def estado_mensaje(self, message_id):
        """GET /api/v1/instances/:instanceId/messages/:messageId"""
        url = f"{self.api_url}/api/v1/instances/{self.instance_id}/messages/{message_id}"
        try:
            r = requests.get(url, headers=self._headers, timeout=self.timeout)
        except requests.RequestException as e:
            raise WhatsAppError(f"no se pudo consultar el estado: {e}") from e
        if r.status_code != 200:
            raise WhatsAppError(f"HTTP {r.status_code} al consultar {message_id}")
        return r.json().get("data", {})

    def estado_instancia(self):
        """GET /api/v1/instances/:instanceId/status"""
        url = f"{self.api_url}/api/v1/instances/{self.instance_id}/status"
        try:
            r = requests.get(url, headers=self._headers, timeout=self.timeout)
        except requests.RequestException as e:
            raise WhatsAppError(f"no se pudo consultar la instancia: {e}") from e
        if r.status_code != 200:
            raise WhatsAppError(f"HTTP {r.status_code} al consultar la instancia")
        return r.json().get("data", {})


def _destinatarios_whatsapp():
    """Lista de numeros configurados para las alertas."""
    crudo = settings.ALERTA_WHATSAPP_DESTINATARIOS or ""
    return [t.strip() for t in crudo.split(",") if t.strip()]


def _cuerpo_whatsapp(asunto, cuerpo):
    """
    Arma el texto de WhatsApp. Sin HTML: el gateway manda texto plano y los
    caracteres de formato se verian tal cual.
    """
    lineas = [f"*{asunto}*", ""]
    lineas.append(str(cuerpo).strip())
    lineas.append("")
    lineas.append(f"— {settings.SITE_NOMBRE if hasattr(settings, 'SITE_NOMBRE') else 'AN & Asociados'}")
    return "\n".join(lineas)


def enviar_alerta(asunto, cuerpo, destinatarios_email=None, solo_whatsapp=False):
    """
    Manda la alerta por los dos canales y devuelve que paso en cada uno.

    Devuelve un dict:
        {
          "email":    {"ok": bool, "detalle": str},
          "whatsapp": {"ok": bool, "detalle": str, "message_ids": [...]},
        }

    Nunca levanta excepcion: el proposito de una alerta es que se use cuando
    algo ya fallo, y en ese momento no puede ser ella misma una fuente de
    errores.
    """
    resultado = {"email": {"ok": False, "detalle": "omitido"},
                 "whatsapp": {"ok": False, "detalle": "omitido", "message_ids": []}}

    # --- Canal 1: mail ---------------------------------------------------
    if not solo_whatsapp:
        try:
            destinos = destinatarios_email or [a[1] for a in settings.ADMINS]
            if not destinos:
                resultado["email"]["detalle"] = "sin destinatarios"
            else:
                EmailMessage(
                    asunto,
                    str(cuerpo),
                    settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER,
                    destinos,
                ).send(fail_silently=False)
                resultado["email"] = {"ok": True, "detalle": f"enviado a {len(destinos)}"}
        except Exception as e:
            logger.exception("Fallo el envio de la alerta por mail")
            resultado["email"] = {"ok": False, "detalle": str(e)[:300]}

    # --- Canal 2: WhatsApp ------------------------------------------------
    try:
        numeros = _destinatarios_whatsapp()
        if not numeros:
            resultado["whatsapp"]["detalle"] = "sin numeros configurados"
        else:
            cliente = WhatsAppClient()
            if not cliente.habilitado:
                resultado["whatsapp"]["detalle"] = "WhatsApp deshabilitado o sin API key"
            else:
                texto = _cuerpo_whatsapp(asunto, cuerpo)
                errores, enviados = [], []
                for n in numeros:
                    try:
                        data = cliente.enviar_texto(
                            n, texto, external_ref=f"an:alerta:{asunto[:40]}"
                        )
                        enviados.append(data.get("messageId"))
                    except Exception as e:
                        errores.append(f"{n}: {e}")
                resultado["whatsapp"] = {
                    "ok": not errores,
                    "detalle": (
                        f"enviado a {len(enviados)}" if not errores
                        else f"{len(enviados)} ok, {len(errores)} con error"
                    ),
                    "message_ids": enviados,
                }
                if errores:
                    logger.warning("Fallos parciales de WhatsApp: %s", "; ".join(errores))
    except Exception as e:
        logger.exception("Fallo el envio de la alerta por WhatsApp")
        resultado["whatsapp"] = {"ok": False, "detalle": str(e)[:300], "message_ids": []}

    return resultado