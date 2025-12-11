import requests
import urllib.parse
import mysql.connector
import argparse
import time
import math
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()
DESTINOS = {
    "ASPP": "ASERRADERO PUERTO PIRAY",
    "PPE": "PLANTA PUERTO ESPERANZA",
}
# Configuración Airtable
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
# New preferred name used by Airtable: AIRTABLE_TOKEN (personal access token / PAT)
AIRTABLE_TOKEN = os.getenv("AIRTABLE_TOKEN")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME")
# Allow creating placeholder movils when patente is missing (set to 'true' to enable)
ALLOW_PLACEHOLDER_MOVIL = os.getenv('ALLOW_PLACEHOLDER_MOVIL', 'false').lower() in ('1', 'true', 'yes')
PLACEHOLDER_PREFIX = os.getenv('PLACEHOLDER_MOVIL_PREFIX', 'UNKNOWN')

# Basic validation of required environment variables so we fail fast with
# actionable messages instead of receiving a 404 from the Airtable API.
missing = []
# Require either AIRTABLE_TOKEN (preferred) or AIRTABLE_API_KEY (fallback)
if not (AIRTABLE_TOKEN or AIRTABLE_API_KEY):
    missing.append('AIRTABLE_TOKEN or AIRTABLE_API_KEY')
if not AIRTABLE_BASE_ID:
    missing.append('AIRTABLE_BASE_ID')
if not AIRTABLE_TABLE_NAME:
    missing.append('AIRTABLE_TABLE_NAME')
if missing:
    print({"error": "missing_env_vars", "message": f"Missing environment variables: {', '.join(missing)}"})
    raise SystemExit(2)

# URL-encode the table name in case it contains spaces or special chars.
encoded_table = urllib.parse.quote(AIRTABLE_TABLE_NAME, safe='')
AIRTABLE_URL = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{encoded_table}"

def build_airtable_headers():
    # Prefer AIRTABLE_TOKEN (newer PAT style). Fall back to AIRTABLE_API_KEY
    token = AIRTABLE_TOKEN or AIRTABLE_API_KEY
    if not token:
        return None
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

HEADERS = build_airtable_headers()


def fetch_airtable_records(url, headers):
    """Fetch all records from Airtable using pagination and retries.

    Returns a list of all records across pages. Retries on 429 and 5xx with
    exponential backoff. Raises RuntimeError on unrecoverable errors.
    """
    all_records = []
    offset = None
    max_retries = 5

    while True:
        params = {}
        if offset:
            params['offset'] = offset

        attempt = 0
        while True:
            try:
                resp = requests.get(url, headers=headers, params=params, timeout=30)
            except requests.RequestException as e:
                attempt += 1
                if attempt > max_retries:
                    raise RuntimeError(f"Network error while contacting Airtable after {max_retries} attempts: {e}")
                sleep = min(2 ** attempt, 60)
                time.sleep(sleep)
                continue

            # Parse JSON
            try:
                data = resp.json()
            except ValueError:
                raise RuntimeError(f"Airtable returned non-JSON response (status {resp.status_code}): {resp.text}")

            # Handle rate limits and server errors with retry/backoff
            if resp.status_code == 429 or 500 <= resp.status_code < 600:
                attempt += 1
                if attempt > max_retries:
                    raise RuntimeError(f"Airtable returned status {resp.status_code} after {max_retries} retries")
                # If Airtable provides Retry-After, respect it
                retry_after = resp.headers.get('Retry-After')
                if retry_after:
                    try:
                        wait = int(retry_after)
                    except ValueError:
                        wait = min(2 ** attempt, 60)
                else:
                    wait = min(2 ** attempt, 60)
                time.sleep(wait)
                continue

            # If Airtable returns an error shape like {'error': 'NOT_FOUND'} or {'error': {...}}
            if isinstance(data, dict) and "error" in data:
                err = data.get("error")
                if isinstance(err, dict):
                    msg = err.get("message") or err.get("type") or str(err)
                else:
                    msg = str(err)
                if resp.status_code == 404:
                    raise RuntimeError(
                        f"Airtable API 404 Not Found. Check AIRTABLE_BASE_ID and AIRTABLE_TABLE_NAME. "
                        f"Resolved URL: {url} (ensure table name is correct and URL-encoded)."
                    )
                raise RuntimeError(f"Airtable API error (status {resp.status_code}): {msg}")

            # Successful response should include 'records'
            if not isinstance(data, dict) or "records" not in data:
                raise RuntimeError(f"Unexpected Airtable response shape (status {resp.status_code}): {data}")

            # Append records and handle pagination
            page_records = data.get('records', [])
            all_records.extend(page_records)
            offset = data.get('offset')
            break

        if not offset:
            break

    return all_records


##########################
# Database helper functions
##########################

def get_or_create_predio(cursor, predio_id):
    """Lookup or create predio by its id (not nombre). 
    
    The Airtable 'Origen' field contains the predio id (e.g. '59400').
    If the predio exists by id, return it; otherwise create a new predio 
    with that id and a default nombre.
    """
    table = 'moviles_predios'
    if not predio_id:
        return None
    
    # Try to parse as int
    try:
        pid = int(predio_id)
    except Exception:
        # If it's not numeric, return None (or you can insert with that string as nombre)
        return None
    
    # Check if predio with this id exists
    cursor.execute(f"SELECT id FROM {table} WHERE id = %s", (pid,))
    row = cursor.fetchone()
    if row:
        return row[0]
    
    # Create new predio with given id and a default nombre
    # Note: if your schema has id as auto-increment, you may need to adjust this logic
    # For now, we'll insert with explicit id
    cursor.execute(f"INSERT INTO {table} (id, nombre) VALUES (%s, %s)", (pid, f"Predio {pid}"))
    return cursor.lastrowid if cursor.lastrowid else pid


def get_or_create_personal(cursor, cuit, fields, empresa_id=None):
    table = 'moviles_personal'
    cursor.execute(f"SELECT id FROM {table} WHERE cuit = %s", (cuit,))
    row = cursor.fetchone()
    if row:
        return row[0]

    nombre = fields.get('Chofer_nombre') or fields.get('Chofer') or fields.get('Nombre') or ''
    apellido = fields.get('Chofer_apellido') or ''
    dni = fields.get('DNI') or ''

    # Determine fecha_nacimiento: try common field names and formats, otherwise use default
    fecha_nac_raw = fields.get('Fecha_Nacimiento') or fields.get('fecha_nacimiento') or fields.get('FechaNacimiento') or fields.get('Fecha de Nacimiento')
    fecha_nac = None
    if fecha_nac_raw:
        from datetime import datetime
        # Try ISO or common formats
        for fmt in (None, '%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
            try:
                if fmt is None:
                    # try fromisoformat (handles many ISO variants)
                    fecha_nac = datetime.fromisoformat(fecha_nac_raw).date()
                else:
                    fecha_nac = datetime.strptime(fecha_nac_raw, fmt).date()
                break
            except Exception:
                fecha_nac = None
                continue

    # If still not parsed, set a safe default (indicates unknown)
    if not fecha_nac:
        fecha_nac = '1900-01-01'

    cursor.execute(
        f"INSERT INTO {table} (nombre, apellido, dni, cuit, baja, empresa_id, fecha_nacimiento) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (nombre, apellido, dni, cuit, False, empresa_id, fecha_nac),
    )
    return cursor.lastrowid


def get_or_create_movil(cursor, patente, fields, empresa_id=None):
    table = 'moviles_movil'
    cursor.execute(f"SELECT id FROM {table} WHERE patente = %s", (patente,))
    row = cursor.fetchone()
    if row:
        return row[0]

    marca = fields.get('Marca') or fields.get('marca') or ''
    modelo = fields.get('Modelo') or fields.get('modelo') or ''
    anio = None
    try:
        anio_val = fields.get('Anio') or fields.get('anio') or fields.get('Año')
        if anio_val:
            anio = int(anio_val)
    except Exception:
        anio = None
    # Ensure anio is non-null to avoid inserting NULL into NOT NULL column; use 0 as safe default
    if anio is None:
        anio = 0

    cursor.execute(
        f"INSERT INTO {table} (empresa_id, patente, marca, modelo, anio, baja) VALUES (%s, %s, %s, %s, %s, %s)",
        (empresa_id, patente, marca, modelo, anio, False),
    )
    return cursor.lastrowid


def normalize_patente(value):
    """Normalize different Airtable shapes for patente into a string or None."""
    if not value:
        return None
    # If it's a list, take first item
    if isinstance(value, (list, tuple)) and value:
        first = value[0]
        return normalize_patente(first)
    # If it's a dict, try common keys
    if isinstance(value, dict):
        return value.get('name') or value.get('Patente') or value.get('patente') or None
    # Otherwise, coerce to string
    try:
        s = str(value).strip()
        return s if s else None
    except Exception:
        return None


def extract_patente_from_fields(fields):
    """Try multiple candidate fields and regex extraction to find a patente string."""
    # Candidate field names commonly used
    candidates = [
        'Patente', 'patente', 'Patente_text', 'Patente (texto)', 'Vehiculo', 'Vehículo', 'Vehiculo_Patente',
        'Movil', 'movil', 'vehiculo', 'vehicle', 'vehicle_plate', 'Placa', 'placa', 'Plate', 'plate',
        'Descripcion', 'Descripcion del Vehiculo', 'Observaciones', 'observaciones', 'Notas', 'note',
    ]

    # First try direct candidates
    for key in candidates:
        if key in fields:
            val = fields.get(key)
            p = normalize_patente(val)
            if p:
                return p, key

    # If not found, try to search in free text fields for a plate-like token
    text_candidates = [fields.get('Observaciones'), fields.get('Descripcion'), fields.get('Notas'), fields.get('note')]
    for txt in text_candidates:
        if not txt:
            continue
        try:
            s = str(txt)
        except Exception:
            continue
        # Quick regex: look for alphanumeric tokens of length 4-8 (common plate-like)
        import re

        matches = re.findall(r"[A-Z0-9-]{4,8}", s.upper())
        for m in matches:
            # rudimentary filter: must contain at least one letter and one digit
            if re.search(r"[A-Z]", m) and re.search(r"[0-9]", m):
                return m, 'regex_from_text'

    return None, None


def map_destino(raw):
    """Map a raw destino value using DESTINOS dict. Return the detail string.

    If DESTINOS value is a dict, prefer 'detalle' or 'detail' keys; otherwise stringify.
    """
    if raw is None:
        return None
    # Try direct match
    val = DESTINOS.get(raw)
    if val is None:
        # try trimmed and upper/lower variants
        key = str(raw).strip()
        val = DESTINOS.get(key)
        if val is None:
            val = DESTINOS.get(key.upper())
            if val is None:
                val = DESTINOS.get(key.title())
    if val is None:
        return raw
    if isinstance(val, dict):
        return val.get('detalle') or val.get('detail') or str(val)
    return val


def get_numeric_field(fields, candidates, default=0.0):
    """Try multiple candidate keys in fields and coerce to float safely."""
    for key in candidates:
        if key in fields:
            v = fields.get(key)
            try:
                return float(v or 0)
            except Exception:
                # Try to extract numeric from string
                try:
                    import re

                    s = str(v)
                    m = re.search(r"[-+]?[0-9]*\.?[0-9]+", s.replace(',', '.'))
                    if m:
                        return float(m.group(0))
                except Exception:
                    continue
    return float(default)


def insert_viaje(cursor, movil_id, cliente_id, area_id, fecha, origen_id, destino, producto, tn_pulpable, tn_aserrable, tn_chip, sin_actividad, motivo, observaciones, personal_id):
    table = 'moviles_viajes'
    cursor.execute(
        f"""
        INSERT INTO {table} (movil_id, cliente_id, area_id, fecha, origen_id, destino, producto, tn_pulpable, tn_aserrable, tn_chip, 
        sin_actividad, motivo_sin_actividad, observaciones, personal_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            movil_id,
            cliente_id,
            area_id,
            fecha,
            origen_id,
            destino,
            producto,
            tn_pulpable,
            tn_aserrable,
            tn_chip,
            sin_actividad,
            motivo,
            observaciones,
            personal_id
        ),
    )
    return cursor.lastrowid


def get_table_columns(cursor, table_name):
    cursor.execute(f"SHOW COLUMNS FROM {table_name}")
    rows = cursor.fetchall()
    return [r[0] for r in rows]


def parse_args():
    """Parsea los argumentos de la línea de comandos necesarios para sincronizar registros de Airtable a MySQL.

    Opciones:
        --dry-run   : Si se especifica, recupera e imprime los registros sin modificar la base de datos ni borrar registros en Airtable.
        --limit     : Límite del número de registros a imprimir en modo dry-run (entero). 0 significa sin límite.
        --confirm   : Si se especifica, permite realizar las escrituras en la base de datos y borrar registros en Airtable. Usar con precaución.

    Retorna:
        argparse.Namespace con los argumentos parseados:
            - dry_run (bool)
            - limit (int)
            - confirm (bool)
    """
    p = argparse.ArgumentParser(description="Sync Airtable records to MySQL")
    p.add_argument("--dry-run", action="store_true", help="Si se especifica, recupera e imprime los registros sin modificar la base de datos ni borrar registros en Airtable.")
    p.add_argument("--limit", type=int, default=0, help="Límite del número de registros a imprimir en modo dry-run (0 = sin límite)")
    p.add_argument("--confirm", action="store_true", help="Si se especifica, permite realizar las escrituras en la base de datos y borrar registros en Airtable. Usar con precaución.")
    p.add_argument("--mysql", action="store_true", help="Realiza inserciones/actualizaciones en MySQL pero no borra los registros en Airtable.")
    return p.parse_args()


def main():
    args = parse_args()

    if not HEADERS:
        print({"error": "missing_auth_token", "message": "No AIRTABLE_TOKEN or AIRTABLE_API_KEY found in environment"})
        raise SystemExit(2)

    try:
        records = fetch_airtable_records(AIRTABLE_URL, HEADERS)
    except RuntimeError as e:
        print({"error": "airtable_fetch_failed", "message": str(e)})
        raise SystemExit(1)

    print({"info": "fetched_records_count", "count": len(records)})

    # Dry-run: print records and exit
    if args.dry_run:
        limit = args.limit if args.limit > 0 else len(records)
        for i, record in enumerate(records[:limit]):
            print({"record_index": i, "id": record.get("id"), "fields": record.get("fields", {})})
        print({"info": "dry_run_complete", "printed": min(limit, len(records))})
        return

    # Configuración MySQL
    mysql_conn = mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE")
    )
    cursor = mysql_conn.cursor()

    for record in records:
        fields = record.get("fields", {})
        # Simulation mode unless --mysql or --confirm is provided
        if not args.confirm and not args.mysql:
            print({
                "action": "simulate_insert_or_update",
                "record_id": record.get("id"),
                "fields": fields,
            })
            print({"action": "simulate_delete", "record_id": record.get("id")})
            continue

        # Confirmed mode: perform DB insert and delete from Airtable
        # Resolve empresa and area from environment (support multiple env var names)
        empresa_env = os.getenv('MOVILES_EMPRESA_ID') or os.getenv('EMPRESA_ID') or os.getenv('COMPANY_ID')
        area_env = os.getenv('MOVILES_AREA_ID') or os.getenv('AREA_ID')
        try:
            empresa_id = (empresa_env) if empresa_env else None
        except Exception:
            empresa_id = None
        try:
            area_id = (area_env) if area_env else None
        except Exception:
            area_id = None

        # Parse fecha into YYYY-MM-DD (attempt common formats)
        fecha_val = fields.get('Fecha') or fields.get('fecha')
        fecha = None
        if fecha_val:
            from datetime import datetime

            try:
                # Try ISO first
                fecha = datetime.fromisoformat(fecha_val).date()
            except Exception:
                try:
                    # Try common dd/mm/YYYY or dd-mm-YYYY
                    for fmt in ('%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d'):
                        try:
                            fecha = datetime.strptime(fecha_val, fmt).date()
                            break
                        except Exception:
                            continue
                except Exception:
                    fecha = None

        # Resolve origen predio id (Airtable sends predio id in 'Origen' field, e.g. '59400')
        origen_value = None
        origen_field = fields.get('Origen') or fields.get('origen')
        if isinstance(origen_field, dict):
            # If it's an object, try common keys for id
            origen_value = origen_field.get('id') or origen_field.get('Id') or origen_field.get('ID')
        else:
            # Otherwise, treat the value as the predio id directly
            origen_value = origen_field

        # Destino and producto
        raw_destino = fields.get('Destino') or fields.get('destino') or ''
        destino = map_destino(raw_destino)
        producto = fields.get('Producto') or fields.get('producto') or ''

        # Quantities
        tn_pulpable = get_numeric_field(fields, ['TNPulpable', 'TN_Pulpable', 'TNPulpable', 'TNPulpable', 'TNPulpable', 'TNPulpable', 'TNPulpable', 'TNPulpable', 'TNPulpable', 'TNPulpable', 'TNPulpable', 'TNPulpable', 'TN_Pulpable', 'TNPulpable', 'TNPulpable', 'TNPulpable', 'TNPulpable', 'TN Pulpable', 'TNPulpable', 'TNPulpable', 'TNPulpable', 'TNPulpable', 'TNPulpable', 'TNPulpable'], 0)
        tn_aserrable = get_numeric_field(fields, ['TNAserrable', 'TN_Aserrable', 'TN_Rollos', 'TNAserrable', 'TNAserrable', 'TNAserrable', 'TNAserrable'], 0)
        tn_chip = get_numeric_field(fields, ['TNChips', 'TN_Chips', 'TN_Chip', 'TNChips', 'TNChips'], 0)

        sin_actividad = bool(fields.get('Sin_Actividad') or fields.get('sin_actividad') or False)
        motivo = fields.get('Motivo_Sin_Actividad') or fields.get('motivo') or None
        observaciones = fields.get('Observaciones') or fields.get('observaciones') or None

        # Chofer lookup by CUIT. If CUIT isn't in its own field but 'Chofer' contains a numeric CUIT, use that.
        cuit = fields.get('CUIT') or fields.get('Cuit') or fields.get('cuit') or fields.get('Chofer_CUIT')
        chofer_field = fields.get('Chofer') or fields.get('chofer') or ''
        # If cuit is missing and chofer_field looks like a numeric CUIT (10-12 digits), use it
        if not cuit and chofer_field:
            import re
            m = re.search(r"(\d{10,12})", str(chofer_field))
            if m:
                cuit = m.group(1)

        # Patente: try multiple extraction strategies
        patente_raw = fields.get('Patente') or fields.get('patente')
        patente, found_in = extract_patente_from_fields(fields)
        if not patente:
            patente = normalize_patente(patente_raw)

        if not patente:
            print({"warning": "missing_patente", "record_id": record.get('id'), "raw": patente_raw, "found_in": found_in})

        # Ensure origin predio exists (lookup/create by predio id)
        origen_id = None
        if origen_value:
            origen_id = get_or_create_predio(cursor, origen_value)

        # Ensure personal (chofer) exists (by cuit). If no cuit, try name lookup by 'Chofer'
        personal_id = None
        if cuit:
            personal_id = get_or_create_personal(cursor, cuit, fields, empresa_id=empresa_id)
        else:
            # Try to find by name
            chofer_name = fields.get('Chofer') or ''
            if chofer_name:
                # naive split
                parts = chofer_name.split()
                nombre = parts[0] if parts else ''
                apellido = ' '.join(parts[1:]) if len(parts) > 1 else ''
                # Try to find existing by nombre and apellido
                cursor.execute("SELECT id FROM moviles_personal WHERE nombre = %s AND apellido = %s", (nombre, apellido))
                r = cursor.fetchone()
                if r:
                    personal_id = r[0]
                else:
                    # create without cuit
                    personal_id = get_or_create_personal(cursor, '', fields, empresa_id=empresa_id)

        # Ensure movil exists
        movil_id = None
        if patente:
            try:
                movil_id = get_or_create_movil(cursor, patente, fields, empresa_id=empresa_id)
                if not movil_id:
                    print({"error": "movil_creation_failed", "patente": patente, "record_id": record.get('id')})
            except Exception as e:
                movil_id = None
                print({"error": "movil_exception", "patente": patente, "record_id": record.get('id'), "exception": str(e)})

        if not movil_id:
            # If allowed, create a placeholder movil
            if ALLOW_PLACEHOLDER_MOVIL:
                import random
                suffix = ''.join(random.choices('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=4))
                placeholder_patente = f"{PLACEHOLDER_PREFIX}-{suffix}"
                try:
                    movil_id = get_or_create_movil(cursor, placeholder_patente, fields, empresa_id=empresa_id)
                    print({"info": "created_placeholder_movil", "patente": placeholder_patente, "record_id": record.get('id'), "movil_id": movil_id})
                except Exception as e:
                    print({"error": "placeholder_movil_failed", "record_id": record.get('id'), "exception": str(e)})
                    continue
            else:
                print({"error": "missing_movil_id", "record_id": record.get('id'), "patente": patente})
                # skip this record to avoid DB constraint violation
                continue

        # Insert viaje
        try:
            # Dynamically build insert based on existing columns in moviles_viajes
            cols = get_table_columns(cursor, 'moviles_viajes')
            insert_cols = []
            insert_vals = []

            if 'movil_id' in cols:
                insert_cols.append('movil_id')
                insert_vals.append(movil_id)
            if 'cliente_id' in cols:
                # Map empresa_id env to cliente_id if provided
                insert_cols.append('cliente_id')
                insert_vals.append(empresa_id)
            if 'area_id' in cols:
                insert_cols.append('area_id')
                insert_vals.append(area_id)
            if 'fecha' in cols:
                insert_cols.append('fecha')
                insert_vals.append(fecha)
            if 'origen_id' in cols and not sin_actividad and origen_id is not None:
                insert_cols.append('origen_id')
                insert_vals.append(origen_id)
            if 'destino' in cols:
                insert_cols.append('destino')
                insert_vals.append(destino)
            if 'producto' in cols:
                insert_cols.append('producto')
                insert_vals.append(producto)
            if 'tn_pulpable' in cols:
                insert_cols.append('tn_pulpable')
                insert_vals.append(tn_pulpable)
            if 'tn_aserrable' in cols:
                insert_cols.append('tn_aserrable')
                insert_vals.append(tn_aserrable)
            if 'tn_chip' in cols:
                insert_cols.append('tn_chip')
                insert_vals.append(tn_chip)
            if 'sin_actividad' in cols:
                insert_cols.append('sin_actividad')
                insert_vals.append(sin_actividad)
            if 'motivo_sin_actividad' in cols:
                insert_cols.append('motivo_sin_actividad')
                insert_vals.append(motivo)
            if 'observaciones' in cols:
                insert_cols.append('observaciones')
                insert_vals.append(observaciones)
            # Map chofer: prefer chofer_id if present
            if 'chofer_id' in cols and personal_id:
                insert_cols.append('chofer_id')
                insert_vals.append(personal_id)
            # Also map personal_id column if present (user requested mapping from chofer)
            if 'personal_id' in cols and personal_id:
                insert_cols.append('personal_id')
                insert_vals.append(personal_id)

            if 'record_id' in cols:
                # Include Airtable record id in insert/update
                airtable_id = record.get('id')
                insert_cols.append('record_id')
                insert_vals.append(airtable_id)

                # Check if a row with this record_id already exists
                cursor.execute("SELECT id FROM moviles_viajes WHERE record_id = %s", (airtable_id,))
                existing = cursor.fetchone()
                if existing:
                    # Update existing row
                    set_parts = []
                    set_vals = []
                    for col, val in zip(insert_cols, insert_vals):
                        # skip record_id in set (it's same) or you can include it
                        if col == 'record_id':
                            continue
                        set_parts.append(f"{col} = %s")
                        set_vals.append(val)
                    # If the table has updated_at, set it to now
                    if 'updated_at' in cols:
                        set_parts.append('updated_at = %s')
                        set_vals.append(datetime.utcnow())
                    if set_parts:
                        set_sql = ','.join(set_parts)
                        sql = f"UPDATE moviles_viajes SET {set_sql} WHERE id = %s"
                        cursor.execute(sql, tuple(set_vals) + (existing[0],))
                    viaje_id = existing[0]
                else:
                    # Insert new row (with record_id included)
                    # If table supports created_at or updated_at, add current timestamps for insert
                    if 'created_at' in cols and 'created_at' not in insert_cols:
                        insert_cols.append('created_at')
                        insert_vals.append(datetime.utcnow())
                    if 'updated_at' in cols and 'updated_at' not in insert_cols:
                        insert_cols.append('updated_at')
                        insert_vals.append(datetime.utcnow())

                    if not insert_cols:
                        raise RuntimeError('No matching columns found in moviles_viajes to insert data')
                    placeholders = ','.join(['%s'] * len(insert_vals))
                    cols_sql = ','.join(insert_cols)
                    sql = f"INSERT INTO moviles_viajes ({cols_sql}) VALUES ({placeholders})"
                    cursor.execute(sql, tuple(insert_vals))
                    viaje_id = cursor.lastrowid
            else:
                # No record_id column: simple insert
                # If table supports created_at or updated_at, add current timestamps for insert
                if 'created_at' in cols and 'created_at' not in insert_cols:
                    insert_cols.append('created_at')
                    insert_vals.append(datetime.utcnow())
                if 'updated_at' in cols and 'updated_at' not in insert_cols:
                    insert_cols.append('updated_at')
                    insert_vals.append(datetime.utcnow())

                if not insert_cols:
                    raise RuntimeError('No matching columns found in moviles_viajes to insert data')
                placeholders = ','.join(['%s'] * len(insert_vals))
                cols_sql = ','.join(insert_cols)
                sql = f"INSERT INTO moviles_viajes ({cols_sql}) VALUES ({placeholders})"
                cursor.execute(sql, tuple(insert_vals))
                viaje_id = cursor.lastrowid
        except Exception as e:
            print({"error": "insert_viaje_failed", "record_id": record.get('id'), "error": str(e)})
            continue

        # If insert/update succeeded, optionally delete the record from Airtable
        if args.confirm:
            try:
                resp = requests.delete(f"{AIRTABLE_URL}/{record['id']}", headers=HEADERS, timeout=30)
            except requests.RequestException as e:
                print({"warning": "failed_to_delete_airtable_record_network", "record_id": record.get("id"), "error": str(e)})
            else:
                if resp.status_code not in (200, 202, 204):
                    # Try to include JSON error body if present
                    body = None
                    try:
                        body = resp.json()
                    except Exception:
                        body = resp.text
                    msg = {"error": "airtable_delete_failed", "record_id": record.get("id"), "status": resp.status_code, "body": body}
                    # Add hint for auth/permissions
                    if resp.status_code in (401, 403):
                        msg['hint'] = 'Check AIRTABLE_TOKEN permissions (needs data.records:delete) and that the token has access to the base.'
                    print(msg)
                else:
                    print({"info": "airtable_record_deleted", "record_id": record.get("id"), "status": resp.status_code})

    mysql_conn.commit()
    cursor.close()
    mysql_conn.close()


if __name__ == "__main__":
    main()