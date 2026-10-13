# 🚀 PASOS RÁPIDOS PARA SOLUCIONAR ERROR EN VPS

## ⚡ Solución Rápida (5 minutos)

Ejecuta estos comandos en tu VPS en orden:

### 1️⃣ Conéctate al VPS y ve al directorio del proyecto
```bash
cd /var/www/an
source /var/www/venv_an/bin/activate
```

### 2️⃣ Instala/actualiza python-dotenv
```bash
pip install --upgrade python-dotenv
```

### 3️⃣ Verifica el archivo .env
```bash
# Ver si existe
ls -la .env

# Si NO existe, créalo
nano .env
# Pega el contenido de tu .env local (con las credenciales del VPS)
# Guarda con Ctrl+O, Enter, Ctrl+X
```

### 4️⃣ Sube los archivos nuevos al VPS
Desde tu máquina local, sube estos archivos nuevos:
```bash
# Opción 1: Con SCP (desde tu máquina local)
scp check_airtable_env.py usuario@tu-vps:/var/www/an/
scp SOLUCION_AIRTABLE_VPS.md usuario@tu-vps:/var/www/an/

# Opción 2: Con git (si usas git)
git add check_airtable_env.py SOLUCION_AIRTABLE_VPS.md
git commit -m "Agregar scripts de diagnóstico Airtable"
git push

# Luego en el VPS:
cd /var/www/an
git pull
```

### 5️⃣ Ejecuta el diagnóstico
```bash
python check_airtable_env.py
```

**Resultado esperado:** Debes ver ✅ en todas las variables. Si ves ❌, sigue las instrucciones.

### 6️⃣ Prueba el script manualmente
```bash
# Dry-run (no modifica nada)
python utiles/sync_airtable_to_mysql.py --dry-run
```

**Si este paso funciona pero falla desde la web,** el problema es que el servicio web no tiene acceso a las variables de entorno. Continúa con el paso 7.

### 7️⃣ Configura el servicio web para cargar el .env

#### Si usas Gunicorn con systemd:
```bash
sudo nano /etc/systemd/system/gunicorn.service
# o el nombre de tu servicio, busca con:
sudo systemctl list-units | grep -i django
```

Agrega esta línea en la sección `[Service]`:
```ini
[Service]
EnvironmentFile=/var/www/an/.env
# ... resto de la configuración
```

Luego:
```bash
sudo systemctl daemon-reload
sudo systemctl restart gunicorn  # o tu servicio
```

#### Si usas Supervisor:
```bash
sudo nano /etc/supervisor/conf.d/django.conf
```

Agrega las variables de entorno:
```ini
[program:django]
# ... otras configuraciones ...
environment=AIRTABLE_TOKEN="tu_token_aqui",AIRTABLE_BASE_ID="tu_base_id",AIRTABLE_TABLE_NAME="tu_tabla"
```

Luego:
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl restart django
```

### 8️⃣ Prueba desde la web
Abre tu aplicación web y prueba el botón "Sincronizar". Debería funcionar ahora.

---

## 🆘 Si Aún Falla

### Obtén más información del error:
```bash
cd /var/www/an
source /var/www/venv_an/bin/activate
python utiles/sync_airtable_to_mysql.py --mysql --confirm 2>&1 | tee error_completo.log
cat error_completo.log
```

### Verifica logs del servicio web:
```bash
# Para systemd
sudo journalctl -u gunicorn -n 50

# Para supervisor
sudo supervisorctl tail django stderr

# Nginx
sudo tail -f /var/log/nginx/error.log
```

### Variables de entorno requeridas en .env:
```bash
AIRTABLE_TOKEN=patXXXXXXXXXXXXXX  # Tu token de Airtable
AIRTABLE_BASE_ID=appXXXXXXXXXXXX  # ID de tu base
AIRTABLE_TABLE_NAME=Viajes         # Nombre de tu tabla

# MySQL (usa las mismas de Django)
MYSQL_HOST=localhost
MYSQL_USER=tu_usuario
MYSQL_PASSWORD=tu_contraseña
MYSQL_DATABASE=tu_base_datos
```

---

## ✅ Checklist de Verificación

Marca cada ítem cuando lo completes:

- [ ] Conectado al VPS en el directorio correcto
- [ ] python-dotenv instalado: `pip list | grep dotenv`
- [ ] Archivo .env existe: `ls -la .env`
- [ ] Permisos correctos en .env: `-rw-r----- o similar`
- [ ] Diagnóstico muestra todo ✅: `python check_airtable_env.py`
- [ ] Script funciona manualmente: `python utiles/sync_airtable_to_mysql.py --dry-run`
- [ ] Servicio web configurado para cargar .env
- [ ] Servicio web reiniciado
- [ ] Funciona desde la interfaz web

---

## 📚 Documentación Completa

- **SOLUCION_AIRTABLE_VPS.md** - Guía detallada con todas las soluciones posibles
- **AIRTABLE_SYNC_README.md** - Documentación completa del módulo
- **comandos_vps_diagnostico.sh** - Todos los comandos útiles

---

## 🎯 Problema Más Común

**El archivo .env no se carga en el contexto del servicio web.**

**Solución:** Agregar `EnvironmentFile=/var/www/an/.env` en la configuración de systemd o las variables directamente en supervisor, luego reiniciar el servicio.
