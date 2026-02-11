#!/bin/bash
# Script de comandos útiles para diagnosticar y solucionar el error de Airtable en VPS
# Este archivo contiene comandos para copiar y ejecutar manualmente

echo "======================================"
echo "COMANDOS DE DIAGNÓSTICO AIRTABLE VPS"
echo "======================================"
echo ""

# PASO 1: Ir al directorio del proyecto
echo "1. Cambiar al directorio del proyecto:"
echo "   cd /var/www/an"
echo ""

# PASO 2: Activar entorno virtual
echo "2. Activar entorno virtual:"
echo "   source /var/www/venv/bin/activate"
echo ""

# PASO 3: Verificar archivo .env
echo "3. Verificar que existe el archivo .env:"
echo "   ls -la .env"
echo "   Esperado: -rw-r----- 1 usuario grupo XXXX fecha .env"
echo ""

# PASO 4: Ver variables (sin valores sensibles)
echo "4. Ver variables de Airtable en .env (enmascarado):"
echo "   grep -E 'AIRTABLE|MYSQL|DB_' .env | sed 's/=.*/=***/' "
echo ""

# PASO 5: Ejecutar script de diagnóstico
echo "5. Ejecutar script de diagnóstico:"
echo "   python check_airtable_env.py"
echo "   Debe mostrar ✅ en todas las variables requeridas"
echo ""

# PASO 6: Probar script directamente (dry-run)
echo "6. Probar script de sincronización (dry-run, no modifica BD):"
echo "   python utiles/sync_airtable_to_mysql.py --dry-run"
echo ""

# PASO 7: Probar con MySQL sin borrar Airtable
echo "7. Probar sincronización a MySQL (sin borrar de Airtable):"
echo "   python utiles/sync_airtable_to_mysql.py --mysql"
echo ""

# PASO 8: Si todo funciona, ejecutar completo
echo "8. Ejecutar sincronización completa:"
echo "   python utiles/sync_airtable_to_mysql.py --mysql --confirm"
echo ""

# PASO 9: Probar desde management command
echo "9. Probar desde Django management command:"
echo "   python manage.py sync_airtable --mysql --confirm"
echo ""

# PASO 10: Ver logs
echo "10. Ver logs de error (ajustar rutas según tu configuración):"
echo "    tail -f /var/log/django/error.log"
echo "    # o"
echo "    tail -f /var/log/nginx/error.log"
echo "    # o"
echo "    journalctl -u gunicorn -n 50"
echo ""

echo "======================================"
echo "SOLUCIONES RÁPIDAS"
echo "======================================"
echo ""

echo "Si falta python-dotenv:"
echo "   pip install python-dotenv"
echo ""

echo "Si el archivo .env no existe o está vacío:"
echo "   nano .env"
echo "   # Copiar contenido de .env.example y llenar con tus valores"
echo ""

echo "Si hay problemas de permisos:"
echo "   chmod 640 .env"
echo "   chown www-data:www-data .env  # Ajustar usuario según tu config"
echo ""

echo "Si usas systemd, editar servicio para cargar .env:"
echo "   sudo nano /etc/systemd/system/tu-servicio.service"
echo "   # Agregar: EnvironmentFile=/var/www/an/.env"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl restart tu-servicio"
echo ""

echo "Si usas supervisor:"
echo "   sudo nano /etc/supervisor/conf.d/django.conf"
echo "   # Agregar línea environment con las variables"
echo "   sudo supervisorctl reread && sudo supervisorctl update"
echo ""

echo "Reiniciar servicio web después de cambios:"
echo "   sudo systemctl restart gunicorn"
echo "   # o"
echo "   sudo systemctl restart uwsgi"
echo "   # o"
echo "   sudo supervisorctl restart django"
echo ""

echo "======================================"
echo "VERIFICACIÓN FINAL"
echo "======================================"
echo ""
echo "Una vez aplicados los cambios:"
echo "   1. python check_airtable_env.py  # Debe estar todo ✅"
echo "   2. python utiles/sync_airtable_to_mysql.py --dry-run  # Debe funcionar"
echo "   3. sudo systemctl restart gunicorn  # Reiniciar servicio"
echo "   4. Probar desde la interfaz web"
echo ""
