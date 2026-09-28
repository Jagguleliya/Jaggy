"""
Stop the background daemon.
"""
import os
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
pid_file = os.path.join(BASE_DIR, 'data', 'daemon.pid')

if os.path.exists(pid_file):
    try:
        with open(pid_file) as f:
            pid = int(f.read().strip())
        subprocess.run(['taskkill', '/F', '/PID', str(pid)], capture_output=True)
        if os.path.exists(pid_file):
            os.remove(pid_file)
        print(f"Successfully stopped background daemon (PID: {pid}).")
    except Exception as e:
        print(f"Error stopping daemon: {e}")
        if os.path.exists(pid_file):
            os.remove(pid_file)
else:
    print("No active background daemon was running.")
