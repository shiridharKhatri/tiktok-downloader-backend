import os
import subprocess
import sys

def setup_production():
    print("--- TikDown Production Setup ---")
    
    # 1. Install necessary libraries
    print("[*] Installing production dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "fastapi", "uvicorn", "requests", "selenium", "webdriver-manager"])
    
    # 2. Instructions for VPS hosting
    vps_guide = """
# Production Hosting Guide

To keep your TikTok Downloader running 24/7 on a VPS (Ubuntu/Debian), 
it is recommended to use PM2 or a Systemd service.

## 1. Running with PM2 (Recommended)
PM2 will automatically restart the app if it crashes or the server reboots.

```bash
sudo npm install -g pm2
pm2 start "python3 app.py" --name tikdown-api
pm2 save
pm2 startup
```

## 2. API Endpoints
- **GET /info?url=...** -> Returns a direct JSON download link (Fastest)
- **GET /download?url=...** -> Downloads the file and serves it (Bypasses CORS)

## 3. Scaling
To handle massive traffic, consider adding a list of proxies to `tiktok_downloader.py` 
inside the `requests.Session()` object.
"""
    
    with open("PRODUCTION_GUIDE.md", "w") as f:
        f.write(vps_guide)
        
    print("[+] Done! PRODUCTION_GUIDE.md has been created.")
    print("[!] To start the server, run: python app.py")

if __name__ == "__main__":
    setup_production()
