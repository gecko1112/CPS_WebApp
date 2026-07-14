# scripts/start.ps1 - start the whole P13 stack with one command (Windows).
# PowerShell port of scripts/start.sh - keep the two in sync.
#
#   .\scripts\start.ps1              # DEMO: mock data + Mailpit email demo
#   .\scripts\start.ps1 -Real        # REAL: broker + our backend; P06 runs elsewhere
#   .\scripts\start.ps1 -Full        # REAL + local P06 stack (InfluxDB, logger,
#                                    #   query API, aggregator) from ..\monorepo
#   .\scripts\start.ps1 -NoEmail     # any mode without Mailpit/email
#
# Always starts (Ctrl+C stops everything):
#   * backend  - uvicorn on :8000  (MOCK_DATA=true in demo mode)
#   * frontend - Vite dev server on :5173 (exposed on LAN for phones)
#   * Mailpit (docker) unless already running / -NoEmail
# -Real adds:  Mosquitto broker :1883 (docker, if not running)
# -Full adds:  InfluxDB :8086 (docker) + P06 logger/api/aggregator (uv)
#
# NOTE (-Full): P06 logs whatever is published on the bus - actual sensor DATA
# still needs the other groups' publishers (run mprocs in ..\monorepo).
# On the Pi, P06 runs its own stack - use -Real there.

param(
    [switch]$Real,
    [switch]$Full,
    [switch]$NoEmail
)

$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Monorepo = if ($env:MONOREPO) { $env:MONOREPO } else { Join-Path (Split-Path -Parent $RepoRoot) 'monorepo' }
$Mode = if ($Full) { 'full' } elseif ($Real) { 'real' } else { 'demo' }
$Email = -not $NoEmail

$Procs = @()

function Test-Port([int]$Port) {
    try {
        $client = New-Object Net.Sockets.TcpClient
        $ok = $client.ConnectAsync('127.0.0.1', $Port).Wait(500)
        $client.Close()
        return $ok
    } catch { return $false }
}

# --- Mailpit (email demo) ----------------------------------------------------
if ($Email) {
    if (Test-Port 8025) {
        Write-Host '==> Mailpit already running (http://localhost:8025)'
    } elseif (Get-Command docker -ErrorAction SilentlyContinue) {
        Write-Host '==> Starting Mailpit ...'
        docker run --rm -d --name p13-mailpit -p 1025:1025 -p 8025:8025 axllent/mailpit | Out-Null
    } else {
        Write-Host '==> docker not found - skipping Mailpit (email demo disabled)'
    }
}

# --- Broker (real/full) ------------------------------------------------------
if ($Mode -ne 'demo') {
    if (Test-Port 1883) {
        Write-Host '==> MQTT broker already running (:1883)'
    } else {
        Write-Host '==> Starting Mosquitto broker ...'
        $mosqConf = Join-Path $Monorepo 'docker\mosquitto.conf'
        docker run --rm -d --name cps-mqtt -p 1883:1883 `
            -v "${mosqConf}:/mosquitto/config/mosquitto.conf" `
            eclipse-mosquitto:2 | Out-Null
    }
}

# --- Local P06 stack (full only) ----------------------------------------------
if ($Mode -eq 'full') {
    if (-not (Test-Path $Monorepo)) {
        Write-Error "monorepo not found at $Monorepo (set `$env:MONOREPO)"
        exit 1
    }
    $influxOrg    = if ($env:INFLUX_ORG)    { $env:INFLUX_ORG }    else { 'cps' }
    $influxBucket = if ($env:INFLUX_BUCKET) { $env:INFLUX_BUCKET } else { 'cps_raw' }
    $influxToken  = if ($env:INFLUX_TOKEN)  { $env:INFLUX_TOKEN }  else { 'dev-token-change-me' }

    if (Test-Port 8086) {
        Write-Host '==> InfluxDB already running (:8086)'
    } else {
        Write-Host '==> Starting InfluxDB ...'
        docker run -d --name cps-influxdb -p 8086:8086 `
            -e DOCKER_INFLUXDB_INIT_MODE=setup `
            -e DOCKER_INFLUXDB_INIT_USERNAME=admin `
            -e DOCKER_INFLUXDB_INIT_PASSWORD=changeme123 `
            -e DOCKER_INFLUXDB_INIT_ORG=$influxOrg `
            -e DOCKER_INFLUXDB_INIT_BUCKET=$influxBucket `
            -e DOCKER_INFLUXDB_INIT_RETENTION=7d `
            -e DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=$influxToken `
            -v cps_influxdb_data:/var/lib/influxdb2 `
            -v cps_influxdb_config:/etc/influxdb2 `
            influxdb:2.7 2>$null | Out-Null
        if ($LASTEXITCODE -ne 0) { docker start cps-influxdb | Out-Null }
    }

    # Port opens before Influx finishes first-run setup - wait for real health.
    Write-Host -NoNewline '    waiting for InfluxDB to be ready '
    while ($true) {
        try {
            Invoke-RestMethod -Uri 'http://localhost:8086/health' -TimeoutSec 2 | Out-Null
            break
        } catch { Write-Host -NoNewline '.'; Start-Sleep 1 }
    }
    Write-Host ' ok'

    Write-Host '==> Starting P06 logger + query API + aggregator ...'
    $p06Env = @{
        INFLUX_URL    = 'http://localhost:8086'
        INFLUX_ORG    = $influxOrg
        INFLUX_BUCKET = $influxBucket
        INFLUX_TOKEN  = $influxToken
    }
    foreach ($k in $p06Env.Keys) { Set-Item "env:$k" $p06Env[$k] }
    $env:MQTT_BROKER = 'localhost'
    $Procs += Start-Process -PassThru -NoNewWindow -WorkingDirectory $Monorepo `
        uv -ArgumentList 'run', '--package', 'p06_data_logging_visualisation', 'p06-logger'
    $env:API_HOST = '0.0.0.0'; $env:API_PORT = '8088'
    $Procs += Start-Process -PassThru -NoNewWindow -WorkingDirectory $Monorepo `
        uv -ArgumentList 'run', '--package', 'p06_data_logging_visualisation', 'p06-api'
    $Procs += Start-Process -PassThru -NoNewWindow -WorkingDirectory $Monorepo `
        uv -ArgumentList 'run', '--package', 'p06_data_logging_visualisation', 'p06-aggregator'
}

if ($Mode -eq 'real') {
    Write-Host "    NOTE: expecting P06's query API on :8088 (start it separately, or use -Full)."
}

# --- Backend -------------------------------------------------------------------
Write-Host "==> Starting backend (:8000, mode: $Mode) ..."
if ($Mode -eq 'demo') { $env:MOCK_DATA = 'true' } else { Remove-Item env:MOCK_DATA -ErrorAction SilentlyContinue }
if ($Email) { $env:EMAIL_ENABLED = 'true' }
$Procs += Start-Process -PassThru -NoNewWindow -WorkingDirectory (Join-Path $RepoRoot 'backend') `
    uv -ArgumentList 'run', 'uvicorn', 'app.main:app', '--reload'

# --- Frontend --------------------------------------------------------------------
Write-Host '==> Starting frontend (:5173) ...'
# --host: reachable from phones on the same WiFi
$Procs += Start-Process -PassThru -NoNewWindow -WorkingDirectory (Join-Path $RepoRoot 'frontend') `
    npm -ArgumentList 'run', 'dev', '--', '--host'

Start-Sleep 3
$lanIp = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } |
    Select-Object -First 1).IPAddress

Write-Host ''
Write-Host '────────────────────────────────────────────────────────'
Write-Host '  App:      http://localhost:5173'
if ($lanIp) { Write-Host "  Phone:    http://${lanIp}:5173  (same WiFi)" }
Write-Host '  API docs: http://localhost:8000/docs'
if ($Email) { Write-Host '  Mailpit:  http://localhost:8025' }
if ($Mode -eq 'full') { Write-Host '  P06 API:  http://localhost:8088/health' }
Write-Host ''
Write-Host '  Logins:   operator@example.com / operator123'
Write-Host '            viewer@example.com   / viewer123'
if ($Mode -eq 'demo') {
    Write-Host ''
    Write-Host '  Demo story: healthy -> 1 warning (~40s) -> 1 critical (~2min, emailed)'
} else {
    Write-Host ''
    Write-Host '  Real mode: dashboard fills as groups publish on the bus.'
}
Write-Host ''
Write-Host '  Ctrl+C stops everything.'
Write-Host '────────────────────────────────────────────────────────'

# Wait until interrupted, then stop every child process we started.
try {
    Wait-Process -Id ($Procs | ForEach-Object Id)
} finally {
    Write-Host ''
    Write-Host '==> Stopping ...'
    foreach ($p in $Procs) {
        try { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue } catch {}
    }
}
