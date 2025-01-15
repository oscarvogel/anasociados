import logging
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.core.mail import EmailMessage

from core_an import settings
from syh.models import Movimientos


class Command(BaseCommand):
    help = 'Envia los hallazgos de los movimientos'

    def handle(self, *args, **kwargs):
        # Configurar el registro 
        logging.basicConfig(filename='log_tarea.log', level=logging.INFO, format='%(asctime)s:%(levelname)s:%(message)s')
        logging.info('Iniciando el envío de correos')

        clientes_movimientos = {}

        # Agrupar movimientos por cliente
        movimientos = Movimientos.objects.filter(estado__in=['Incumplido', 'Gestión en Curso']).order_by('cliente', 'area', 'fecha_cumplimiento')
        for movimiento in movimientos:
            clave = f'{movimiento.cliente}{movimiento.area}'
            if clave not in clientes_movimientos:
                clientes_movimientos[clave] = []
            clientes_movimientos[clave].append(movimiento)

        # Enviar un correo por cliente
        for cliente, movimientos in clientes_movimientos.items():
            subject = f"Movimientos Pendientes {movimiento.cliente.nombre} - {movimiento.area.detalle}"
            mensaje_html = render_to_string('pages/syh/hallazgos_incumplidos.html', {
                'hallazgos_incumplidos': movimientos,
            })
            # html_message = render_to_string('movimientos_email.html', {'cliente': cliente, 'movimientos': movimientos})
            # plain_message = strip_tags(html_message)
            # from_email = 'tu_correo@example.com'
            # to = cliente.email  # Asumiendo que el modelo Cliente tiene un campo email
            if movimiento.area.email:
                to_email = movimiento.area.email
            else:
                to_email = ""
            if movimiento.cliente.email:
                cc_email = movimiento.cliente.email
            else:
                cc_email = ""
            
            email = EmailMessage(
                subject,
                mensaje_html,
                settings.EMAIL_HOST_USER,
                ['oscarvogel@gmail.com', to_email],  # Lista de destinatarios TODO-- enviar a clientes y por area
                cc=cc_email
            )
            email.content_subtype = "html"  # Esto es importante para que se interprete como HTML
            
            # Enviar el correo
            email.send()
            logging.info(f'Correo enviado a {to_email} con copia a {cc_email}')
        
        self.stdout.write(self.style.SUCCESS('Correos enviados'))
        logging.info('Todos los correos han sido enviados')

        # Enviar el log por correo
        with open('log_tarea.log', 'r') as log_file:
            log_content = log_file.read()
        
        email_log = EmailMessage(
            'Log de Tarea',
            log_content,
            settings.EMAIL_HOST_USER,
            ['oscarvogel@gmail.com']  # Lista de destinatarios del log
        )
        email_log.send()
        logging.info('Log de la tarea enviado por correo')
        
# crontab -e
# 0 0 * * * /path/to/your/virtualenv/bin/python /path/to/your/project/manage.py update_movimientos
