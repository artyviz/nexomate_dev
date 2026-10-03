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


def _start_fastapi_thread():
    """Fallback in-process daemon thread runner for FastAPI."""
    try:
        import uvicorn
        import importlib.util
        spec = importlib.util.spec_from_file_location("demo_server", str(SERVER_SCRIPT))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        config = uvicorn.Config(mod.app, host="0.0.0.0", port=8000, log_level="warning")
        server = uvicorn.Server(config)
        t = threading.Thread(target=server.run, daemon=True)
        t.start()
    except Exception as e:
        print(f"[ServiceManager] In-thread fallback error: {e}")


def start_fastapi_server():
    """Starts the FastAPI lead generation server if not running."""
    global _fastapi_proc
    with _lock:
        if is_service_alive(FASTAPI_URL):
            return True

        sub_env = os.environ.copy()
        sub_env["BACKEND_PORT"] = "8000"
        sub_env["PORT"] = "8000"

        if _fastapi_proc is None or _fastapi_proc.poll() is not None:
            cmd = [sys.executable, str(SERVER_SCRIPT)]
            kwargs = {
                "cwd": str(SERVER_DIR),
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
                "env": sub_env,
            }
            if os.name == "nt":
                kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
            try:
                _fastapi_proc = subprocess.Popen(cmd, **kwargs)
            except Exception as e:
                print(f"[ServiceManager] Subprocess spawn failed, using in-thread runner: {e}")
                _start_fastapi_thread()

        for _ in range(8):
            time.sleep(0.5)
            if is_service_alive(FASTAPI_URL):
                return True

        # If subprocess didn't start in time, initiate in-thread runner
        if not is_service_alive(FASTAPI_URL):
            _start_fastapi_thread()
            for _ in range(6):
                time.sleep(0.5)
                if is_service_alive(FASTAPI_URL):
                    return True

    return is_service_alive(FASTAPI_URL)


def resolve_node_and_npm():
    """Finds node and npm binaries, auto-bootstrapping standalone Node on Linux if absent."""
    # 1. Check system PATH
    sys_node = shutil.which("node")
    if sys_node:
        return sys_node, shutil.which("npm")

    # 2. Check user home location (~/.node/bin/node)
    home_node = Path.home() / ".node" / "bin" / "node"
    if home_node.exists() and os.access(str(home_node), os.X_OK):
        home_npm = Path.home() / ".node" / "bin" / "npm"
        return str(home_node), str(home_npm)

    # 3. Check workspace runtime (.node_runtime)
    local_dir = BASE_DIR / ".node_runtime"
    local_node = local_dir / "bin" / "node"
    if local_node.exists() and os.access(str(local_node), os.X_OK):
        local_npm = local_dir / "bin" / "npm"
        return str(local_node), str(local_npm)

    # 4. On Linux (e.g. Render Python environment), download standalone Node.js
    if sys.platform.startswith("linux"):
        print("[ServiceManager] Node.js not detected. Bootstrapping standalone Node.js on Linux...")
        try:
            import urllib.request
            import tarfile
            local_dir.mkdir(parents=True, exist_ok=True)
            tar_path = local_dir / "node.tar.gz"
            url = "https://nodejs.org/dist/v20.18.0/node-v20.18.0-linux-x64.tar.gz"
            urllib.request.urlretrieve(url, str(tar_path))
            with tarfile.open(str(tar_path), "r:gz") as tar:
                for member in tar.getmembers():
                    parts = Path(member.name).parts
                    if len(parts) > 1:
                        target = local_dir / Path(*parts[1:])
                        if member.isdir():
                            target.mkdir(parents=True, exist_ok=True)
                        elif member.isfile():
                            target.parent.mkdir(parents=True, exist_ok=True)
                            with tar.extractfile(member) as src, open(target, "wb") as dst:
                                dst.write(src.read())
                            if "bin" in parts:
                                os.chmod(str(target), 0o755)
            if tar_path.exists():
                tar_path.unlink()
            if local_node.exists():
                os.chmod(str(local_node), 0o755)
                local_npm = local_dir / "bin" / "npm"
                if local_npm.exists():
                    os.chmod(str(local_npm), 0o755)
                print("[ServiceManager] Standalone Node.js ready.")
                return str(local_node), str(local_npm)
        except Exception as e:
            print(f"[ServiceManager] Error bootstrapping portable Node.js: {e}")

    return None, None


def ensure_bridge_deps(npm_path):
    """Installs npm dependencies inside whatsapp-bridge if missing."""
    baileys_dir = BRIDGE_DIR / "node_modules" / "@whiskeysockets" / "baileys"
    if baileys_dir.exists():
        return True

    if not npm_path:
        print("[ServiceManager] Cannot install bridge dependencies: npm not found.")
        return False

    print("[ServiceManager] Installing WhatsApp Baileys bridge dependencies (npm install)...")
    try:
        subprocess.run([npm_path, "install", "--omit=dev"], cwd=str(BRIDGE_DIR), check=True, timeout=120)
        return True
    except Exception as e:
        print(f"[ServiceManager] Failed running npm install: {e}")
        return False


def start_whatsapp_bridge():
    """Starts the Node.js WhatsApp bridge if not running."""
    global _bridge_proc
    with _lock:
        if is_service_alive(BRIDGE_URL):
            return True

        node_bin, npm_bin = resolve_node_and_npm()
        if not node_bin:
            print("[ServiceManager] Node runtime could not be resolved.")
            return False

        # Ensure dependencies exist
        ensure_bridge_deps(npm_bin)

        if _bridge_proc is None or _bridge_proc.poll() is not None:
            cmd = [node_bin, "bridge.js"]
            bridge_env = os.environ.copy()
            if node_bin:
                node_dir = str(Path(node_bin).parent)
                bridge_env["PATH"] = f"{node_dir}:{bridge_env.get('PATH', '')}"

            kwargs = {
                "cwd": str(BRIDGE_DIR),
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
                "env": bridge_env,
            }
            if os.name == "nt":
                kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
            try:
                _bridge_proc = subprocess.Popen(cmd, **kwargs)
            except Exception as e:
                print(f"[ServiceManager] Error starting WhatsApp bridge: {e}")
                return False

        for _ in range(12):
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
