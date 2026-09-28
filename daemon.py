"""
Background Daemon for YouTube Shorts Bot.
Runs silently in the background, waking up whenever the laptop is open.
Checks cooldown (3.0 hours) and daily limit (3 posts/day) every 60 seconds.
When eligible, automatically curates, narrates, edits, and uploads a viral Short.
"""
import os
import sys
import time
import signal
import logging
from datetime import datetime

# Path setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

# Configure logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [DAEMON] - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/daemon.log', encoding='utf-8')
    ]
)
logger = logging.getLogger("AutoPostDaemon")

PID_FILE = os.path.join(BASE_DIR, "data", "daemon.pid")

def is_pid_running(pid: int) -> bool:
    """Check if process with PID is alive on Windows."""
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if handle == 0:
            return False
        kernel32.CloseHandle(handle)
        return True
    except Exception:
        return False

def acquire_single_instance_lock():
    """Ensure only one daemon instance is active at a time."""
    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, 'r') as f:
                old_pid = int(f.read().strip())
            if is_pid_running(old_pid):
                logger.warning(f"Daemon already running with PID {old_pid}. Exiting duplicate.")
                sys.exit(0)
        except Exception:
            pass

    current_pid = os.getpid()
    with open(PID_FILE, 'w') as f:
        f.write(str(current_pid))
    logger.info(f"Daemon lock acquired. Running PID: {current_pid}")

def cleanup_pid():
    if os.path.exists(PID_FILE):
        try:
            os.remove(PID_FILE)
        except Exception:
            pass

def main():
    acquire_single_instance_lock()
    logger.info("========================================================")
    logger.info("  YouTube Shorts Auto-Poster Daemon Started")
    logger.info("  Active monitoring: Every 60s (Laptop wake/unlock safe)")
    logger.info("========================================================")

    from main import ShortsBotPipeline

    bot = None
    try:
        bot = ShortsBotPipeline()
    except Exception as e:
        logger.error(f"Failed to initialize ShortsBotPipeline: {e}")
        cleanup_pid()
        sys.exit(1)

    CHECK_INTERVAL = 60  # Check every 60 seconds
    last_logged_reason = ""

    from core.clipping_orchestrator import ClippingOrchestrator
    clipping_orch = ClippingOrchestrator()
    last_upload_minute = ""

    while True:
        try:
            cfg = bot._load_config() if hasattr(bot, '_load_config') else {}
            mode = cfg.get("content", {}).get("mode", "channel_clipping")
            sched_cfg = cfg.get("schedule", {})
            sched_mode = sched_cfg.get("mode", "fixed_times")
            upload_times = sched_cfg.get("upload_times", ["10:00", "18:00"])

            now = datetime.now()
            now_hm = now.strftime("%H:%M")

            trigger_upload = False

            if sched_mode == "fixed_times":
                if now_hm in upload_times and now_hm != last_upload_minute:
                    logger.info(f"⏰ SCHEDULED TIME REACHED ({now_hm})! Triggering upload window.")
                    trigger_upload = True
                    last_upload_minute = now_hm
                else:
                    reason = f"Waiting for scheduled upload times: {upload_times} (Current time: {now_hm})"
            else:
                can_post, reason = bot._can_upload_now()
                if can_post:
                    trigger_upload = True

            if trigger_upload:
                logger.info(f"🚀 Launching pipeline in mode: '{mode}'...")
                
                if mode == "channel_clipping":
                    result = clipping_orch.run_automated_clip_and_upload()
                    if result and result.get("status") == "success":
                        logger.info(f"✅ AUTO-CLIP UPLOAD COMPLETE! URL: {result.get('youtube_url')}")
                    else:
                        logger.warning("⚠️ Channel clipping pipeline returned no upload.")
                else:
                    # Story universe / other modes
                    result = bot.run(force=False)
                    if result.get('success'):
                        yt_id = result.get('platforms', {}).get('youtube', 'Unknown')
                        logger.info(f"✅ AUTO-POST COMPLETE! YouTube Video ID: {yt_id}")
                    else:
                        logger.warning(f"⚠️ Pipeline completed with errors: {result.get('errors')}")

                time.sleep(CHECK_INTERVAL)
            else:
                if reason != last_logged_reason:
                    logger.info(f"⏳ {reason}")
                    last_logged_reason = reason
                    
                time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            logger.info("Daemon stopped by user.")
            break
        except Exception as e:
            logger.error(f"Unexpected error in daemon loop: {e}", exc_info=True)
            time.sleep(30)  # brief cool-off on error (e.g. WiFi reconnecting on lid open)

    cleanup_pid()

if __name__ == '__main__':
    main()
