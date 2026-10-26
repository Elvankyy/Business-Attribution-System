param(
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$root = Split-Path $PSScriptRoot -Parent
$rootEnv = Join-Path $root ".env"
$rootEnvExample = Join-Path $root ".env.example"

if (-not (Test-Path $rootEnv)) {
    Copy-Item $rootEnvExample $rootEnv
    Write-Host "Created root .env from .env.example"
}

if (-not $SkipInstall) {
    npm install
}

$vite = Join-Path $PSScriptRoot "node_modules\vite\bin\vite.js"
if (-not (Test-Path $vite)) {
    throw "vite not found. Run: npm install"
}

New-Item -ItemType Directory -Force -Path ".runtime" | Out-Null
New-Item -ItemType Directory -Force -Path "logs" | Out-Null

$pidFile = Join-Path $PSScriptRoot ".runtime\frontend.pid.json"
if (Test-Path $pidFile) {
    $existing = Get-Content $pidFile -Raw | ConvertFrom-Json
    $process = Get-Process -Id $existing.pid -ErrorAction SilentlyContinue
    if ($null -ne $process) {
        Write-Host "Frontend is already running (PID $($existing.pid))"
        exit 0
    }
    Remove-Item $pidFile -Force
}

$stdout = Join-Path $PSScriptRoot "logs\frontend.out.log"
$stderr = Join-Path $PSScriptRoot "logs\frontend.err.log"
$process = Start-Process -FilePath "node" -ArgumentList "`"$vite`"", "--host", "0.0.0.0", "--port", "5173" -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru

@{ pid = $process.Id; started_at = (Get-Date).ToString("o") } | ConvertTo-Json | Set-Content -Encoding utf8 $pidFile
Write-Host "Frontend started (PID $($process.Id)). Logs: logs\frontend.out.log"
