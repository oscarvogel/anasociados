#!/usr/bin/env python
"""
Script de verificación de configuración para sincronización Airtable.
Ejecuta este script para verificar que todas las variables de entorno
y dependencias estén correctamente configuradas antes de sincronizar.
"""

import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def print_status(check_name, passed, message=""):
    """Imprime el estado de una verificación"""
    status = "✅" if passed else "❌"
    print(f"{status} {check_name}")
    if message:
        print(f"   → {message}")

def main():
    print("\n" + "="*60)
    print("VERIFICACIÓN DE CONFIGURACIÓN - SINCRONIZACIÓN AIRTABLE")
    print("="*60 + "\n")

    all_passed = True

    # 1. Verificar variables de Airtable
    print("1. Variables de Airtable:")
    airtable_token = os.getenv('AIRTABLE_TOKEN')
    airtable_key = os.getenv('AIRTABLE_API_KEY')
    has_auth = airtable_token or airtable_key
    print_status("Token/API Key", bool(has_auth), 
                 f"Usando: {'AIRTABLE_TOKEN' if airtable_token else 'AIRTABLE_API_KEY' if airtable_key else 'NINGUNO'}")
    all_passed = all_passed and bool(has_auth)

    base_id = os.getenv('AIRTABLE_BASE_ID')
    print_status("Base ID", bool(base_id), base_id[:20] + "..." if base_id and len(base_id) > 20 else base_id)
    all_passed = all_passed and bool(base_id)

    table_name = os.getenv('AIRTABLE_TABLE_NAME')
    print_status("Table Name", bool(table_name), table_name)
    all_passed = all_passed and bool(table_name)

    # 2. Verificar variables MySQL
    print("\n2. Variables MySQL:")
    mysql_host = os.getenv('MYSQL_HOST') or os.getenv('DB_HOST')
    print_status("Host", bool(mysql_host), mysql_host)
    all_passed = all_passed and bool(mysql_host)

    mysql_user = os.getenv('MYSQL_USER') or os.getenv('DB_USERNAME')
    print_status("User", bool(mysql_user), mysql_user)
    all_passed = all_passed and bool(mysql_user)

    mysql_pass = os.getenv('MYSQL_PASSWORD') or os.getenv('DB_PASS')
    print_status("Password", bool(mysql_pass), "***" if mysql_pass else None)
    all_passed = all_passed and bool(mysql_pass)

    mysql_db = os.getenv('MYSQL_DATABASE') or os.getenv('DB_NAME')
    print_status("Database", bool(mysql_db), mysql_db)
    all_passed = all_passed and bool(mysql_db)

    # 3. Verificar dependencias Python
    print("\n3. Dependencias Python:")
    
    try:
        import requests
        print_status("requests", True, f"v{requests.__version__}")
    except ImportError as e:
        print_status("requests", False, "No instalado - pip install requests")
        all_passed = False

    try:
        import mysql.connector
        print_status("mysql-connector-python", True)
    except ImportError:
        print_status("mysql-connector-python", False, "No instalado - pip install mysql-connector-python")
        all_passed = False

    try:
        import dotenv
        print_status("python-dotenv", True, f"v{dotenv.__version__}")
    except ImportError:
        print_status("python-dotenv", False, "No instalado - pip install python-dotenv")
        all_passed = False

    # 4. Probar conexión a MySQL
    print("\n4. Conexión MySQL:")
    if mysql_host and mysql_user and mysql_pass and mysql_db:
        try:
            import mysql.connector
            conn = mysql.connector.connect(
                host=mysql_host,
                user=mysql_user,
                password=mysql_pass,
                database=mysql_db,
                connect_timeout=5
            )
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            print_status("Conexión a MySQL", True, "Conexión exitosa")
        except Exception as e:
            print_status("Conexión a MySQL", False, str(e))
            all_passed = False
    else:
        print_status("Conexión a MySQL", False, "Faltan credenciales")
        all_passed = False

    # 5. Probar conexión a Airtable
    print("\n5. Conexión Airtable:")
    if has_auth and base_id and table_name:
        try:
            import requests
            import urllib.parse
            
            encoded_table = urllib.parse.quote(table_name, safe='')
            url = f"https://api.airtable.com/v0/{base_id}/{encoded_table}"
            
            token = airtable_token or airtable_key
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(f"{url}?maxRecords=1", headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                record_count = len(data.get('records', []))
                print_status("Conexión a Airtable", True, f"Conexión exitosa (encontrados registros)")
            else:
                print_status("Conexión a Airtable", False, 
                           f"HTTP {response.status_code}: {response.text[:100]}")
                all_passed = False
        except Exception as e:
            print_status("Conexión a Airtable", False, str(e))
            all_passed = False
    else:
        print_status("Conexión a Airtable", False, "Faltan credenciales")
        all_passed = False

    # 6. Verificar archivo de script
    print("\n6. Archivos:")
    script_path = os.path.join(os.path.dirname(__file__), 'utiles', 'sync_airtable_to_mysql.py')
    script_exists = os.path.exists(script_path)
    print_status("Script de sincronización", script_exists, script_path if script_exists else "No encontrado")
    all_passed = all_passed and bool(script_exists)

    # Resultado final
    print("\n" + "="*60)
    if all_passed:
        print("✅ TODAS LAS VERIFICACIONES PASARON")
        print("\nPuedes ejecutar la sincronización con:")
        print("  python manage.py sync_airtable --dry-run  # Ver qué se sincronizaría")
        print("  python manage.py sync_airtable --mysql --confirm  # Sincronizar")
    else:
        print("❌ ALGUNAS VERIFICACIONES FALLARON")
        print("\nCorrige los errores antes de sincronizar.")
        print("Consulta AIRTABLE_SYNC_README.md para más información.")
    print("="*60 + "\n")

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
