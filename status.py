"""
CLI Status tool for YouTube Shorts Bot.
"""
import os
import json
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
history_file = os.path.join(BASE_DIR, 'data', 'upload_history.json')
pid_file = os.path.join(BASE_DIR, 'data', 'daemon.pid')
max_daily = 3
min_cooldown = 3.0

print("========================================================")
print("  YouTube Shorts Bot - Live Status & Schedule Checker")
print("========================================================")

print("\n--- [1] Background Auto-Post Daemon ---")
daemon_running = False
if os.path.exists(pid_file):
    try:
        with open(pid_file) as f:
            pid = int(f.read().strip())
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, pid)
        if handle != 0:
            kernel32.CloseHandle(handle)
            daemon_running = True
            print(f" Status: [RUNNING] (Process ID: {pid})")
            print(" The bot is active in the background and monitors your laptop.")
    except Exception:
        pass

if not daemon_running:
    print(" Status: [NOT RUNNING]")
    print(" (Double-click 'start_daemon.bat' to start it right now,")
    print("  or it will automatically start next time you boot/log into Windows)")

print("\n--- [2] Upload Quota & 3-Hour Cooldown ---")
history = []
if os.path.exists(history_file):
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
    except Exception:
        history = []

today_str = datetime.now().strftime('%Y-%m-%d')
today_uploads = [t for t in history if t.get('date') == today_str]
print(f" Today's Date: {today_str}")
print(f" Posts Uploaded Today: {len(today_uploads)} / {max_daily}")

if len(today_uploads) >= max_daily:
    print(" Status: Daily limit reached! All 3 Shorts for today are uploaded.")
elif history:
    last_t = history[-1].get('timestamp', 0)
    elapsed = (time.time() - last_t) / 3600.0
    if elapsed < min_cooldown:
        rem_mins = int((min_cooldown - elapsed) * 60)
        print(f" Cooldown: Active (Last uploaded {elapsed:.1f} hours ago)")
        print(f" Next Post: Unlocks in ~{rem_mins} minutes (or on next laptop open after that)")
    else:
        print(" Cooldown: CLEARED (Ready to upload on next laptop open or trigger)")
else:
    print(" Cooldown: CLEARED (Ready to post first video!)")

print("\n--- [3] Recent Daemon Activity ---")
log_file = os.path.join(BASE_DIR, 'logs', 'daemon.log')
if os.path.exists(log_file):
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
        for line in lines[-8:]:
            print(" ", line.strip())
else:
    print(" No background logs recorded yet.")

print("\n========================================================")
