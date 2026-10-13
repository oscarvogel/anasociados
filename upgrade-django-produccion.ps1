<#
.SYNOPSIS
    Actualiza Django en el VPS de AN & Asociados (4.1 -> 5.2.18 LTS).

.DESCRIPTION
    Ejecuta por SSH todo el procedimiento: descubrimiento, backup, venv nuevo
    al lado del actual, verificacion, git pull, swap y reinicio de servicios.
    Si algo falla despues del swap, hace rollback automatico.

    La base de datos solo se toca para el backup: antes de seguir verifica que
    no haya migraciones pendientes, y frena si las hay.

.PARAMETER Server
    Host del VPS. Default: vps-3177145-x.dattaweb.com

.PARAMETER Port
    Puerto SSH. Default: 5438

.PARAMETER User
    Usuario SSH. Default: root

.PARAMETER ProjectPath
    Directorio del proyecto en el servidor. Default: /var/www/an

.PARAMETER VenvPath
    Venv actual. Default: /var/www/venv

.PARAMETER WebService
    Servicio web en systemd. Si se omite, se autodetecta.

.PARAMETER CeleryService
    Servicio de Celery. Si se omite, se autodetecta.

.PARAMETER AutoConfirm
    No pedir confirmacion antes de parar servicios y hacer el swap.

.PARAMETER RollbackOnly
    Solo revertir: restaurar el venv anterior.

.EXAMPLE
    .\upgrade-django-produccion.ps1 -AutoConfirm

.EXAMPLE
    .\upgrade-django-produccion.ps1 -WebService gunicorn -CeleryService celery@core_an

.EXAMPLE
    .\upgrade-django-produccion.ps1 -RollbackOnly
#>
[CmdletBinding()]
param(
    [string]$Server       = 'vps-3177145-x.dattaweb.com',
    [int]   $Port         = 5438,
    [string]$User         = 'root',
    [string]$ProjectPath  = '/var/www/an',
    [string]$VenvPath     = '/var/www/venv',
    [string]$WebService,
    [string]$CeleryService,
    [switch]$AutoConfirm,
    [switch]$RollbackOnly
)

$ErrorActionPreference = 'Stop'
$target = "$User@$Server"
$sshOpts = @('-p', $Port, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15',
             '-o', 'StrictHostKeyChecking=accept-new')

# ---------------------------------------------------------------------------
# Presentacion
# ---------------------------------------------------------------------------
function Step($m) {
    $pad = '=' * [Math]::Max(3, 64 - $m.Length)
    Write-Host ("`n=== " + $m + " " + $pad) -ForegroundColor Cyan
}
function Ok($m)   { Write-Host ("    OK     " + $m) -ForegroundColor Green }
function Warn($m) { Write-Host ("    AVISO  " + $m) -ForegroundColor Yellow }
function Die($m)  { Write-Host ("`n    FALLO  " + $m) -ForegroundColor Red; exit 1 }
function Hint($m) { Write-Host ("    > " + $m) -ForegroundColor DarkGray }

# ---------------------------------------------------------------------------
# SSH: envuelve la llamada para que el stderr de ssh no dispare el
# ErrorActionPreference='Stop' de PowerShell. Devuelve Output y ExitCode.
# ---------------------------------------------------------------------------
function Invoke-Ssh {
    param(
        [string[]]$InputScript,
        [string]$Cmd,
        [int]$TimeoutSec = 15
    )
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $opts = @('-p', $Port, '-o', "ConnectTimeout=$TimeoutSec",
                  '-o', 'StrictHostKeyChecking=accept-new')
        if ($Cmd) {
            $out = & ssh @opts $target $Cmd 2>&1
        } else {
            $out = $InputScript | & ssh @opts $target 'bash -s' 2>&1
        }
        $rc = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $prev
    }
    return [pscustomobject]@{ Out = @($out); Rc = $rc }
}

function Show($r) { $r.Out | ForEach-Object { Write-Host "    $_" } }

# ---------------------------------------------------------------------------
Write-Host "AN & Asociados - Upgrade de Django en produccion" -ForegroundColor White
Write-Host "Destino: $target :$Port   proyecto: $ProjectPath`n"

# ---------------------------------------------------------------------------
# Fase 0: conexion
# ---------------------------------------------------------------------------
Step "Fase 0 - Conexion"

$probe = Invoke-Ssh -Cmd 'echo "conectado como $(id -un) en $(hostname)"'
if ($probe.Rc -ne 0) {
    Write-Host ("    ssh devolvio: " + ($probe.Out -join ' | ')) -ForegroundColor DarkGray
    Hint "Cargá la clave publica en el servidor como root:"
    $pub = (Get-Content "$env:USERPROFILE\.ssh\id_ed25519_anasociados.pub" -ErrorAction SilentlyContinue)
    if ($pub) { Hint ("echo '" + $pub + "' >> /root/.ssh/authorized_keys") }
    Die "no se pudo entrar por clave publica. Produccion NO fue tocada."
}
Show $probe | Out-Null
Ok (($probe.Out | Select-Object -Last 1))

# ---------------------------------------------------------------------------
# Autodetectar servicios
# ---------------------------------------------------------------------------
if (-not $WebService -or -not $CeleryService) {
    Step "Fase 0b - Autodetectar servicios"
    $det = Invoke-Ssh -Cmd @'
systemctl list-units --type=service --state=running --no-legend 2>/dev/null | awk '{print $1}' | grep -Ei 'gunicorn|uwsgi|django' | head -1
systemctl list-units --type=service --state=running --no-legend 2>/dev/null | awk '{print $1}' | grep -Ei 'celery' | head -1
supervisorctl status 2>/dev/null | awk '{print $1}' | grep -Ei 'gunicorn|uwsgi|django' | head -1
supervisorctl status 2>/dev/null | awk '{print $1}' | grep -Ei 'celery' | head -1
'@
    $l = @($det.Out | Where-Object { $_ -and $_ -match '^[a-z0-9@\.\-_]+$' })
    if (-not $WebService)    { $WebService    = ($l | Select-Object -First 1) }
    if (-not $CeleryService) { $CeleryService = ($l | Select-Object -Skip 1 -First 1) }
}

if (-not $RollbackOnly) {
    if ($WebService)    { Ok ("servicio web:    " + $WebService) }    else { Warn "no detecte el servicio web: pasalo con -WebService" }
    if ($CeleryService) { Ok ("servicio celery: " + $CeleryService) } else { Warn "no detecte celery: pasalo con -CeleryService" }
}

# ---------------------------------------------------------------------------
# Bloques bash remotos
# ---------------------------------------------------------------------------
$bashUpgrade = @'
set -uo pipefail

PROJECT="__PROJECT__"
VENV="__VENV__"
WEB="__WEB__"
CELERY="__CELERY__"
STAMP=$(date +%Y%m%d-%H%M%S)
BACKUP="/root/an-backup-$STAMP"
OLD_VENV="${VENV}_ANTES_$STAMP"
NEW_VENV="${VENV}_nuevo_$STAMP"
LOG="$BACKUP/logs.txt"

say()  { echo "REMOTE|$1"; }
ok()   { echo "  OK   $1"; }
die()  { echo "REMOTE|FATAL $1" >&2; exit 1; }
SUDO=""; [ "$(id -u)" -eq 0 ] || SUDO="sudo -n"

cd "$PROJECT" || die "no existe $PROJECT"
mkdir -p "$BACKUP"
exec > >(tee -a "$LOG") 2>&1

say "INICIO"
say " proyecto=$PROJECT"
say " venv=$VENV"
say " web=$WEB celery=$CELERY"
say " backup=$BACKUP"

echo "--- estado actual ---"
[ -d "$VENV" ] || die "no existe el venv $VENV"
OLD_PY=$(ls -1d "$VENV"/bin/python* 2>/dev/null | head -1)
[ -n "$OLD_PY" ] || die "el venv no tiene interprete"
"$OLD_PY" --version || die "el python del venv no corre"

OLD_DJ=$("$OLD_PY" -c 'import django;print(django.get_version())' 2>/dev/null || echo "desconocida")
echo "  Django actual: $OLD_DJ"
if "$OLD_PY" -m pip --version >/dev/null 2>&1; then
  "$OLD_PY" -m pip freeze > "$BACKUP/requirements-ANTES.txt" 2>/dev/null
else
  echo "(el venv actual no tiene pip; se guardara el estado de los site-packages)"
  "$OLD_PY" -m pip freeze > "$BACKUP/requirements-ANTES.txt" 2>/dev/null || \
    ls -1 "$VENV"/lib/python*/site-packages > "$BACKUP/requirements-ANTES.txt"
fi
echo "  packages registrados: $(wc -l < "$BACKUP/requirements-ANTES.txt")"

git rev-parse HEAD > "$BACKUP/git-HEAD-antes.txt" 2>/dev/null || true
git status --porcelain > "$BACKUP/git-status-antes.txt" 2>/dev/null || true
echo "  git HEAD: $(cat "$BACKUP/git-HEAD-antes.txt" 2>/dev/null || echo '?')"
echo "  archivos modificados a mano: $(wc -l < "$BACKUP/git-status-antes.txt")"

echo "--- migraciones pendientes (condicion de freno) ---"
PLAN=$("$OLD_PY" manage.py migrate --plan 2>&1)
echo "$PLAN" | tail -15
if echo "$PLAN" | grep -q "No planned migration operations"; then
  ok "no hay migraciones pendientes"
else
  die "migrate --plan NO dice 'No planned migration operations'. El estado de la base no es el conocido. NO seguir."
fi

echo "--- backup de la base ---"
export PROJECT_DIR="$PROJECT"
MYCNF="$BACKUP/.my.cnf"
"$OLD_PY" - "$MYCNF" <<'PY'
import os, sys
sys.path.insert(0, os.environ["PROJECT_DIR"])
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core_an.settings")
import django; django.setup()
from core_an import settings
d = settings.DATABASES["default"]
with open(sys.argv[1], "w") as fh:
    fh.write("[client]\n")
    fh.write("host=%s\nport=%s\nuser=%s\npassword=%s\n" % (
        d["HOST"], d["PORT"] or 3306, d["USER"], d["PASSWORD"]))
print("archivo de credenciales para mysqldump: %s" % sys.argv[1])
PY
[ -f "$MYCNF" ] || die "no se pudo escribir el archivo de credenciales del dump"
chmod 600 "$MYCNF"

DBNAME=$("$OLD_PY" -c "import os,sys;sys.path.insert(0,'$PROJECT');os.environ.setdefault('DJANGO_SETTINGS_MODULE','core_an.settings');import django;django.setup();from core_an import settings;print(settings.DATABASES['default']['NAME'])")
echo "  base: $DBNAME"

$SUDO mysqldump --defaults-extra-file="$MYCNF" --single-transaction --routines --triggers "$DBNAME" > "$BACKUP/an.sql" 2>"$BACKUP/dump.err"
if [ ! -s "$BACKUP/an.sql" ]; then
  cat "$BACKUP/dump.err" >&2
  die "el dump salio vacio"
fi
NTAB=$(grep -c 'CREATE TABLE' "$BACKUP/an.sql" || true)
echo "  dump: $(du -h "$BACKUP/an.sql" | cut -f1), $NTAB tablas"
[ "${NTAB:-0}" -gt 0 ] || die "el dump no tiene CREATE TABLE: no es restaurable"
ok "backup de la base completo"

say "FASE1_OK"
say "BACKUP=$BACKUP"
say "OLD_VENV=$OLD_VENV"
say "NEW_VENV=$NEW_VENV"
say "OLD_DJANGO=$OLD_DJ"

# --- venv nuevo al lado ----------------------------------------------------
say "FASE2"
echo "--- creando venv nuevo ---"
PYBIN=$(command -v python3 || command -v python) || die "no hay python3 en el sistema"
echo "  interprete base: $($PYBIN --version 2>&1)"
"$PYBIN" -m venv "$NEW_VENV" || die "no se pudo crear el venv nuevo"
"$NEW_VENV/bin/python" -m pip install --upgrade pip setuptools wheel -q 2>/dev/null || echo "  (upgrade de pip omitido)"

cd "$PROJECT" || die "no existe $PROJECT"
echo "--- instalando requirements.txt ---"
"$NEW_VENV/bin/python" -m pip install -r requirements.txt > "$BACKUP/pip-install.log" 2>&1
PIPRC=$?
tail -20 "$BACKUP/pip-install.log"
if [ $PIPRC -ne 0 ]; then
  grep -Ei 'error|could not|conflict|no matching' "$BACKUP/pip-install.log" | head -20 >&2
  die "pip install fallo. Log en $BACKUP/pip-install.log. El venv actual NO se toco."
fi
NEW_DJ=$("$NEW_VENV/bin/python" -c 'import django;print(django.get_version())' 2>/dev/null || echo "NO-INSTALADO")
echo "  Django nuevo: $NEW_DJ"
[ "$NEW_DJ" != "NO-INSTALADO" ] || die "Django no quedo instalado en el venv nuevo"
echo "$NEW_DJ" > "$BACKUP/django-nuevo.txt"
ok "dependencias instaladas"

# --- verificacion (el sitio sigue con el venv viejo) ------------------------
say "FASE3"
echo "--- manage.py check ---"
"$NEW_VENV/bin/python" manage.py check 2>&1 | tail -25
"$NEW_VENV/bin/python" manage.py check >/dev/null 2>&1 || die "manage.py check fallo con el venv nuevo. Produccion NO fue tocada."
ok "check sin errores"

echo "--- smoke test de imports (detecta APIs removidas en Django 5) ---"
"$NEW_VENV/bin/python" - <<'PY'
import os, sys
sys.path.insert(0, os.environ.get("PROJECT_DIR", "."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core_an.settings")
import django; django.setup()
from django.core.management import get_commands
mods = ["core_an.celery", "syh.models", "syh.views", "moviles.models", "moviles.views",
        "usuarios.models", "usuarios.views", "usuarios.middleware", "usuarios.signals",
        "home.views", "utiles.impresiones", "utiles.generador_graficos"]
for m in mods:
    __import__(m)
print("comandos cargados:", len(get_commands()), "| modulos importados:", len(mods))
PY
[ $? -eq 0 ] || die "falla un import: probable API removida en Django 5. Produccion NO fue tocada."
ok "todos los modulos de la app importan"

echo "--- paquetes que cambian ---"
diff <(sort "$BACKUP/requirements-ANTES.txt") <("$NEW_VENV/bin/python" -m pip freeze 2>/dev/null | sort) \
  | grep -E '^[<>]' | head -40 || true

# --- git pull --------------------------------------------------------------
say "FASE4"
DIRTY=$(wc -l < "$BACKUP/git-status-antes.txt")
if [ "$DIRTY" -gt 0 ]; then
  echo "ATENCION: $DIRTY archivos modificados a mano en el servidor:" >&2
  head -20 "$BACKUP/git-status-antes.txt" >&2
  die "codigo del servidor modificado fuera de git. Revisar antes de seguir."
fi
ok "arbol de trabajo limpio"

git fetch origin -q 2>/dev/null || echo "  (aviso: git fetch fallo, revisar red)"
git pull --ff-only origin main 2>&1 | tail -8 || die "git pull no fue fast-forward."
ok "codigo actualizado a $(git rev-parse --short HEAD)"

"$NEW_VENV/bin/python" manage.py check >/dev/null 2>&1 || die "check fallo tras el pull. Produccion NO fue tocada."
"$NEW_VENV/bin/python" manage.py migrate --plan 2>&1 | grep -q "No planned migration operations" \
  || die "el pull trajo migraciones inesperadas."
ok "check y migraciones OK tras el pull"

say "LISTO_PARA_SWAP"
'@

$bashSwap = @'
set -uo pipefail
VENV="__VENV__"; OLD="__OLD__"; NEW="__NEW__"; WEB="__WEB__"; CELERY="__CELERY__"
say(){ echo "REMOTE|$1"; }
SUDO=""; [ "$(id -u)" -eq 0 ] || SUDO="sudo -n"

say "PARANDO"
[ -n "$WEB" ]    && { $SUDO systemctl stop "$WEB"    2>/dev/null || $SUDO supervisorctl stop "$WEB"    2>/dev/null; }
[ -n "$CELERY" ] && { $SUDO systemctl stop "$CELERY" 2>/dev/null || $SUDO supervisorctl stop "$CELERY" 2>/dev/null; }
sleep 2
if pgrep -f 'gunicorn|uwsgi|celery' >/dev/null 2>&1; then
  echo "  aviso: quedan procesos:"; pgrep -af 'gunicorn|uwsgi|celery' | head -4
else
  say "procesos detenidos"
fi

say "SWAP"
[ -d "$NEW" ] || { echo "no existe el venv nuevo $NEW" >&2; exit 1; }
if [ -d "$VENV" ]; then mv "$VENV" "$OLD" || exit 1; fi
mv "$NEW" "$VENV" || { echo "fallo el mv; devolviendo" >&2; [ -d "$OLD" ] && mv "$OLD" "$VENV"; exit 1; }
say "venv nuevo en su lugar"

say "ARRANCANDO"
[ -n "$WEB" ]    && { $SUDO systemctl start "$WEB"    2>/dev/null || $SUDO supervisorctl start "$WEB"    2>/dev/null; }
[ -n "$CELERY" ] && { $SUDO systemctl start "$CELERY" 2>/dev/null || $SUDO supervisorctl start "$CELERY" 2>/dev/null; }
sleep 6

say "VERIFICANDO"
CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 http://127.0.0.1/ 2>/dev/null || echo "000")
echo "  HTTP en 127.0.0.1: $CODE"
case "$CODE" in
  2*|3*) say "http_ok" ;;
  000)   echo "  sin respuesta HTTP" >&2; exit 3 ;;
  404)   echo "  404: puede ser normal si la app no vive en la raiz" ;;
  *)     echo "  HTTP inesperado: $CODE" >&2; exit 3 ;;
esac

echo "--- errores recientes en el log ---"
if [ -n "$WEB" ]; then
  $SUDO journalctl -u "$WEB" -n 120 --no-pager 2>/dev/null \
    | grep -Ei 'traceback|modulenotfound|importerror|attributeerror' | head -8 || true
fi
ps aux | grep -Ei 'gunicorn|uwsgi' | grep -v grep | head -3 || true
say "SWAP_OK"
'@

$bashRollback = @'
set -uo pipefail
VENV="__VENV__"; OLD="__OLD__"; WEB="__WEB__"; CELERY="__CELERY__"
SUDO=""; [ "$(id -u)" -eq 0 ] || SUDO="sudo -n"
[ -n "$WEB" ]    && { $SUDO systemctl stop "$WEB"    2>/dev/null; }
[ -n "$CELERY" ] && { $SUDO systemctl stop "$CELERY" 2>/dev/null; }
if [ -d "$OLD" ]; then
  if [ -d "$VENV" ]; then mv "$VENV" "${VENV}_roto_$(date +%H%M%S)"; fi
  mv "$OLD" "$VENV" && echo "venv anterior restaurado en $VENV"
else
  echo "ATENCION: no se encontro el venv anterior en $OLD" >&2
  ls -1d "${VENV}"_ANTES_* 2>/dev/null || echo "  revisar a mano"
fi
[ -n "$WEB" ]    && { $SUDO systemctl start "$WEB"    2>/dev/null; }
[ -n "$CELERY" ] && { $SUDO systemctl start "$CELERY" 2>/dev/null; }
sleep 5
curl -s -o /dev/null -w "HTTP %{http_code}\n" --max-time 15 http://127.0.0.1/
'@

function Expand-Marks($text) {
    $map = @{
        '__PROJECT__' = $ProjectPath
        '__VENV__'    = $VenvPath
        '__WEB__'     = $WebService
        '__CELERY__'  = $CeleryService
    }
    foreach ($k in $map.Keys) { $text = $text.Replace($k, $map[$k]) }
    return $text
}

# ---------------------------------------------------------------------------
# Modo rollback
# ---------------------------------------------------------------------------
if ($RollbackOnly) {
    Step "Rollback"
    $cands = Invoke-Ssh -Cmd "ls -1dt ${VenvPath}_ANTES_* 2>/dev/null | head -3"
    if (-not $cands.Rc -eq 0 -or -not ($cands.Out | Where-Object { $_ -match "${VenvPath}_ANTES_" })) {
        Die "no hay venv anterior guardado (${VenvPath}_ANTES_*). Nada que revertir."
    }
    $oldVenv = ($cands.Out | Where-Object { $_ -match "${VenvPath}_ANTES_" } | Select-Object -First 1)
    Ok "venv a restaurar: $oldVenv"
    $rb = Invoke-Ssh -InputScript (Expand-Marks $bashRollback).Replace('__OLD__', $oldVenv)
    Show $rb
    if ($rb.Rc -ne 0) { Die "el rollback fallo. Revisar a mano en el servidor." }
    Ok "rollback aplicado"
    exit 0
}

# ---------------------------------------------------------------------------
# Fases 1-4 remotas
# ---------------------------------------------------------------------------
Step "Fases 1-4 - backup, venv nuevo, verificacion y pull"
Hint "puede tardar varios minutos"

$run = Invoke-Ssh -InputScript (Expand-Marks $bashUpgrade) -TimeoutSec 900
Show $run

$txt = $run.Out -join "`n"
if ($run.Rc -ne 0 -or $txt -notmatch 'REMOTE\|LISTO_PARA_SWAP') {
    $b = [regex]::Match($txt, 'REMOTE\|BACKUP=(\S+)').Groups[1].Value
    if ($b) { Warn ("log parcial en: " + $b + "/logs.txt") }
    Die "fallo en las fases remotas. Produccion NO fue tocada: el venv actual sigue intacto."
}

$backup  = [regex]::Match($txt, 'REMOTE\|BACKUP=(\S+)').Groups[1].Value
$newVenv = [regex]::Match($txt, 'REMOTE\|NEW_VENV=(\S+)').Groups[1].Value
$oldVenv = [regex]::Match($txt, 'REMOTE\|OLD_VENV=(\S+)').Groups[1].Value
$oldDj   = [regex]::Match($txt, 'REMOTE\|OLD_DJANGO=(\S+)').Groups[1].Value

Ok ("backup completo: " + $backup)
Ok ("Django actual: " + $oldDj)

# ---------------------------------------------------------------------------
# Fase 5: puerta
# ---------------------------------------------------------------------------
Step "Fase 5 - Publicar"

Write-Host ("    Se va a parar " + $WebService + " y " + $CeleryService + " unos segundos,") -ForegroundColor Yellow
Write-Host ("    renombrar el venv actual -> " + $oldVenv) -ForegroundColor Yellow
Write-Host ("    poner " + $newVenv + " en su lugar y arrancar de nuevo") -ForegroundColor Yellow
Write-Host ("    El venv anterior queda intacto: el rollback es renombrar al reves.`n") -ForegroundColor Yellow

if (-not $AutoConfirm) {
    $r = Read-Host '  Continuar? (s/N)'
    if ($r -notmatch '^[sSyY]') { Die "cancelado. Nada fue tocado." }
}

# ---------------------------------------------------------------------------
# Fase 6: swap con rollback automatico
# ---------------------------------------------------------------------------
Step "Fase 6 - Swap, reinicio y verificacion"

$sw = Invoke-Ssh -InputScript ((Expand-Marks $bashSwap).Replace('__OLD__', $oldVenv).Replace('__NEW__', $newVenv)) -TimeoutSec 300
Show $sw

if ($sw.Rc -ne 0 -or -not (($sw.Out -join "`n") -match 'REMOTE\|SWAP_OK')) {
    Write-Host "`n    El swap fallo o la verificacion dio error. ROLLBACK AUTOMATICO..." -ForegroundColor Red
    $rb = Invoke-Ssh -InputScript ((Expand-Marks $bashRollback).Replace('__OLD__', $oldVenv)) -TimeoutSec 300
    Show $rb
    Die "rollback aplicado. El sitio deberia estar como estaba. Log del backup en $backup"
}

# ---------------------------------------------------------------------------
Step "Resultado"
$newDj = (Invoke-Ssh -Cmd "$VenvPath/bin/python -c 'import django;print(django.get_version())'").Out | Select-Object -Last 1
Ok ("Django " + $oldDj + " -> " + $newDj)
Ok ("backup: " + $backup)
Ok ("venv anterior conservado en: " + $oldVenv)

Write-Host @"

    QUEDA VERIFICAR A MANO (el script no puede hacerlo):
      - Dashboard '/': el grafico 'Estados de hallazgos mes a mes'
      - '/usuarios/reporte-accesos/': los 3 graficos del reporte
      - '/moviles/viajes-graficos/': se reparo un 404 de JS (commit 422ec2b)
      - Generar un PDF de hallazgos (reportlab y matplotlib cambiaron de version)
      - Disparar un resumen mensual: prueba que Celery procesa tareas

    Si algo falla:
      .\upgrade-django-produccion.ps1 -RollbackOnly

"@ -ForegroundColor Yellow