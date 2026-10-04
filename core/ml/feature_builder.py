"""
core/ml/feature_builder.py

Builds a feature matrix by joining each historical trade with the
indicator values that existed AT THE ENTRY BAR — no lookahead.

Features used:
  signal_type_enc  — PB-L / BO-L / BASE-BO encoded as int
  direction        — 1=long, 0=short
  rsi              — RSI at entry bar
  adx              — ADX at entry bar (trend strength)
  vol_ratio        — Volume / VOL_SMA20 (volume confirmation quality)
  atr_pct          — ATR / Close (volatility regime)
  pct_from_high    — % below 52-week high (pullback depth)
  near_support     — 1 if price within 1.5 ATR of prior pivot low
  bull_trend       — 1 if EMA stack bullish
  green_mesh       — 1 if EMA21 > EMA50
  exit_reason_enc  — TP=2, MeshBreak=1, SL=0  (for analysis only — NOT a feature)
"""

from __future__ import annotations

import glob
import warnings
from pathlib import Path

import pandas as pd

_RESULTS = Path("results")
_RAW     = Path("data/raw")

SIGNAL_ENC = {"PB-L": 0, "BO-L": 1, "BASE-BO": 2, "PB50-L": 3,
              "PB-S": 4, "BO-S": 5}

FEATURE_COLS = [
    "signal_type_enc", "direction", "rsi", "adx", "vol_ratio",
    "atr_pct", "pct_from_high", "near_support", "bull_trend", "green_mesh",
]


def _safe_name(ticker: str) -> str:
    return ticker.replace("^", "IDX_").replace(".", "_")


def _load_indicators(ticker: str) -> pd.DataFrame | None:
    """Load and prepare indicators for a ticker. Cached in memory per call."""
    csv = _RAW / f"{_safe_name(ticker)}.csv"
    if not csv.exists():
        return None
    try:
        from indicators import prepare_indicators
        raw = pd.read_csv(csv, index_col=0, parse_dates=True)
        raw.index = pd.to_datetime(raw.index).tz_localize(None)
        if len(raw) < 100:
            return None
        return prepare_indicators(raw)
    except Exception as e:
        import warnings
        warnings.warn(f"Failed to load indicators for {ticker}: {e}")
        return None


def build_features(results_dir: str | None = None) -> pd.DataFrame:
    """
    Build feature matrix for all historical trades.
    Returns DataFrame with FEATURE_COLS + 'win' (target) + meta columns.
    """
    base = Path(results_dir) if results_dir else _RESULTS
    frames = []
    for f in glob.glob(str(base / "trades_*.csv")):
        # trades_OOS_best.csv is the optimiser's walk-forward aggregate: a
        # DIFFERENT parameter set, and ~56% of its rows duplicate trades already
        # present in the per-ticker files. Pooling it double-counts samples and
        # mixes two strategies into one training set.
        if "OOS" in Path(f).name:
            continue
        try:
            df = pd.read_csv(f)
            if not df.empty and "signal_type" in df.columns:
                frames.append(df)
        except Exception as e:
            warnings.warn(f"Skipping {Path(f).name}: {e}")

    if not frames:
        raise FileNotFoundError("No trade CSVs found — run backtest first.")

    trades = pd.concat(frames, ignore_index=True)
    trades["entry_date"] = pd.to_datetime(trades["entry_date"])
    trades = trades.sort_values("entry_date").reset_index(drop=True)

    # Cache indicator DataFrames per ticker to avoid re-reading
    ind_cache: dict[str, pd.DataFrame | None] = {}
    rows = []

    for _, t in trades.iterrows():
        ticker = t["ticker"]

        if ticker not in ind_cache:
            ind_cache[ticker] = _load_indicators(ticker)

        ind = ind_cache[ticker]
        if ind is None:
            continue

        # Find closest bar to entry_date (forward-fill safe)
        entry = pd.Timestamp(t["entry_date"])
        if entry not in ind.index:
            loc = ind.index.get_indexer([entry], method="nearest")[0]
            bar = ind.iloc[loc]
        else:
            bar = ind.loc[entry]

        # pct_from_high: how far below the 52-week high was the entry
        idx_pos = ind.index.get_loc(bar.name) if bar.name in ind.index else -1
        if idx_pos >= 20:
            high_252 = float(ind["High"].iloc[max(0, idx_pos - 252): idx_pos + 1].max())
            pct_from_high = (float(bar["Close"]) - high_252) / high_252
        else:
            pct_from_high = 0.0

        row = {
            # ── Features (all known at entry bar) ────────────────────────────
            "signal_type_enc": SIGNAL_ENC.get(str(t["signal_type"]), -1),
            "direction":       1 if str(t["direction"]) == "long" else 0,
            "rsi":             float(bar.get("RSI", 50)),
            "adx":             float(bar.get("ADX", 20)),
            "vol_ratio":       float(bar.get("Volume", 1)) /
                               max(float(bar.get("VOL_SMA20", 1)), 1e-6),
            "atr_pct":         float(t["atr_at_entry"]) /
                               max(float(bar.get("Close", 100)), 1e-6),
            "pct_from_high":   pct_from_high,
            "near_support":    int(bool(bar.get("near_support", False))),
            "bull_trend":      int(bool(bar.get("bull_trend", False))),
            "green_mesh":      int(bool(bar.get("green_mesh", False))),
            # ── Target ───────────────────────────────────────────────────────
            "win":             int(float(t["pnl_pct"]) > 0),
            # ── Meta (not used as features) ───────────────────────────────────
            "entry_date":      entry,
            "ticker":          ticker,
            "signal_type":     t["signal_type"],
            "pnl_pct":         float(t["pnl_pct"]),
            "pnl_on_equity":   float(t.get("pnl_on_equity", t["pnl_pct"])),
            "exit_reason":     str(t.get("exit_reason", "")),
            "position_pct":    float(t.get("position_pct", 15.0)),
        }
        rows.append(row)

    result = pd.DataFrame(rows).dropna(subset=FEATURE_COLS)
    print(f"  Built feature matrix: {len(result)} samples "
          f"({result['win'].mean()*100:.1f}% wins)")
    return result
