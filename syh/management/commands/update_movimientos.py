from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.utils import timezone
from django.db.models import F

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
            email_body = '''
            <html>
            <head>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-EVSTQN3/azprG1Anm3QDgpJLIm9Nao0Yz1ztcQTwFspd3yD65VohhpuuCOmLASjC" crossorigin="anonymous">
            </head>
            <body>
                <h2>Hallazgos Incumplidos</h2>
                <p>Los siguientes hallazgos han cambiado de estado a Incumplido:</p>
                <table class="table table-success table-striped">
                    <thead>
                        <tr>
                            <th>Cliente</th>
                            <th>Área</th>
                            <th>Hallazgo</th>
                            <th>Fecha de Cumplimiento</th>
                        </tr>
                    </thead>
                    <tbody>
            '''

            for movimiento in hallazgos_incumplidos:
                email_body += f'''
                        <tr>
                            <td>{movimiento.cliente.nombre}</td>
                            <td>{movimiento.area.detalle}</td>
                            <td>{movimiento.hallazgo}</td>
                            <td>{movimiento.fecha + timezone.timedelta(days=movimiento.plazo)}</td>
                        </tr>
                '''

            email_body += '''
                    </tbody>
                </table>
            </body>
            </html>
            '''

            send_mail(
                'Hallazgos Incumplidos',
                '',
                'sistemas@servinlgsm.com.ar',
                ['oscarvogel@gmail.com', 'almada_neri@hotmail.com'],
                fail_silently=False,
                html_message=email_body
            )
        
        self.stdout.write(self.style.SUCCESS('Estados de movimientos actualizados y correos enviados'))

# crontab -e
# 0 0 * * * /path/to/your/virtualenv/bin/python /path/to/your/project/manage.py update_movimientos
