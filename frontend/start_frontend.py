"""
start_frontend.py — Launch the Vite dev server as a fully-detached process.
Returns immediately. Logs to TEMP/n2s-svc-logs/frontend.log.
"""

import os
import subprocess
import sys
from pathlib import Path

if sys.platform != "win32":
    print("Windows-only")
    sys.exit(1)

DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200

FRONTEND_DIR = Path("C:/WorkSpace/novel2script/frontend")
NPM_CMD = "npm.cmd" if sys.platform == "win32" else "npm"
LOG_DIR = Path(os.environ.get("TEMP", "/tmp")) / "n2s-svc-logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "frontend.log"


def start():
    log_h = open(LOG_FILE, "wb")
    try:
        subprocess.Popen(
            [NPM_CMD, "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"],
            cwd=str(FRONTEND_DIR),
            stdout=log_h, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
            close_fds=True,
        )
        print(f"started frontend dev server (logs: {LOG_FILE})")
    finally:
        log_h.close()


def stop():
    import ctypes
    subprocess.run(
        ["taskkill", "/F", "/IM", "node.exe", "/FI", "WINDOWTITLE eq npm*"],
        capture_output=True, text=True,
    )
    # Fallback: kill any node holding port 3000
    try:
        out = subprocess.check_output(
            ["netstat", "-ano"], text=True, stderr=subprocess.DEVNULL,
        )
        for line in out.splitlines():
            if ":3000" in line and "LISTENING" in line:
                pid = line.strip().split()[-1]
                subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)
    except Exception:
        pass
    print("killed frontend")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "stop":
        stop()
    else:
        start()
