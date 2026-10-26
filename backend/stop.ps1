$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$pidFile = Join-Path $PSScriptRoot ".runtime\backend.pid.json"
if (-not (Test-Path $pidFile)) {
    Write-Host "Backend is not running"
    exit 0
}

$info = Get-Content $pidFile -Raw | ConvertFrom-Json
try {
    Stop-Process -Id $info.pid -Force -ErrorAction Stop
    Write-Host "Backend stopped (PID $($info.pid))"
} catch {
    Write-Host "Process $($info.pid) was not found"
}
Remove-Item $pidFile -Force
