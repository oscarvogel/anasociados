import logging
import os
from datetime import datetime
from collections import defaultdict
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
        parser.add_argument(
            '--list-emails',
            action='store_true',
            help='Muestra a qué emails (TO y CC) se enviarían los correos sin enviarlos',
        )
        parser.add_argument(
            '--send-list-to',
            type=str,
            help='Enviar el listado de emails a estas direcciones (separadas por coma) cuando se use --list-emails',
        )

    def handle(self, *args, **kwargs):
        preview_mode = kwargs.get('preview', False)
        test_email = kwargs.get('test_email', None)
        list_emails = kwargs.get('list_emails', False)
        send_list_to = kwargs.get('send_list_to', None)
        
        # Configurar el registro (ruta absoluta en BASE_DIR para ejecutarlo desde cron)
        log_path = os.path.join(settings.BASE_DIR, 'log_tarea.log')
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        logging.basicConfig(filename=log_path, level=logging.INFO, format='%(asctime)s:%(levelname)s:%(message)s')
        
        if preview_mode:
            logging.info('Iniciando generación de HTML en modo PREVIEW (sin envío)')
            self.stdout.write(self.style.WARNING('Modo PREVIEW - No se enviarán correos'))
        elif test_email:
            logging.info(f'Iniciando envío de correos en modo TEST a {test_email}')
            self.stdout.write(self.style.WARNING(f'Modo TEST - Todos los correos se enviarán a: {test_email}'))
        elif list_emails:
            logging.info('Iniciando modo LIST-EMAILS - solo se mostrarán destinatarios')
            self.stdout.write(self.style.WARNING('Modo LIST-EMAILS - No se enviarán correos, solo se mostrarán destinatarios'))
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
        unique_recipients = defaultdict(set)
        unique_cc = defaultdict(set)
        for cliente, movimientos in clientes_movimientos.items():
            contador += 1
            first_mov = movimientos[0]
            subject = f"Movimientos Pendientes {first_mov.cliente.nombre} - {first_mov.area.detalle}"
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
                if first_mov.area.email:
                    # Si hay múltiples emails separados por coma, dividirlos
                    area_emails = [email.strip() for email in first_mov.area.email.split(',') if email.strip()]
                    to_emails.extend(area_emails)
                
                # Preparar lista de CC
                cc_emails = []
                if first_mov.cliente.email:
                    # Si hay múltiples emails separados por coma, dividirlos
                    cliente_emails = [email.strip() for email in first_mov.cliente.email.split(',') if email.strip()]
                    cc_emails.extend(cliente_emails)
            # Si estamos en modo list_emails, mostrar destinatarios y recolectar únicos
            if list_emails:
                self.stdout.write(self.style.SUCCESS(f'[{contador}] {first_mov.cliente.nombre} - {first_mov.area.detalle}'))
                self.stdout.write(f'  To: {", ".join(to_emails)}')
                self.stdout.write(f'  CC: {", ".join(cc_emails) if cc_emails else "sin CC"}')
                logging.info(f'Lista de emails para {movimiento.cliente.nombre} - To: {to_emails} CC: {cc_emails}')
                # Asociar cada email con el cliente/area correspondiente
                tag = f"{first_mov.cliente.nombre} - {first_mov.area.detalle if getattr(first_mov, 'area', None) else 'sin area'}"
                for e in to_emails:
                    unique_recipients[e].add(tag)
                for e in cc_emails:
                    unique_cc[e].add(tag)
                continue
                continue
            
            if preview_mode:
                # Guardar el HTML en un archivo
                filename = f'preview_hallazgos_{first_mov.cliente.nombre.replace(" ", "_")}_{first_mov.area.detalle.replace(" ", "_")}_{contador}.html'
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
                    self.stdout.write(self.style.SUCCESS(f'Correo {contador} enviado a {test_email} [{first_mov.cliente.nombre} - {first_mov.area.detalle}]'))
                else:
                    logging.info(f'Correo enviado a {", ".join(to_emails)} con copia a {", ".join(cc_emails) if cc_emails else "sin CC"}')
                    self.stdout.write(self.style.SUCCESS(f'Correo {contador} enviado a {first_mov.cliente.nombre} - {first_mov.area.detalle}'))
        
        if preview_mode:
            self.stdout.write(self.style.SUCCESS(f'\n✓ {contador} archivos HTML generados en modo PREVIEW'))
            logging.info(f'{contador} archivos HTML generados en modo PREVIEW')
        elif list_emails:
            self.stdout.write(self.style.SUCCESS(f'\n✓ {contador} clientes procesados (modo LIST-EMAILS)'))
            self.stdout.write(self.style.SUCCESS(f'Emails únicos TO: {len(unique_recipients)}'))
            for e in sorted(unique_recipients):
                tags = ', '.join(sorted(unique_recipients[e]))
                self.stdout.write(f'  {e}: {tags}')
            self.stdout.write(self.style.SUCCESS(f'Emails únicos CC: {len(unique_cc)}'))
            if unique_cc:
                for e in sorted(unique_cc):
                    tags = ', '.join(sorted(unique_cc[e]))
                    self.stdout.write(f'  {e}: {tags}')
            else:
                self.stdout.write('  sin CC')
            logging.info('Modo LIST-EMAILS finalizado')

            # Si se pidió enviar el listado por correo, prepararlo y enviarlo
            if send_list_to:
                recipients = [e.strip() for e in send_list_to.split(',') if e.strip()]
                body_lines = [f'Listado de destinatarios TO ({len(unique_recipients)}):', '']
                for e in sorted(unique_recipients):
                    tags = ', '.join(sorted(unique_recipients[e]))
                    body_lines.append(f'{e}: {tags}')
                body_lines.append('')
                body_lines.append(f'Listado de destinatarios CC ({len(unique_cc)}):')
                body_lines.append('')
                if unique_cc:
                    for e in sorted(unique_cc):
                        tags = ', '.join(sorted(unique_cc[e]))
                        body_lines.append(f'{e}: {tags}')
                else:
                    body_lines.append('sin CC')
                body = '\n'.join(body_lines)

                email_list = EmailMessage(
                    'Listado de destinatarios - Hallazgos',
                    body,
                    settings.EMAIL_HOST_USER,
                    recipients
                )
                try:
                    email_list.send()
                    logging.info(f'Listado de emails enviado a: {recipients}')
                    self.stdout.write(self.style.SUCCESS(f'Listado enviado a: {", ".join(recipients)}'))
                except Exception as e:
                    logging.exception('Error enviando listado de emails')
                    self.stdout.write(self.style.ERROR(f'Error enviando listado: {e}'))

            return
        else:
            self.stdout.write(self.style.SUCCESS(f'\n✓ {contador} correos enviados'))
            logging.info('Todos los correos han sido enviados')

            # Enviar el log por correo
            with open(log_path, 'r') as log_file:
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
