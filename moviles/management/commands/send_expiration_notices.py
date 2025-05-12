# your_app/management/commands/send_expiration_notices.py

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.core.mail import send_mail
from datetime import date, timedelta

from moviles.models import Matafuegos
# Asegúrate de importar tu modelo Matafuegos desde donde se encuentre
# Por ejemplo, si está en models.py de la misma app:

class Command(BaseCommand):
    help = 'Sends email notifications for fire extinguishers expiring in the next 30 days.'

    def handle(self, *args, **options):
        self.stdout.write("Iniciando el proceso de notificación de vencimientos de matafuegos...")

        # Calcular la fecha límite (hoy + 30 días)
        thirty_days_from_now = date.today() + timedelta(days=30)
        today = date.today()

        self.stdout.write(f"Buscando matafuegos que vencen entre {today.strftime('%d/%m/%Y')} y {thirty_days_from_now.strftime('%d/%m/%Y')}")

        try:
            # Consulta para encontrar matafuegos que vencen en los próximos 30 días
            # Excluimos los que están de baja
            expiring_extinguishers = Matafuegos.objects.filter(
                fecha_vencimiento__lte=thirty_days_from_now,
                fecha_vencimiento__gte=today,
                baja=False # Solo considerar los matafuegos activos
            ).select_related('cliente', 'area') # Optimización: cargar cliente y area en la misma consulta

            if not expiring_extinguishers:
                self.stdout.write("No se encontraron matafuegos que venzan en los próximos 30 días.")
                return # Salir si no hay nada que hacer

            self.stdout.write(f"Encontrados {expiring_extinguishers.count()} matafuegos próximos a vencer.")

            emails_sent_count = 0
            skipped_count = 0

            # Enviar correos electrónicos
            for extinguisher in expiring_extinguishers:
                recipient_email = extinguisher.mail_responsable

                if recipient_email:
                    # Asunto del correo
                    subject = f"Aviso de Vencimiento Próximo de Matafuegos - Código: {extinguisher.codigo_interno}"

                    # Cuerpo del correo
                    message = f"""
Estimado/a responsable,

Este correo es para informarle que el siguiente matafuegos bajo su responsabilidad está próximo a vencer:

Código Interno: {extinguisher.codigo_interno}
Cliente: {extinguisher.cliente.nombre if extinguisher.cliente else 'N/A'}
Área: {extinguisher.area.detalle if extinguisher.area else 'N/A'}
Ubicación: {extinguisher.ubicacion}
Fecha de Vencimiento: {extinguisher.fecha_vencimiento.strftime('%d/%m/%Y')}

Por favor, tome las medidas necesarias para su recarga o reemplazo antes de la fecha de vencimiento.

Saludos cordiales,

Sistema de Gestión
""" # Puedes personalizar más el mensaje según tus necesidades

                    try:
                        # Usar send_mail de Django
                        send_mail(
                            subject,
                            message,
                            settings.DEFAULT_FROM_EMAIL, # Remitente configurado en settings.py
                            [recipient_email],
                            fail_silently=False, # Esto hará que falle si hay un error en el envío
                        )
                        self.stdout.write(self.style.SUCCESS(f"Correo enviado con éxito para {extinguisher.codigo_interno} a {recipient_email}"))
                        emails_sent_count += 1
                    except Exception as e:
                        self.stderr.write(self.style.ERROR(f"Error al enviar correo para {extinguisher.codigo_interno} a {recipient_email}: {e}"))
                        # Aquí podrías añadir lógica para reintentar o loguear el error de forma más detallada

                else:
                    self.stdout.write(self.style.WARNING(f"Saltando {extinguisher.codigo_interno}: No tiene un correo de responsable definido."))
                    skipped_count += 1

            self.stdout.write("\n--- Resumen ---")
            self.stdout.write(f"Proceso finalizado.")
            self.stdout.write(f"Total de matafuegos próximos a vencer encontrados: {expiring_extinguishers.count()}")
            self.stdout.write(f"Correos intentados enviar: {emails_sent_count + skipped_count}")
            self.stdout.write(f"Correos enviados con éxito: {emails_sent_count}")
            self.stdout.write(f"Matafuegos saltados (sin email): {skipped_count}")
            self.stdout.write("----------------")

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Ocurrió un error inesperado durante la ejecución del comando: {e}"))
            # Puedes levantar un CommandError si quieres que el script falle ruidosamente en cron
            # raise CommandError(f'Execution failed: {e}')

