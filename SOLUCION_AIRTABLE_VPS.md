# 🔧 Guía de Solución: Error de Sincronización Airtable en VPS

## 📋 Problema

El script de sincronización de Airtable funciona en local pero falla en el VPS con el error:
```
subprocess.CalledProcessError: Command '['/var/www/venv_an/bin/python3', '/var/www/an/utiles/sync_airtable_to_mysql.py', '--mysql', '--confirm']' returned non-zero exit status 1.
```

## 🔍 Diagnóstico

### Paso 1: Ejecutar Script de Diagnóstico

Conéctate a tu VPS y ejecuta el script de diagnóstico:

```bash
cd /var/www/an
source /var/www/venv_an/bin/activate
python check_airtable_env.py
```

Este script te mostrará:
- ✅ Qué variables de entorno están correctamente configuradas
- ❌ Qué variables faltan
- 📂 Dónde busca el archivo `.env`
- 🔐 Estado de permisos del archivo

### Paso 2: Verificar Archivo .env

El archivo `.env` debe estar en: `/var/www/an/.env`

```bash
# Verificar que existe
ls -la /var/www/an/.env

# Ver permisos (debe ser legible por el usuario del proceso Django)
ls -l /var/www/an/.env

# Verificar contenido (sin mostrar valores sensibles)
grep -E "AIRTABLE|MYSQL|DB_" /var/www/an/.env | sed 's/=.*/=***/'
```

### Paso 3: Verificar Variables Requeridas

Asegúrate de que tu archivo `.env` contiene:

```bash
# Airtable Configuration (al menos uno de estos dos)
AIRTABLE_TOKEN=tu_personal_access_token_aqui  # Recomendado
# o
AIRTABLE_API_KEY=tu_api_key_legacy_aqui      # Legacy

# Airtable Base & Table
AIRTABLE_BASE_ID=appXXXXXXXXXXXXXX
AIRTABLE_TABLE_NAME=Nombre de tu Tabla

# MySQL Configuration
MYSQL_HOST=localhost
MYSQL_USER=tu_usuario
MYSQL_PASSWORD=tu_contraseña
MYSQL_DATABASE=tu_base_de_datos

# O alternativamente usar las variables DB_*
DB_HOST=localhost
DB_USERNAME=tu_usuario
DB_PASS=tu_contraseña
DB_NAME=tu_base_de_datos
```

## 🛠️ Soluciones Comunes

### Solución 1: Archivo .env No Existe o No es Legible

```bash
# Crear/copiar archivo .env a la ubicación correcta
cd /var/www/an
nano .env  # o vim .env

# Establecer permisos correctos
chmod 640 .env
chown www-data:www-data .env  # Ajustar usuario según tu configuración
```

### Solución 2: Variables de Entorno en Servicio Systemd/Supervisor

Si usas systemd o supervisor para ejecutar Django, las variables de entorno pueden no cargarse automáticamente.

#### Para Systemd:

Edita tu archivo de servicio:
```bash
sudo nano /etc/systemd/system/django.service
```

Agrega:
```ini
[Service]
# Opción 1: Cargar archivo .env
EnvironmentFile=/var/www/an/.env

# Opción 2: Definir variables directamente
Environment="AIRTABLE_TOKEN=tu_token"
Environment="AIRTABLE_BASE_ID=tu_base_id"
# ... etc
```

Recarga y reinicia:
```bash
sudo systemctl daemon-reload
sudo systemctl restart django
```

#### Para Supervisor:

Edita tu archivo de configuración:
```bash
sudo nano /etc/supervisor/conf.d/django.conf
```

Agrega:
```ini
[program:django]
# ... otras configuraciones ...
environment=AIRTABLE_TOKEN="tu_token",AIRTABLE_BASE_ID="tu_base_id",...
```

Recarga:
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl restart django
```

### Solución 3: Variables en /etc/environment (Sistema Completo)

Para hacer las variables disponibles en todo el sistema:

```bash
sudo nano /etc/environment
```

Agregar:
```bash
AIRTABLE_TOKEN="tu_token"
AIRTABLE_BASE_ID="tu_base_id"
AIRTABLE_TABLE_NAME="tu_tabla"
# ... etc
```

**Importante:** Después de editar `/etc/environment`, debes reiniciar el servicio o la sesión.

### Solución 4: Permisos de Archivos

Asegúrate de que el usuario que ejecuta Django puede leer el archivo `.env`:

```bash
# Ver qué usuario ejecuta Django
ps aux | grep django
# o
ps aux | grep gunicorn

# Cambiar permisos si es necesario
cd /var/www/an
chown usuario_django:grupo_django .env
chmod 640 .env
```

### Solución 5: Instalar python-dotenv

Verifica que `python-dotenv` esté instalado en el entorno virtual del VPS:

```bash
source /var/www/venv_an/bin/activate
pip install python-dotenv
```

## 🧪 Pruebas

### Probar Manualmente el Script

Conéctate al VPS y ejecuta el script directamente:

```bash
cd /var/www/an
source /var/www/venv_an/bin/activate

# Prueba en modo dry-run primero
python utiles/sync_airtable_to_mysql.py --dry-run

# Si funciona, prueba con MySQL sin confirmar
python utiles/sync_airtable_to_mysql.py --mysql

# Si todo está bien, ejecuta con confirmación
python utiles/sync_airtable_to_mysql.py --mysql --confirm
```

Si el script funciona manualmente pero falla desde Django, el problema es la carga de variables de entorno en el contexto del servicio web.

### Probar desde Django Management Command

```bash
cd /var/www/an
source /var/www/venv_an/bin/activate
python manage.py sync_airtable --mysql --confirm
```

## 📝 Checklist de Verificación

- [ ] Archivo `.env` existe en `/var/www/an/.env`
- [ ] Permisos del archivo `.env` son correctos (legible por usuario Django)
- [ ] Todas las variables requeridas están en `.env`
- [ ] `python-dotenv` está instalado en el venv
- [ ] El script `check_airtable_env.py` muestra ✅ en todas las variables
- [ ] El script funciona manualmente: `python utiles/sync_airtable_to_mysql.py --dry-run`
- [ ] El comando Django funciona: `python manage.py sync_airtable --dry-run`
- [ ] El servicio web (gunicorn/uwsgi) tiene acceso a las variables de entorno

## 🆘 Obtener Más Información sobre el Error

Si el error persiste, obtén más detalles ejecutando:

```bash
cd /var/www/an
source /var/www/venv_an/bin/activate

# Ver error completo del script
python utiles/sync_airtable_to_mysql.py --mysql --confirm 2>&1 | tee sync_error.log

# Ver logs de Django (ajustar ruta según tu configuración)
tail -f /var/log/django/error.log
# o
tail -f /var/log/nginx/error.log
```

## 📞 Información para Reportar

Si necesitas ayuda adicional, incluye:

1. Salida de `python check_airtable_env.py`
2. Contenido de `ls -la /var/www/an/.env` (sin mostrar valores)
3. Usuario que ejecuta Django: `ps aux | grep django`
4. Tipo de servidor web: Gunicorn, uWSGI, etc.
5. Sistema de gestión de procesos: systemd, supervisor, etc.
6. Salida completa del error desde los logs

## 🎯 Solución Rápida Recomendada

Para la mayoría de los casos, esto debería resolver el problema:

```bash
# 1. Ir al directorio del proyecto
cd /var/www/an

# 2. Activar entorno virtual
source /var/www/venv_an/bin/activate

# 3. Instalar/actualizar python-dotenv
pip install --upgrade python-dotenv

# 4. Verificar que .env existe y tiene las variables
cat .env | grep AIRTABLE

# 5. Ejecutar diagnóstico
python check_airtable_env.py

# 6. Si todo está OK, reiniciar el servicio web
sudo systemctl restart gunicorn  # o el nombre de tu servicio
# o
sudo supervisorctl restart django
```

---

**Nota:** Después de aplicar cualquiera de estas soluciones, recuerda reiniciar tu servidor web o aplicación Django para que los cambios surtan efecto.
