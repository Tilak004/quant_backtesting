"""
main.py — Run the NSE swing screener once and send the email alert.

Usage
-----
  # Run immediately (manual / test run):
  python bot/main.py

  # Test with a few specific tickers only:
  python bot/main.py --tickers WIPRO.NS PERSISTENT.NS

  # Dry run — scan and print results, do NOT send email:
  python bot/main.py --dry-run
"""

import sys
import os
import argparse
from datetime import datetime
from zoneinfo import ZoneInfo

# Ensure Unicode prints correctly on Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from bot.screener import run_scan
from bot.notifier import send_alert


def _print_summary(signals: list[dict], patterns: list[dict]) -> None:
    """Pretty-print scan results to the terminal."""
    print()
    if not signals:
        print("  ── No signals today ─────────────────────────────────────────")
    else:
        sep = "─" * 70
        print(f"  {sep}")
        print(f"  {'TICKER':<14} {'TYPE':<8} {'DIR':<6} {'SCORE':<7} "
              f"{'ENTRY':>9} {'SL':>9} {'TP':>9}  {'R/R'}")
        print(f"  {sep}")
        for s in signals:
            warn = " ⚠" if s.get("negative_edge") else ""
            print(
                f"  {s['ticker']:<14} {s['signal_type']:<8} {s['direction']:<6} "
                f"{s['score']}/7    "
                f"₹{s['entry']:>8,.0f}  ₹{s['sl']:>8,.0f}  ₹{s['tp']:>8,.0f}  "
                f"1:{s['rr']}{warn}"
            )
        print(f"  {sep}")
        print(f"  Total signals: {len(signals)}")

    if patterns:
        print(f"\n  ── Chart Patterns ({len(patterns)}) ──────────────────────────────")
        for p in patterns[:10]:   # show top 10 in terminal
            conf = "🟢" if p["confidence"] == "HIGH" else "🟡"
            print(f"  {conf} {p['ticker']:<18} [{p['pattern']}]")


def run(watchlist: list[str] | None = None,
        dry_run:   bool            = False) -> dict:
    """Callable entry-point used by pipeline.py and tests."""
    print("=" * 70)
    print(f"  NSE Swing Screener  ·  {datetime.now(ZoneInfo('Asia/Kolkata')).strftime('%d %b %Y  %H:%M IST')}")
    print("=" * 70)

    result   = run_scan(watchlist=watchlist, verbose=True)
    signals  = result["signals"]
    patterns = result["patterns"]

    _print_summary(signals, patterns)

    if dry_run:
        print("\n  [DRY RUN] Email not sent.")
    else:
        print()
        send_alert(signals, patterns=patterns)

    return result


def main():
    parser = argparse.ArgumentParser(description="NSE Swing Alert Screener")
    parser.add_argument("--tickers", nargs="+", metavar="TICKER")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(watchlist=args.tickers or None, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
