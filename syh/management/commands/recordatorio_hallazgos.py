import logging
import os
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.utils import timezone

from core_an import settings
from syh.models import Movimientos


class Command(BaseCommand):
    help = 'Envía recordatorios de hallazgos próximos a vencer (5 días antes) e incumplidos'

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
            '--dias',
            type=int,
            default=5,
            help='Días de anticipación para el recordatorio (default: 5)',
        )

    def handle(self, *args, **kwargs):
        preview_mode = kwargs.get('preview', False)
        test_email = kwargs.get('test_email', None)
        dias_anticipacion = kwargs.get('dias', 5)
        
        # Configurar el registro 
        logging.basicConfig(filename='log_recordatorio.log', level=logging.INFO, format='%(asctime)s:%(levelname)s:%(message)s')
        
        if preview_mode:
            logging.info('Iniciando generación de HTML en modo PREVIEW (sin envío)')
            self.stdout.write(self.style.WARNING('Modo PREVIEW - No se enviarán correos'))
        elif test_email:
            logging.info(f'Iniciando envío de recordatorios en modo TEST a {test_email}')
            self.stdout.write(self.style.WARNING(f'Modo TEST - Todos los correos se enviarán a: {test_email}'))
        else:
            logging.info('Iniciando el envío de recordatorios')

        # Calcular fecha límite para recordatorio
        fecha_limite = timezone.now().date() + timedelta(days=dias_anticipacion)
        fecha_hoy = timezone.now().date()
        
        self.stdout.write(f'Buscando hallazgos que vencen el {fecha_limite.strftime("%d/%m/%Y")} (dentro de {dias_anticipacion} días)')

        clientes_movimientos = {}

        # Obtener hallazgos próximos a vencer (exactamente en X días)
        movimientos_proximos = Movimientos.objects.filter(
            estado__in=['Gestión en Curso'],
            fecha_cumplimiento=fecha_limite
        ).order_by('cliente', 'area', 'fecha_cumplimiento')
        
        # Obtener hallazgos ya incumplidos
        movimientos_incumplidos = Movimientos.objects.filter(
            estado='Incumplido',
            fecha_cumplimiento__lt=fecha_hoy
        ).order_by('cliente', 'area', 'fecha_cumplimiento')

        # Combinar ambos querysets
        total_proximos = movimientos_proximos.count()
        total_incumplidos = movimientos_incumplidos.count()
        
        if total_proximos == 0 and total_incumplidos == 0:
            mensaje = f'No hay hallazgos próximos a vencer en {dias_anticipacion} días ni incumplidos. ¡Todo en orden!'
            self.stdout.write(self.style.SUCCESS(mensaje))
            logging.info(mensaje)
            return
        
        self.stdout.write(self.style.SUCCESS(f'Se encontraron {total_proximos} hallazgos próximos a vencer'))
        self.stdout.write(self.style.WARNING(f'Se encontraron {total_incumplidos} hallazgos incumplidos'))
        logging.info(f'Hallazgos próximos a vencer: {total_proximos}')
        logging.info(f'Hallazgos incumplidos: {total_incumplidos}')
        
        # Agrupar movimientos por cliente y área
        for movimiento in movimientos_proximos:
            clave = f'{movimiento.cliente}{movimiento.area}'
            if clave not in clientes_movimientos:
                clientes_movimientos[clave] = {'proximos': [], 'incumplidos': []}
            clientes_movimientos[clave]['proximos'].append(movimiento)
        
        for movimiento in movimientos_incumplidos:
            clave = f'{movimiento.cliente}{movimiento.area}'
            if clave not in clientes_movimientos:
                clientes_movimientos[clave] = {'proximos': [], 'incumplidos': []}
            clientes_movimientos[clave]['incumplidos'].append(movimiento)

        # Enviar un correo por cliente/área
        contador = 0
        for clave, datos in clientes_movimientos.items():
            # Obtener referencia al primer movimiento para datos del cliente/área
            movimiento_ref = datos['proximos'][0] if datos['proximos'] else datos['incumplidos'][0]
            
            contador += 1
            subject = f"Recordatorio: Hallazgos Pendientes - {movimiento_ref.cliente.nombre} - {movimiento_ref.area.detalle}"
            
            mensaje_html = render_to_string('pages/syh/recordatorio_hallazgos.html', {
                'hallazgos_proximos': datos['proximos'],
                'hallazgos_incumplidos': datos['incumplidos'],
                'cliente': movimiento_ref.cliente.nombre,
                'area': movimiento_ref.area.detalle,
                'dias_anticipacion': dias_anticipacion,
                'fecha_vencimiento': fecha_limite.strftime('%d/%m/%Y'),
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
                if movimiento_ref.area.email:
                    # Si hay múltiples emails separados por coma, dividirlos
                    area_emails = [email.strip() for email in movimiento_ref.area.email.split(',') if email.strip()]
                    to_emails.extend(area_emails)
                
                # Preparar lista de CC
                cc_emails = []
                if movimiento_ref.cliente.email:
                    # Si hay múltiples emails separados por coma, dividirlos
                    cliente_emails = [email.strip() for email in movimiento_ref.cliente.email.split(',') if email.strip()]
                    cc_emails.extend(cliente_emails)
            
            if preview_mode:
                # Guardar el HTML en un archivo
                filename = f'preview_recordatorio_{movimiento_ref.cliente.nombre.replace(" ", "_")}_{movimiento_ref.area.detalle.replace(" ", "_")}_{contador}.html'
                filepath = os.path.join(settings.BASE_DIR, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(mensaje_html)
                self.stdout.write(self.style.SUCCESS(f'HTML generado: {filepath}'))
                logging.info(f'HTML generado: {filepath}')
                self.stdout.write(f'  Próximos a vencer: {len(datos["proximos"])}')
                self.stdout.write(f'  Incumplidos: {len(datos["incumplidos"])}')
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
                    logging.info(f'[MODO TEST] Recordatorio enviado a {test_email} - Próximos: {len(datos["proximos"])}, Incumplidos: {len(datos["incumplidos"])}')
                    self.stdout.write(self.style.SUCCESS(f'Recordatorio {contador} enviado a {test_email} [{movimiento_ref.cliente.nombre} - {movimiento_ref.area.detalle}]'))
                else:
                    logging.info(f'Recordatorio enviado a {", ".join(to_emails)} - Próximos: {len(datos["proximos"])}, Incumplidos: {len(datos["incumplidos"])}')
                    self.stdout.write(self.style.SUCCESS(f'Recordatorio {contador} enviado a {movimiento_ref.cliente.nombre} - {movimiento_ref.area.detalle}'))
        
        if preview_mode:
            self.stdout.write(self.style.SUCCESS(f'\n✓ {contador} archivos HTML generados en modo PREVIEW'))
            logging.info(f'{contador} archivos HTML generados en modo PREVIEW')
        else:
            self.stdout.write(self.style.SUCCESS(f'\n✓ {contador} recordatorios enviados'))
            logging.info('Todos los recordatorios han sido enviados')

            # Enviar el log por correo
            with open('log_recordatorio.log', 'r') as log_file:
                log_content = log_file.read()
            
            email_log = EmailMessage(
                'Log de Recordatorios',
                log_content,
                settings.EMAIL_HOST_USER,
                ['oscarvogel@gmail.com']
            )
            email_log.send()
            logging.info('Log de recordatorios enviado por correo')
        
# crontab -e
# Ejecutar todos los días a las 8:00 AM para enviar recordatorios de hallazgos que vencen en 5 días
# 0 8 * * * /path/to/your/virtualenv/bin/python /path/to/your/project/manage.py recordatorio_hallazgos
