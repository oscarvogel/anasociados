#!/usr/bin/env python3
"""
Script de diagnóstico para verificar la configuración de Airtable en el VPS.
Ejecutar este script en el VPS para verificar que las variables de entorno estén correctamente configuradas.
"""
import os
import sys
from pathlib import Path

def check_environment():
    """Verifica la configuración del entorno para Airtable sync."""
    
    print("=" * 60)
    print("DIAGNÓSTICO DE CONFIGURACIÓN DE AIRTABLE")
    print("=" * 60)
    print()
    
    # 1. Verificar ubicación del script
    script_dir = Path(__file__).parent.absolute()
    print(f"📂 Directorio del script: {script_dir}")
    print()
    
    # 2. Buscar archivo .env
    env_locations = [
        script_dir / '.env',
        script_dir.parent / '.env' if script_dir.name == 'utiles' else None,
        Path.cwd() / '.env',
    ]
    env_locations = [loc for loc in env_locations if loc]
    
    print("🔍 Buscando archivo .env en:")
    env_found = None
    for loc in env_locations:
        exists = loc.exists()
        readable = loc.is_file() and os.access(loc, os.R_OK) if exists else False
        print(f"   {'✅' if exists else '❌'} {loc} {'(LEGIBLE)' if readable else '(NO LEGIBLE)' if exists else ''}")
        if exists and readable and not env_found:
            env_found = loc
    print()
    
    if env_found:
        print(f"✅ Archivo .env encontrado: {env_found}")
        print(f"   Tamaño: {env_found.stat().st_size} bytes")
        print(f"   Permisos: {oct(env_found.stat().st_mode)[-3:]}")
        print()
    else:
        print("❌ No se encontró archivo .env legible")
        print()
    
    # 3. Intentar cargar dotenv
    print("📦 Intentando cargar python-dotenv...")
    try:
        from dotenv import load_dotenv
        print("   ✅ Módulo dotenv disponible")
        
        if env_found:
            result = load_dotenv(env_found)
            print(f"   {'✅' if result else '⚠️'} load_dotenv() retornó: {result}")
        else:
            result = load_dotenv()
            print(f"   {'✅' if result else '⚠️'} load_dotenv() (auto) retornó: {result}")
    except ImportError:
        print("   ❌ Módulo dotenv NO disponible - instalar con: pip install python-dotenv")
        return False
    print()
    
    # 4. Verificar variables de entorno requeridas
    print("🔐 Verificando variables de entorno requeridas:")
    required_vars = {
        'AIRTABLE_TOKEN': 'Personal Access Token (preferido)',
        'AIRTABLE_API_KEY': 'API Key (legacy, alternativa)',
        'AIRTABLE_BASE_ID': 'ID de la base de Airtable',
        'AIRTABLE_TABLE_NAME': 'Nombre de la tabla',
    }
    
    mysql_vars = {
        'MYSQL_HOST': 'Host de MySQL (o DB_HOST)',
        'MYSQL_USER': 'Usuario de MySQL (o DB_USERNAME)',
        'MYSQL_PASSWORD': 'Contraseña de MySQL (o DB_PASS)',
        'MYSQL_DATABASE': 'Base de datos (o DB_NAME)',
    }
    
    all_ok = True
    
    # Verificar token de Airtable (al menos uno debe estar presente)
    has_token = bool(os.getenv('AIRTABLE_TOKEN'))
    has_key = bool(os.getenv('AIRTABLE_API_KEY'))
    
    if has_token:
        token_value = os.getenv('AIRTABLE_TOKEN')
        masked = token_value[:8] + '...' + token_value[-4:] if len(token_value) > 12 else '***'
        print(f"   ✅ AIRTABLE_TOKEN: {masked} (longitud: {len(token_value)})")
    elif has_key:
        key_value = os.getenv('AIRTABLE_API_KEY')
        masked = key_value[:8] + '...' + key_value[-4:] if len(key_value) > 12 else '***'
        print(f"   ⚠️ AIRTABLE_API_KEY: {masked} (legacy, considerar migrar a TOKEN)")
    else:
        print(f"   ❌ AIRTABLE_TOKEN o AIRTABLE_API_KEY: NO ENCONTRADO")
        all_ok = False
    
    # Verificar otras variables de Airtable
    for var, desc in list(required_vars.items())[2:]:  # Skip token vars ya verificadas
        value = os.getenv(var)
        if value:
            # Mostrar solo primeros/últimos caracteres para seguridad
            if len(value) > 10:
                masked = value[:8] + '...' + value[-4:]
            else:
                masked = value
            print(f"   ✅ {var}: {masked}")
        else:
            print(f"   ❌ {var}: NO ENCONTRADO - {desc}")
            all_ok = False
    
    print()
    print("🗄️ Verificando variables de MySQL:")
    
    # Para MySQL, verificar con fallback a DB_*
    mysql_checks = [
        ('MYSQL_HOST', 'DB_HOST'),
        ('MYSQL_USER', 'DB_USERNAME'),
        ('MYSQL_PASSWORD', 'DB_PASS'),
        ('MYSQL_DATABASE', 'DB_NAME'),
    ]
    
    for primary, fallback in mysql_checks:
        value = os.getenv(primary) or os.getenv(fallback)
        if value:
            # Enmascarar contraseñas
            if 'PASS' in primary or 'PASSWORD' in primary:
                masked = '***'
            else:
                masked = value
            source = primary if os.getenv(primary) else f"{fallback} (fallback)"
            print(f"   ✅ {primary}: {masked} (desde {source})")
        else:
            print(f"   ❌ {primary} o {fallback}: NO ENCONTRADO")
            all_ok = False
    
    print()
    print("=" * 60)
    
    if all_ok:
        print("✅ CONFIGURACIÓN COMPLETA - El script debería funcionar")
    else:
        print("❌ CONFIGURACIÓN INCOMPLETA - Faltan variables de entorno")
        print()
        print("💡 Soluciones:")
        print("   1. Verificar que el archivo .env existe en la raíz del proyecto")
        print("   2. Verificar permisos del archivo .env (debe ser legible)")
        print("   3. Verificar que las variables están correctamente definidas en .env")
        print("   4. Si usas systemd/supervisor, cargar .env en el servicio")
        print("   5. Alternativamente, definir variables en /etc/environment o shell profile")
    
    print("=" * 60)
    print()
    
    return all_ok

if __name__ == '__main__':
    success = check_environment()
    sys.exit(0 if success else 1)
