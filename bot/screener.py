"""
screener.py — Fetch fresh daily data for every stock in the watchlist
and run the signal engine on each one.

Returns a list of signal dicts for stocks that fired a signal today.
"""

import sys
import os
import warnings
import pandas as pd
import yfinance as yf
from tqdm import tqdm

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from bot.universe import WATCHLIST, NEGATIVE_EDGE
from bot.signal_engine import detect
from bot.config import DATA_PERIOD, MIN_BARS

warnings.filterwarnings("ignore")


def _fetch(ticker: str) -> pd.DataFrame | None:
    """Download last 2 years of daily OHLCV. Returns None on failure."""
    try:
        raw = yf.download(
            ticker,
            period=DATA_PERIOD,
            interval="1d",
            auto_adjust=True,
            progress=False,
            actions=False,
        )
    except Exception as e:
        print(f"  [ERROR] {ticker}: {e}")
        return None

    if raw is None or raw.empty:
        return None

    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)

    needed = ["Open", "High", "Low", "Close", "Volume"]
    if not all(c in raw.columns for c in needed):
        return None

    df = raw[needed].copy()
    df.ffill(inplace=True)
    df.dropna(inplace=True)
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df = df[df["Close"] > 0]

    if len(df) < MIN_BARS:
        print(f"  [SKIP]  {ticker}: only {len(df)} bars (need {MIN_BARS})")
        return None

    return df


def run_scan(watchlist: list[str] = None, verbose: bool = True) -> list[dict]:
    """
    Scan every ticker in watchlist.

    Parameters
    ----------
    watchlist : list of tickers (defaults to universe.WATCHLIST)
    verbose   : print progress bar

    Returns
    -------
    List of signal dicts sorted by signal score descending.
    Each dict also carries a 'negative_edge' bool flag.
    """
    if watchlist is None:
        watchlist = WATCHLIST

    alerts: list[dict] = []
    failed: list[str]  = []

    iterator = tqdm(watchlist, desc="Scanning", ncols=72) if verbose else watchlist

    for ticker in iterator:
        df = _fetch(ticker)
        if df is None:
            failed.append(ticker)
            continue

        try:
            signals = detect(df, ticker)
        except Exception as e:
            print(f"  [ERR]   {ticker}: signal engine failed — {e}")
            failed.append(ticker)
            continue

        for sig in signals:
            sig["negative_edge"] = (ticker in NEGATIVE_EDGE)
            alerts.append(sig)

    if failed and verbose:
        print(f"\n  Could not process: {', '.join(failed)}")

    # Sort: high score first; within same score, longs before shorts
    alerts.sort(key=lambda s: (-s["score"], s["direction"]))
    return alerts
