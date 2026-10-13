# Sincronización Airtable a MySQL

## Descripción

Este módulo permite sincronizar registros de viajes desde Airtable hacia la base de datos MySQL de Django.

## Configuración

### 1. Variables de Entorno

Copia `.env.example` a `.env` y configura las siguientes variables:

```bash
# Token de Airtable (recomendado - Personal Access Token)
AIRTABLE_TOKEN=patXXXXXXXXXXXXXX

# O usa la API Key legacy (no recomendado)
# AIRTABLE_API_KEY=keyXXXXXXXXXXXXXX

# ID de la base de Airtable (encontrado en la URL)
AIRTABLE_BASE_ID=appXXXXXXXXXXXXXX

# Nombre de la tabla en Airtable
AIRTABLE_TABLE_NAME=Viajes

# Configuración MySQL (usa las mismas credenciales de Django si aplica)
MYSQL_HOST=localhost
MYSQL_USER=tu_usuario
MYSQL_PASSWORD=tu_password
MYSQL_DATABASE=tu_base_datos

# IDs de empresa y área para asociar los registros
MOVILES_EMPRESA_ID=1
MOVILES_AREA_ID=1
```

### 2. Obtener Token de Airtable

1. Ve a https://airtable.com/create/tokens
2. Crea un nuevo token con los siguientes permisos:
   - `data.records:read` - Para leer registros
   - `data.records:write` - Para actualizar/crear registros
   - `data.records:delete` - Para eliminar registros después de sincronizar
3. Selecciona la base de datos específica
4. Copia el token generado a tu archivo `.env`

### 3. Obtener Base ID

1. Abre tu base en Airtable
2. La URL será algo como: `https://airtable.com/appXXXXXXXXXXXXXX/tblYYYYYYYYYYYYYY`
3. El `appXXXXXXXXXXXXXX` es tu `AIRTABLE_BASE_ID`

## Uso

### Desde la Interfaz Web

1. Inicia sesión como usuario staff/administrador
2. Ve a la página de viajes
3. Haz clic en el botón "Sincronizar Airtable"
4. Confirma la acción
5. Espera a que complete la sincronización

### Desde la Línea de Comandos

#### Modo Dry-Run (solo ver qué se sincronizaría)
```bash
python manage.py sync_airtable --dry-run
```

#### Sincronizar a MySQL (sin eliminar de Airtable)
```bash
python manage.py sync_airtable --mysql
```

#### Sincronización completa (inserta en MySQL y elimina de Airtable)
```bash
python manage.py sync_airtable --mysql --confirm
```

## Funcionamiento

El proceso de sincronización realiza los siguientes pasos:

1. **Obtiene registros** de Airtable usando la API
2. **Valida y normaliza** los datos (patentes, fechas, CUITs)
3. **Crea registros relacionados** si no existen:
   - Predios (origen)
   - Personal (choferes)
   - Móviles (camiones)
4. **Inserta o actualiza** el viaje en MySQL
   - Si existe un `record_id` igual, actualiza
   - Si no existe, crea un nuevo registro
5. **Elimina el registro** de Airtable (solo con `--confirm`)

## Mapeo de Campos

### Airtable → MySQL

| Campo Airtable | Campo MySQL | Notas |
|----------------|-------------|-------|
| Fecha | fecha | Formatos soportados: ISO, dd/mm/YYYY, dd-mm-YYYY |
| Patente | movil.patente | Normalizado (mayúsculas, sin espacios) |
| CUIT / Chofer | personal.cuit | Extrae CUIT del nombre si es necesario |
| Origen | origen_id | Busca/crea predio por ID |
| Destino | destino | Mapeo ASPP→ASERRADERO PUERTO PIRAY |
| Producto | producto | Texto directo |
| TNPulpable | tn_pulpable | Convertido a decimal |
| TNAserrable | tn_aserrable | Convertido a decimal |
| TNChips | tn_chip | Convertido a decimal |
| Sin_Actividad | sin_actividad | Boolean |
| Motivo_Sin_Actividad | motivo_sin_actividad | Texto |
| Observaciones | observaciones | Texto |

## Resolución de Problemas

### Error: "missing_env_vars"
- Verifica que todas las variables requeridas estén en `.env`
- Asegúrate de que el archivo `.env` esté en el directorio raíz de Django

### Error: "airtable_fetch_failed" 
- Verifica que el `AIRTABLE_TOKEN` sea válido
- Confirma que el token tenga permisos de lectura
- Verifica que el `AIRTABLE_BASE_ID` sea correcto

### Error: "airtable_delete_failed" (401/403)
- El token necesita permisos `data.records:delete`
- Verifica que el token tenga acceso a la base específica

### Error: "missing_patente" / "missing_movil_id"
- Algunos registros en Airtable no tienen patente válida
- Opción 1: Corregir los datos en Airtable
- Opción 2: Activar `ALLOW_PLACEHOLDER_MOVIL=true` para crear móviles temporales

### Error: MySQL connection
- Verifica las credenciales MySQL en `.env`
- Asegúrate de que el servidor MySQL esté corriendo
- Confirma que el usuario tenga permisos en la base de datos

## Deployment en Ubuntu/Nginx

### 1. Instalar dependencias

```bash
sudo apt-get update
sudo apt-get install python3-dev default-libmysqlclient-dev build-essential
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

En producción, configura las variables de entorno en:
- `/etc/environment` (sistema)
- O en el archivo `.env` del proyecto
- O en la configuración de systemd/supervisor

### 3. Permisos

Asegúrate de que el usuario que ejecuta Gunicorn/uWSGI tenga:
- Acceso de lectura al script `utiles/sync_airtable_to_mysql.py`
- Acceso al intérprete de Python correcto
- Acceso a las variables de entorno
- Permisos de lectura en el archivo `.env` (chmod 640)

### 4. Ejecutar sincronización programada (opcional)

Crear un cron job para sincronizar automáticamente:

```bash
# Editar crontab
crontab -e

# Agregar línea (ejemplo: cada hora)
0 * * * * cd /ruta/a/tu/proyecto && /ruta/al/venv/bin/python manage.py sync_airtable --mysql --confirm >> /var/log/airtable_sync.log 2>&1
```

## 🔧 Troubleshooting

### Error: "CalledProcessError returned non-zero exit status 1"

Este error indica que el script `sync_airtable_to_mysql.py` falló. Causas comunes:

#### 1. Archivo .env no encontrado o mal ubicado
**Síntomas:** Script funciona en local pero falla en producción

**Solución:**
```bash
# Verificar ubicación del .env
cd /var/www/an  # Ajustar a tu ruta
ls -la .env

# Debe estar en la raíz del proyecto Django
# Si no existe, crearlo con las variables necesarias
```

#### 2. Variables de entorno no cargadas en el servicio web
**Síntomas:** Script funciona manualmente pero falla desde la web

**Solución para systemd:**
```bash
# Editar archivo de servicio
sudo nano /etc/systemd/system/tu-servicio.service

# Agregar en la sección [Service]:
[Service]
EnvironmentFile=/var/www/an/.env

# Recargar
sudo systemctl daemon-reload
sudo systemctl restart tu-servicio
```

**Solución para supervisor:**
```bash
# Editar configuración
sudo nano /etc/supervisor/conf.d/django.conf

# Agregar línea environment
[program:django]
environment=AIRTABLE_TOKEN="tu_token",AIRTABLE_BASE_ID="tu_base_id"

# Recargar
sudo supervisorctl reread && sudo supervisorctl update
```

#### 3. Falta python-dotenv
**Solución:**
```bash
source /ruta/al/venv/bin/activate
pip install python-dotenv
```

#### 4. Permisos incorrectos en .env
**Solución:**
```bash
cd /var/www/an
chmod 640 .env
chown www-data:www-data .env  # Ajustar usuario según tu configuración
```

### Herramientas de Diagnóstico

#### Script de Diagnóstico Automático
Ejecuta este script en el servidor para verificar la configuración:

```bash
cd /var/www/an
source /var/www/venv_an/bin/activate
python check_airtable_env.py
```

Este script verifica:
- ✅ Existencia y permisos del archivo `.env`
- ✅ Presencia de todas las variables requeridas
- ✅ Instalación de `python-dotenv`
- ❌ Problemas de configuración

#### Prueba Manual del Script
Para probar sin modificar la base de datos:

```bash
cd /var/www/an
source /var/www/venv_an/bin/activate

# Dry-run (solo lectura, no modifica nada)
python utiles/sync_airtable_to_mysql.py --dry-run

# Probar escritura a MySQL sin borrar Airtable
python utiles/sync_airtable_to_mysql.py --mysql

# Sincronización completa (CUIDADO: borra de Airtable)
python utiles/sync_airtable_to_mysql.py --mysql --confirm
```

#### Ver Logs Detallados
```bash
# Logs del servicio (systemd)
journalctl -u tu-servicio -n 100 -f

# Logs de Nginx/Apache
tail -f /var/log/nginx/error.log

# Logs de la aplicación Django
tail -f /ruta/a/logs/django.log
```

### Consultar Documentación Extendida

Para una guía completa de solución de problemas en VPS, consulta:
- 📄 **SOLUCION_AIRTABLE_VPS.md** - Guía detallada paso a paso
- 📝 **comandos_vps_diagnostico.sh** - Comandos útiles para copiar/pegar

## Logs y Debugging

El script imprime mensajes JSON estructurados en stdout:

```json
{"info": "fetched_records_count", "count": 25}
{"warning": "missing_patente", "record_id": "recXXXXXX", "raw": null}
{"error": "airtable_delete_failed", "record_id": "recYYYYYY", "status": 403}
```

Para debugging, revisa:
1. Console del navegador (errores JS)
2. Logs de Django/Gunicorn
3. Output del comando `sync_airtable`
4. Ejecuta `check_airtable_env.py` para diagnóstico
