<#
.SYNOPSIS
    Instala una clave SSH en el VPS y crea el alias en ~/.ssh/config.

.DESCRIPTION
    Hace las dos cosas de una:
      1. genera la clave si no existe y la copia al servidor (authorized_keys)
      2. escribe la entrada del alias en ~/.ssh/config
      3. prueba que la conexion funciona

    Es idempotente: se puede volver a correr sin duplicar la clave ni la
    entrada del config.

    Te va a pedir la password del servidor UNA vez, en el paso de copiar la
    clave. Es normal: es la unica forma de instalar la clave.

.PARAMETER Server
    Host del VPS. Default: vps-3177145-x.dattaweb.com

.PARAMETER Port
    Puerto SSH. Default: 5438

.PARAMETER User
    Usuario SSH. Default: root

.PARAMETER Alias
    Nombre del alias en ~/.ssh/config. Default: anasociados

.PARAMETER KeyName
    Nombre del archivo de clave (sin .pub). Default: id_ed25519_anasociados

.PARAMETER Comment
    Comentario de la clave. Default: anasociados-vps-2026

.PARAMETER SkipKey
    No copiar la clave al servidor, solo escribir el alias.

.PARAMETER Force
    No pedir confirmacion.

.EXAMPLE
    .\configurar-ssh-vps.ps1

.EXAMPLE
    .\configurar-ssh-vps.ps1 -User root -Port 5438 -Alias anasociados

.EXAMPLE
    .\configurar-ssh-vps.ps1 -SkipKey     # si la clave ya esta instalada
#>
[CmdletBinding()]
param(
    [string]$Server    = 'vps-3177145-x.dattaweb.com',
    [int]   $Port      = 5438,
    [string]$User      = 'root',
    [string]$Alias     = 'anasociados',
    [string]$KeyName   = 'id_ed25519_anasociados',
    [string]$Comment   = 'anasociados-vps-2026',
    [switch]$SkipKey,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$sshDir = Join-Path $env:USERPROFILE '.ssh'
$keyPath = Join-Path $sshDir $KeyName
$pubPath = "$keyPath.pub"
$cfgPath = Join-Path $sshDir 'config'

function Step($m) { Write-Host ("`n=== " + $m + " " + ("=" * [Math]::Max(3, 58 - $m.Length))) -ForegroundColor Cyan }
function Ok($m)   { Write-Host ("    OK     " + $m) -ForegroundColor Green }
function Warn($m) { Write-Host ("    AVISO  " + $m) -ForegroundColor Yellow }
function Die($m)  { Write-Host ("`n    FALLO  " + $m) -ForegroundColor Red; exit 1 }

# El stderr de ssh no debe disparar el ErrorActionPreference='Stop':
# devuelve [pscustomobject]@{ Out; Rc } y lo maneja el llamador.
function Invoke-Ssh {
    param([string[]]$SshArgs)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $out = & ssh @SshArgs 2>&1
        $rc = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $prev
    }
    return [pscustomobject]@{ Out = @($out); Rc = $rc }
}

Write-Host "Configurar acceso SSH por clave al VPS" -ForegroundColor White
Write-Host ("  $User@$Server :$Port   alias: $Alias`n")

# ---------------------------------------------------------------------------
Step "Paso 1 - Clave"
# ---------------------------------------------------------------------------
if (-not (Test-Path $sshDir)) {
    New-Item -ItemType Directory -Path $sshDir -Force | Out-Null
    Write-Host "    (cree $sshDir)"
}

if (Test-Path $keyPath) {
    Ok "la clave ya existe: $keyPath"
    if (-not (Test-Path $pubPath)) {
        Write-Host "    no esta el .pub; lo regenero desde la privada"
        & ssh-keygen -y -f $keyPath 2>$null | Out-File -FilePath $pubPath -Encoding ascii
        if (Test-Path $pubPath) { Ok "regenerado: $pubPath" }
    }
} else {
    Write-Host "    no existe, la genero ahora (sin passphrase, para poder usarla sin prompt)"
    & ssh-keygen -t ed25519 -a 100 -f $keyPath -N '""' -C $Comment | Out-Null
    if (-not (Test-Path $keyPath)) { Die "ssh-keygen no pudo crear la clave" }
    Ok "creada: $keyPath"
}

if (-not (Test-Path $pubPath)) { Die "no se pudo obtener la clave publica" }
$pub = (Get-Content $pubPath -Raw).Trim()
if (-not $pub.StartsWith('ssh-')) { Die "el .pub no parece una clave publica valida" }
Ok "clave publica lista"

Write-Host ("    fingerprint: " + (& ssh-keygen -lf $pubPath | ForEach-Object { ($_ -split '\s+')[1] }))

# ---------------------------------------------------------------------------
Step "Paso 2 - Copiar la clave al servidor"

if ($SkipKey) {
    Write-Host "    -SkipKey: no se copia, solo se escribe el alias" -ForegroundColor DarkGray
} else {
    $pubSafe = $pub.Replace("'", "")
    $remote = "mkdir -p ~/.ssh && chmod 700 ~/.ssh && " +
              "touch ~/.ssh/authorized_keys && " +
              "grep -qxF '$pubSafe' ~/.ssh/authorized_keys 2>/dev/null || echo '$pubSafe' >> ~/.ssh/authorized_keys; " +
              "chmod 600 ~/.ssh/authorized_keys; " +
              "grep -c 'ssh-' ~/.ssh/authorized_keys | sed 's/^/claves en authorized_keys: /'"

    Write-Host "    Te va a pedir la password de $User@$Server (una sola vez)." -ForegroundColor Yellow
    Write-Host "    Si el usuario root esta deshabilitado, corre esto como el usuario que sea:`n"

    if (-not $Force) {
        $r = Read-Host '  Instalar la clave ahora? (s/N)'
        if ($r -notmatch '^[sSyY]') { Die "cancelado" }
    }

    Write-Host ""
    $r = Invoke-Ssh -SshArgs @('-p', $Port, '-o', 'StrictHostKeyChecking=accept-new', "$User@$Server", $remote)
    $r.Out | ForEach-Object { Write-Host ("    " + $_) }
    if ($r.Rc -ne 0) {
        Write-Host ""
        Die "fallo al copiar la clave (ssh devolvio $($r.Rc)).`n    Comprobaciones: password correcta, usuario correcto, puerto correcto."
    }
    Ok "clave instalada en el servidor"
}

# ---------------------------------------------------------------------------
Step "Paso 3 - Alias en ~/.ssh/config"
# ---------------------------------------------------------------------------

$bloque = @"
Host $Alias
    HostName $Server
    Port $Port
    User $User
    IdentityFile ~/.ssh/$KeyName
    IdentitiesOnly yes
    ServerAliveInterval 60
    ServerAliveCountMax 3
"@

$lineaAlias = "Host $Alias"

if (-not (Test-Path $cfgPath)) {
    Set-Content -Path $cfgPath -Value $bloque -Encoding ascii
    Ok "creado $cfgPath con el alias $Alias"
} else {
    $lineas = @(Get-Content $cfgPath)

    # indice de la linea "Host <alias>" (comparacion exacta)
    $idx = -1
    for ($i = 0; $i -lt $lineas.Count; $i++) {
        $t = $lineas[$i].Trim()
        if ($t -eq $lineaAlias -or $t -match ('^Host\s+' + [regex]::Escape($Alias) + '(\s|$)')) {
            if ($t -eq $lineaAlias) { $idx = $i; break }
        }
    }

    if ($idx -ge 0) {
        # reemplazar el bloque existente: desde "Host alias" hasta el proximo Host
        $fin = $lineas.Count
        for ($j = $idx + 1; $j -lt $lineas.Count; $j++) {
            if ($lineas[$j] -match '^\s*Host\s+') { $fin = $j; break }
        }
        $antes = $fin - $idx

        # Ojo: con $idx = 0, el rango 0..-1 devuelve el array COMPLETO en
        # PowerShell (indice negativo cuenta desde el final) y duplicaba el bloque.
        $cab = @()
        if ($idx -gt 0) { $cab = @($lineas[0..($idx - 1)]) }
        $cola = @()
        if ($fin -lt $lineas.Count) { $cola = @($lineas[$fin..($lineas.Count - 1)]) }

        $nuevas = $cab + @($bloque -split "`r?`n") + $cola
        Set-Content -Path $cfgPath -Value $nuevas -Encoding ascii
        Ok "alias $Alias actualizado (reemplazo un bloque de $antes lineas)"
    } else {
        $nuevas = @($lineas) + @('', $bloque)
        Set-Content -Path $cfgPath -Value $nuevas -Encoding ascii
        Ok "alias $Alias agregado al final del config"
    }
}

$patronAlias = '^Host\s+' + [regex]::Escape($Alias) + '\s*$'
$nAlias = @(Select-String -Path $cfgPath -Pattern $patronAlias).Count
if ($nAlias -eq 1) { Ok "el config tiene exactamente una entrada para $Alias" }
else { Warn "el config tiene $nAlias entradas para ${Alias}: revisalo a mano" }

# ---------------------------------------------------------------------------
Step "Paso 4 - Probar"
# ---------------------------------------------------------------------------
$t = Invoke-Ssh -SshArgs @('-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', $Alias, 'echo CONECTADO && id -un && hostname && uname -sr')
$rc = $t.Rc

if ($rc -eq 0) {
    $t.Out | ForEach-Object { Write-Host ("    " + $_) }
    Write-Host ""
    Ok "autenticacion por clave funcionando"
    Write-Host ""
    Write-Host "    Para conectarte:" -ForegroundColor White
    Write-Host ("      ssh $Alias") -ForegroundColor Gray
    Write-Host ""
    Write-Host "    Y el upgrade de Django:" -ForegroundColor White
    Write-Host ("      .\upgrade-django-produccion.ps1 -AutoConfirm") -ForegroundColor Gray
} else {
    Write-Host ("    " + ($t.Out -join ' | ')) -ForegroundColor DarkGray
    Write-Host ""
    Warn "la clave todavia no permite entrar. Probables causas:"
    Write-Host "      - la copia fallo: volve a correrlo sin -SkipKey"
    Write-Host "      - la password con la que copiaste no era la del usuario $User"
    Write-Host "      - el servidor pide otro metodo: proba  ssh -v $Alias"
    exit 1
}