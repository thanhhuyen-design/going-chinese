"""
server_launcher.py - Khởi chạy đồng thời FastAPI Server (0.0.0.0:8000) và Cloudflare Public Tunnel.
Cung cấp đồng thời 3 đường dẫn truy cập:
1. Local: http://localhost:8000
2. Mạng LAN / Wi-Fi (cho điện thoại cùng Wi-Fi): http://<LAN_IP>:8000
3. Internet Công Khai (cho mọi người ở bất cứ đâu): https://<id>.trycloudflare.com
"""

import os
import re
import sys
import time
import json
import socket
import subprocess
from threading import Thread

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON_EXE = sys.executable
CLOUDFLARED_EXE = os.path.join(BASE_DIR, "cloudflared.exe")
TUNNEL_FILE = os.path.join(BASE_DIR, "tunnel_info.json")


def get_lan_ip():
    """Lấy địa chỉ IP mạng nội bộ (Wi-Fi / Ethernet)"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def save_tunnel_info(public_url, lan_ip):
    data = {
        "local_url": "http://127.0.0.1:8000",
        "lan_url": f"http://{lan_ip}:8000",
        "public_url": public_url,
        "updated_at": time.time()
    }
    with open(TUNNEL_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def main():
    lan_ip = get_lan_ip()
    print("=" * 65)
    print(" 🀄 KHOI DONG HE THONG HOC TU VUNG TIENG TRUNG KHUNG DEN")
    print("=" * 65)
    print(f"\n[1/3] May chu dang chay tren dia chi IP noi bo: http://{lan_ip}:8000")
    print("[2/3] Dang khoi tao duong truyen Internet cong khai (Cloudflare Tunnel)...")

    # Khoi chay cloudflared neu co
    public_url = "https://pressed-including-lock-nothing.trycloudflare.com"
    if os.path.exists(CLOUDFLARED_EXE):
        cmd = [CLOUDFLARED_EXE, "tunnel", "--url", "http://127.0.0.1:8000"]
        cf_proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        def read_tunnel_output():
            nonlocal public_url
            for line in cf_proc.stdout:
                # Tim URL trycloudflare.com
                match = re.search(r'https://[a-zA-Z0-9\-]+\.trycloudflare\.com', line)
                if match:
                    public_url = match.group(0)
                    save_tunnel_info(public_url, lan_ip)
                    print(f"\n[3/3] DA TAO THANH CONG DUONG LINK TRUY CAP CONG KHAI:")
                    print(f"      🔗 {public_url}")
                    print(f"\n      => Bat ky ai tren the gioi (dien thoai, may tinh khac) deu co the vao link tren!")
                    print("=" * 65)

        t = Thread(target=read_tunnel_output, daemon=True)
        t.start()
    else:
        save_tunnel_info(public_url, lan_ip)

    # Chay Uvicorn
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
