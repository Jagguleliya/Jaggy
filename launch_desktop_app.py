"""
JAGY Native Desktop Application Launcher.
Launches the local engine and opens a native chromeless desktop window (or pywebview).
"""
import os
import sys
import time
import subprocess
import threading
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.absolute()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def start_backend():
    import uvicorn
    from web.app import app
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")

def main():
    # Start web app server in background thread
    t = threading.Thread(target=start_backend, daemon=True)
    t.start()
    
    # Wait 1.5s for server to start
    time.sleep(1.5)
    
    url = "http://127.0.0.1:8000"
    
    # Attempt 1: Try pywebview if installed
    try:
        import webview
        webview.create_window("JAGY AI Desktop Studio v2.0", url, width=1320, height=840, resizable=True)
        webview.start()
        return
    except ImportError:
        pass
    except Exception as e:
        print(f"pywebview note: {e}")

    # Attempt 2: Try Microsoft Edge or Chrome in --app mode (chromeless native desktop window)
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    ]
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    ]
    
    for ep in edge_paths:
        if os.path.exists(ep):
            subprocess.Popen([ep, f"--app={url}", "--window-size=1320,840"])
            print("Opened JAGY in native Desktop Window (MS Edge App mode).")
            return

    for cp in chrome_paths:
        if os.path.exists(cp):
            subprocess.Popen([cp, f"--app={url}", "--window-size=1320,840"])
            print("Opened JAGY in native Desktop Window (Chrome App mode).")
            return

    # Fallback: Default browser
    import webbrowser
    webbrowser.open(url)
    print("Opened JAGY Studio at http://127.0.0.1:8000")

if __name__ == "__main__":
    main()
