"""
indicators.py — Indicator computation module.

All calculations are strictly causal (no lookahead bias).
All rolling/shift operations use only past data.

ASSUMPTIONS VS PINE SCRIPT:
  • Pine Script's `ta.ema` uses RMA (Wilder MA) for ATR/ADX internals but EMA
    for plain EMA calls. The `ta` library matches this behaviour.
  • Weekly EMA50 uses shift(1) before reindex so each daily bar sees only the
    last *completed* weekly bar (matches barmerge.lookahead_off).
  • `highest_high_12` and `lowest_low_12` are shifted by 1 bar to exclude the
    current bar (matches Pine's `ta.highest(high, 12)[1]`).
  • `lowest_low_50` is *not* shifted (current bar included), matching Pine's
    `ta.lowest(low, room_bars)` used in the room_to_fall calculation.
"""

import numpy as np
import pandas as pd
from ta.trend import EMAIndicator, ADXIndicator
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange


# ── Weekly EMA50 ───────────────────────────────────────────────────────────────
def compute_weekly_ema50(df: pd.DataFrame) -> pd.Series:
    """
    Resample daily close to weekly (week-ending Friday), compute EMA50,
    shift by 1 completed week to avoid lookahead, then forward-fill to daily.
    """
    weekly_close = df["Close"].resample("W-FRI").last().dropna()

    if len(weekly_close) < 52:
        # Not enough weekly history — return NaN series
        return pd.Series(np.nan, index=df.index, name="weekly_ema50")

    w_ema50 = EMAIndicator(close=weekly_close, window=50, fillna=False).ema_indicator()

    # shift(1): use the value from the *last completed* weekly bar, not the current one
    w_ema50_lag = w_ema50.shift(1)

    # Reindex to daily frequency, forward-fill (last known weekly value)
    daily = w_ema50_lag.reindex(df.index, method="ffill")
    daily.name = "weekly_ema50"
    return daily


# ── Main indicator factory ─────────────────────────────────────────────────────
def prepare_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute all strategy indicators and derived columns.
    Input df must have columns: Open, High, Low, Close, Volume.
    Returns a new DataFrame with all indicator columns appended.
    """
    df = df.copy()

    # ── Core EMAs ─────────────────────────────────────────────────────────────
    df["EMA21"]  = EMAIndicator(close=df["Close"], window=21,  fillna=False).ema_indicator()
    df["EMA50"]  = EMAIndicator(close=df["Close"], window=50,  fillna=False).ema_indicator()
    df["EMA200"] = EMAIndicator(close=df["Close"], window=200, fillna=False).ema_indicator()

    # ── RSI 14 ────────────────────────────────────────────────────────────────
    df["RSI"] = RSIIndicator(close=df["Close"], window=14, fillna=False).rsi()

    # ── ADX / DI+ / DI- (14) ──────────────────────────────────────────────────
    adx_ind     = ADXIndicator(
        high=df["High"], low=df["Low"], close=df["Close"],
        window=14, fillna=False
    )
    df["ADX"]    = adx_ind.adx()
    df["DI_pos"] = adx_ind.adx_pos()
    df["DI_neg"] = adx_ind.adx_neg()

    # ── ATR 14 ────────────────────────────────────────────────────────────────
    df["ATR"] = AverageTrueRange(
        high=df["High"], low=df["Low"], close=df["Close"],
        window=14, fillna=False
    ).average_true_range()

    # ── Volume SMA 20 ─────────────────────────────────────────────────────────
    df["VOL_SMA20"] = df["Volume"].rolling(window=20, min_periods=20).mean()

    # ── Weekly EMA 50 (higher-timeframe filter) ───────────────────────────────
    df["weekly_ema50"] = compute_weekly_ema50(df)
    df["weekly_bull"]  = df["Close"] > df["weekly_ema50"]
    df["weekly_bear"]  = df["Close"] < df["weekly_ema50"]

    # ── EMA slopes (5-bar look-back, strictly causal) ─────────────────────────
    df["ema21_slope"] = df["EMA21"] - df["EMA21"].shift(5)
    df["ema50_slope"] = df["EMA50"] - df["EMA50"].shift(5)

    # ── Mesh / trend composite ────────────────────────────────────────────────
    df["green_mesh"] = df["EMA21"] > df["EMA50"]
    df["red_mesh"]   = df["EMA21"] < df["EMA50"]

    df["bull_trend"] = (
        df["green_mesh"] &
        (df["EMA50"] > df["EMA200"]) &
        (df["ema21_slope"] > 0) &
        (df["ema50_slope"] > 0)
    )
    df["bear_trend"] = (
        df["red_mesh"] &
        (df["EMA50"] < df["EMA200"]) &
        (df["ema21_slope"] < 0) &
        (df["ema50_slope"] < 0)
    )

    # ── Candle quality ────────────────────────────────────────────────────────
    hl = (df["High"] - df["Low"]).clip(lower=1e-8)

    df["candle_bull"] = (
        (df["Close"] > df["Open"]) &
        ((df["Close"] - df["Low"]) / hl >= 0.50)
    )
    df["candle_bear"] = (
        (df["Close"] < df["Open"]) &
        ((df["High"] - df["Close"]) / hl >= 0.50)
    )
    df["bo_candle_bull"] = (
        (df["Close"] > df["Open"]) &
        (df["Close"] >= df["High"] * 0.96)
    )
    df["bo_candle_bear"] = (
        (df["Close"] < df["Open"]) &
        (df["Close"] <= df["Low"] * 1.04)
    )

    # ── Swing levels ──────────────────────────────────────────────────────────
    # shift(1): exclude current bar so the breakout condition is strictly
    # "close > the highest high of the previous 12 bars"  (no lookahead)
    df["highest_high_12"] = df["High"].rolling(window=12, min_periods=12).max().shift(1)
    df["lowest_low_12"]   = df["Low"].rolling(window=12, min_periods=12).min().shift(1)

    # NOT shifted: room_to_fall needs current bar's rolling low
    df["lowest_low_50"] = df["Low"].rolling(window=50, min_periods=50).min()

    return df
