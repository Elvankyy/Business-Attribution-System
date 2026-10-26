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
    uv sync
}

$uvicorn = Join-Path $PSScriptRoot ".venv\Scripts\uvicorn.exe"
if (-not (Test-Path $uvicorn)) {
    throw "uvicorn not found. Run: uv sync"
}

New-Item -ItemType Directory -Force -Path ".runtime" | Out-Null
New-Item -ItemType Directory -Force -Path "logs" | Out-Null

$pidFile = Join-Path $PSScriptRoot ".runtime\backend.pid.json"
if (Test-Path $pidFile) {
    $existing = Get-Content $pidFile -Raw | ConvertFrom-Json
    $process = Get-Process -Id $existing.pid -ErrorAction SilentlyContinue
    if ($null -ne $process) {
        Write-Host "Backend is already running (PID $($existing.pid))"
        exit 0
    }
    Remove-Item $pidFile -Force
}

$stdout = Join-Path $PSScriptRoot "logs\backend.out.log"
$stderr = Join-Path $PSScriptRoot "logs\backend.err.log"
$process = Start-Process -FilePath $uvicorn -ArgumentList "app.main:app", "--host", "127.0.0.1", "--port", "8000" -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru

@{ pid = $process.Id; started_at = (Get-Date).ToString("o") } | ConvertTo-Json | Set-Content -Encoding utf8 $pidFile
Write-Host "Backend started (PID $($process.Id)). Logs: logs\backend.out.log"
