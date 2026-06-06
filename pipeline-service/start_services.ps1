# start_services.ps1
# Robustly launch all 4 pipeline services + ensure Redis is running.
# Designed to return IMMEDIATELY (no waiting on stdout/stderr pipes).
#
# Usage: powershell -ExecutionPolicy Bypass -File start_services.ps1
#
# Each service is launched via `cmd /c start /B "" "<uvicorn>" ...` which:
#   - /B = no new window
#   - "" = dummy title for the start command
#   - Detaches the child from the parent's console
# Stdout/stderr are redirected to TEMP files but inherited from cmd,
# so the parent doesn't wait on them.

$ErrorActionPreference = "SilentlyContinue"
$logDir = "$env:TEMP\n2s-svc-logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null

# Kill any existing uvicorn processes
Get-Process -Name "uvicorn" -ErrorAction SilentlyContinue | ForEach-Object {
    Stop-Process -Id $_.Id -Force
}
Start-Sleep -Milliseconds 500

# Service definitions
$services = @(
    @{ Port = 8001; Module = "services.input_service:app";     Name = "input"      }
    @{ Port = 8002; Module = "services.structure_service:app"; Name = "structure"  }
    @{ Port = 8003; Module = "services.beat_service:app";      Name = "beat"       }
    @{ Port = 8000; Module = "services.orchestrator:app";      Name = "orchestrator" }
)

$workdir = "C:\WorkSpace\novel2script\pipeline-service"
$uvicorn = "$workdir\.venv\Scripts\uvicorn.exe"

foreach ($svc in $services) {
    $log = "$logDir\$($svc.Name).log"
    $err = "$logDir\$($svc.Name).err"
    $arg = "`"$uvicorn`" `"$($svc.Module)`" --host 127.0.0.1 --port $($svc.Port) > `"$log`" 2> `"$err`""
    # /B = no new window, "" = dummy title
    $cmd = "cmd.exe /c start /B "" "" $arg"
    Invoke-Expression $cmd
    Write-Host "started $($svc.Name) on port $($svc.Port)"
}

# Ensure Redis is up
$redisRunning = docker ps --filter "name=novel-redis" --format "{{.Names}}" 2>$null
if ($redisRunning -ne "novel-redis") {
    Write-Host "starting Redis container..."
    cmd.exe /c start /B "" "docker" "run" "-d" "--name" "novel-redis" "-p" "6379:6379" "redis:7-alpine"
} else {
    Write-Host "Redis already running"
}

Write-Host "All services launched (detached). Logs in $logDir"
