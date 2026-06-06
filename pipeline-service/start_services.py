"""
start_services.py — Robust Windows background service launcher.

Uses subprocess.Popen with DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP flags
to fully detach uvicorn from the parent shell. Returns immediately.

Usage: python start_services.py [start|stop|status]
"""

import os
import subprocess
import sys
import time
from pathlib import Path

# Windows-specific flags
if sys.platform != "win32":
    print("This script is Windows-only")
    sys.exit(1)

DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200

WORKDIR = Path(__file__).parent
UVICORN = WORKDIR / ".venv" / "Scripts" / "uvicorn.exe"
LOG_DIR = Path(os.environ.get("TEMP", "/tmp")) / "n2s-svc-logs"
LOG_DIR.mkdir(exist_ok=True)

SERVICES = [
    (8001, "services.input_service:app",     "input"),
    (8002, "services.structure_service:app", "structure"),
    (8003, "services.beat_service:app",      "beat"),
    (8000, "services.orchestrator:app",      "orchestrator"),
]


def start_all() -> None:
    """Launch all 4 services as detached background processes."""
    LOG_DIR.mkdir(exist_ok=True)
    for port, module, name in SERVICES:
        log = LOG_DIR / f"{name}.log"
        err = LOG_DIR / f"{name}.err"
        # Open log files and pass handles to subprocess (which detaches them)
        log_h = open(log, "wb")
        err_h = open(err, "wb")
        try:
            subprocess.Popen(
                [str(UVICORN), module, "--host", "127.0.0.1", "--port", str(port)],
                cwd=str(WORKDIR),
                stdout=log_h,
                stderr=err_h,
                stdin=subprocess.DEVNULL,
                creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                close_fds=True,
            )
            print(f"started {name} on port {port} (logs: {log})")
        except Exception as e:
            print(f"FAILED to start {name}: {e}")
        finally:
            # Close parent's handle — child has its own
            log_h.close()
            err_h.close()

    # Ensure Redis is up
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=novel-redis", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=5,
        )
        if "novel-redis" not in result.stdout:
            subprocess.Popen(
                ["docker", "run", "-d", "--name", "novel-redis",
                 "-p", "6379:6379", "redis:7-alpine"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
            )
            print("started Redis container")
        else:
            print("Redis already running")
    except Exception as e:
        print(f"Redis check failed: {e}")


def stop_all() -> None:
    """Kill all uvicorn processes."""
    import ctypes
    kernel32 = ctypes.windll.kernel32
    # Use taskkill for clean shutdown
    result = subprocess.run(
        ["taskkill", "/F", "/IM", "uvicorn.exe"],
        capture_output=True, text=True,
    )
    print(result.stdout.strip() or "no uvicorn processes to kill")


def status() -> None:
    """Show running services + port reachability."""
    import socket
    procs = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq uvicorn.exe"],
        capture_output=True, text=True,
    )
    n_uvicorn = procs.stdout.count("uvicorn.exe")
    print(f"uvicorn processes: {n_uvicorn}")
    for port, _, name in SERVICES:
        s = socket.socket()
        s.settimeout(1.0)
        try:
            s.connect(("localhost", port))
            print(f"  {name:12s} :{port}  OK")
        except Exception:
            print(f"  {name:12s} :{port}  DOWN")
        finally:
            s.close()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "start"
    if cmd == "start":
        start_all()
    elif cmd == "stop":
        stop_all()
    elif cmd == "status":
        status()
    else:
        print(f"unknown command: {cmd}")
        sys.exit(1)
