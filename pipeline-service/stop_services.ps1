# stop_services.ps1
# Kill all 4 pipeline services + (optionally) stop Redis container.
# Idempotent — safe to run multiple times.

$ErrorActionPreference = "SilentlyContinue"

$count = (Get-Process -Name "uvicorn" -ErrorAction SilentlyContinue | Measure-Object).Count
Get-Process -Name "uvicorn" -ErrorAction SilentlyContinue | ForEach-Object {
    Stop-Process -Id $_.Id -Force
}
Write-Host "killed $count uvicorn processes"
