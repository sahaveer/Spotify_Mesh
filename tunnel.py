import os
import sys
import re
import time
import socket
import pathlib
import logging
import threading
import subprocess
import urllib.request
import shutil
from typing import Optional, Dict, Any

import config
import settings

logger = logging.getLogger("tunnel")

# Global Tunnel State
_process: Optional[subprocess.Popen] = None
_status: str = "stopped"  # "stopped", "starting", "running", "error"
_tunnel_url: Optional[str] = None
_error_message: Optional[str] = None
_started_at: Optional[float] = None
_lock = threading.RLock()

def get_binary_path() -> pathlib.Path:
    bin_dir = config.BASE_DIR / "bin"
    bin_dir.mkdir(exist_ok=True)
    is_windows = sys.platform.startswith("win")
    binary_name = "cloudflared.exe" if is_windows else "cloudflared"
    return bin_dir / binary_name

def ensure_cloudflared() -> pathlib.Path:
    """Ensures cloudflared binary is available, using system binary if present or downloading if missing."""
    # 1. Check if cloudflared is already in PATH
    binary_name = "cloudflared.exe" if sys.platform.startswith("win") else "cloudflared"
    sys_path = shutil.which(binary_name) or shutil.which("cloudflared")
    if sys_path:
        return pathlib.Path(sys_path)

    # 2. Check local project bin directory
    cloudflared_path = get_binary_path()
    if cloudflared_path.exists() and cloudflared_path.stat().st_size > 1000000:
        return cloudflared_path

    logger.info("Downloading official Cloudflare Tunnel binary (cloudflared)...")
    is_windows = sys.platform.startswith("win")

    if is_windows:
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
    elif sys.platform.startswith("darwin"):
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-amd64"
    else:
        import platform
        machine = platform.machine().lower()
        if "arm" in machine or "aarch64" in machine:
            url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64"
        else:
            url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"

    temp_path = cloudflared_path.with_suffix(".tmp")
    urllib.request.urlretrieve(url, str(temp_path))
    if temp_path.exists():
        temp_path.replace(cloudflared_path)

    if not is_windows:
        import stat
        cloudflared_path.chmod(cloudflared_path.stat().st_mode | stat.S_IEXEC)

    logger.info("Cloudflared binary successfully installed.")
    return cloudflared_path

def _monitor_output(proc: subprocess.Popen):
    global _status, _tunnel_url, _error_message
    url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

    for line in iter(proc.stdout.readline, ''):
        if not line:
            break
        stripped = line.strip()
        logger.debug(f"[cloudflared] {stripped}")

        # Search for public URL
        match = url_pattern.search(stripped)
        if match:
            with _lock:
                _tunnel_url = match.group(0)
                _status = "running"
                _error_message = None
            logger.info(f"Worldwide Tunnel Active: {_tunnel_url}")

    return_code = proc.poll()
    with _lock:
        if _status != "stopped":
            _status = "error" if return_code not in (0, None, -15) else "stopped"
            if return_code not in (0, None, -15):
                _error_message = f"Process exited unexpectedly with code {return_code}"

def start_tunnel(port: int = config.PORT, custom_token: Optional[str] = None) -> Dict[str, Any]:
    """Starts the Cloudflare Tunnel process in the background."""
    global _process, _status, _tunnel_url, _error_message, _started_at

    with _lock:
        if _status == "running" and _tunnel_url:
            return get_tunnel_status()
        if _status == "starting":
            return get_tunnel_status()

        _status = "starting"
        _error_message = None
        _started_at = time.time()

    def _worker():
        global _process, _status, _error_message
        try:
            exe_path = ensure_cloudflared()
            cmd = [str(exe_path), "tunnel"]
            if custom_token and custom_token.strip():
                cmd.extend(["run", "--token", custom_token.strip()])
            else:
                cmd.extend(["--url", f"http://localhost:{port}"])

            startupinfo = None
            if sys.platform.startswith("win"):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                startupinfo=startupinfo
            )

            with _lock:
                _process = proc

            _monitor_output(proc)
        except Exception as e:
            logger.error(f"Failed to start Cloudflare Tunnel: {e}")
            with _lock:
                _status = "error"
                _error_message = str(e)

    t = threading.Thread(target=_worker, daemon=True, name="CloudflareTunnelWorker")
    t.start()

    # Wait up to 3 seconds for initial spin-up check
    for _ in range(6):
        time.sleep(0.5)
        with _lock:
            if _status == "running" and _tunnel_url:
                break
            if _status == "error":
                break

    return get_tunnel_status()

def stop_tunnel() -> Dict[str, Any]:
    """Stops the Cloudflare Tunnel process."""
    global _process, _status, _tunnel_url, _error_message
    with _lock:
        if _process:
            try:
                _process.terminate()
                _process.wait(timeout=2)
            except Exception:
                try:
                    _process.kill()
                except Exception:
                    pass
            _process = None
        _status = "stopped"
        _tunnel_url = None
        _error_message = None
    logger.info("Cloudflare Worldwide Tunnel stopped.")
    return get_tunnel_status()

def get_tunnel_status() -> Dict[str, Any]:
    """Returns the current state and public HTTPS URL of the worldwide tunnel."""
    with _lock:
        active = (_status == "running" and _tunnel_url is not None)
        return {
            "status": _status,
            "is_active": active,
            "url": _tunnel_url if active else None,
            "error": _error_message,
            "started_at": _started_at
        }
