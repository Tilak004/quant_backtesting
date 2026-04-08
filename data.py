"""
data.py — Data download and management module.

Downloads daily OHLCV data for all NSE tickers from yfinance,
cleans it, and saves to /data/raw/ as CSV files.
"""

import os
import warnings
import pandas as pd
import yfinance as yf
from tqdm import tqdm

warnings.filterwarnings("ignore")

# ── Configuration ──────────────────────────────────────────────────────────────
TICKERS = [
    # ── Core large-caps ────────────────────────────────────────────────────────
    "HDFCBANK.NS",   "INFY.NS",       "ICICIBANK.NS",
    "SBIN.NS",       "WIPRO.NS",      "SUNPHARMA.NS",  "LT.NS",
    # ── User watchlist ─────────────────────────────────────────────────────────
    "BHARTIARTL.NS", "DIXON.NS",      "BSE.NS",
    "CANBK.NS",      "BEL.NS",        "HAL.NS",
    # ── Additional trending NSE names (sample-size expansion) ──────────────────
    "TITAN.NS",      "BAJFINANCE.NS", "HCLTECH.NS",
    "TRENT.NS",      "PERSISTENT.NS",    "SIEMENS.NS",
]
NIFTY_TICKER   = "^NSEI"
START_DATE     = "2019-01-01"
END_DATE       = "2026-04-30"
MAX_MISSING_PCT = 0.05          # skip ticker if >5 % bars missing

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR  = os.path.join(BASE_DIR, "data", "raw")


# ── Helpers ────────────────────────────────────────────────────────────────────
def ensure_dirs():
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "results", "charts"), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "results"), exist_ok=True)


def _safe_name(ticker: str) -> str:
    """Convert ticker to a safe filename stem."""
    return ticker.replace("^", "IDX_").replace(".", "_")


# ── Core download function ─────────────────────────────────────────────────────
def download_ticker(ticker: str,
                    start: str = START_DATE,
                    end: str   = END_DATE,
                    interval: str = "1d") -> pd.DataFrame | None:
    """
    Download OHLCV data for a single ticker.
    Returns cleaned DataFrame or None if data quality fails.
    """
    try:
        raw = yf.download(
            ticker, start=start, end=end,
            interval=interval, auto_adjust=True,
            progress=False, actions=False,
        )
    except Exception as exc:
        print(f"  [ERROR] {ticker}: download exception — {exc}")
        return None

    if raw is None or raw.empty:
        print(f"  [WARN]  {ticker}: no data returned")
        return None

    # Flatten multi-level columns (happens when yfinance returns extra levels)
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)

    # Keep standard OHLCV columns only
    needed = ["Open", "High", "Low", "Close", "Volume"]
    missing_cols = [c for c in needed if c not in raw.columns]
    if missing_cols:
        print(f"  [WARN]  {ticker}: missing columns {missing_cols}")
        return None

    df = raw[needed].copy()

    # ── Data-quality gate ──────────────────────────────────────────────────────
    total_rows   = len(df)
    n_nan        = df["Close"].isna().sum()
    missing_frac = n_nan / total_rows if total_rows > 0 else 1.0

    if missing_frac > MAX_MISSING_PCT:
        print(
            f"  [SKIP]  {ticker}: {missing_frac:.1%} missing bars "
            f"exceeds {MAX_MISSING_PCT:.0%} threshold — skipping"
        )
        return None

    # Forward-fill minor gaps, then drop any remaining NaN rows
    df.ffill(inplace=True)
    df.dropna(inplace=True)

    # Ensure index is DatetimeIndex (timezone-naive)
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df.index.name = "Date"

    # Sanity: close must be positive
    df = df[df["Close"] > 0]

    n_filled = int(n_nan)
    print(
        f"  [OK]    {ticker}: {len(df):,} bars  "
        f"({n_filled} NaN rows forward-filled)"
    )
    return df


# ── Batch download ─────────────────────────────────────────────────────────────
def download_all_data(tickers=None, force_download: bool = False) -> dict:
    """
    Download (or load from cache) data for all tickers.
    Returns dict  { ticker: DataFrame }.
    """
    if tickers is None:
        tickers = TICKERS + [NIFTY_TICKER]

    ensure_dirs()
    data_dict: dict[str, pd.DataFrame] = {}

    print("\n" + "=" * 60)
    print("  STAGE 1 — Downloading Market Data")
    print("=" * 60)

    for ticker in tqdm(tickers, desc="Tickers", ncols=70):
        csv_path = os.path.join(RAW_DIR, f"{_safe_name(ticker)}.csv")

        if os.path.exists(csv_path) and not force_download:
            df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
            df.index = pd.to_datetime(df.index).tz_localize(None)
            print(f"  [CACHE] {ticker}: loaded {len(df):,} bars from disk")
        else:
            df = download_ticker(ticker)
            if df is not None:
                df.to_csv(csv_path)

        if df is not None and not df.empty:
            data_dict[ticker] = df

    print(f"\n  Downloaded {len(data_dict)} / {len(tickers)} tickers successfully.")
    return data_dict


# ── Single-ticker loader ───────────────────────────────────────────────────────
def load_data(ticker: str) -> pd.DataFrame | None:
    """Load a single ticker from CSV cache."""
    csv_path = os.path.join(RAW_DIR, f"{_safe_name(ticker)}.csv")
    if not os.path.exists(csv_path):
        return None
    df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df
