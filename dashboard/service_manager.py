"""Automatic Background Service Supervisor for Nexomate.

Zero-configuration auto-starter: Checks if the FastAPI engine (port 8000)
and the WhatsApp Bridge (port 8001) are running. If not, spawns them
automatically as detached background subprocesses. Non-tech users never
need to run terminal commands.
"""

import os
import sys
import time
import shutil
import subprocess
import requests
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SERVER_SCRIPT = BASE_DIR / "lead-workflow-demo" / "server.py"
BRIDGE_DIR = BASE_DIR / "whatsapp-bridge"
BRIDGE_SCRIPT = BRIDGE_DIR / "bridge.js"

FASTAPI_URL = "http://127.0.0.1:8000/api/config"
BRIDGE_URL = "http://127.0.0.1:8001/status"

_spawned_processes = {}


def is_service_alive(url, timeout=1.5):
    try:
        r = requests.get(url, timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False


def start_fastapi_server():
    """Spawns the FastAPI lead generation backend in the background."""
    if is_service_alive(FASTAPI_URL):
        return True

    python_bin = sys.executable
    cmd = [python_bin, str(SERVER_SCRIPT)]
    kwargs = {
        "cwd": str(SERVER_SCRIPT.parent),
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }

    if os.name == "nt":
        # Windows: CREATE_NO_WINDOW | DETACHED_PROCESS
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW | 0x00000008

    try:
        proc = subprocess.Popen(cmd, **kwargs)
        _spawned_processes["fastapi"] = proc
        # Wait up to 3 seconds for port to bind
        for _ in range(6):
            time.sleep(0.5)
            if is_service_alive(FASTAPI_URL):
                return True
    except Exception as e:
        print(f"[ServiceManager] Error spawning FastAPI: {e}")

    return is_service_alive(FASTAPI_URL)


def start_whatsapp_bridge():
    """Spawns the Node.js WhatsApp Baileys bridge in the background."""
    if is_service_alive(BRIDGE_URL):
        return True

    node_bin = shutil.which("node")
    if not node_bin:
        print("[ServiceManager] Node.js not found in PATH")
        return False

    cmd = [node_bin, str(BRIDGE_SCRIPT)]
    kwargs = {
        "cwd": str(BRIDGE_DIR),
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }

    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW | 0x00000008

    try:
        proc = subprocess.Popen(cmd, **kwargs)
        _spawned_processes["bridge"] = proc
        for _ in range(6):
            time.sleep(0.5)
            if is_service_alive(BRIDGE_URL):
                return True
    except Exception as e:
        print(f"[ServiceManager] Error spawning WhatsApp bridge: {e}")

    return is_service_alive(BRIDGE_URL)


def ensure_all_services_running():
    """Ensures both FastAPI and WhatsApp bridge are healthy and auto-starts them."""
    fastapi_ok = is_service_alive(FASTAPI_URL)
    if not fastapi_ok:
        fastapi_ok = start_fastapi_server()

    bridge_ok = is_service_alive(BRIDGE_URL)
    if not bridge_ok:
        bridge_ok = start_whatsapp_bridge()

    return fastapi_ok, bridge_ok
