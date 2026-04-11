"""
scheduler.py — Keep running and fire the screener every weekday at 11:00 AM IST.

At 11 AM the market has been open ~1h 45min but today's daily bar is not yet
closed.  yfinance returns the last COMPLETED daily bar (previous day's close),
so the signals you receive at 11 AM are based on yesterday's final candle —
ready to act on today.

This script is meant to run silently in the background.
The easiest way to auto-start it on Windows is via Task Scheduler
(see README or the run_screener.bat file in the project root).
"""

import sys
import os
import time
import schedule
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from bot.main import main as run_screener

# ── Scheduled job ──────────────────────────────────────────────────────────────
SCAN_TIME_IST = "11:00"   # 11:00 AM IST — change here if you ever want a different time


def _job():
    now = datetime.now()
    # Skip weekends (Saturday=5, Sunday=6)
    if now.weekday() >= 5:
        print(f"[SCHEDULER] {now.strftime('%a %d %b')} is a weekend — skipping.")
        return
    print(f"\n[SCHEDULER] Firing scan at {now.strftime('%H:%M')} IST …")
    try:
        run_screener()
    except Exception as e:
        print(f"[SCHEDULER] Scan failed with error: {e}")


# ── Schedule and loop ──────────────────────────────────────────────────────────
schedule.every().day.at(SCAN_TIME_IST).do(_job)

print("=" * 60)
print(f"  NSE Screener Scheduler started")
print(f"  Scan time : {SCAN_TIME_IST} IST  (Mon - Fri)")
print(f"  Local time: {datetime.now().strftime('%H:%M')} on "
      f"{datetime.now().strftime('%A %d %b %Y')}")
print(f"  Keep this window open.  Press Ctrl+C to stop.")
print("=" * 60)

while True:
    schedule.run_pending()
    time.sleep(30)   # check every 30 seconds
