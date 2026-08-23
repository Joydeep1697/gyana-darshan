# capture_cdp_screenshots.py — High-Fidelity Post-Splash Screenshots via Chrome CDP

import os
import time
import json
import base64
import urllib.request
import subprocess
from pathlib import Path

BASE_DIR = Path(r"d:\Gyana Darshan")
SCREENSHOTS_DIR = BASE_DIR / "evaluation" / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
if not os.path.exists(CHROME_PATH):
    CHROME_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

VIEWPORTS = [
    ("desktop_1920x1080", 1920, 1080),
    ("desktop_1440x900", 1440, 900),
    ("laptop_1366x768", 1366, 768),
    ("tablet_768x1024", 768, 1024),
    ("mobile_390x844", 390, 844)
]

def capture_via_cdp():
    import urllib.parse
    for name, w, h in VIEWPORTS:
        out_file = SCREENSHOTS_DIR / f"{name}.png"
        print(f"\n[+] Launching headless browser for {name} ({w}x{h})...")
        
        # Start Chrome with remote debugging on port 9222
        proc = subprocess.Popen([
            CHROME_PATH,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            f"--window-size={w},{h}",
            "--remote-debugging-port=9222",
            "--user-data-dir=" + str(BASE_DIR / "evaluation" / f"chrome_profile_{w}_{h}"),
            "http://127.0.0.1:8000/"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        time.sleep(1.5)
        
        try:
            # Query CDP targets
            req = urllib.request.urlopen("http://127.0.0.1:9222/json/list", timeout=5)
            targets = json.loads(req.read().decode())
            ws_url = targets[0]["webSocketDebuggerUrl"]
            
            # Simple websocket communication using standard library or simple socket
            # Or use Chrome DevTools Protocol HTTP endpoint
            import socket
            # Connect to ws_url
            parsed = urllib.parse.urlparse(ws_url)
            host, port = parsed.hostname, parsed.port
            path = parsed.path
            
            s = socket.create_connection((host, port), timeout=10)
            
            # Perform WebSocket handshake
            key = base64.b64encode(os.urandom(16)).decode()
            handshake = (
                f"GET {path} HTTP/1.1\r\n"
                f"Host: {host}:{port}\r\n"
                f"Upgrade: websocket\r\n"
                f"Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {key}\r\n"
                f"Sec-WebSocket-Version: 13\r\n\r\n"
            )
            s.sendall(handshake.encode())
            
            # Read handshake response
            resp = b""
            while b"\r\n\r\n" not in resp:
                resp += s.recv(1024)
            
            # Helper to send WS text frame
            def send_frame(msg_dict):
                raw = json.dumps(msg_dict).encode()
                length = len(raw)
                header = bytearray([0x81]) # FIN + Text
                mask_key = os.urandom(4)
                if length <= 125:
                    header.append(0x80 | length)
                elif length <= 65535:
                    header.append(0x80 | 126)
                    header.extend(length.to_bytes(2, 'big'))
                else:
                    header.append(0x80 | 127)
                    header.extend(length.to_bytes(8, 'big'))
                header.extend(mask_key)
                masked = bytearray(b ^ mask_key[i % 4] for i, b in enumerate(raw))
                s.sendall(header + masked)
            
            # Helper to receive WS text frame
            def recv_frame():
                buf = s.recv(2)
                if not buf:
                    return None
                masked = bool(buf[1] & 0x80)
                length = buf[1] & 0x7F
                if length == 126:
                    length = int.from_bytes(s.recv(2), 'big')
                elif length == 127:
                    length = int.from_bytes(s.recv(8), 'big')
                mask_key = s.recv(4) if masked else b""
                data = b""
                while len(data) < length:
                    chunk = s.recv(length - len(data))
                    if not chunk:
                        break
                    data += chunk
                if masked:
                    data = bytes(b ^ mask_key[i % 4] for i, b in enumerate(data))
                return json.loads(data.decode('utf-8', errors='ignore'))

            # Wait 4.5s for splash animation to fade and remove
            time.sleep(4.5)
            
            # Capture Screenshot
            send_frame({"id": 1, "method": "Page.captureScreenshot", "params": {"format": "png"}})
            
            while True:
                msg = recv_frame()
                if msg and msg.get("id") == 1:
                    img_data = base64.b64decode(msg["result"]["data"])
                    with open(out_file, "wb") as f:
                        f.write(img_data)
                    print(f"  [+] Successfully captured post-splash {name}: {out_file.name} ({len(img_data)//1024} KB)")
                    break
            
            s.close()
        except Exception as e:
            print(f"  [-] CDP error on {name}: {e}")
        finally:
            proc.terminate()
            proc.wait()

if __name__ == "__main__":
    capture_via_cdp()
