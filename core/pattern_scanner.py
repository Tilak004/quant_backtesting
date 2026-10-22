"""
core/pattern_scanner.py — Chart pattern recognition across the full universe.

Runs BEFORE the EMA signal fires — detects setups FORMING so you can watch them.
Each detector returns a dict or None.

Bullish patterns:
  DOUBLE_BOTTOM        — Two swing lows at same level, neckline above
  BULL_FLAG            — Sharp pole + tight consolidation channel (5+ bars)
  BULL_PENNANT         — Sharp pole + symmetrical triangle consolidation
  FALLING_WEDGE        — Converging declining highs/lows (reversal)
  DESCENDING_CHANNEL   — Parallel declining channel (like NTPCGREEN)
  ASCENDING_TRIANGLE   — Flat resistance + rising support
  CUP_AND_HANDLE       — U-shape recovery + shallow handle pullback
  INV_HEAD_SHOULDERS   — Three troughs, middle deepest, neckline overhead

Bearish patterns:
  HEAD_SHOULDERS       — Three peaks, middle highest, neckline below
  DOUBLE_TOP           — Two swing highs at same level

Neutral patterns:
  SYMMETRICAL_TRIANGLE — Converging highs/lows, breakout either direction
"""

from __future__ import annotations

import math
import numpy as np
import pandas as pd
from typing import Optional


# ── helpers ───────────────────────────────────────────────────────────────────

def _swing_lows(low: pd.Series, high: pd.Series, n: int = 3) -> list[tuple[int, float]]:
    """Return list of (bar_index, price) for confirmed swing lows (causal)."""
    out = []
    window = 2 * n + 1
    roll_min = low.rolling(window, min_periods=window).min()
    past_low = low.shift(n)
    is_pl    = past_low <= roll_min
    for i in range(len(low)):
        if is_pl.iloc[i] and not math.isnan(past_low.iloc[i]):
            out.append((i - n, float(past_low.iloc[i])))
    return out


def _swing_highs(high: pd.Series, n: int = 3) -> list[tuple[int, float]]:
    """Return list of (bar_index, price) for confirmed swing highs (causal)."""
    out = []
    window = 2 * n + 1
    roll_max = high.rolling(window, min_periods=window).max()
    past_high = high.shift(n)
    is_ph     = past_high >= roll_max
    for i in range(len(high)):
        if is_ph.iloc[i] and not math.isnan(past_high.iloc[i]):
            out.append((i - n, float(past_high.iloc[i])))
    return out


# ── Pattern 1: Double Bottom ──────────────────────────────────────────────────

def detect_double_bottom(df: pd.DataFrame,
                         lookback:            int   = 80,
                         tol_pct:             float = 0.02,   # user: 2% tolerance
                         min_downtrend_pct:   float = 0.08,   # prior drop before pattern
                         min_recovery_pct:    float = 0.04,   # neckline must be 4%+ above bottoms
                         false_break_tol:     float = 0.015)  -> Optional[dict]:  # spring tolerance
    """
    Rules defined by user:
    - Prior downtrend required (reversal pattern, not continuation)
    - Two bottoms within 2% of each other (no minimum time between them)
    - Recovery between bottoms must reach a clear neckline (4%+ above bottoms)
    - Three entry types returned:
        SECOND_BOTTOM   — price holding at second bottom level (sustaining)
        FALSE_BREAKDOWN — price briefly broke below, then recovered (spring)
        NECKLINE_BREAK  — price closed above neckline (most confirmed)
    """
    n = len(df)
    if n < lookback + 20:
        return None

    close  = df["Close"].values
    low_s  = df["Low"]
    sub    = df.iloc[-lookback:]

    # ── 1. Prior downtrend: price was meaningfully higher before the pattern ──
    # Look at the price 40+ bars before today — should be substantially higher
    pre_pattern_price = float(df["Close"].iloc[-(lookback)])
    current           = float(close[-1])
    first_bottom_area = float(low_s.iloc[-lookback:].min())

    # Prior high must be at least min_downtrend_pct above the pattern lows
    if (pre_pattern_price - first_bottom_area) / pre_pattern_price < min_downtrend_pct:
        return None   # no meaningful prior downtrend — not a reversal setup

    # ── 2. Find two swing lows within 2% of each other ───────────────────────
    lows  = _swing_lows(sub["Low"], sub["High"], n=3)
    highs = _swing_highs(sub["High"], n=2)

    if len(lows) < 2:
        return None

    best = None   # we want the MOST RECENT valid pair

    for i in range(len(lows) - 1, 0, -1):
        idx2, p2 = lows[i]
        for j in range(i - 1, -1, -1):
            idx1, p1 = lows[j]

            # ── 2a. Bottoms within 2% ─────────────────────────────────────────
            avg_bottom = (p1 + p2) / 2
            spread     = abs(p2 - p1) / avg_bottom
            if spread > tol_pct:
                continue

            # ── 2b. Neckline: highest high BETWEEN the two bottoms ────────────
            between = [ph for pidx, ph in highs if idx1 < pidx < idx2]
            if not between:
                continue
            neckline = max(between)

            # ── 2c. No significantly lower low in the window (user rule) ─────
            # If a lower swing low exists more than 3% below our bottoms,
            # these are NOT the real bottoms — pattern is invalid.
            # (This is what caught 5PAISA: ₹250 low invalidated ₹292-295 pair)
            floor = float(sub["Low"].min())
            if (avg_bottom - floor) / avg_bottom > 0.03:
                continue   # a deeper low exists — our "bottoms" aren't real bottoms

            # ── 2d. Recovery must be meaningful (neckline well above bottoms) ─
            recovery = (neckline - avg_bottom) / avg_bottom
            if recovery < min_recovery_pct:
                continue   # too flat — not a real W shape

            # ── 3. Determine entry type based on current price ────────────────
            # Map sub-index back to full df position
            bars_since_b2 = lookback - idx2

            # Current price relative to the pattern levels
            near_bottom   = current <= avg_bottom * (1 + false_break_tol * 2)
            broke_below   = float(low_s.iloc[-bars_since_b2:].min()) < avg_bottom * 0.998
            recovered     = current > avg_bottom * 0.998
            above_neck    = current >= neckline * 1.002

            if above_neck:
                entry_type = "NECKLINE_BREAK"
                confidence = "HIGH"
            elif broke_below and recovered:
                entry_type = "FALSE_BREAKDOWN"   # spring — trapped bears
                confidence = "HIGH"
            elif near_bottom and not broke_below:
                entry_type = "SECOND_BOTTOM"
                confidence = "MODERATE"
            else:
                # Pattern exists but price is between bottom and neckline
                entry_type = "WATCH"
                confidence = "MODERATE"

            # Skip LOW confidence entirely
            if confidence == "LOW":
                continue

            target = neckline + (neckline - avg_bottom)

            entry_desc = {
                "NECKLINE_BREAK":  f"✅ Confirmed — price broke above neckline ₹{neckline:,.0f}. Enter now.",
                "FALSE_BREAKDOWN": f"⚡ Spring entry — price faked below ₹{avg_bottom:,.0f} then recovered. Strong.",
                "SECOND_BOTTOM":   f"📍 At support ₹{avg_bottom:,.0f} — wait for bullish candle to sustain.",
                "WATCH":           f"⏳ Pattern valid, price between bottom and neckline. Watch ₹{neckline:,.0f}.",
            }.get(entry_type, "")

            best = {
                "pattern":       "DOUBLE_BOTTOM",
                "confidence":    confidence,
                "entry_type":    entry_type,
                "bottom1":       round(p1, 2),
                "bottom2":       round(p2, 2),
                "avg_bottom":    round(avg_bottom, 2),
                "neckline":      round(neckline, 2),
                "current":       round(current, 2),
                "target":        round(target, 2),
                "spread_pct":    round(spread * 100, 2),
                "recovery_pct":  round(recovery * 100, 1),
                "bars_forming":  int(idx2 - idx1),
                "description": (
                    f"Double Bottom: two lows at ₹{avg_bottom:,.0f} "
                    f"({spread*100:.1f}% apart, {recovery*100:.0f}% recovery to neckline ₹{neckline:,.0f}). "
                    f"{entry_desc} Target ₹{target:,.0f}."
                ),
            }
            break   # use most-recent valid pair
        if best:
            break

    return best


# ── Pattern 2: Bull Flag ──────────────────────────────────────────────────────

def detect_bull_flag(df: pd.DataFrame,
                     pole_min_pct:     float = 7.0,
                     pole_max_bars:    int   = 12,
                     flag_max_bars:    int   = 20,
                     flag_min_bars:    int   = 3,    # confirmed: SBIN/LT have 4-bar flags
                     flag_max_retrace: float = 0.50,
                     max_slope_per_bar: float = 1.5) -> Optional[dict]:
    """
    Pole: close rose >= pole_min_pct in <= pole_max_bars bars.
    Flag: subsequent consolidation retraces <= 50% of the pole, duration <= flag_max_bars.
    Confidence based on tightness of the flag channel.
    """
    n = len(df)
    if n < pole_max_bars + flag_max_bars + 10:
        return None

    close = df["Close"].values
    high  = df["High"].values
    low   = df["Low"].values
    vol   = df["Volume"].values

    # Search backward for a valid pole
    for flag_end in range(n - 1, n - flag_max_bars - 2, -1):
        for pole_end in range(flag_end, max(flag_end - flag_max_bars, 0), -1):
            for pole_start in range(pole_end - 1, max(pole_end - pole_max_bars, 0), -1):
                rise = (close[pole_end] - close[pole_start]) / close[pole_start] * 100
                if rise < pole_min_pct:
                    continue

                # Valid pole found — check flag consolidation from pole_end to current
                flag_slice_high = high[pole_end: flag_end + 1]
                flag_slice_low  = low[pole_end: flag_end + 1]
                flag_high = float(np.max(flag_slice_high))
                flag_low  = float(np.min(flag_slice_low))

                pole_size     = close[pole_end] - close[pole_start]
                retrace_pct   = (close[pole_end] - flag_low) / pole_size if pole_size > 0 else 1
                flag_range_pct = (flag_high - flag_low) / close[pole_end] * 100

                if retrace_pct > flag_max_retrace:
                    continue
                if flag_range_pct > 8.0:
                    continue  # too wide — not a flag

                # Flag duration — minimum 5 bars for a meaningful consolidation
                flag_bars = flag_end - pole_end
                if flag_bars < flag_min_bars:
                    continue

                # ── Slope constraint: max 45 degrees (user rule) ──────────────
                # Confirmed real flags: SBIN=0.27%/bar, LT=0.47%/bar
                # 45° max ≈ 1.5% decline per bar on NSE daily charts
                flag_decline_pct = (close[pole_end] - float(np.min(flag_slice_low))) \
                                   / close[pole_end] * 100
                slope_per_bar = flag_decline_pct / max(flag_bars, 1)
                if slope_per_bar > max_slope_per_bar:
                    continue   # too steep — exceeds 45-degree limit

                # Volume should decline during flag vs pole
                pole_vol  = float(np.mean(vol[pole_start:pole_end + 1]))
                flag_vol  = float(np.mean(vol[pole_end:flag_end + 1]))
                vol_contracting = flag_vol < pole_vol * 0.85

                if flag_range_pct < 4 and vol_contracting:
                    confidence = "HIGH"
                elif flag_range_pct < 6:
                    confidence = "MODERATE"
                else:
                    confidence = "LOW"

                target = float(close[pole_end]) + pole_size

                return {
                    "pattern":        "BULL_FLAG",
                    "confidence":     confidence,
                    "pole_start_px":  round(float(close[pole_start]), 2),
                    "pole_end_px":    round(float(close[pole_end]), 2),
                    "pole_rise_pct":  round(rise, 1),
                    "flag_high":      round(flag_high, 2),
                    "flag_low":       round(flag_low, 2),
                    "flag_bars":      flag_bars,
                    "retrace_pct":    round(retrace_pct * 100, 1),
                    "target":         round(target, 2),
                    "description": (
                        f"Bull flag: pole +{rise:.1f}% in {pole_end - pole_start} bars. "
                        f"Flag consolidating {flag_bars} bars ({flag_range_pct:.1f}% range, "
                        f"{retrace_pct * 100:.0f}% retrace). "
                        f"{'Volume contracting ✓' if vol_contracting else 'Volume not contracting'}. "
                        f"Breakout above ₹{flag_high:,.0f} targets ₹{target:,.0f}."
                    ),
                }

    return None


# ── Pattern 3: Falling Wedge ──────────────────────────────────────────────────

def detect_falling_wedge(df: pd.DataFrame,
                         lookback:           int   = 60,
                         min_bars:           int   = 10,
                         min_slope_pct:      float = 0.001,  # lines must clearly decline (lowered)
                         max_violation_frac: float = 0.25,   # max 25% bars above upper line
                         pivot_n:            int   = 2) -> Optional[dict]:
    """
    Rules confirmed by user:
    - No prior downtrend required
    - Both lines declining (minimum slope — rejects channels like SUNPHARMA)
    - Upper line falls FASTER than lower (converging to a point)
    - Upper trendline must be CLEAN — not too many bars spiking above it
    - Bullish reversal: breakout is upward above the upper declining line
    """
    n = len(df)
    if n < lookback + 10:
        return None

    sub      = df.iloc[-lookback:]
    highs_ph = _swing_highs(sub["High"], n=pivot_n)
    lows_pl  = _swing_lows(sub["Low"], sub["High"], n=pivot_n)

    # Need at least 2 pivot highs and 2 pivot lows for trendlines
    if len(highs_ph) < 2 or len(lows_pl) < 2:
        return None

    # Use last 3 pivots (or all available if fewer)
    h_pts = highs_ph[-3:] if len(highs_ph) >= 3 else highs_ph[-2:]
    l_pts = lows_pl[-3:]  if len(lows_pl)  >= 3 else lows_pl[-2:]

    h_idx  = np.array([x[0] for x in h_pts], dtype=float)
    h_vals = np.array([x[1] for x in h_pts], dtype=float)
    l_idx  = np.array([x[0] for x in l_pts], dtype=float)
    l_vals = np.array([x[1] for x in l_pts], dtype=float)

    h_slope, h_inter = np.polyfit(h_idx, h_vals, 1)
    l_slope, l_inter = np.polyfit(l_idx, l_vals, 1)
    h_slope = float(h_slope)
    h_inter = float(h_inter)
    l_slope = float(l_slope)
    l_inter = float(l_inter)

    # ── Rule 1: Both lines must be clearly declining ──────────────────────────
    # Normalise by price to get % slope per bar
    price_ref = float(sub["Close"].mean())
    h_slope_pct = abs(h_slope) / price_ref
    l_slope_pct = abs(l_slope) / price_ref

    if h_slope >= 0 or l_slope >= 0:
        return None   # lines not declining
    if h_slope_pct < min_slope_pct or l_slope_pct < min_slope_pct:
        return None   # too flat — this is a channel, not a wedge (rejects SUNPHARMA)

    # ── Rule 2: Upper line must fall faster than lower (converging) ───────────
    if abs(h_slope) <= abs(l_slope):
        return None   # not converging

    # ── Rule 3: Upper trendline must be clean ─────────────────────────────────
    # Count bars where price HIGH is significantly above the projected upper line
    pattern_start = int(min(h_idx[0], l_idx[0]))
    pattern_slice = sub.iloc[pattern_start:]
    bar_count = len(pattern_slice)

    if bar_count < min_bars:
        return None

    x_full     = np.arange(pattern_start, pattern_start + bar_count, dtype=float)
    upper_proj = h_inter + h_slope * x_full
    high_vals  = pattern_slice["High"].values

    # Violations: bar high exceeds the upper trendline by more than 1%
    violations = int(np.sum(high_vals > upper_proj * 1.01))
    if violations / bar_count > max_violation_frac:
        return None   # upper trendline is not clean (like INDUSTOWER's noisy line)

    # ── Output ─────────────────────────────────────────────────────────────────
    current    = float(df["Close"].iloc[-1])
    wedge_top  = float(h_inter + h_slope * (pattern_start + bar_count - 1))
    wedge_bot  = float(l_inter + l_slope * (pattern_start + bar_count - 1))
    breaking_out = current > wedge_top * 1.005

    converge_ratio = abs(h_slope) / max(abs(l_slope), 1e-6)
    violation_pct  = violations / bar_count

    if converge_ratio > 1.5 and violation_pct < 0.15:
        confidence = "HIGH"
    elif converge_ratio > 1.2:
        confidence = "MODERATE"
    else:
        confidence = "MODERATE"

    return {
        "pattern":       "FALLING_WEDGE",
        "confidence":    confidence,
        "wedge_top":     round(wedge_top, 2),
        "wedge_bottom":  round(wedge_bot, 2),
        "upper_slope":   round(h_slope, 4),
        "lower_slope":   round(l_slope, 4),
        "bars_forming":  bar_count,
        "violation_pct": round(violation_pct * 100, 1),
        "breaking_out":  breaking_out,
        "description": (
            f"Falling wedge over {bar_count} bars. "
            f"Upper line slope {h_slope:.3f}, lower {l_slope:.3f} "
            f"(converge ratio {converge_ratio:.1f}×, "
            f"{violation_pct*100:.0f}% line violations). "
            f"{'Breaking above ₹' + str(round(wedge_top, 0)) + ' ↑' if breaking_out else 'Watch for break above ₹' + str(round(wedge_top, 0))}."
        ),
    }


# ── Pattern 4: Ascending Triangle ────────────────────────────────────────────

def detect_ascending_triangle(df: pd.DataFrame,
                               lookback:           int   = 60,
                               min_bars:           int   = 8,
                               flat_tol_pct:       float = 0.015,
                               min_resist_touches: int   = 2,
                               max_dist_from_res:  float = 0.03) -> Optional[dict]:
    """
    Rules confirmed by user:
    1. Reject if stock is in clear bear trend (not valid in strong downtrend — TCS)
    2. Flat resistance must be tested at least 2 times by pivot highs
    3. Current price must be within 3% below resistance — pattern not actionable if far below
    4. Rising support (higher lows, positive slope)
    """
    n = len(df)
    if n < lookback + 10:
        return None

    # ── Rule 1: Reject clear bear trend (TCS fix) ─────────────────────────────
    if "bear_trend" in df.columns and bool(df["bear_trend"].iloc[-1]):
        return None   # EMA stack bearish — ascending triangle not valid

    sub      = df.iloc[-lookback:]
    highs_ph = _swing_highs(sub["High"], n=2)
    lows_pl  = _swing_lows(sub["Low"], sub["High"], n=2)

    if len(highs_ph) < 2 or len(lows_pl) < 2:
        return None

    # ── Find resistance: cluster from most-recent pivot high outward ──────────
    # Don't blindly take last 4 — old pivots at different levels break the calc.
    # Start from the most recent pivot high and collect others within flat_tol_pct.
    if not highs_ph:
        return None

    ref_high      = highs_ph[-1][1]   # most recent pivot high = anchor
    resist_cluster = [(idx, ph) for idx, ph in highs_ph
                      if abs(ph - ref_high) / ref_high < flat_tol_pct]

    # ── Rule 2: At least 2 pivot touches on resistance ────────────────────────
    resist_touches = len(resist_cluster)
    if resist_touches < min_resist_touches:
        return None   # resistance not tested enough times

    resistance = float(np.mean([x[1] for x in resist_cluster]))
    ph_vals    = [x[1] for x in resist_cluster]
    max_h, min_h = max(ph_vals), min(ph_vals)

    if (max_h - min_h) / max_h > flat_tol_pct:
        return None   # cluster too wide — not a clean flat level

    # ── Rule 3: Current price within 3% of resistance ─────────────────────────
    current = float(df["Close"].iloc[-1])
    dist_from_res = (resistance - current) / resistance

    if dist_from_res > max_dist_from_res and current < resistance:
        return None   # price too far below resistance — not actionable yet

    # ── Rising support: positive slope on pivot lows ──────────────────────────
    l_pts  = lows_pl[-3:] if len(lows_pl) >= 3 else lows_pl
    l_idx  = np.array([x[0] for x in l_pts], dtype=float)
    l_vals = np.array([x[1] for x in l_pts], dtype=float)
    l_slope = float(np.polyfit(l_idx, l_vals, 1)[0])

    if l_slope <= 0:
        return None   # support not rising

    # ── Confidence: tight resistance + multiple touches + near breakout ────────
    spread_pct   = (max_h - min_h) / max_h * 100
    breaking_out = current >= resistance * 1.002

    if spread_pct < 1.0 and resist_touches >= 3:
        confidence = "HIGH"
    elif spread_pct < flat_tol_pct * 100:
        confidence = "MODERATE"
    else:
        confidence = "MODERATE"

    triangle_height = resistance - float(l_vals[0])
    target = resistance + triangle_height

    return {
        "pattern":         "ASCENDING_TRIANGLE",
        "confidence":      confidence,
        "resistance":      round(resistance, 2),
        "resist_touches":  resist_touches,
        "support_slope":   round(l_slope, 4),
        "dist_from_res":   round(dist_from_res * 100, 1),
        "target":          round(target, 2),
        "breaking_out":    breaking_out,
        "description": (
            f"Ascending triangle: resistance ₹{resistance:,.0f} "
            f"({resist_touches} tests, {spread_pct:.1f}% spread). "
            f"Support rising. Price {dist_from_res*100:.1f}% from resistance. "
            f"{'Breaking out ↑' if breaking_out else 'Watch ₹' + str(round(resistance, 0)) + ' for breakout'}. "
            f"Target ₹{target:,.0f}."
        ),
    }


# ── Pattern 5: Bull Pennant ───────────────────────────────────────────────────

def detect_bull_pennant(df: pd.DataFrame,
                        pole_min_pct:      float = 7.0,
                        pole_max_bars:     int   = 12,
                        pennant_min_bars:  int   = 5,    # user: min 5-7 bars
                        pennant_max_bars:  int   = 20,
                        min_trendline_touches: int = 2,  # user: 2 touches each line
                        touch_tol_pct:     float = 0.015) -> Optional[dict]:
    """
    Rules confirmed by user:
    - Pole must be a clear UPWARD move only (not a crash recovery)
    - Pennant = converging triangle: highs declining, lows rising
    - Minimum 2 touches on the upper resistance trendline
    - Minimum 2 touches on the lower support trendline
    - Minimum 5 bars inside the pennant
    """
    n = len(df)
    if n < pole_max_bars + pennant_min_bars + 10:
        return None

    close = df["Close"].values
    high  = df["High"].values
    low   = df["Low"].values

    for pole_end in range(n - pennant_min_bars - 1,
                          max(n - pennant_max_bars - pole_max_bars, 0), -1):
        for pole_start in range(pole_end - 1,
                                max(pole_end - pole_max_bars, 0), -1):

            rise = (close[pole_end] - close[pole_start]) / close[pole_start] * 100

            # ── Rule 1: Pole must be a clear upward move ──────────────────────
            if rise < pole_min_pct:
                continue

            # Pole must trend upward cleanly — close at pole_end above midpoint
            pole_mid = (close[pole_start] + close[pole_end]) / 2
            if close[pole_end] < pole_mid * 1.02:
                continue   # not a clean pole-top — likely a crash recovery

            # ── Rule 2: Pennant consolidation from pole_end to now ────────────
            ph = high[pole_end: n]
            pl = low[pole_end:  n]
            pbars = len(ph)

            if pbars < pennant_min_bars:
                continue

            x = np.arange(pbars, dtype=float)

            # Fit trendlines
            h_coeffs = np.polyfit(x, ph, 1)
            l_coeffs = np.polyfit(x, pl, 1)
            h_slope, h_inter = h_coeffs[0], h_coeffs[1]
            l_slope, l_inter = l_coeffs[0], l_coeffs[1]

            # Pennant: highs must decline, lows must rise (converge)
            if h_slope >= 0 or l_slope <= 0:
                continue

            # ── Rule 3: Minimum 2 PIVOT touches on each trendline ────────────
            # Touches = actual swing pivot highs near the resistance line,
            # and swing pivot lows near the support line.
            # Not "every bar close to the fitted line" — that's always true.

            # Find swing pivot highs within pennant (need 2+ for resistance)
            ph_pivots = []
            for k in range(1, pbars - 1):
                if ph[k] >= ph[k-1] and ph[k] >= ph[k+1]:
                    # Local high — check if it's near the fitted upper line
                    fitted_h = h_inter + h_slope * k
                    if abs(ph[k] - fitted_h) / fitted_h < touch_tol_pct:
                        ph_pivots.append((k, ph[k]))

            # Find swing pivot lows within pennant (need 2+ for support)
            pl_pivots = []
            for k in range(1, pbars - 1):
                if pl[k] <= pl[k-1] and pl[k] <= pl[k+1]:
                    fitted_l = l_inter + l_slope * k
                    if abs(pl[k] - fitted_l) / fitted_l < touch_tol_pct:
                        pl_pivots.append((k, pl[k]))

            upper_touches = len(ph_pivots)
            lower_touches = len(pl_pivots)

            if upper_touches < min_trendline_touches:
                continue   # resistance not confirmed by pivot highs
            if lower_touches < min_trendline_touches:
                continue   # support not confirmed by pivot lows

            # Pivot highs must be declining (each lower than the previous)
            if len(ph_pivots) >= 2:
                ph_prices = [p[1] for p in ph_pivots]
                if not all(ph_prices[i] > ph_prices[i+1]
                           for i in range(len(ph_prices)-1)):
                    continue   # not consistently lower highs

            # Pivot lows must be rising (each higher than the previous)
            if len(pl_pivots) >= 2:
                pl_prices = [p[1] for p in pl_pivots]
                if not all(pl_prices[i] < pl_prices[i+1]
                           for i in range(len(pl_prices)-1)):
                    continue   # not consistently higher lows

            # ── Confidence based on touch quality and pennant duration ─────────
            total_touches = upper_touches + lower_touches
            if total_touches >= 5 and pbars >= 7:
                confidence = "HIGH"
            elif total_touches >= 4:
                confidence = "MODERATE"
            else:
                confidence = "MODERATE"

            pole_size = close[pole_end] - close[pole_start]
            target    = float(close[n - 1]) + pole_size

            # Current upper/lower boundary
            pennant_high_now = float(h_inter + h_slope * (pbars - 1))
            pennant_low_now  = float(l_inter + l_slope * (pbars - 1))
            breaking_out     = float(close[-1]) > pennant_high_now * 1.005

            return {
                "pattern":        "BULL_PENNANT",
                "confidence":     confidence,
                "pole_rise":      round(rise, 1),
                "pennant_bars":   pbars,
                "upper_touches":  upper_touches,
                "lower_touches":  lower_touches,
                "upper_boundary": round(pennant_high_now, 2),
                "lower_boundary": round(pennant_low_now, 2),
                "target":         round(target, 2),
                "breaking_out":   breaking_out,
                "description": (
                    f"Bull pennant: pole +{rise:.1f}%, "
                    f"triangle {pbars} bars "
                    f"({upper_touches} resistance touches, {lower_touches} support touches). "
                    f"{'Breaking out ↑' if breaking_out else 'Watch ₹' + str(round(pennant_high_now, 0)) + ' for breakout'}. "
                    f"Target ₹{target:,.0f}."
                ),
            }
    return None


# ── Pattern 6: Descending Channel ────────────────────────────────────────────

def detect_descending_channel(df: pd.DataFrame,
                               lookback:   int   = 60,
                               min_bars:   int   = 15,
                               par_tol:    float = 0.15) -> Optional[dict]:
    """
    Two PARALLEL declining trendlines (unlike falling wedge which converges).
    This is what NTPCGREEN showed — a defined channel, not converging lines.
    Bullish when price breaks above the upper channel line.
    """
    n = len(df)
    if n < lookback + 10:
        return None

    sub      = df.iloc[-lookback:]
    highs_ph = _swing_highs(sub["High"], n=2)
    lows_pl  = _swing_lows(sub["Low"], sub["High"], n=2)

    if len(highs_ph) < 3 or len(lows_pl) < 3:
        return None

    h_idx  = np.array([x[0] for x in highs_ph[-3:]], dtype=float)
    h_vals = np.array([x[1] for x in highs_ph[-3:]], dtype=float)
    l_idx  = np.array([x[0] for x in lows_pl[-3:]], dtype=float)
    l_vals = np.array([x[1] for x in lows_pl[-3:]], dtype=float)

    h_slope = float(np.polyfit(h_idx, h_vals, 1)[0])
    l_slope = float(np.polyfit(l_idx, l_vals, 1)[0])

    # Both lines must be declining
    if h_slope >= 0 or l_slope >= 0:
        return None

    # Lines must be PARALLEL (slopes similar) — unlike falling wedge which converges
    slope_ratio = abs(h_slope) / max(abs(l_slope), 1e-6)
    if not (1 - par_tol < slope_ratio < 1 + par_tol):
        return None

    channel_height = float(h_vals[-1] - l_vals[-1])
    upper_line     = float(h_vals[-1])
    lower_line     = float(l_vals[-1])
    current        = float(df["Close"].iloc[-1])

    # Breakout: close above upper channel line
    breaking_out = current > upper_line * 1.005
    target       = upper_line + channel_height  # measured move = channel height

    pattern_bars = int(max(h_idx[-1], l_idx[-1]) - min(h_idx[0], l_idx[0]))
    if pattern_bars < min_bars:
        return None

    confidence = "HIGH" if pattern_bars >= 20 and breaking_out else "MODERATE"

    return {
        "pattern":       "DESCENDING_CHANNEL",
        "confidence":    confidence,
        "upper_line":    round(upper_line, 2),
        "lower_line":    round(lower_line, 2),
        "channel_height": round(channel_height, 2),
        "bars_forming":  pattern_bars,
        "breaking_out":  breaking_out,
        "target":        round(target, 2),
        "description": (
            f"Descending channel over {pattern_bars} bars "
            f"(₹{lower_line:,.0f}–₹{upper_line:,.0f}, height ₹{channel_height:,.0f}). "
            f"Slopes parallel ({h_slope:.3f} vs {l_slope:.3f}). "
            f"{'Breaking above upper channel ↑' if breaking_out else 'Watch for break above ₹' + str(round(upper_line, 0))}. "
            f"Target ₹{target:,.0f}."
        ),
    }


# ── Pattern 7: Cup & Handle ───────────────────────────────────────────────────

def detect_cup_and_handle(df: pd.DataFrame,
                           lookback:        int   = 200,
                           right_rim_tol:   float = 0.03,   # user: within 3% of left rim
                           max_handle_depth: float = 0.05)  -> Optional[dict]:  # user: max 5%
    """
    Rules confirmed by user:
    - Right rim must recover to within 3% of left rim (BSE was at 50%+ below — correctly reject)
    - No depth restriction — any drop is valid
    - V-shape or U-shape both valid
    - Handle: max 5% pullback from right rim, no minimum bar count
    """
    n = len(df)
    if n < 30:
        return None

    close = df["Close"].values
    high  = df["High"].values

    # ── Find left rim: highest high in the lookback (not too recent) ──────────
    search_start = max(0, n - lookback)
    search_end   = n - 10   # leave room for right rim + handle

    left_rim_idx = int(search_start + np.argmax(high[search_start:search_end]))
    left_rim     = float(high[left_rim_idx])

    # Must have a meaningful decline after the left rim
    after_left = close[left_rim_idx: search_end]
    if len(after_left) < 5:
        return None

    bottom_offset = int(np.argmin(after_left))
    bottom_idx    = left_rim_idx + bottom_offset
    bottom        = float(close[bottom_idx])

    if bottom >= left_rim * 0.98:
        return None   # no real cup — price barely moved down

    # ── Find right rim: price recovers to within 3% of left rim ──────────────
    # Search from bottom onward for a bar whose high is within 3% of left_rim
    found_rim = None
    for i in range(bottom_idx + 2, n - 1):
        rh = float(high[i])
        if abs(rh - left_rim) / left_rim <= right_rim_tol:
            found_rim = (i, rh)
            break   # use first valid right rim (most recent complete cup)

    if found_rim is None:
        return None   # right rim never recovered to left rim level — not a cup

    right_rim_i, right_rim = found_rim

    # ── Handle: price after right rim should not drop more than 5% ───────────
    handle_slice = close[right_rim_i:]
    if len(handle_slice) == 0:
        return None

    handle_low   = float(np.min(handle_slice))
    handle_depth = (right_rim - handle_low) / right_rim

    if handle_depth > max_handle_depth:
        return None   # handle too deep — price fell more than 5% after right rim

    # ── Output ─────────────────────────────────────────────────────────────────
    current      = float(close[-1])
    breaking_out = current >= right_rim * 1.002
    cup_depth    = (left_rim - bottom) / left_rim
    cup_bars     = right_rim_i - left_rim_idx
    target       = right_rim + (right_rim - bottom)
    rim_diff_pct = abs(right_rim - left_rim) / left_rim * 100

    # Confidence: tighter rim match + shallower handle = higher conviction
    if rim_diff_pct < 1.5 and handle_depth < 0.03:
        confidence = "HIGH"
    else:
        confidence = "MODERATE"

    return {
        "pattern":          "CUP_AND_HANDLE",
        "confidence":       confidence,
        "left_rim":         round(left_rim, 2),
        "cup_bottom":       round(bottom, 2),
        "right_rim":        round(right_rim, 2),
        "rim_diff_pct":     round(rim_diff_pct, 1),
        "cup_depth_pct":    round(cup_depth * 100, 1),
        "handle_depth_pct": round(handle_depth * 100, 1),
        "cup_bars":         cup_bars,
        "target":           round(target, 2),
        "breaking_out":     breaking_out,
        "description": (
            f"Cup & Handle: {cup_bars}-bar cup, depth {cup_depth*100:.0f}% "
            f"(bottom ₹{bottom:,.0f}). "
            f"Right rim ₹{right_rim:,.0f} ({rim_diff_pct:.1f}% from left rim ₹{left_rim:,.0f}). "
            f"Handle {handle_depth*100:.1f}% deep. "
            f"{'Breaking out ↑' if breaking_out else 'Watch for break above ₹' + str(round(right_rim, 0))}. "
            f"Target ₹{target:,.0f}."
        ),
    }


# ── Pattern 8: Inverse Head & Shoulders ──────────────────────────────────────

def detect_inv_head_shoulders(df: pd.DataFrame,
                               lookback:  int   = 80,
                               sym_tol:   float = 0.10) -> Optional[dict]:
    """
    Three troughs: left shoulder, head (deepest), right shoulder.
    Shoulders at similar price; head 8-40% lower.
    Neckline connects the peaks between the shoulders.
    """
    n = len(df)
    if n < lookback + 10:
        return None

    sub      = df.iloc[-lookback:]
    lows_pl  = _swing_lows(sub["Low"], sub["High"], n=3)
    highs_ph = _swing_highs(sub["High"], n=2)

    if len(lows_pl) < 3:
        return None

    for i in range(len(lows_pl) - 2, 1, -1):
        rs_idx, rs = lows_pl[i]       # right shoulder
        hd_idx, hd = lows_pl[i - 1]  # head
        ls_idx, ls = lows_pl[i - 2]  # left shoulder

        # Head must be the deepest
        if not (hd < rs and hd < ls):
            continue

        # Shoulders at similar level
        if abs(rs - ls) / max(ls, 1e-6) > sym_tol:
            continue

        # Head must be meaningfully deeper than shoulders
        shoulder_avg = (rs + ls) / 2
        head_depth = (shoulder_avg - hd) / shoulder_avg
        if head_depth < 0.08 or head_depth > 0.40:
            continue

        # Neckline: highest point between left shoulder and head,
        # and between head and right shoulder
        neckline_highs = [ph for pidx, ph in highs_ph if ls_idx < pidx < rs_idx]
        if not neckline_highs:
            continue
        neckline = float(np.mean(neckline_highs[-2:]) if len(neckline_highs) >= 2
                         else neckline_highs[-1])

        current      = float(df["Close"].iloc[-1])
        breaking_out = current > neckline * 1.002
        target       = neckline + (neckline - hd)

        confidence = "HIGH" if head_depth > 0.15 and abs(rs - ls) / max(ls, 1e-6) < 0.05 \
                     else "MODERATE"

        return {
            "pattern":     "INV_HEAD_SHOULDERS",
            "confidence":  confidence,
            "left_sh":     round(ls, 2),
            "head":        round(hd, 2),
            "right_sh":    round(rs, 2),
            "neckline":    round(neckline, 2),
            "head_depth":  round(head_depth * 100, 1),
            "target":      round(target, 2),
            "breaking_out": breaking_out,
            "description": (
                f"Inv. Head & Shoulders: shoulders ₹{(ls+rs)/2:,.0f}, "
                f"head ₹{hd:,.0f} ({head_depth*100:.0f}% deeper). "
                f"Neckline ₹{neckline:,.0f}. "
                f"{'Breaking above neckline ↑' if breaking_out else 'Watch neckline ₹' + str(round(neckline, 0))}. "
                f"Target ₹{target:,.0f}."
            ),
        }
    return None


# ── Pattern 9: Head & Shoulders (bearish) ────────────────────────────────────

def detect_head_shoulders(df: pd.DataFrame,
                          lookback: int   = 80,
                          sym_tol:  float = 0.10) -> Optional[dict]:
    """
    Three peaks: left shoulder, head (highest), right shoulder.
    Classic bearish reversal — neckline break = distribution.
    """
    n = len(df)
    if n < lookback + 10:
        return None

    sub      = df.iloc[-lookback:]
    highs_ph = _swing_highs(sub["High"], n=3)
    lows_pl  = _swing_lows(sub["Low"], sub["High"], n=2)

    if len(highs_ph) < 3:
        return None

    for i in range(len(highs_ph) - 2, 1, -1):
        rs_idx, rs = highs_ph[i]
        hd_idx, hd = highs_ph[i - 1]
        ls_idx, ls = highs_ph[i - 2]

        if not (hd > rs and hd > ls):
            continue
        if abs(rs - ls) / max(ls, 1e-6) > sym_tol:
            continue

        head_height = (hd - (rs + ls) / 2) / hd
        if head_height < 0.05 or head_height > 0.35:
            continue

        neckline_lows = [pl for pidx, pl in lows_pl if ls_idx < pidx < rs_idx]
        if not neckline_lows:
            continue
        neckline = float(np.mean(neckline_lows[-2:]) if len(neckline_lows) >= 2
                         else neckline_lows[-1])

        current  = float(df["Close"].iloc[-1])
        breaking = current < neckline * 0.998
        target   = neckline - (hd - neckline)

        confidence = "HIGH" if head_height > 0.10 and abs(rs - ls) / max(ls, 1e-6) < 0.05 \
                     else "MODERATE"

        return {
            "pattern":     "HEAD_SHOULDERS",
            "confidence":  confidence,
            "left_sh":     round(ls, 2),
            "head":        round(hd, 2),
            "right_sh":    round(rs, 2),
            "neckline":    round(neckline, 2),
            "target":      round(target, 2),
            "breaking_out": breaking,
            "description": (
                f"Head & Shoulders (bearish): shoulders ₹{(ls+rs)/2:,.0f}, "
                f"head ₹{hd:,.0f}. Neckline ₹{neckline:,.0f}. "
                f"{'Breaking below neckline ↓' if breaking else 'Watch neckline ₹' + str(round(neckline, 0))}. "
                f"Target ₹{target:,.0f}."
            ),
        }
    return None


# ── Pattern 10: Symmetrical Triangle ─────────────────────────────────────────

def detect_symmetrical_triangle(df: pd.DataFrame,
                                 lookback:  int   = 50,
                                 min_bars:  int   = 10) -> Optional[dict]:
    """
    Converging highs (declining) and lows (rising) — equal slopes.
    Neutral: breakout direction determines trade direction.
    High win rate when combined with prior trend.
    """
    n = len(df)
    if n < lookback + 10:
        return None

    sub      = df.iloc[-lookback:]
    highs_ph = _swing_highs(sub["High"], n=2)
    lows_pl  = _swing_lows(sub["Low"], sub["High"], n=2)

    if len(highs_ph) < 3 or len(lows_pl) < 3:
        return None

    h_idx  = np.array([x[0] for x in highs_ph[-3:]], dtype=float)
    h_vals = np.array([x[1] for x in highs_ph[-3:]], dtype=float)
    l_idx  = np.array([x[0] for x in lows_pl[-3:]], dtype=float)
    l_vals = np.array([x[1] for x in lows_pl[-3:]], dtype=float)

    h_slope = float(np.polyfit(h_idx, h_vals, 1)[0])
    l_slope = float(np.polyfit(l_idx, l_vals, 1)[0])

    # Highs declining, lows rising (converging)
    if h_slope >= 0 or l_slope <= 0:
        return None

    # Slopes should be roughly equal in magnitude (symmetrical)
    if abs(abs(h_slope) - abs(l_slope)) / max(abs(h_slope), 1e-6) > 0.50:
        return None

    current      = float(df["Close"].iloc[-1])
    upper_now    = float(h_vals[-1])
    lower_now    = float(l_vals[-1])
    breaking_up  = current > upper_now * 1.005
    breaking_dn  = current < lower_now * 0.995

    pattern_bars = int(max(h_idx[-1], l_idx[-1]) - min(h_idx[0], l_idx[0]))
    if pattern_bars < min_bars:
        return None

    direction = "UPSIDE" if breaking_up else "DOWNSIDE" if breaking_dn else "FORMING"
    confidence = "HIGH" if pattern_bars >= 15 and (breaking_up or breaking_dn) else "MODERATE"

    triangle_height = float(h_vals[0] - l_vals[0])
    target = (upper_now + triangle_height) if breaking_up else (lower_now - triangle_height)

    return {
        "pattern":       "SYMM_TRIANGLE",
        "confidence":    confidence,
        "upper_line":    round(upper_now, 2),
        "lower_line":    round(lower_now, 2),
        "bars_forming":  pattern_bars,
        "direction":     direction,
        "target":        round(target, 2),
        "description": (
            f"Symmetrical triangle over {pattern_bars} bars "
            f"(₹{lower_now:,.0f}–₹{upper_now:,.0f}). "
            f"{'Breaking UP ↑' if breaking_up else 'Breaking DOWN ↓' if breaking_dn else 'Apex approaching — watch for breakout'}. "
            f"Target ₹{target:,.0f}."
        ),
    }


# ── Master scanner ────────────────────────────────────────────────────────────

def scan_patterns(df: pd.DataFrame) -> list[dict]:
    """
    Run all pattern detectors on a prepared indicator DataFrame.
    Returns list of detected patterns (empty if none found).
    Only returns patterns with MODERATE or HIGH confidence.
    """
    detectors = [
        detect_double_bottom,
        detect_bull_flag,
        detect_bull_pennant,
        detect_falling_wedge,
        detect_descending_channel,
        detect_ascending_triangle,
        detect_cup_and_handle,
        detect_inv_head_shoulders,
        detect_head_shoulders,
        detect_symmetrical_triangle,
    ]

    found = []
    for fn in detectors:
        try:
            result = fn(df)
            if result and result.get("confidence") in ("HIGH", "MODERATE"):
                found.append(result)
        except Exception:
            pass

    return found
