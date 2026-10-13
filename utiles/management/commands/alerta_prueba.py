"""
Prueba de envio de alertas por los dos canales (mail + WhatsApp).

Uso:

    # ver la configuracion y el estado del gateway, sin enviar nada
    manage.py alerta_prueba --ver-estado

    # mandar una alerta de prueba real
    manage.py alerta_prueba --mensaje "Este es un mensaje de prueba"

    # probar solo WhatsApp (util para ver si responde sin generar mail)
    manage.py alerta_prueba --solo-whatsapp
"""

import textwrap

from django.conf import settings
from django.core.management.base import BaseCommand

from utiles.notificaciones import WhatsAppClient, WhatsAppError, enviar_alerta


class Command(BaseCommand):
    help = "Manda una alerta de prueba por mail y por WhatsApp."

    def add_arguments(self, parser):
        parser.add_argument("--mensaje", default="Mensaje de prueba del sistema de alertas.")
        parser.add_argument("--asunto", default="AN & Asociados - alerta de prueba")
        parser.add_argument("--solo-whatsapp", action="store_true",
                            help="No mandar el mail, solo probar WhatsApp.")
        parser.add_argument("--sin-mail", action="store_true",
                            help="No mandar el mail, pero igual mostrar el estado.")
        parser.add_argument("--ver-estado", action="store_true",
                            help="Solo mostrar la configuracion y el estado del gateway.")

    def handle(self, *args, **opciones):
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Configuracion de alertas"))

        c = WhatsAppClient()
        self.stdout.write(f"  WHATSAPP_ENABLED       : {settings.WHATSAPP_ENABLED}")
        self.stdout.write(f"  WHATSAPP_API_URL       : {settings.WHATSAPP_API_URL}")
        self.stdout.write(f"  WHATSAPP_INSTANCE_ID   : {settings.WHATSAPP_INSTANCE_ID}")
        self.stdout.write(f"  API key configurada    : {'si' if settings.WHATSAPP_API_KEY else 'NO'}")
        self.stdout.write(f"  WhatsApp habilitado    : {'si' if c.habilitado else 'no'}")
        self.stdout.write(f"  Destinatarios WhatsApp : {settings.ALERTA_WHATSAPP_DESTINATARIOS or '(ninguno)'}")
        self.stdout.write(f"  Destinatarios mail     : {[a[1] for a in settings.ADMINS]}")
        self.stdout.write("")

        # Normalizacion de telefonos: aca se ven los errores de formato antes de enviar.
        numeros = [t.strip() for t in (settings.ALERTA_WHATSAPP_DESTINATARIOS or "").split(",") if t.strip()]
        if numeros:
            self.stdout.write("  Telefonos normalizados:")
            for n in numeros:
                try:
                    self.stdout.write(f"    {n:20} -> {c.normalizar_telefono(n)}")
                except WhatsAppError as e:
                    self.stdout.write(self.style.ERROR(f"    {n:20} -> ERROR: {e}"))
            self.stdout.write("")

        if opciones["ver_estado"]:
            if not c.habilitado:
                self.stdout.write(self.style.WARNING("  WhatsApp no esta habilitado: no se consulta nada."))
                return
            self.stdout.write("  Estado de la instancia en el gateway:")
            try:
                estado = c.estado_instancia()
                for k, v in estado.items():
                    self.stdout.write(f"    {k}: {v}")
            except WhatsAppError as e:
                self.stdout.write(self.style.ERROR(f"    ERROR consultando el gateway: {e}"))
            return

        if not c.habilitado:
            self.stdout.write(self.style.WARNING(
                "WhatsApp esta deshabilitado o sin API key: solo se mandaria el mail.\n"
                "  Poner en el .env:\n"
                "    WHATSAPP_ENABLED=True\n"
                "    WHATSAPP_API_KEY=<key de este sistema>\n"
                "    ALERTA_WHATSAPP_DESTINATARIOS=549xxxxxxxxxx"
            ))

        cuerpo = textwrap.dedent(f"""\
            Esta es una alerta de prueba del sistema de notificaciones.

            Sistema  : AN & Asociados
            Servidor : vps-3177145-x.dattaweb.com
            Hora     : {self.timestamp()}
            Origen   : comando 'manage.py alerta_prueba'

            Si estas leyendo esto y no lo pediste, se puede ignorar:
            no hay nada roto, es una prueba del canal.
        """)

        if opciones["sin_mail"] or opciones["solo_whatsapp"]:
            self.stdout.write("  (sin envio de mail por pedido explicito)")
            resultado = enviar_alerta(
                opciones["asunto"], cuerpo,
                destinatarios_email=[], solo_whatsapp=True,
            )
        else:
            resultado = enviar_alerta(opciones["asunto"], cuerpo)

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Resultado"))
        for canal in ("email", "whatsapp"):
            info = resultado[canal]
            marca = self.style.SUCCESS("OK  ") if info["ok"] else self.style.ERROR("FALL")
            self.stdout.write(f"  {marca} {canal:9} {info['detalle']}")
            for mid in info.get("message_ids", []):
                self.stdout.write(f"           messageId: {mid}")

        self.stdout.write("")
        if resultado["whatsapp"]["ok"]:
            self.stdout.write(self.style.SUCCESS("Prueba enviada."))
        else:
            self.stdout.write(self.style.WARNING(
                "WhatsApp no salio. El mail es el canal que garanteiza el aviso."
            ))

    def timestamp(self):
        from django.utils import timezone
        return timezone.localtime().strftime("%Y-%m-%d %H:%M:%S")