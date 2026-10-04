"""
analysis.py — Statistical analysis module.

Computes performance metrics, breakdowns, regime analysis,
and inter-stock correlation corrections.
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import Optional


# ── Equity curve ──────────────────────────────────────────────────────────────
def compute_equity_curve(trades_df: pd.DataFrame,
                         initial_equity: float = 100.0) -> pd.Series:
    """
    Build a trade-by-trade equity curve sorted by exit date.

    Uses pnl_on_equity (position-sized return on account equity) when available,
    which gives a realistic max-drawdown. Falls back to pnl_pct for legacy data.
    """
    if trades_df.empty:
        return pd.Series([initial_equity], dtype=float)

    col = "pnl_on_equity" if "pnl_on_equity" in trades_df.columns else "pnl_pct"
    df  = trades_df.sort_values("exit_date").reset_index(drop=True)
    equity = np.empty(len(df) + 1)
    equity[0] = initial_equity
    for k, row in enumerate(df[col].values):
        equity[k + 1] = equity[k] * (1.0 + row / 100.0)

    dates = [df["entry_date"].iloc[0]] + list(df["exit_date"])
    return pd.Series(equity, index=pd.to_datetime(dates))


def compute_drawdown_series(eq: pd.Series) -> pd.Series:
    """Return drawdown percentage series (0 to -100)."""
    peak = eq.expanding().max()
    return (eq - peak) / peak * 100.0


# ── Core metrics ──────────────────────────────────────────────────────────────
def compute_metrics(trades_df: pd.DataFrame) -> dict:
    """
    Compute comprehensive performance metrics from a trade DataFrame.
    Sharpe / Sortino are trade-based, annualised by trades-per-year.
    """
    empty = dict(
        n_trades=0, win_rate=0.0, avg_win=0.0, avg_loss=0.0,
        win_loss_ratio=0.0, profit_factor=0.0, expectancy=0.0,
        sharpe=0.0, sortino=0.0, max_dd=0.0, avg_dd=0.0,
        dd_duration=0, z_stat=0.0, p_value=1.0,
        gross_profit=0.0, gross_loss=0.0, n_wins=0, n_losses=0,
        total_pnl=0.0,
    )
    if trades_df is None or trades_df.empty:
        return empty

    pnl = trades_df["pnl_pct"].values   # trade-level returns (signal quality)
    n   = len(pnl)
    if n < 2:
        return empty

    wins   = pnl[pnl > 0]
    losses = pnl[pnl < 0]

    win_rate       = len(wins) / n
    avg_win        = float(wins.mean())   if len(wins)   > 0 else 0.0
    avg_loss       = float(losses.mean()) if len(losses) > 0 else 0.0
    win_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else np.inf

    gross_profit  = float(wins.sum())          if len(wins)   > 0 else 0.0
    gross_loss    = float(abs(losses.sum()))   if len(losses) > 0 else 0.0
    profit_factor = gross_profit / gross_loss  if gross_loss > 0 else np.inf

    expectancy = win_rate * avg_win + (1.0 - win_rate) * avg_loss

    # Annualisation factor from date range
    try:
        date_range = (
            pd.to_datetime(trades_df["exit_date"].max()) -
            pd.to_datetime(trades_df["entry_date"].min())
        ).days
        years = max(date_range / 365.25, 0.1)
    except Exception:
        years = 1.0
    trades_per_year = n / years
    ann_factor = np.sqrt(trades_per_year)

    # Sharpe/Sortino use pnl_on_equity (portfolio returns) when available
    pnl_eq  = trades_df["pnl_on_equity"].values \
              if "pnl_on_equity" in trades_df.columns else pnl
    neg_eq  = pnl_eq[pnl_eq <= 0]

    eq_std  = pnl_eq.std(ddof=1)
    sharpe  = (pnl_eq.mean() / eq_std * ann_factor) if eq_std > 0 else 0.0

    neg_std = neg_eq.std(ddof=1) if len(neg_eq) > 1 else eq_std
    sortino = (pnl_eq.mean() / neg_std * ann_factor) if neg_std > 0 else sharpe

    # Drawdown
    eq = compute_equity_curve(trades_df)
    dd = compute_drawdown_series(eq)
    max_dd  = float(dd.min())
    avg_dd  = float(dd[dd < 0].mean()) if (dd < 0).any() else 0.0

    # Drawdown duration (in trade count)
    dd_dur = cur = 0
    for v in (dd < 0).values:
        cur  = cur + 1 if v else 0
        dd_dur = max(dd_dur, cur)

    # One-sample t-test: H0: mean(pnl_on_equity) = 0  (one-tailed: is edge > 0?)
    # Replaces binomial WR test which is misleading for trend-following strategies
    # (low win-rate + high win/loss ratio strategies always fail WR > 50% test)
    if n >= 10:
        t_stat, two_tail_p = stats.ttest_1samp(pnl_eq, 0.0)
        z_stat  = float(t_stat)
        p_value = float(two_tail_p / 2.0)   # one-tailed: mean > 0
    else:
        z_stat, p_value = 0.0, 1.0

    return dict(
        n_trades=n, win_rate=win_rate * 100, avg_win=avg_win,
        avg_loss=avg_loss, win_loss_ratio=win_loss_ratio,
        profit_factor=profit_factor, expectancy=expectancy,
        sharpe=sharpe, sortino=sortino, max_dd=max_dd,
        avg_dd=avg_dd, dd_duration=dd_dur, z_stat=z_stat,
        p_value=p_value, gross_profit=gross_profit,
        gross_loss=gross_loss, n_wins=len(wins), n_losses=len(losses),
        total_pnl=float(pnl.sum()),
    )


# ── Breakdowns ────────────────────────────────────────────────────────────────
def breakdown_by_exit(trades_df: pd.DataFrame) -> dict:
    out = {}
    for reason in ("SL", "TP", "MeshBreak", "Trail"):
        sub = trades_df[trades_df["exit_reason"] == reason]
        if sub.empty:
            continue
        out[reason] = dict(
            count=len(sub),
            win_rate=(sub["pnl_pct"] > 0).mean() * 100,
            avg_pnl=sub["pnl_pct"].mean(),
        )
    return out


def breakdown_by_signal(trades_df: pd.DataFrame) -> dict:
    out = {}
    for sig in ("PB-L", "BO-L", "PB50-L", "PB-S", "BO-S"):
        sub = trades_df[trades_df["signal_type"] == sig]
        if sub.empty:
            continue
        w          = sub[sub["pnl_pct"] > 0]["pnl_pct"].sum()
        gross_loss = abs(sub[sub["pnl_pct"] < 0]["pnl_pct"].sum())
        out[sig] = dict(
            count=len(sub),
            win_rate=(sub["pnl_pct"] > 0).mean() * 100,
            avg_pnl=sub["pnl_pct"].mean(),
            profit_factor=w / gross_loss if gross_loss > 0 else np.inf,
        )
    return out


def breakdown_by_year(trades_df: pd.DataFrame) -> dict:
    if trades_df.empty:
        return {}
    df = trades_df.copy()
    df["year"] = pd.to_datetime(df["exit_date"]).dt.year
    out = {}
    for yr in sorted(df["year"].unique()):
        sub = df[df["year"] == yr]
        out[int(yr)] = dict(
            count=len(sub),
            win_rate=(sub["pnl_pct"] > 0).mean() * 100,
            avg_pnl=sub["pnl_pct"].mean(),
            total_pnl=sub["pnl_pct"].sum(),
        )
    return out


# ── Regime analysis ───────────────────────────────────────────────────────────
def classify_regime(trade_entry_date: pd.Timestamp,
                    nifty_ind: pd.DataFrame) -> str:
    """Return 'bull', 'bear', or 'unknown' for a single trade's entry date."""
    try:
        # Find the last Nifty bar on or before the entry date
        row = nifty_ind[nifty_ind.index <= trade_entry_date]
        if row.empty:
            return "unknown"
        last = row.iloc[-1]
        w50  = last["weekly_ema50"]
        if np.isnan(w50):
            return "unknown"
        return "bull" if last["Close"] > w50 else "bear"
    except Exception:
        return "unknown"


def breakdown_by_regime(trades_df: pd.DataFrame,
                        nifty_ind: Optional[pd.DataFrame]) -> dict:
    """Win-rate / avg-PnL breakdown by bull / bear Nifty regime."""
    if trades_df.empty or nifty_ind is None:
        return {}

    df = trades_df.copy()
    df["regime"] = df["entry_date"].apply(
        lambda d: classify_regime(pd.Timestamp(d), nifty_ind)
    )

    out = {}
    for regime in ("bull", "bear", "unknown"):
        sub = df[df["regime"] == regime]
        if sub.empty:
            continue
        out[regime] = dict(
            count=len(sub),
            win_rate=(sub["pnl_pct"] > 0).mean() * 100,
            avg_pnl=sub["pnl_pct"].mean(),
        )
    return out


# ── Inter-stock correlation & effective sample size ───────────────────────────
def build_trade_return_matrix(all_trades: dict[str, pd.DataFrame],
                              freq: str = "ME") -> pd.DataFrame:
    """
    For each ticker, resample trade returns to monthly, then build a
    ticker × month matrix for correlation analysis.
    """
    series = {}
    for ticker, tdf in all_trades.items():
        if tdf.empty:
            continue
        s = (tdf.set_index("exit_date")["pnl_pct"]
               .sort_index()
               .resample(freq)
               .sum())
        series[ticker] = s

    if not series:
        return pd.DataFrame()
    return pd.DataFrame(series).fillna(0.0)


def effective_sample_size(n_stocks: int, avg_rho: float, n_trades: int) -> float:
    """
    Adjust total trade count for average inter-stock correlation.
    ESS = n / (1 + (n-1)*rho)
    """
    if n_stocks <= 1 or avg_rho <= 0:
        return float(n_trades)
    ess = n_stocks / (1.0 + (n_stocks - 1.0) * avg_rho)
    return float(n_trades) * ess / n_stocks


def adjusted_z_test(all_trades: dict[str, pd.DataFrame]) -> dict:
    """
    Compute binomial Z-test adjusted for inter-stock correlation.
    """
    combined = pd.concat(all_trades.values(), ignore_index=True)
    if combined.empty or len(combined) < 10:
        return {"z_raw": 0.0, "z_adj": 0.0, "p_adj": 1.0, "avg_rho": 0.0}

    mat = build_trade_return_matrix(all_trades)
    if mat.shape[1] >= 2:
        corr = mat.corr()
        mask = np.triu(np.ones(corr.shape), k=1).astype(bool)
        upper = corr.values[mask]
        avg_rho = float(np.nanmean(upper))
    else:
        avg_rho = 0.0

    pnl   = combined["pnl_pct"].values
    n     = len(pnl)
    wr    = (pnl > 0).mean()
    z_raw = (wr - 0.5) / np.sqrt(0.25 / n)

    ess   = effective_sample_size(mat.shape[1], max(avg_rho, 0.0), n)
    z_adj = (wr - 0.5) / np.sqrt(0.25 / ess) if ess > 0 else 0.0
    p_adj = float(2.0 * (1.0 - stats.norm.cdf(abs(z_adj))))

    return dict(z_raw=z_raw, z_adj=z_adj, p_adj=p_adj,
                avg_rho=avg_rho, ess=ess)


# ── Combined portfolio metrics ────────────────────────────────────────────────
def compute_portfolio_equity(all_trades: dict[str, pd.DataFrame],
                             initial_equity: float = 100.0) -> pd.Series:
    """
    Equal-weight portfolio equity: each stock contributes 1/N of capital.
    """
    n = len([v for v in all_trades.values() if not v.empty])
    if n == 0:
        return pd.Series([initial_equity], dtype=float)

    # Merge all trades
    frames = [v for v in all_trades.values() if not v.empty]
    combined = pd.concat(frames, ignore_index=True).sort_values("exit_date")

    # Scale each trade's PnL by 1/n (equal weight)
    combined = combined.copy()
    combined["pnl_pct_scaled"] = combined["pnl_pct"] / n

    equity = [initial_equity]
    for row_pnl in combined["pnl_pct_scaled"].values:
        equity.append(equity[-1] * (1.0 + row_pnl / 100.0))

    dates = [combined["entry_date"].iloc[0]] + list(combined["exit_date"])
    return pd.Series(equity, index=pd.to_datetime(dates))


def compute_universe_breadth(ind_dfs: dict[str, pd.DataFrame],
                             col: str = "bull_trend") -> pd.Series:
    """
    Daily % of the universe in an uptrend — the size of the opportunity set.

    Strictly causal: `bull_trend` at bar t uses only bars <= t, and this is a
    cross-sectional mean at each date, so no future information enters.

    Why this and not the Nifty EMA200 gate: in 2025 the index rose 10.5% while
    breadth collapsed to 15.4% and the strategy lost money. Index level and
    opportunity set can diverge; breakouts need the latter.

    Measured relationship (9 years):
        breadth < 20%  -> mean win rate 27.7%, mean return -130 equity-%
        breadth 20-40% -> 37.1%, +341
        breadth > 40%  -> 46.6%, +1468
    """
    cols = []
    for df in ind_dfs.values():
        if col in df.columns:
            cols.append(df[col].astype(float))
    if not cols:
        return pd.Series(dtype=float)
    m = pd.concat(cols, axis=1).sort_index()
    return (m.mean(axis=1) * 100.0).rename("breadth_pct")


# ── Nifty rolling correlation ─────────────────────────────────────────────────
def nifty_rolling_corr(portfolio_eq: pd.Series,
                       nifty_df: pd.DataFrame,
                       window: int = 60) -> pd.Series:
    """Rolling correlation between portfolio equity returns and Nifty returns."""
    nifty_ret = nifty_df["Close"].pct_change()

    # Resample portfolio equity to daily via forward-fill
    port_daily = portfolio_eq.resample("B").last().ffill()
    port_ret   = port_daily.pct_change()

    combined = pd.concat([port_ret, nifty_ret], axis=1, join="inner")
    combined.columns = ["port", "nifty"]
    return combined["port"].rolling(window).corr(combined["nifty"])


# ── Pretty-print ──────────────────────────────────────────────────────────────
def print_metrics(ticker: str, m: dict) -> None:
    print(f"\n  ── {ticker} ──────────────────────────────────")
    print(f"  Trades         : {m['n_trades']:,}   "
          f"(Wins {m['n_wins']} / Losses {m['n_losses']})")
    print(f"  Win Rate       : {m['win_rate']:.1f} %")
    print(f"  Avg Win        : {m['avg_win']:+.2f} %   "
          f"Avg Loss: {m['avg_loss']:+.2f} %")
    print(f"  Win/Loss Ratio : {m['win_loss_ratio']:.2f}")
    print(f"  Profit Factor  : {m['profit_factor']:.2f}")
    print(f"  Expectancy     : {m['expectancy']:+.2f} % / trade")
    print(f"  Sharpe (ann.)  : {m['sharpe']:.2f}   "
          f"Sortino: {m['sortino']:.2f}")
    print(f"  Max Drawdown   : {m['max_dd']:.1f} %   "
          f"Avg DD: {m['avg_dd']:.1f} %")
    print(f"  Expect t-stat  : {m['z_stat']:.2f}   "
          f"p-value: {m['p_value']:.4f}"
          + ("  *** SIGNIFICANT ***" if m['p_value'] < 0.05 else ""))
