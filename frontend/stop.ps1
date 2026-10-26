$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$pidFile = Join-Path $PSScriptRoot ".runtime\frontend.pid.json"
if (-not (Test-Path $pidFile)) {
    Write-Host "Frontend is not running"
    exit 0
}

$info = Get-Content $pidFile -Raw | ConvertFrom-Json
try {
    Stop-Process -Id $info.pid -Force -ErrorAction Stop
    Write-Host "Frontend stopped (PID $($info.pid))"
} catch {
    Write-Host "Process $($info.pid) was not found"
}
Remove-Item $pidFile -Force
