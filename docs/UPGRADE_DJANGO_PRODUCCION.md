# Actualizar Django en produccion: 4.1 -> 5.2.18 LTS

Instrucciones para ejecutar **en el VPS** donde corre el sistema. Esta
escrito para que lo ejecute un agente (o una persona) con acceso root, sin
contexto previo del proyecto.

- Proyecto: `/var/www/an`
- Venv actual: `/var/www/venv`
- Repositorio: `https://github.com/oscarvogel/anasociados.git`
- Base: MySQL 8.0.46 (Ubuntu 22.04)
- Celery: app `core_an`, broker RabbitMQ en `localhost:5672`, vhost `an`

## Que se cambia y por que

El proyecto arrastraba migraciones generadas con Django 4.1.2, 5.0.1, 5.1 y
5.1.1, y el `requirements.txt` **no fijaba la version de Django**, asi que
cada entorno instalaba una distinta. Ademas, todas esas versiones estan
**fuera de soporte desde hace tiempo** (4.1 murio en diciembre 2023, 5.0 en
abril 2025, 5.1 en diciembre 2025, 4.2 LTS en abril 2026): el sistema venia
corriendo sin parches de seguridad.

El `requirements.txt` nuevo esta **pineado completo** y fija **Django
5.2.18 LTS**, soportado hasta abril 2028.

Ademas agrega `cryptography`, que antes no estaba: sin ese paquete PyMySQL no
puede autenticarse contra MySQL 8 con `caching_sha2_password`, que es el
default de MySQL 8.

**No hay migraciones pendientes.** `migrate --plan` contra la base de
produccion responde `No planned migration operations`. El unico cambio real es
el de las librerias. Aun asi, hacé el backup de la base igual.

## Estado validado antes de subir esto

Todo esto se probo contra una copia de la base de produccion (MySQL 8.4)
antes de cambiar el `requirements.txt`:

- Con Django 4.1.13, 5.0.1 y 5.2.18: `manage.py check` sin errores
- `makemigrations --check` -> `No changes detected` en las tres
- Suite funcional (26 tests) pasando en las tres, contra datos reales
- Venv nuevo instalado **solo** desde el `requirements.txt` nuevo: 30
  paquetes fijados + 23 transitivas, todo funcionando

Lo que **no** se probo: el servidor web real (nginx/gunicorn) y el worker de
Celery levantados con el venv nuevo. Por eso este procedimiento arranca
parando servicios y verificando antes de exponer nada.

---

## Reglas de seguridad

1. **No borres ni muevas `/var/www/venv` hasta que el venv nuevo este
   verificado.** Todo el rollback depende del venv viejo intacto.
2. **No uses `pip install -U django`** ni instales paquetes sueltos. Todo sale
   de `requirements.txt`. Si falta algo, se agrega al archivo y se commitea.
3. **No corras `migrate` a ciegas.** Primero `migrate --plan`, y solo si dice
   lo que esperas.
4. **No toques la base** mas que para el backup. No hay migraciones que
   aplicar.
5. Si algo falla, **parate y hacé rollback** (seccion final). No improvises.

---

## Fase 0 — Descubrimiento (solo lectura)

Registrá el estado actual. Lo vas a necesitar para el rollback y para
comparar despues.

```bash
cd /var/www/an
source /var/www/venv/bin/activate

echo "=== Python ==="
python --version
which python

echo "=== Django y paquetes clave (ACTUALES) ==="
python -c "import django; print('Django', django.get_version())"
pip freeze > /root/an-requirements-ANTES.txt
grep -Ei '^(django|djangorestframework|celery|pymysql|cryptography|numpy|matplotlib|pillow|reportlab|openpyxl|whitenoise|gunicorn|kombu)' /root/an-requirements-ANTES.txt

echo "=== Version de MySQL ==="
python -c "
from core_an import settings
print('ENGINE:', settings.DATABASES['default']['ENGINE'])
print('HOST  :', settings.DATABASES['default']['HOST'])
print('NAME  :', settings.DATABASES['default']['NAME'])
print('DEBUG :', settings.DEBUG)
"
```

Anotá la salida de `pip freeze`. Ese archivo es el camino de vuelta.

```bash
echo "=== Estado de los servicios ==="
systemctl list-units --type=service --state=running | grep -Ei 'gunicorn|uwsgi|django|celery|an'
echo "--- supervisor ---"
supervisorctl status 2>/dev/null
echo "--- procesos ---"
ps aux | grep -Ei 'gunicorn|uwsgi|celery' | grep -v grep
```

Guardá esa salida: con ella vas a saber que reiniciar despues.

```bash
echo "=== Unit files de gunicorn/celery ==="
systemctl list-unit-files | grep -Ei 'gunicorn|uwsgi|django|celery|an\.' 
ls -la /etc/systemd/system/ | grep -Ei 'gunicorn|uwsgi|django|celery'
```

```bash
echo "=== Migraciones pendientes (NO aplicar) ==="
python manage.py migrate --plan
```

**Esperado: `No planned migration operations.`** Si aparece algo distinto,
**frená** y reportá: significa que el estado de la base no es el que se conoce
y el procedimiento no aplica.

```bash
echo "=== .env presente y legible ==="
ls -la /var/www/an/.env
grep -E '^(DEBUG|DJANGO_SETTINGS)' /var/www/an/.env
```

`DEBUG` deberia ser `False` en produccion. Si dice `True`, anotalo y
avisalo: con DEBUG en True, `settings.py` imprime host, usuario y base de
datos en cada arranque.

---

## Fase 1 — Backup

```bash
mkdir -p /root/an-backup-$(date +%Y%m%d-%H%M%S)
BACKUP=/root/an-backup-$(date +%Y%m%d-%H%M%S)
echo "Backup en: $BACKUP"

cp /root/an-requirements-ANTES.txt "$BACKUP/"

# Codigo actual
cd /var/www/an
git rev-parse HEAD > "$BACKUP/git-HEAD-antes.txt"
git status --porcelain > "$BACKUP/git-status-antes.txt"

# Base de datos
source /var/www/venv/bin/activate
python -c "
import os,sys
sys.path.insert(0,'/var/www/an')
os.environ.setdefault('DJANGO_SETTINGS_MODULE','core_an.settings')
import django; django.setup()
from core_an import settings
d=settings.DATABASES['default']
print(d['NAME'], d['USER'], d['HOST'])
" > "$BACKUP/db-info.txt"

# mysqldump leyendo las credenciales del propio Django
python - <<'PY' > "$BACKUP/mysqldump.cmd"
import os, sys
sys.path.insert(0, '/var/www/an')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core_an.settings')
import django; django.setup()
from core_an import settings
d = settings.DATABASES['default']
print(f"mysqldump -h {d['HOST']} -P {d['PORT']} -u {d['USER']} -p'{d['PASSWORD']}' "
      f"--single-transaction --routines --triggers {d['NAME']}")
PY

eval "$(cat "$BACKUP/mysqldump.cmd")" > "$BACKUP/an.sql"

echo "Dump:"
ls -lh "$BACKUP/an.sql"
echo "Tablas en el dump:"
grep -c 'CREATE TABLE' "$BACKUP/an.sql"
```

Verificá que el dump no este vacio. Si `grep -c` da 0, **frená**.

---

## Fase 2 — Venv nuevo (a un lado, sin tocar el actual)

Se instala **al lado** del venv que está en producción. Si algo sale mal, el
viejo sigue intacto y el rollback es instantáneo.

```bash
cd /var/www
python3 --version          # Django 5.2 pide Python >= 3.10

python3 -m venv /var/www/venv_nuevo
source /var/www/venv_nuevo/bin/activate
pip install --upgrade pip setuptools wheel

cd /var/www/an
pip install -r requirements.txt 2>&1 | tee "$BACKUP/pip-install.log"
```

Revisá el log: no deberia haber lineas `ERROR`. Si el `pip install` falla, no
sigas: el problema es de `requirements.txt`, no del servidor.

```bash
echo "=== Django instalado ==="
python -c "import django; print(django.get_version())"
```

Deberia decir **5.2.18**.

---

## Fase 3 — Verificacion con el venv nuevo (aun sin publicar)

Esto corre con el venv nuevo pero **el sitio sigue sirviendo el viejo**.

```bash
cd /var/www/an
source /var/www/venv_nuevo/bin/activate

echo "=== check ==="
python manage.py check

echo "=== deploy check (mas estricto: revisa settings de produccion) ==="
python manage.py check --deploy
```

`manage.py check` tiene que terminar en `System check identified no issues`.

`check --deploy` va a marcar varios avisos (DEBUG, SECURE_HSTS_SECONDS, etc.).
**Esos avisos son preexistentes y no bloquean**: no hay HTTPS ni HSTS
configurado en este despliegue. Lo que importa es que no haya `ERRORS`.
Anotalos, no los arregles en este cambio.

```bash
echo "=== Que paquetes cambiaron respecto del venv viejo ==="
diff <(sort /root/an-requirements-ANTES.txt) <(pip freeze | sort) | head -60
```

```bash
echo "=== El proyecto importa (smoke test de imports) ==="
python -c "
import django, os, sys
sys.path.insert(0,'/var/www/an')
os.environ.setdefault('DJANGO_SETTINGS_MODULE','core_an.settings')
django.setup()
from django.core.management import get_commands
print('comandos cargados:', len(get_commands()))
import core_an.celery
import syh.models, syh.views, moviles.models, moviles.views
import usuarios.models, usuarios.views, usuarios.middleware, usuarios.signals
import home.views, utiles.impresiones, utiles.generador_graficos
print('todos los modulos de la app importan OK')
"
```

Ese import es el que detecta roturas por APIs removidas en Django 5
(`django.utils.timezone.utc` y similares). Si algo falla, **frená y hacé
rollback**: el error te dice exactamente que hay que cambiar en el codigo.

---

## Fase 4 — Cambios de codigo pendientes

El repo local ya tiene todo commiteado y pusheado. En el servidor:

```bash
cd /var/www/an
git fetch origin
git log --oneline -3
git pull origin main
```

Fancier: los ultimos commits son

- `ff899c9` requirements pineado + doc de entorno
- `1d152d1` gitignore del dump
- `9a82e7b` doc de entorno
- `422ec2b` auditoria de accesos, grafico de estados mensuales, design system

`git pull` **deberia ser limpio**. Si hay conflictos o archivos modificados a
mano en el servidor, **frená**: el codigo del servidor fue modificado fuera de
git y hay que resolver eso antes.

```bash
echo "=== Cambios de migraciones que trae el pull ==="
source /var/www/venv_nuevo/bin/activate
python manage.py migrate --plan
```

**Esperado de nuevo: `No planned migration operations.`**

```bash
echo "=== check de nuevo, con el codigo actualizado ==="
python manage.py check
```

---

## Fase 5 — Publicar

Recien ahora se para el sitio. Ventana de caida de segundos.

```bash
# 1. Parar todo
systemctl stop gunicorn 2>/dev/null
supervisorctl stop all 2>/dev/null
pkill -f 'celery.*core_an'   # si el worker corre como systemd: systemctl stop celery@core_an

sleep 2
ps aux | grep -Ei 'gunicorn|uwsgi|celery' | grep -v grep || echo "sin procesos: OK"

# 2. Swap de venv (el viejo queda intacto, solo renombrado)
cd /var/www
mv venv venv_ANTES_$(date +%Y%m%d-%H%M%S)
mv venv_nuevo venv

# 3. Levantar
systemctl start gunicorn 2>/dev/null
supervisorctl start all 2>/dev/null
systemctl start celery@core_an 2>/dev/null

sleep 5
ps aux | grep -Ei 'gunicorn|uwsgi|celery' | grep -v grep
```

**Si el nombre del servicio no es `gunicorn`**, usá el que encontraste en la
Fase 0. Lo mismo para el worker de Celery.

Comprobacion inmediata de que respondio:

```bash
systemctl status gunicorn --no-pager -l | head -20
journalctl -u gunicorn -n 30 --no-pager
```

---

## Fase 6 — Verificacion funcional

```bash
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1/
```

Debe devolver `200` o `302` (si redirige al login, es correcto).

```bash
echo "=== Logs: errores de import o de Django ==="
journalctl -u gunicorn -n 100 --no-pager | grep -Ei 'error|traceback|exception|modulenot|importerror' | head -20
echo "(vacio = sin errores)"
```

```bash
echo "=== El worker de Celery levanto bien? ==="
journalctl -u celery@core_an -n 40 --no-pager 2>/dev/null | tail -20
supervisorctl tail celery stderr 2>/dev/null | tail -20
```

Celery deberia mostrar `ready`. Si dice `Connection refused` hacia RabbitMQ,
el problema es el broker, **no** el upgrade de Django.

### A verificar a mano en el navegador

Estas pantallas son las que toco el cambio de version. Miralas de verdad:

| Pantalla | Que mirar |
|---|---|
| `/` — Tablero | carga el dashboard, los graficos y el **nuevo grafico "Estados de hallazgos mes a mes"** |
| `/usuarios/reporte-accesos/` | reporte de auditoria, solo superuser; debe listar los 3 graficos |
| `/syh/` — Hallazgos | listado y detalle de hallazgos |
| `/moviles/viajes/` | listado de viajes |
| `/moviles/viajes-graficos/` | los graficos interactivos (se reparo un 404 de JS en el commit `422ec2b`) |
| Login y logout | entrar y salir, y confirmarlo en el reporte de accesos |
| `/admin/` | panel de administracion |

Prueba **generar un PDF** de hallazgos y el **resumen mensual**: usan
`reportlab` y `matplotlib`, que cambiaron de version.

Y mandá un resumen mensual desde la web: eso dispara la tarea de Celery
(`task_resumen_mensual`), que es la forma de confirmar que el worker funciona
con las librerias nuevas.

---

## Rollback

Si algo falla, en orden. Cada paso es reversible.

```bash
# 1. Volver al venv viejo (el sitio sigue con el codigo viejo, asi que
#    alcanza con restaurar el venv)
cd /var/www
systemctl stop gunicorn 2>/dev/null
supervisorctl stop all 2>/dev/null

mv venv venv_nuevo_ROTO_$(date +%H%M%S)
mv venv_ANTES_* venv     # el mas reciente; si hay varios, verificar con ls -dt

systemctl start gunicorn 2>/dev/null
supervisorctl start all 2>/dev/null
sleep 5
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1/
```

**Rollback del venv alcanza solo si no commiteaste nada incompatible.** Como
`git pull` solo trae el `requirements.txt` y docs, y no hay migraciones, el
sitio vuelve a funcionar con el venv viejo.

Si ademas quieres volver el codigo:

```bash
cd /var/www/an
git checkout $(cat /root/an-backup-*/git-HEAD-antes.txt | tail -1)
```

### Si el venv viejo se rompio

Reconstruilo desde el freeze:

```bash
cd /var/www
python3 -m venv /var/www/venv
source /var/www/venv/bin/activate
pip install -r /root/an-requirements-ANTES.txt
```

### Si la base quedo tocada

Aunque `migrate --plan` dice que no hay nada que hacer, si llegaste a correr
`migrate` y algo se aplico:

```bash
BACKUP=/root/an-backup-<el-que-creaste>
# Revertir solo la base, sin tocar archivos
mysql -h <HOST> -u <USER> -p < <(gunzip -c "$BACKUP/an.sql.gz") 2>/dev/null || \
mysql -h <HOST> -u <USER> -p < "$BACKUP/an.sql"
```

Esto **borra todo lo que se haya escrito desde el backup**, asi que
confirmalo antes. Con auditoria activada, eso incluye los accesos registrados
despues del dump.

---

## Resumen del resultado esperado

Si todo sale bien:

- `python -c "import django;print(django.get_version())"` -> `5.2.18`
- `manage.py check` -> sin issues
- `migrate --plan` -> sin operaciones
- sitio respondiendo 200/302
- worker de Celery en `ready`
- sin errores en los logs

## Que hacer si falla

Reportá exactamente:

1. Salida de `python manage.py check` (completa)
2. Ultimos 50 del log de gunicorn: `journalctl -u gunicorn -n 50 --no-pager`
3. Si falla en imports: el traceback completo
4. `diff` de `pip freeze` entre el venv viejo y el nuevo
5. Resultado de `migrate --plan`

Con eso se puede seguir depurando sin volver a empezar.