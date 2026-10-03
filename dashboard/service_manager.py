"""Autonomous Background Service Supervisor for Nexomate.

Zero-configuration auto-starter:
Manages FastAPI backend (port 8000) and Node.js WhatsApp Baileys bridge (port 8001).
If either service is ever offline, automatically spawns it and keeps it alive.
"""

import os
import sys
import time
import shutil
import threading
import subprocess
import requests
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SERVER_DIR = BASE_DIR / "lead-workflow-demo"
SERVER_SCRIPT = SERVER_DIR / "server.py"
BRIDGE_DIR = BASE_DIR / "whatsapp-bridge"

FASTAPI_URL = "http://127.0.0.1:8000/api/config"
BRIDGE_URL = "http://127.0.0.1:8001/status"

_fastapi_proc = None
_bridge_proc = None
_lock = threading.Lock()


def is_service_alive(url, timeout=1.0):
    try:
        r = requests.get(url, timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False


def start_fastapi_server():
    """Starts the FastAPI lead generation server if not running."""
    global _fastapi_proc
    with _lock:
        if is_service_alive(FASTAPI_URL):
            return True

        if _fastapi_proc is None or _fastapi_proc.poll() is not None:
            cmd = [sys.executable, str(SERVER_SCRIPT)]
            kwargs = {
                "cwd": str(SERVER_DIR),
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
            }
            if os.name == "nt":
                kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
            try:
                _fastapi_proc = subprocess.Popen(cmd, **kwargs)
            except Exception as e:
                print(f"[ServiceManager] Error starting FastAPI: {e}")
                return False

        for _ in range(8):
            time.sleep(0.5)
            if is_service_alive(FASTAPI_URL):
                return True

    return is_service_alive(FASTAPI_URL)


def start_whatsapp_bridge():
    """Starts the Node.js WhatsApp bridge if not running."""
    global _bridge_proc
    with _lock:
        if is_service_alive(BRIDGE_URL):
            return True

        node_bin = shutil.which("node")
        if not node_bin:
            return False

        if _bridge_proc is None or _bridge_proc.poll() is not None:
            cmd = [node_bin, "bridge.js"]
            kwargs = {
                "cwd": str(BRIDGE_DIR),
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
            }
            if os.name == "nt":
                kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
            try:
                _bridge_proc = subprocess.Popen(cmd, **kwargs)
            except Exception as e:
                print(f"[ServiceManager] Error starting WhatsApp bridge: {e}")
                return False

        for _ in range(8):
            time.sleep(0.5)
            if is_service_alive(BRIDGE_URL):
                return True

    return is_service_alive(BRIDGE_URL)


def ensure_all_services_running():
    """Checks both services and starts them if necessary."""
    fastapi_ok = is_service_alive(FASTAPI_URL)
    if not fastapi_ok:
        fastapi_ok = start_fastapi_server()

    bridge_ok = is_service_alive(BRIDGE_URL)
    if not bridge_ok:
        bridge_ok = start_whatsapp_bridge()

    return fastapi_ok, bridge_ok
