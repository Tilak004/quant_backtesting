"""
config.py — Strategy parameters and environment variable names.

Parameters are the Walk-Forward Optimisation best-fit values from the backtest.
Edit PARAMS to tune the strategy without touching any other file.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Strategy parameters (WFO best-fit) ────────────────────────────────────────
PARAMS: dict = {
    # Risk management
    "sl_mult":       1.5,    # SL = entry − ATR × 1.5
    "tp_mult_long":  3.5,    # TP = entry + ATR × 3.5
    "tp_mult_short": 2.25,

    # ADX thresholds
    "adx_long":      12,     # minimum ADX to take a long
    "adx_short":     20,     # minimum ADX to take a short

    # RSI ranges — longs (pullback)
    "rsi_pb_lo":     35,
    "rsi_pb_hi":     58,

    # RSI ranges — longs (breakout)
    "rsi_bo_lo":     48,
    "rsi_bo_hi":     75,

    # RSI ranges — longs (pullback to EMA50)
    "rsi_pb50_lo":   38,
    "rsi_pb50_hi":   55,

    # RSI ranges — shorts
    "rsi_pbs_lo":    45,
    "rsi_pbs_hi":    60,
    "rsi_bos_lo":    30,
    "rsi_bos_hi":    50,

    # Volume multipliers
    "vol_mult_long":  1.1,
    "vol_mult_short": 1.3,

    # Entry zone tolerances (matching Pine Script)
    "pb_tol":        1.008,  # low ≤ EMA21 × 1.008
    "pb50_tol":      1.005,  # low ≤ EMA50 × 1.005
    "pb_short_tol":  0.997,  # high ≥ EMA21 × 0.997

    # Short-only filters
    "di_gap_min":    5.0,
    "min_room_atr":  3.0,
}

# ── Gmail credentials (loaded from .env) ──────────────────────────────────────
GMAIL_SENDER   = os.getenv("GMAIL_SENDER")       # Gmail address that sends the alert
GMAIL_APP_PASS = os.getenv("GMAIL_APP_PASS")     # Gmail App Password (16 chars, no spaces)

# Multiple recipients supported — comma-separated in .env
# e.g.  ALERT_RECIPIENTS=you@gmail.com,friend@gmail.com
_raw_recipients = os.getenv("ALERT_RECIPIENTS", os.getenv("ALERT_RECIPIENT", ""))
ALERT_RECIPIENTS: list[str] = [r.strip() for r in _raw_recipients.split(",") if r.strip()]

# ── Data settings ─────────────────────────────────────────────────────────────
DATA_PERIOD = "2y"       # how far back to pull for indicator warm-up (needs ≥ 250 bars)
MIN_BARS    = 260        # skip ticker if fewer bars available
