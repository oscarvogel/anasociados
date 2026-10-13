"""
Backup de la base de datos de produccion.

Se usa desde cron:

    /var/www/venv_an/bin/python /var/www/an/manage.py backup_base

Las credenciales NO estan escritas en el comando: se leen de
settings.DATABASES, que a su vez las saca del .env. Asi el unico lugar donde
cambian es el .env y el backup nunca queda con una copia desactualizada de la
password.

El dump se comprime y se rotan los backups viejos segun --conservar (dias).

Como verificar que un backup sirve, sin tocar la base real:

    gunzip -c /var/backups/an/an-AAAAMMDD-HHMMSS.sql.gz > /tmp/r.sql
    mysql -h HOST -u USER -p PASSWORD prueba_restore < /tmp/r.sql
    mysql -h HOST -u USER -p -e "SELECT COUNT(*) FROM prueba_restore.movimientos;"
    mysql -h HOST -u USER -p -e "DROP DATABASE prueba_restore;"
"""
import gzip
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Backup comprimido de la base MySQL, con rotacion de archivos viejos."

    def add_arguments(self, parser):
        parser.add_argument(
            "--destino",
            default="/var/backups/an",
            help="Directorio donde se dejan los backups (default: /var/backups/an)",
        )
        parser.add_argument(
            "--conservar",
            type=int,
            default=14,
            help="Cuantos dias de backups conservar (default: 14)",
        )
        parser.add_argument(
            "--etiqueta",
            default="",
            help="Texto para sumar al nombre del archivo, ej: 'antes-upgrade'",
        )
        parser.add_argument(
            "--mysql-dump",
            default="mysqldump",
            help="Ruta o nombre del binario mysqldump (default: mysqldump)",
        )

    def handle(self, *args, **opciones):
        destino = opciones["destino"]
        conservar = opciones["conservar"]
        etiqueta = opciones["etiqueta"]
        mysql_dump = opciones["mysql_dump"]

        db = settings.DATABASES["default"]

        if "mysql" not in db["ENGINE"]:
            raise CommandError(
                f"Este comando solo funciona con MySQL; el ENGINE actual es {db['ENGINE']}"
            )

        if not shutil.which(mysql_dump):
            raise CommandError(f"No se encontro '{mysql_dump}' en el PATH")

        os.makedirs(destino, mode=0o700, exist_ok=True)

        ahora = datetime.now()
        sufijo = f"-{etiqueta}" if etiqueta else ""
        nombre = f"an-{ahora:%Y%m%d-%H%M%S}{sufijo}.sql.gz"
        destino_final = os.path.join(destino, nombre)
        crudo = destino_final[:-3]  # sin .gz

        # Archivo temporal con las credenciales: 600 y se borra siempre.
        # Se usa --defaults-extra-file para que la password no aparezca en la
        # linea de comandos (quedaria visible en 'ps' para cualquier usuario).
        cred = tempfile.NamedTemporaryFile(
            mode="w", suffix=".cnf", prefix="dump-", delete=False
        )
        try:
            cred.write("[client]\n")
            cred.write(f"host={db['HOST']}\n")
            cred.write(f"port={db['PORT'] or 3306}\n")
            cred.write(f"user={db['USER']}\n")
            cred.write(f"password={db['PASSWORD']}\n")
            cred.flush()
            cred.close()
            os.chmod(cred.name, 0o600)

            comando = [
                mysql_dump,
                f"--defaults-extra-file={cred.name}",
                "--single-transaction",
                "--routines",
                "--triggers",
                "--no-tablespaces",
                db["NAME"],
            ]

            self.stdout.write(f"Respaldando '{db['NAME']}' en {db['HOST']}...")
            with open(crudo, "wb") as fh:
                proc = subprocess.run(
                    comando, stdout=fh, stderr=subprocess.PIPE, timeout=1800
                )

            if proc.returncode != 0:
                if os.path.exists(crudo):
                    os.remove(crudo)
                error = proc.stderr.decode("utf-8", "replace").strip()
                raise CommandError(f"mysqldump fallo (exit {proc.returncode}):\n{error}")

            # Un dump vacio o sin tablas no sirve de nada: se descarta.
            # Ojo: hay que contar TODAS las lineas CREATE TABLE. mysqldump
            # intercala la definicion de cada tabla con sus indices y sus
            # datos, asi que cortar en la primera linea que no sea CREATE
            # TABLE contaba 1 sola.
            tablas = 0
            with open(crudo, "r", encoding="utf-8", errors="replace") as fh:
                for linea in fh:
                    if linea.startswith("CREATE TABLE"):
                        tablas += 1

            if not os.path.getsize(crudo) or tablas == 0:
                os.remove(crudo)
                raise CommandError(
                    "El dump salio vacio o sin tablas; no se guardo nada."
                )

            tam = os.path.getsize(crudo)
            with open(crudo, "rb") as origen, gzip.open(destino_final, "wb") as destino_fh:
                shutil.copyfileobj(origen, destino_fh)
            os.remove(crudo)

        finally:
            try:
                os.unlink(cred.name)
            except OSError:
                pass

        os.chmod(destino_final, 0o600)

        self.stdout.write(self.style.SUCCESS(
            f"OK  {nombre}  {tablas} tablas  {tam / 1024:.0f} KB (sin comprimir)"
        ))

        self._rotar(destino, conservar, ahora, nombre)

    def _rotar(self, destino, conservar, ahora, conservar_este):
        """Borra los backups mas viejos que la ventana indicada."""
        if conservar <= 0:
            return

        limite = ahora - timedelta(days=conservar)
        borrados = 0

        for archivo in os.listdir(destino):
            if not archivo.endswith(".sql.gz"):
                continue
            if archivo == conservar_este:
                continue
            ruta = os.path.join(destino, archivo)
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(ruta))
            except OSError:
                continue
            if mtime < limite:
                try:
                    os.remove(ruta)
                    borrados += 1
                except OSError:
                    continue

        if borrados:
            self.stdout.write(f"Rotacion: {borrados} backup(s) de mas de {conservar} dias eliminados")

        self.stdout.write(
            f"En {destino}: {len([a for a in os.listdir(destino) if a.endswith('.sql.gz')])} backup(s)"
        )