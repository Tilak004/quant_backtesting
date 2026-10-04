"""
core/portfolio.py

Portfolio-level replay of per-ticker backtest trades against ONE account.

Why this exists
---------------
backtester.py runs each ticker in isolation ("one position at a time per
ticker"), so pooling the per-ticker results silently assumes an independent
account per stock. Measured on the current trade set that means:

    mean 209 concurrent positions   (max 754)
    mean 4060% of equity deployed   (max 14381%)
    99.4% of trading days over 100% deployed

Every pooled figure downstream — equity curve, drawdown, Sharpe — inherits that.

This module replays the same trades chronologically against a single account
with a real capital constraint. It does NOT change entry or exit logic: a trade's
entry date, exit date and prices are taken as given. It only decides whether the
account could actually afford to open the position, and when it cannot, which
candidates win the available capital.

That selection step is where a signal score earns its keep: not as a yes/no gate,
but as the ranking that picks which N of today's signals get funded.

Equity is marked to market daily from cached closes, so drawdown reflects
open-position pain, not just realised P&L.

Usage:
    from core.portfolio import simulate_portfolio
    res = simulate_portfolio(trades_df, max_positions=20, rank_col="ml_score")
    print(res.metrics)
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from core.config import load_config

_RAW = Path(__file__).resolve().parent.parent / "data" / "raw"

TRADING_DAYS = 252.0


def _safe_name(ticker: str) -> str:
    return ticker.replace("^", "IDX_").replace(".", "_")


# Module-level caches. The optimiser calls simulate_portfolio thousands of times
# with the same universe; without these it re-reads 869 CSVs on every call.
_CLOSE_CACHE: dict[str, pd.Series | None] = {}
_TURNOVER_CACHE: dict[tuple[str, int], pd.Series | None] = {}


def load_close_series(ticker: str) -> pd.Series | None:
    """Daily closes for a ticker from the shared cache. None if unavailable."""
    if ticker in _CLOSE_CACHE:
        return _CLOSE_CACHE[ticker]
    _CLOSE_CACHE[ticker] = _load_close_uncached(ticker)
    return _CLOSE_CACHE[ticker]


def _load_close_uncached(ticker: str) -> pd.Series | None:
    csv = _RAW / f"{_safe_name(ticker)}.csv"
    if not csv.exists():
        return None
    try:
        df = pd.read_csv(csv, index_col=0, parse_dates=True, usecols=[0, 4])
        df.index = pd.to_datetime(df.index).tz_localize(None)
        s = df.iloc[:, 0].astype(float)
        return s[~s.index.duplicated(keep="last")].sort_index()
    except Exception as e:
        warnings.warn(f"Failed to load closes for {ticker}: {e}")
        return None


def load_turnover_series(ticker: str, window: int = 60) -> pd.Series | None:
    """
    Trailing median daily rupee turnover (Close x Volume) for a ticker.

    Causal by construction: the value at bar t uses only bars <= t, so screening
    a 2017 trade cannot borrow liquidity the stock only acquired in 2024.
    """
    key = (ticker, window)
    if key in _TURNOVER_CACHE:
        return _TURNOVER_CACHE[key]
    _TURNOVER_CACHE[key] = _load_turnover_uncached(ticker, window)
    return _TURNOVER_CACHE[key]


def _load_turnover_uncached(ticker: str, window: int) -> pd.Series | None:
    csv = _RAW / f"{_safe_name(ticker)}.csv"
    if not csv.exists():
        return None
    try:
        df = pd.read_csv(csv, index_col=0, parse_dates=True,
                         usecols=[0, 4, 5])
        df.index = pd.to_datetime(df.index).tz_localize(None)
        df = df[~df.index.duplicated(keep="last")].sort_index()
        turnover = df.iloc[:, 0].astype(float) * df.iloc[:, 1].astype(float)
        return turnover.rolling(window, min_periods=max(window // 3, 5)).median()
    except Exception as e:
        warnings.warn(f"Failed to load turnover for {ticker}: {e}")
        return None


_TURNOVER_LUT: dict[tuple, pd.DataFrame] = {}


def _turnover_lut(tickers: tuple[str, ...], window: int) -> pd.DataFrame:
    """
    Long (ticker, entry_date, turnover) table for merge_asof, built once.

    Turnover is a pure function of price data — it does not depend on any
    strategy parameter — so during a grid search this is identical for every
    candidate and must not be recomputed per combo.
    """
    key = (window, tickers)
    if key in _TURNOVER_LUT:
        return _TURNOVER_LUT[key]
    frames = []
    for tk in tickers:
        s = load_turnover_series(tk, window)
        if s is None or s.empty:
            continue
        frames.append(pd.DataFrame({"ticker": tk,
                                    "entry_date": s.index,
                                    "turnover": s.to_numpy()}))
    if frames:
        lut = pd.concat(frames, ignore_index=True).dropna(subset=["turnover"])
        lut = lut.sort_values("entry_date", kind="mergesort").reset_index(drop=True)
    else:
        lut = pd.DataFrame(columns=["ticker", "entry_date", "turnover"])
    _TURNOVER_LUT[key] = lut
    return lut


def attach_turnover(trades: pd.DataFrame, window: int = 60) -> pd.DataFrame:
    """
    Add `turnover` — trailing median rupee turnover as of each entry bar.

    merge_asof(direction="backward") on a NaN-free table reproduces
    Series.asof() semantics ("last non-NaN value at or before"), but in one
    vectorised pass rather than one pandas lookup per trade.
    """
    t = trades.copy()
    t["entry_date"] = pd.to_datetime(t["entry_date"])
    if t.empty:
        t["turnover"] = np.nan
        return t

    lut = _turnover_lut(tuple(sorted(t["ticker"].unique())), window)
    if lut.empty:
        t["turnover"] = np.nan
        return t

    t["_ord"] = np.arange(len(t))
    left = t.sort_values("entry_date", kind="mergesort")
    out = pd.merge_asof(left, lut, on="entry_date", by="ticker",
                        direction="backward")
    out = out.sort_values("_ord", kind="mergesort").drop(columns="_ord")
    out.index = trades.index
    return out


@dataclass
class _Position:
    ticker: str
    direction: str
    entry_date: pd.Timestamp
    exit_date: pd.Timestamp
    entry_price: float
    exit_price: float
    shares: float
    cost_basis: float
    row: dict = field(repr=False, default_factory=dict)

    def market_value(self, px: float) -> float:
        """Mark-to-market value, mirroring backtester.py's return convention."""
        if not np.isfinite(px) or px <= 0:
            return self.cost_basis
        if self.direction == "long":
            return self.shares * px
        # short: raw return = entry/current - 1  (matches backtester.py:163-164)
        return self.cost_basis * (self.entry_price / px)


@dataclass
class PortfolioResult:
    equity: pd.Series                  # daily, mark-to-market
    taken: pd.DataFrame
    skipped: pd.DataFrame
    metrics: dict
    daily_positions: pd.Series
    daily_deployed_pct: pd.Series


def _metrics_from_equity(eq: pd.Series, n_taken: int, n_skipped: int) -> dict:
    if len(eq) < 3:
        return {"sharpe": 0.0, "max_dd": 0.0, "cagr": 0.0, "total_return": 0.0,
                "n_taken": n_taken, "n_skipped": n_skipped}

    ret = eq.pct_change().dropna()
    sd = ret.std(ddof=1)
    sharpe = float(ret.mean() / sd * np.sqrt(TRADING_DAYS)) if sd > 0 else 0.0

    downside = ret[ret < 0]
    dsd = downside.std(ddof=1) if len(downside) > 1 else sd
    sortino = float(ret.mean() / dsd * np.sqrt(TRADING_DAYS)) if dsd > 0 else 0.0

    dd = (eq - eq.expanding().max()) / eq.expanding().max() * 100.0
    years = max((eq.index[-1] - eq.index[0]).days / 365.25, 0.1)
    total_return = float(eq.iloc[-1] / eq.iloc[0] - 1.0) * 100.0
    cagr = float((eq.iloc[-1] / eq.iloc[0]) ** (1.0 / years) - 1.0) * 100.0

    return {
        "sharpe":       round(sharpe, 3),
        "sortino":      round(sortino, 3),
        "max_dd":       round(float(dd.min()), 2),
        "cagr":         round(cagr, 2),
        "total_return": round(total_return, 2),
        "years":        round(years, 2),
        "n_taken":      n_taken,
        "n_skipped":    n_skipped,
        "fill_rate":    round(n_taken / max(n_taken + n_skipped, 1) * 100, 1),
    }


def simulate_portfolio(trades: pd.DataFrame,
                       max_positions: int | None = None,
                       max_gross_pct: float | None = None,
                       max_position_pct: float | None = None,
                       rank_col: str | None = None,
                       starting_capital: float | None = None,
                       round_trip_cost: float | None = None,
                       verbose: bool = False) -> PortfolioResult:
    """
    Replay `trades` against one account.

    max_positions    hard cap on concurrent open positions
    max_gross_pct    cap on total deployed capital as % of equity
    max_position_pct cap on a single position as % of equity
    rank_col         column used to rank same-day candidates when capital is
                     scarce (higher is better). None => stable order by ticker.

    Entry/exit dates and prices are taken as given; only funding is simulated.
    """
    cfg = load_config()
    max_positions    = int(max_positions    if max_positions    is not None else cfg.max_positions)
    max_gross_pct    = float(max_gross_pct  if max_gross_pct    is not None else cfg.max_gross_pct)
    max_position_pct = float(max_position_pct if max_position_pct is not None else cfg.max_position_pct)
    equity = float(starting_capital if starting_capital is not None else cfg.starting_capital)
    # Round-trip cost as a fraction. Override to stress-test fills: 0.002 is the
    # configured 0.05% commission + 0.05% slippage per side, which is optimistic
    # for illiquid smallcaps.
    rtc = float(round_trip_cost) if round_trip_cost is not None \
        else (cfg.commission_pct + cfg.slippage_pct) * 2

    t = trades.copy()
    for c in ("entry_date", "exit_date"):
        t[c] = pd.to_datetime(t[c])
    t = t.dropna(subset=["entry_date", "exit_date", "entry_price", "exit_price"])
    t = t[t.exit_date >= t.entry_date].sort_values("entry_date").reset_index(drop=True)
    if t.empty:
        idx = pd.DatetimeIndex([pd.Timestamp.today().normalize()])
        return PortfolioResult(pd.Series([equity], index=idx), t, t,
                               _metrics_from_equity(pd.Series(dtype=float), 0, 0),
                               pd.Series(dtype=float), pd.Series(dtype=float))

    # Price cache + trading calendar from actual data (respects NSE holidays)
    closes: dict[str, pd.Series] = {}
    for tk in t.ticker.unique():
        s = load_close_series(tk)
        if s is not None:
            closes[tk] = s
    if not closes:
        raise FileNotFoundError("No cached price data for any ticker in trades.")

    cal = pd.DatetimeIndex(sorted(set().union(*[s.index for s in closes.values()])))
    cal = cal[(cal >= t.entry_date.min()) & (cal <= t.exit_date.max())]

    # Price matrix aligned to the calendar, indexed by integer. Replaces a
    # Series.asof() call per open position per day (~70k pandas lookups) with
    # an array read.
    px_mat = (pd.DataFrame(closes).reindex(cal).ffill()
              .to_numpy(dtype=np.float64, na_value=np.nan))
    col_of = {tk: j for j, tk in enumerate(pd.DataFrame(closes).columns)}

    by_entry = {d: g for d, g in t.groupby(t.entry_date.dt.normalize())}

    cash = equity
    open_pos: list[_Position] = []
    taken_rows, skipped_rows = [], []
    eq_hist, pos_hist, dep_hist = [], [], []

    for di, day in enumerate(cal):
        # ── 1. exits first (frees capital for same-day entries) ───────────────
        still: list[_Position] = []
        for p in open_pos:
            if p.exit_date <= day:
                raw = (p.exit_price / p.entry_price - 1.0) if p.direction == "long" \
                      else (p.entry_price / p.exit_price - 1.0)
                cash += p.cost_basis * (1.0 + raw - rtc)
                r = dict(p.row)
                r["portfolio_pnl"] = p.cost_basis * (raw - rtc)
                taken_rows.append(r)
            else:
                still.append(p)
        open_pos = still

        # mark equity before sizing today's entries
        def _mtm() -> float:
            tot = cash
            for q in open_pos:
                j = col_of.get(q.ticker)
                px = px_mat[di, j] if j is not None else np.nan
                tot += q.market_value(q.entry_price if not np.isfinite(px) else px)
            return tot

        equity = _mtm()

        # ── 2. entries, ranked when capital is scarce ─────────────────────────
        cands = by_entry.get(day)
        if cands is not None and len(cands):
            if rank_col and rank_col in cands.columns:
                cands = cands.sort_values(rank_col, ascending=False, kind="mergesort")
            else:
                cands = cands.sort_values("ticker", kind="mergesort")

            for _, row in cands.iterrows():
                gross = sum(q.cost_basis for q in open_pos)
                room = equity * max_gross_pct / 100.0 - gross
                pos_pct = min(float(row.get("position_pct", max_position_pct)),
                              max_position_pct)
                want = equity * pos_pct / 100.0

                if len(open_pos) >= max_positions or want > room or want <= 0 \
                        or cash < want:
                    r = dict(row)
                    r["skip_reason"] = ("max_positions" if len(open_pos) >= max_positions
                                        else "insufficient_capital")
                    skipped_rows.append(r)
                    continue

                epx = float(row["entry_price"])
                if not np.isfinite(epx) or epx <= 0:
                    continue
                p = _Position(
                    ticker=str(row["ticker"]),
                    direction=str(row.get("direction", "long")),
                    entry_date=row["entry_date"], exit_date=row["exit_date"],
                    entry_price=epx, exit_price=float(row["exit_price"]),
                    shares=want / epx, cost_basis=want, row=dict(row),
                )
                cash -= want
                open_pos.append(p)

        equity = _mtm()
        eq_hist.append(equity)
        pos_hist.append(len(open_pos))
        dep_hist.append(sum(q.cost_basis for q in open_pos) / max(equity, 1e-9) * 100.0)

    eq = pd.Series(eq_hist, index=cal, dtype=float)
    taken = pd.DataFrame(taken_rows)
    skipped = pd.DataFrame(skipped_rows)
    m = _metrics_from_equity(eq, len(taken), len(skipped))

    if verbose:
        print(f"  taken {len(taken)}  skipped {len(skipped)}  "
              f"fill {m['fill_rate']}%  Sharpe {m['sharpe']}  maxDD {m['max_dd']}%")

    return PortfolioResult(eq, taken, skipped, m,
                           pd.Series(pos_hist, index=cal, dtype=float),
                           pd.Series(dep_hist, index=cal, dtype=float))
