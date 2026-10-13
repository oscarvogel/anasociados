# Entorno de desarrollo local

Este documento describe como armar un entorno funcional para trabajar sobre
este proyecto en una maquina Windows. Antes de existia `requirements.txt` con
10 paquetes (incompleto) y ninguna instruccion de instalacion, por lo que el
proyecto no era instalable ni reproducible.

## Que se necesita

- Python 3.12 (probado) con `uv` para crear el entorno
- MySQL 8.x para las pruebas (opcional: sin BD el proyecto cae a SQLite)

## Dependencias

`requirements.txt` esta pineado completo (30 paquetes directos mas sus
transitivas criticas), asi que alcanza con:

```powershell
python -m uv python install 3.12
python -m uv venv --python 3.12 .venv
python -m uv pip install --python .venv -r requirements.txt
```

Antes el archivo listaba 10 paquetes y el proyecto no era instalable. Los que
faltaban y mas importan:

| Paquete | Para que |
|---|---|
| `django` | el framework, ahora **fijado en 5.2.18 LTS** |
| `djangorestframework` | `rest_framework`, vistas y serializers |
| `pymysql` | backend MySQL (`install_as_MySQLdb`) |
| `cryptography` | **obligatorio** si el MySQL usa `caching_sha2_password` (MySQL 8) |
| `celery`, `kombu`, `django-celery-results` | tareas asincronas y broker |
| `matplotlib`, `numpy` | graficos de `syh` y `utiles` |
| `reportlab`, `pillow` | PDFs e imagenes (`utiles/impresiones.py`) |
| `unidecode` | `syh/models.py` |
| `requests`, `mysql-connector-python` | sincronizacion con Airtable |

## Correr sin tocar la base real

`settings.py` hace `load_dotenv(dotenv_path='.env')` con un path **relativo al
directorio de trabajo**, y cae a SQLite si `DB_ENGINE`, `DB_NAME` y
`DB_USERNAME` no estan definidos.

Advertencia: en PowerShell `$env:DB_NAME=''` **borra** la variable en vez de
dejarla vacia, y entonces el `.env` real la repone y el proceso se conecta a
produccion. La forma segura de aislarse es correr desde otro directorio:

```powershell
$env:DEBUG='True'
Set-Location $env:TEMP\carpeta_sin_env
python C:\ruta\al\proyecto\manage.py check     # DB_HOST -> None
```

Si el settings imprime `DB_HOST -> None`, quedo aislado.

## MySQL de pruebas en WSL

El MySQL del sistema corre en el 3306 pero exige `root` por socket. Para
probarlas sin sudo se levanta una instancia propia en el 3307 con datadir en el
home del usuario y un `--defaults-file` propio (asi no hereda
`/etc/mysql/my.cnf`, que fuerza `log-error` en `/var/log/mysql`):

```bash
mkdir -p ~/mysql_test/data ~/mysql_test/run
cat > ~/mysql_test/my.cnf <<EOF
[mysqld]
datadir=$HOME/mysql_test/data
socket=$HOME/mysql_test/run/mysql.sock
port=3307
pid-file=$HOME/mysql_test/run/mysqld.pid
log-error=$HOME/mysql_test/run/mysqld.log
mysqlx=0
skip-name-resolve
skip-log-bin
EOF

mysqld --defaults-file=~/mysql_test/my.cnf --initialize-insecure
nohup mysqld --defaults-file=~/mysql_test/my.cnf &

mysql --socket=$HOME/mysql_test/run/mysql.sock -u root -e "
  CREATE DATABASE an_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
  CREATE USER 'anuser'@'%' IDENTIFIED BY 'anpass123';
  GRANT ALL ON an_test.* TO 'anuser'@'%';"
```

Desde Windows se accede por la IP de WSL (`wsl -e hostname -I`), no por
`localhost`: el forwarding de localhost de WSL2 puede estar desactivado.

```powershell
$env:DB_ENGINE='mysql'; $env:DB_HOST='<ip-wsl>'; $env:DB_PORT='3307'
$env:DB_NAME='an_test'; $env:DB_USERNAME='anuser'; $env:DB_PASS='anpass123'
```

## El orden de `migrate` no es trivial

`Movimientos`, `Cliente`, `Area` y `Profile` son `managed = False`: Django no
crea esas tablas, pero **otras migraciones si las referencian**. En una base
nueva, `migrate` muere en `syh.0004_evidencia` con:

```
(1824, "Failed to open the referenced table 'movimientos'")
```

El orden que funciona es:

1. Crear a mano `clientes`, `areas` y `movimientos`
   (`movimientos` **sin** la FK a `syh_naturalezahallazgo`: esa tabla la crea
   la migracion `syh.0028`, muy posterior)
2. `migrate contenttypes auth` (necesario para que exista `auth_user`)
3. Crear a mano `perfiles` (tiene FK a `auth_user` y a `clientes`)
4. `migrate` completo

MySQL no hace rollback de DDL: si una migracion falla a mitad, la tabla que
alcanzo a crear queda en la base y la siguiente corrida falla con
"Table already exists". Hay que dropearla a mano.

## Nota sobre versiones de Django

El repo arrastraba migraciones generadas por Django **4.1.2, 5.0.1, 5.1 y
5.1.1**, y `requirements.txt` no fijaba la version, asi que cada entorno
instalaba la que le de la gana.

Ademas, **todas** esas versiones estan fuera de soporte:

| Version | Fin de soporte |
|---|---|
| 4.1 | diciembre 2023 |
| 4.2 LTS | abril 2026 |
| 5.0 | abril 2025 |
| 5.1 | diciembre 2025 |

O sea, el proyecto venia operando sin parches de seguridad. Ahora
`requirements.txt` fija **Django 5.2.18 LTS**, soportado hasta abril 2028 y
compatible con Python 3.10 a 3.14.

Verificado con `manage.py check`, `migrate` y la suite funcional contra MySQL
real: primero con 4.1.13 y 5.0.1, para confirmar que el codigo no dependia de
una version en particular, y despues con un venv instalado desde cero usando
el `requirements.txt` nuevo (5.2.18). Los tres dieron lo mismo.

El upgrade se hizo el 13/10/2026 y quedo en 5.2.18.

En el servidor `an` usa **su propio venv**, `/var/www/venv_an`, que se separo
del compartido `/var/www/venv` porque ese lo usaban tambien `mini-iaes` y
`fg/produccion_api`. Instalar el requirements ahi abajo les habria cambiado las
librerias a las otras dos aplicaciones. Para desplegar hay que actualizar
`/var/www/venv_an` y correr `migrate`.

`migrate --plan` contra la base de produccion responde *"No planned migration
operations"*, asi que el unico cambio real es el de las librerias.

Al separar los venv, `/var/www/venv` quedo con Django 5.0.1 y lo siguen usando
`mini-iaes` y `produccion_api`. Si alguna vez hay que tocar esas dos, primero
verificar si ellas tambien necesitan un venv propio.

El codigo del servidor se despliega con `git pull` desde `/var/www/an`, que ya
es un repositorio con upstream a `origin/main`.