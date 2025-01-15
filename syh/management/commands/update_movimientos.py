from django.core.management.base import BaseCommand
from django.utils import timezone
from django.template.loader import render_to_string
from django.core.mail import EmailMessage

from core_an import settings
from syh.models import Movimientos


class Command(BaseCommand):
    help = 'Actualiza el estado de los movimientos y envía un correo electrónico con los hallazgos'

    def handle(self, *args, **kwargs):
        hoy = timezone.now().date()
        movimientos = Movimientos.objects.filter(
            estado='Gestión en Curso'
        )
        hallazgos_incumplidos = []

        for movimiento in movimientos:
            fecha_limite = movimiento.fecha + timezone.timedelta(days=movimiento.plazo)
            if fecha_limite < hoy:
                movimiento.estado = 'Incumplido'
                movimiento.save()
                hallazgos_incumplidos.append(movimiento)

                
        if hallazgos_incumplidos:
            # Crear el cuerpo del correo en formato HTML
            # Renderizar el template HTML con los datos de los alumnos
            mensaje_html = render_to_string('pages/syh/hallazgos_incumplidos.html', {
                'hallazgos_incumplidos': hallazgos_incumplidos,
            })
            email = EmailMessage(
                'Hallazgos Incumplidos',
                mensaje_html,
                settings.EMAIL_HOST_USER,
                ['oscarvogel@gmail.com', 'almada_neri@hotmail.com'],  # Lista de destinatarios
            )
            email.content_subtype = "html"  # Esto es importante para que se interprete como HTML
            
            # Enviar el correo
            email.send()
            # send_mail(
            #     'Hallazgos Incumplidos',
            #     '',
            #     'sistemas@servinlgsm.com.ar',
            #     ['oscarvogel@gmail.com', 'almada_neri@hotmail.com'],
            #     fail_silently=False,
            #     html_message=email_body, 
            # )
        
        self.stdout.write(self.style.SUCCESS('Estados de movimientos actualizados y correos enviados'))

# crontab -e
# 0 0 * * * /path/to/your/virtualenv/bin/python /path/to/your/project/manage.py update_movimientos
