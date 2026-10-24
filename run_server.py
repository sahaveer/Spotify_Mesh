import os
import sys
import socket
import ipaddress
import subprocess
import urllib.request
import pathlib
import threading
import time
import argparse
from typing import Optional, List
import uvicorn

import config
import settings
import tunnel

def is_tailscale_ip(ip_str: Optional[str]) -> bool:
    """Checks if an IP address belongs to the Tailscale CGNAT (100.64.0.0/10) or Tailscale IPv6 network."""
    if not ip_str:
        return False
    try:
        ip = ipaddress.ip_address(str(ip_str).strip())
        if ip.version == 4:
            return ip in ipaddress.ip_network("100.64.0.0/10")
        elif ip.version == 6:
            return ip in ipaddress.ip_network("fd7a:115c:a1e0::/48")
    except Exception:
        pass
    return False

def get_tailscale_ip() -> Optional[str]:
    """Detects active Tailscale IPv4 address via CLI or network interfaces."""
    # 1. Try tailscale CLI
    try:
        proc = subprocess.run(["tailscale", "ip", "-4"], capture_output=True, text=True, timeout=2)
        if proc.returncode == 0:
            for line in proc.stdout.strip().splitlines():
                candidate = line.strip()
                if is_tailscale_ip(candidate):
                    return candidate
    except Exception:
        pass

    # 2. Check local network interfaces via socket
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if is_tailscale_ip(ip):
                return ip
    except Exception:
        pass

    return None

def get_local_ips():
    """Gets local network IPv4 addresses, strictly prioritizing the active Wi-Fi LAN IP."""
    primary_ip = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        primary_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    lan_ips = []
    virtual_ips = []

    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if ip.startswith("127.") or is_tailscale_ip(ip):
                continue
            if ip.startswith("192.168.") or ip.startswith("10."):
                if ip not in lan_ips:
                    lan_ips.append(ip)
            else:
                if ip not in virtual_ips:
                    virtual_ips.append(ip)
    except Exception:
        pass

    # Ensure the socket-connected primary Wi-Fi IP is always at index 0
    if primary_ip and primary_ip not in ("127.0.0.1",) and not is_tailscale_ip(primary_ip):
        if primary_ip in lan_ips:
            lan_ips.remove(primary_ip)
        lan_ips.insert(0, primary_ip)

    final_list = lan_ips + virtual_ips
    return final_list or ["127.0.0.1"]

def ensure_cloudflared() -> pathlib.Path:
    """Returns cloudflared binary from PATH or downloads official binary if missing."""
    import shutil
    binary_name = "cloudflared.exe" if sys.platform.startswith("win") else "cloudflared"
    sys_path = shutil.which(binary_name) or shutil.which("cloudflared")
    if sys_path:
        return pathlib.Path(sys_path)

    bin_dir = config.BASE_DIR / "bin"
    bin_dir.mkdir(exist_ok=True)
    cloudflared_path = bin_dir / binary_name

    if not cloudflared_path.exists():
        print(f"\n[*] Downloading official Cloudflare Tunnel binary ({binary_name})...")
        if is_windows:
            url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
        elif sys.platform.startswith("darwin"):
            url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-amd64"
        else:
            # Linux: detect architecture (x86_64 vs arm64 / Raspberry Pi)
            import platform
            machine = platform.machine().lower()
            if "arm" in machine or "aarch64" in machine:
                url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64"
            else:
                url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"

        urllib.request.urlretrieve(url, str(cloudflared_path))
        if not is_windows:
            import stat
            cloudflared_path.chmod(cloudflared_path.stat().st_mode | stat.S_IEXEC)
        print("[+] Download complete.")
    return cloudflared_path

def print_terminal_qr(url: str, label: str = "Scan with Phone Camera to Connect"):
    try:
        import qrcode
        sys.stdout.reconfigure(encoding='utf-8')
        qr = qrcode.QRCode(border=1)
        qr.add_data(url)
        print(f" [{label}]:")
        qr.print_ascii(invert=True)
    except Exception:
        pass

def main():
    parser = argparse.ArgumentParser(description="MediaPlayer Dual-Mode Server Launcher (Mesh + Global)")
    parser.add_argument("--local-only", dest="local_only", action="store_true", help="Run only on local Wi-Fi mesh without worldwide tunnel")
    parser.add_argument("--tunnel", "--global", dest="global_mode", action="store_true", help="Start Cloudflare tunnel for worldwide remote access (default: enabled)")
    parser.add_argument("--port", type=int, default=config.PORT, help="Port to listen on")
    args = parser.parse_args()

    # Enforce global access unless explicitly asked for --local-only
    if args.local_only:
        is_global_enabled = False
    else:
        is_global_enabled = True
        settings.set_global_access(True)

    local_ips = get_local_ips()
    primary_ip = local_ips[0] if local_ips else "localhost"
    primary_url = f"http://{primary_ip}:{args.port}"
    tailscale_ip = get_tailscale_ip()

    print("\n" + "=" * 65)
    print(" DECENTRALIZED MEDIA HUB (MULTI-MODE SERVER)")
    print("=" * 65)
    print(" [1] LOCAL MESH NETWORK (Offline Wi-Fi / Hotspot - 0 MB Data):")
    print(f"     * Local Browser:   http://localhost:{args.port}")
    for ip in local_ips:
        print(f"     * Wi-Fi Mobile:    http://{ip}:{args.port}")
    print("=" * 65)

    if tailscale_ip:
        ts_url = f"http://{tailscale_ip}:{args.port}"
        print(" [2] TAILSCALE PRIVATE MESH (Direct WireGuard P2P Anywhere):")
        print(f"     * Tailscale IP:    {tailscale_ip}")
        print(f"     * Tailnet URL:     {ts_url}")
        print("=" * 65)
        print_terminal_qr(ts_url, label="Scan for Tailscale Remote Access")
        print("=" * 65 + "\n")
    else:
        print_terminal_qr(primary_url, label="Scan for Local Wi-Fi Mesh")
        print("=" * 65 + "\n")

    global_section = 3 if tailscale_ip else 2
    if is_global_enabled:
        print("[*] Starting Worldwide Global Access (Cloudflare Tunnel)...")
        token = settings.load_settings().get("global_tunnel_token")
        
        def monitor_and_print_global():
            for _ in range(30):
                time.sleep(1)
                status = tunnel.get_tunnel_status()
                if status["is_active"] and status["url"]:
                    url = status["url"]
                    print("\n" + "=" * 65)
                    print(f" [{global_section}] GLOBAL WORLDWIDE ACCESS (Cloudflare HTTPS / 4G/5G):")
                    print(f"     * Public HTTPS:    {url}")
                    print("=" * 65)
                    print_terminal_qr(url, label="Scan for Worldwide Remote Access")
                    print("=" * 65 + "\n")
                    break
        
        threading.Thread(target=monitor_and_print_global, daemon=True).start()
        tunnel.start_tunnel(args.port, token)
    else:
        print("[Tip] To access anywhere in the world on mobile cellular data (4G/5G):")
        if tailscale_ip:
            print(f"      * Tailscale is ACTIVE! Connect your phone to Tailscale and open: {ts_url}")
        else:
            print("      * Tailscale: Connect this server to Tailscale to stream via encrypted WireGuard P2P")
        print("      * Cloudflare: Run with 'python run_server.py --global' or toggle in Web App Settings.\n")

    # Start FastAPI / Uvicorn Server
    uvicorn.run("main:app", host="0.0.0.0", port=args.port, reload=False)

if __name__ == "__main__":
    main()
