import os
import sys
import socket
import subprocess
import urllib.request
import pathlib
import threading
import time
import argparse
import uvicorn

import config

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
            if ip.startswith("127."):
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
    if primary_ip and primary_ip not in ("127.0.0.1",):
        if primary_ip in lan_ips:
            lan_ips.remove(primary_ip)
        lan_ips.insert(0, primary_ip)

    final_list = lan_ips + virtual_ips
    return final_list or ["127.0.0.1"]

def ensure_cloudflared() -> pathlib.Path:
    """Downloads official cloudflared.exe binary if not already present."""
    bin_dir = config.BASE_DIR / "bin"
    bin_dir.mkdir(exist_ok=True)
    cloudflared_path = bin_dir / "cloudflared.exe"

    if not cloudflared_path.exists():
        print("\n[*] Downloading official Cloudflare Tunnel binary (cloudflared.exe)...")
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
        urllib.request.urlretrieve(url, str(cloudflared_path))
        print("[+] Download complete.")
    return cloudflared_path

def start_cloudflare_tunnel(port: int):
    """Runs a quick Cloudflare Tunnel in background and prints the public HTTPS URL."""
    try:
        cloudflared_exe = ensure_cloudflared()
        print("[*] Starting Cloudflare Tunnel for worldwide remote access...")
        
        proc = subprocess.Popen(
            [str(cloudflared_exe), "tunnel", "--url", f"http://localhost:{port}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        # Read output in thread to extract the trycloudflare.com URL
        def monitor_tunnel():
            tunnel_url = None
            for line in proc.stdout:
                if "trycloudflare.com" in line:
                    for part in line.split():
                        if "https://" in part and "trycloudflare.com" in part:
                            tunnel_url = part.strip()
                            print("\n" + "=" * 60)
                            print(" WORLDWIDE ACCESS URL (iPhone / Android / Anywhere):")
                            print(f" >> {tunnel_url}")
                            print("=" * 60 + "\n")
                            break

        threading.Thread(target=monitor_tunnel, daemon=True).start()
    except Exception as e:
        print(f"[!] Could not start Cloudflare tunnel: {e}")

def print_terminal_qr(url: str):
    try:
        import qrcode
        sys.stdout.reconfigure(encoding='utf-8')
        qr = qrcode.QRCode(border=1)
        qr.add_data(url)
        print(" [Scan with Phone Camera to Connect Instantly]:")
        qr.print_ascii(invert=True)
    except Exception:
        pass

def main():
    parser = argparse.ArgumentParser(description="MediaPlayer Server Launcher")
    parser.add_argument("--tunnel", action="store_true", help="Start Cloudflare tunnel for worldwide remote access")
    parser.add_argument("--port", type=int, default=config.PORT, help="Port to listen on")
    args = parser.parse_args()

    local_ips = get_local_ips()
    primary_ip = local_ips[0] if local_ips else "localhost"
    primary_url = f"http://{primary_ip}:{args.port}"

    print("\n" + "=" * 60)
    print(" DECENTRALIZED MEDIA HUB")
    print("=" * 60)
    print(f" * Local Web Player:   http://localhost:{args.port}")
    for ip in local_ips:
        print(f" * Same Wi-Fi Mobile:  http://{ip}:{args.port}")
    print("=" * 60)

    print_terminal_qr(primary_url)
    print("=" * 60 + "\n")

    if args.tunnel:
        start_cloudflare_tunnel(args.port)
    else:
        print("[Tip] To enable worldwide access on 4G/5G, run with: python run_server.py --tunnel\n")

    # Start FastAPI / Uvicorn Server
    uvicorn.run("main:app", host="0.0.0.0", port=args.port, reload=False)

if __name__ == "__main__":
    main()
