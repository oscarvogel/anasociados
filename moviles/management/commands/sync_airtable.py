from django.core.management.base import BaseCommand
import subprocess
import os
import sys


class Command(BaseCommand):
    help = 'Sincroniza registros de Airtable a MySQL'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mysql',
            action='store_true',
            help='Realiza inserciones/actualizaciones en MySQL pero no borra los registros en Airtable.',
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Si se especifica, permite realizar las escrituras en la base de datos y borrar registros en Airtable.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Si se especifica, recupera e imprime los registros sin modificar la base de datos.',
        )

    def handle(self, *args, **options):
        # Ruta al script de sincronización
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        script_path = os.path.join(base_dir, 'utiles', 'sync_airtable_to_mysql.py')
        script_path = os.path.abspath(script_path)

        if not os.path.exists(script_path):
            self.stdout.write(self.style.ERROR(f'Script no encontrado: {script_path}'))
            raise SystemExit(1)

        # Usar el mismo intérprete de Python que está ejecutando Django
        cmd = [sys.executable, script_path]
        
        if options['mysql']:
            cmd.append('--mysql')
        if options['confirm']:
            cmd.append('--confirm')
        if options['dry_run']:
            cmd.append('--dry-run')

        self.stdout.write(self.style.WARNING(f'Ejecutando: {" ".join(cmd)}'))
        self.stdout.write(self.style.WARNING(f'Python: {sys.executable}'))
        self.stdout.write(self.style.WARNING(f'Script: {script_path}'))

        try:
            # Ejecutar el script con el entorno actual
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=True,
                cwd=base_dir,  # Ejecutar desde el directorio base de Django
                env=os.environ.copy()  # Usar las mismas variables de entorno
            )
            
            self.stdout.write(self.style.SUCCESS('✅ Sincronización completada exitosamente'))
            
            # Mostrar salida
            if result.stdout:
                self.stdout.write('\n--- SALIDA DEL SCRIPT ---')
                self.stdout.write(result.stdout)
            if result.stderr:
                self.stdout.write('\n--- ADVERTENCIAS ---')
                self.stdout.write(self.style.WARNING(result.stderr))
                
            return result.stdout
            
        except subprocess.CalledProcessError as e:
            self.stdout.write(self.style.ERROR(f'❌ Error durante la sincronización (código {e.returncode})'))
            if e.stdout:
                self.stdout.write('\n--- SALIDA ---')
                self.stdout.write(e.stdout)
            if e.stderr:
                self.stdout.write('\n--- ERROR ---')
                self.stdout.write(self.style.ERROR(e.stderr))
            raise
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error inesperado: {str(e)}'))
            raise
