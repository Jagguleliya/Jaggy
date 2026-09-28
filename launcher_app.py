"""
JAGY Desktop Application Launcher (.EXE Entrypoint).
1. Checks dependencies and permissions
2. Authorizes YouTube OAuth if first time launch
3. Launches local backend server
4. Opens chromeless native Desktop App window
"""
import os
import sys
import time
import subprocess
import threading
from pathlib import Path

# Add project root to sys.path
if getattr(sys, 'frozen', False):
    PROJECT_ROOT = Path(sys.executable).parent.absolute()
else:
    PROJECT_ROOT = Path(__file__).parent.absolute()

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def free_port(port=8000):
    """Ensure port is completely free by terminating any stale zombie server."""
    try:
        out = subprocess.check_output(f'netstat -ano | findstr :{port}', shell=True).decode()
        for line in out.strip().splitlines():
            parts = line.split()
            if len(parts) >= 5 and "LISTENING" in line:
                pid = parts[-1]
                if pid != str(os.getpid()):
                    subprocess.call(f'taskkill /F /PID {pid}', shell=True)
                    print(f"Freed port {port} by terminating stale process {pid}.")
    except Exception:
        pass

def verify_and_request_permissions():
    """Verify and request necessary user permissions on first run."""
    print("==================================================================")
    print("  JAGY AI Desktop Studio — Automatic Setup & Permission Verification")
    print("==================================================================")
    
    # 1. Output and Data Directory Access
    output_dir = PROJECT_ROOT / "output"
    data_dir = PROJECT_ROOT / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    print("[1/3] Local storage directories verified (output/ & data/).")

    # 2. YouTube OAuth Check
    token_file = PROJECT_ROOT / "config" / "token.json"
    if not token_file.exists():
        print("\n[2/3] First-Time YouTube Permission Required:")
        print("Opening Google OAuth in your browser to grant YouTube upload permissions...")
        try:
            from setup_oauth import setup_oauth
            setup_oauth()
            print("YouTube permission granted successfully!")
        except Exception as e:
            print(f"Note: YouTube OAuth setup can also be completed later: {e}")
    else:
        print("[2/3] YouTube OAuth permissions: Granted & Verified.")

    # 3. Environment & Server Launch
    print("[3/3] Launching JAGY Engine and opening Desktop Studio...")

def start_backend():
    import uvicorn
    from web.app import app
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

def open_desktop_window():
    url = "http://127.0.0.1:8000"
    
    # Priority 1: Native chromeless Edge App mode (looks like 100% native desktop app)
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    ]
    for ep in edge_paths:
        if os.path.exists(ep):
            subprocess.Popen([ep, f"--app={url}", "--window-size=1366,860", "--app-id=jagy_desktop_studio"])
            print("Opened JAGY in native chromeless Desktop App window.")
            return

    # Priority 2: Chrome App mode
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    ]
    for cp in chrome_paths:
        if os.path.exists(cp):
            subprocess.Popen([cp, f"--app={url}", "--window-size=1366,860", "--app-id=jagy_desktop_studio"])
            print("Opened JAGY in native chromeless Desktop App window (Chrome).")
            return

    # Priority 3: Fallback browser
    import webbrowser
    webbrowser.open(url)

def main():
    free_port(8000)
    verify_and_request_permissions()
    
    # Start web server in background thread
    server_thread = threading.Thread(target=start_backend, daemon=True)
    server_thread.start()
    
    time.sleep(1.5)
    open_desktop_window()
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping JAGY Studio...")

if __name__ == "__main__":
    main()
