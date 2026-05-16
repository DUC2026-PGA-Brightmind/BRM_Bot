# run_both.py - Run both bots in parallel (for single Railway service)
# Each bot runs in its own thread

import threading
import subprocess
import sys
import time
import os

def run_bot(script_name):
    """Run a bot script and restart it if it crashes."""
    while True:
        print(f"▶ Starting {script_name}...")
        try:
            proc = subprocess.Popen(
                [sys.executable, script_name],
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            proc.wait()
            print(f"⚠ {script_name} exited with code {proc.returncode}. Restarting in 5s...")
        except Exception as e:
            print(f"❌ Error running {script_name}: {e}")
        time.sleep(5)

if __name__ == "__main__":
    print("🚀 Starting BrightMind HR Bots...")

    # Run worker bot in thread
    t1 = threading.Thread(target=run_bot, args=("bot.py",), daemon=True)
    t1.start()

    # Run admin bot in main thread (keeps process alive)
    run_bot("admin_bot.py")
