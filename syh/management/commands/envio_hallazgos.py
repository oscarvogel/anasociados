import logging
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.core.mail import EmailMessage

from core_an import settings
from syh.models import Movimientos


class Command(BaseCommand):
    help = 'Envia los hallazgos de los movimientos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--preview',
            action='store_true',
            help='Genera el HTML sin enviar correos',
        )
        parser.add_argument(
            '--test-email',
            type=str,
            help='Envía todos los correos solo a este email de prueba en lugar de los destinatarios reales',
        )

    def handle(self, *args, **kwargs):
        preview_mode = kwargs.get('preview', False)
        test_email = kwargs.get('test_email', None)
        
        # Configurar el registro 
        logging.basicConfig(filename='log_tarea.log', level=logging.INFO, format='%(asctime)s:%(levelname)s:%(message)s')
        
        if preview_mode:
            logging.info('Iniciando generación de HTML en modo PREVIEW (sin envío)')
            self.stdout.write(self.style.WARNING('Modo PREVIEW - No se enviarán correos'))
        elif test_email:
            logging.info(f'Iniciando envío de correos en modo TEST a {test_email}')
            self.stdout.write(self.style.WARNING(f'Modo TEST - Todos los correos se enviarán a: {test_email}'))
        else:
            logging.info('Iniciando el envío de correos')

        clientes_movimientos = {}

        # Agrupar movimientos por cliente
        movimientos = Movimientos.objects.filter(estado__in=['Incumplido', 'Gestión en Curso']).order_by('cliente', 'area', 'fecha_cumplimiento')
        
        # Verificar si hay movimientos
        if not movimientos.exists():
            mensaje = 'No hay hallazgos incumplidos o en gestión. ¡Todo en orden!'
            self.stdout.write(self.style.SUCCESS(mensaje))
            logging.info(mensaje)
            return
        
        total_movimientos = movimientos.count()
        self.stdout.write(self.style.SUCCESS(f'Se encontraron {total_movimientos} hallazgos pendientes'))
        logging.info(f'Se encontraron {total_movimientos} hallazgos pendientes')
        
        for movimiento in movimientos:
            clave = f'{movimiento.cliente}{movimiento.area}'
            if clave not in clientes_movimientos:
                clientes_movimientos[clave] = []
            clientes_movimientos[clave].append(movimiento)

        # Enviar un correo por cliente (o generar preview)
        contador = 0
        for cliente, movimientos in clientes_movimientos.items():
            contador += 1
            subject = f"Movimientos Pendientes {movimiento.cliente.nombre} - {movimiento.area.detalle}"
            mensaje_html = render_to_string('pages/syh/hallazgos_incumplidos.html', {
                'hallazgos_incumplidos': movimientos,
                'current_date': datetime.now().strftime('%d/%m/%Y')
            })
            
            # Preparar lista de destinatarios principales
            if test_email:
                # Modo TEST: enviar solo al email de prueba
                to_emails = [test_email]
                cc_emails = []
            else:
                # Modo NORMAL: usar destinatarios reales
                to_emails = ['oscarvogel@gmail.com']
                if movimiento.area.email:
                    # Si hay múltiples emails separados por coma, dividirlos
                    area_emails = [email.strip() for email in movimiento.area.email.split(',') if email.strip()]
                    to_emails.extend(area_emails)
                
                # Preparar lista de CC
                cc_emails = []
                if movimiento.cliente.email:
                    # Si hay múltiples emails separados por coma, dividirlos
                    cliente_emails = [email.strip() for email in movimiento.cliente.email.split(',') if email.strip()]
                    cc_emails.extend(cliente_emails)
            
            if preview_mode:
                # Guardar el HTML en un archivo
                filename = f'preview_hallazgos_{movimiento.cliente.nombre.replace(" ", "_")}_{movimiento.area.detalle.replace(" ", "_")}_{contador}.html'
                filepath = os.path.join(settings.BASE_DIR, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(mensaje_html)
                self.stdout.write(self.style.SUCCESS(f'HTML generado: {filepath}'))
                logging.info(f'HTML generado: {filepath}')
                self.stdout.write(f'  Para: {", ".join(to_emails)}')
                self.stdout.write(f'  CC: {", ".join(cc_emails) if cc_emails else "sin CC"}')
            else:
                # Enviar el correo
                email = EmailMessage(
                    subject,
                    mensaje_html,
                    settings.EMAIL_HOST_USER,
                    to_emails,
                    cc=cc_emails if cc_emails else None
                )
                email.content_subtype = "html"
                email.send()
                
                if test_email:
                    logging.info(f'[MODO TEST] Correo enviado a {test_email} (destinatarios reales serían: {", ".join(to_emails)})')
                    self.stdout.write(self.style.SUCCESS(f'Correo {contador} enviado a {test_email} [{movimiento.cliente.nombre} - {movimiento.area.detalle}]'))
                else:
                    logging.info(f'Correo enviado a {", ".join(to_emails)} con copia a {", ".join(cc_emails) if cc_emails else "sin CC"}')
                    self.stdout.write(self.style.SUCCESS(f'Correo {contador} enviado a {movimiento.cliente.nombre} - {movimiento.area.detalle}'))
        
        if preview_mode:
            self.stdout.write(self.style.SUCCESS(f'\n✓ {contador} archivos HTML generados en modo PREVIEW'))
            logging.info(f'{contador} archivos HTML generados en modo PREVIEW')
        else:
            self.stdout.write(self.style.SUCCESS(f'\n✓ {contador} correos enviados'))
            logging.info('Todos los correos han sido enviados')

            # Enviar el log por correo
            with open('log_tarea.log', 'r') as log_file:
                log_content = log_file.read()
            
            email_log = EmailMessage(
                'Log de Tarea',
                log_content,
                settings.EMAIL_HOST_USER,
                ['oscarvogel@gmail.com']
            )
            email_log.send()
            logging.info('Log de la tarea enviado por correo')
        
# crontab -e
# 0 0 * * * /path/to/your/virtualenv/bin/python /path/to/your/project/manage.py update_movimientos
