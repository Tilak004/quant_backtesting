"""
tools/decay_analysis.py

Why did 2025 lose money?

Separates the two candidate explanations:

  A. THE MARKET CHANGED — the strategy is a long-momentum system and 2025 simply
     did not offer trends. Signals were as good as ever; the environment wasn't.
  B. THE STRATEGY DECAYED — the same setups stopped working, i.e. entry quality
     fell independently of the market.

Distinguishing evidence:
  - Nifty return per year vs strategy return (is the market the whole story?)
  - Breadth: what % of the universe was in `bull_trend` (is there anything to buy?)
  - Entry quality at the bar: ADX, RSI, volume ratio, ATR% (are setups weaker?)
  - Outcome shape: win rate vs payoff ratio (are we wrong more, or paid less?)
  - Exit mix: SL / TP / MeshBreak (are we being stopped out or chopped out?)
  - Holding period (are trends dying faster?)

    python tools/decay_analysis.py
"""

from __future__ import annotations

import glob
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from core.portfolio import load_close_series

ROOT = Path(__file__).resolve().parent.parent
GOOD_YEARS = [2017, 2020, 2021, 2023]


def load_trades() -> pd.DataFrame:
    frames = []
    for f in glob.glob(str(ROOT / "results/trades_*.csv")):
        if "OOS" in Path(f).name or "portfolio" in Path(f).name:
            continue
        d = pd.read_csv(f)
        if not d.empty and "pnl_pct" in d.columns:
            frames.append(d)
    t = pd.concat(frames, ignore_index=True)
    t["entry_date"] = pd.to_datetime(t.entry_date)
    t["exit_date"] = pd.to_datetime(t.exit_date)
    t["year"] = t.entry_date.dt.year
    return t


def nifty_yearly() -> pd.Series:
    s = load_close_series("^NSEI")
    if s is None:
        return pd.Series(dtype=float)
    y = s.resample("YE").last()
    return (y / y.shift(1) - 1) * 100


def entry_context(t: pd.DataFrame) -> pd.DataFrame:
    """Re-read indicator values at each entry bar to judge SETUP quality."""
    from indicators import prepare_indicators
    rows = []
    cache: dict[str, pd.DataFrame | None] = {}
    for tk, grp in t.groupby("ticker"):
        if tk not in cache:
            f = ROOT / "data/raw" / f"{tk.replace('^','IDX_').replace('.','_')}.csv"
            try:
                raw = pd.read_csv(f, index_col=0, parse_dates=True)
                raw.index = pd.to_datetime(raw.index).tz_localize(None)
                cache[tk] = prepare_indicators(raw) if len(raw) > 300 else None
            except Exception:
                cache[tk] = None
        ind = cache[tk]
        if ind is None:
            continue
        for d, yr in zip(grp.entry_date.values, grp.year.values):
            ts = pd.Timestamp(d)
            if ts not in ind.index:
                continue
            b = ind.loc[ts]
            rows.append({
                "year": yr,
                "adx": float(b.get("ADX", np.nan)),
                "rsi": float(b.get("RSI", np.nan)),
                "vol_ratio": float(b.get("Volume", np.nan)) /
                             max(float(b.get("VOL_SMA20", 1)), 1e-9),
                "atr_pct": float(b.get("ATR", np.nan)) /
                           max(float(b.get("Close", 1)), 1e-9) * 100,
            })
    return pd.DataFrame(rows)


def breadth() -> pd.Series:
    """% of the universe in `bull_trend` per year — is there anything to buy?"""
    from indicators import prepare_indicators
    frames = []
    files = sorted((ROOT / "data/raw").glob("*.csv"))
    step = max(len(files) // 250, 1)          # sample ~250 names, enough for a rate
    for f in files[::step]:
        try:
            raw = pd.read_csv(f, index_col=0, parse_dates=True)
            raw.index = pd.to_datetime(raw.index).tz_localize(None)
            if len(raw) < 300:
                continue
            ind = prepare_indicators(raw)
            frames.append(ind["bull_trend"].astype(float))
        except Exception:
            continue
    if not frames:
        return pd.Series(dtype=float)
    m = pd.concat(frames, axis=1)
    return m.mean(axis=1).groupby(m.index.year).mean() * 100


def main() -> None:
    t = load_trades()
    nif = nifty_yearly()
    nif_by_year = {d.year: v for d, v in nif.items() if pd.notna(v)}

    print("=" * 88)
    print("  OUTCOME SHAPE BY YEAR")
    print("=" * 88)
    print(f"  {'Yr':<6}{'n':>6}{'WR%':>7}{'avgWin':>8}{'avgLoss':>9}{'payoff':>8}"
          f"{'tot_eq':>9}{'SL%':>6}{'TP%':>6}{'Mesh%':>7}{'bars':>6}{'Nifty%':>8}")
    print("  " + "-" * 86)
    for yr, g in t.groupby("year"):
        w, losses = g[g.pnl_pct > 0], g[g.pnl_pct < 0]
        aw = w.pnl_pct.mean() if len(w) else 0
        al = losses.pnl_pct.mean() if len(losses) else 0
        er = g.exit_reason.value_counts(normalize=True) * 100
        print(f"  {yr:<6}{len(g):>6}{(g.pnl_pct>0).mean()*100:>7.1f}{aw:>8.2f}"
              f"{al:>9.2f}{abs(aw/al) if al else 0:>8.2f}{g.pnl_on_equity.sum():>9.1f}"
              f"{er.get('SL',0):>6.0f}{er.get('TP',0):>6.0f}"
              f"{er.get('MeshBreak',0):>7.0f}{g.bars_held.mean():>6.0f}"
              f"{nif_by_year.get(yr, float('nan')):>8.1f}")

    print("\n" + "=" * 88)
    print("  ENTRY SETUP QUALITY (indicator values AT the entry bar)")
    print("=" * 88)
    ec = entry_context(t)
    if not ec.empty:
        agg = ec.groupby("year").agg(
            n=("adx", "size"), adx=("adx", "mean"), rsi=("rsi", "mean"),
            vol_ratio=("vol_ratio", "mean"), atr_pct=("atr_pct", "mean"))
        print(agg.round(2).to_string())
        good = agg.loc[agg.index.isin(GOOD_YEARS)].mean()
        print(f"\n  good years {GOOD_YEARS} mean : ADX {good.adx:.1f}  RSI {good.rsi:.1f}  "
              f"vol {good.vol_ratio:.2f}  ATR% {good.atr_pct:.2f}")
        if 2025 in agg.index:
            r = agg.loc[2025]
            print(f"  2025                        : ADX {r.adx:.1f}  RSI {r.rsi:.1f}  "
                  f"vol {r.vol_ratio:.2f}  ATR% {r.atr_pct:.2f}")

    print("\n" + "=" * 88)
    print("  BREADTH — % of universe in bull_trend (sampled)")
    print("=" * 88)
    b = breadth()
    for yr, v in b.items():
        if yr >= 2016:
            bar = "#" * int(v / 2)
            print(f"    {yr}  {v:5.1f}%  {bar}")

    print("\n" + "=" * 88)
    print("  SIGNAL TYPE BY YEAR (total equity-%)")
    print("=" * 88)
    piv = t.pivot_table(index="year", columns="signal_type",
                        values="pnl_on_equity", aggfunc="sum").round(1)
    print(piv.fillna(0).to_string())


if __name__ == "__main__":
    main()
