"""
charts.py — Visualization module.

All charts are saved as PNG to results/charts/.
Uses non-interactive Agg backend so it works without a display.
"""

import os
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")               # must be before pyplot import
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import seaborn as sns

warnings.filterwarnings("ignore")

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CHARTS_DIR  = os.path.join(BASE_DIR, "results", "charts")

sns.set_theme(style="darkgrid", palette="muted")
_FIG_DPI = 130


def _save(fig: plt.Figure, name: str) -> None:
    os.makedirs(CHARTS_DIR, exist_ok=True)
    path = os.path.join(CHARTS_DIR, name)
    fig.savefig(path, dpi=_FIG_DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  [CHART] saved → {path}")


# ── 1. Equity curves ──────────────────────────────────────────────────────────
def plot_equity_curves(equity_dict: dict,
                       portfolio_eq: pd.Series | None = None,
                       title: str = "Equity Curves") -> None:
    """Plot one equity curve per ticker + optional combined portfolio."""
    fig, ax = plt.subplots(figsize=(14, 6))

    cmap = plt.cm.tab20
    for k, (ticker, eq) in enumerate(equity_dict.items()):
        if eq is None or len(eq) < 2:
            continue
        ax.plot(pd.to_datetime(eq.index), eq.values,
                lw=0.9, alpha=0.6, color=cmap(k / max(len(equity_dict), 1)),
                label=ticker.replace(".NS", ""))

    if portfolio_eq is not None and len(portfolio_eq) > 1:
        ax.plot(pd.to_datetime(portfolio_eq.index), portfolio_eq.values,
                lw=2.5, color="black", label="Portfolio", zorder=5)

    ax.axhline(100, color="grey", lw=0.8, ls="--")
    ax.set_title(title, fontsize=13)
    ax.set_ylabel("Equity (start = 100)")
    ax.legend(ncol=4, fontsize=7)
    ax.yaxis.set_major_formatter(mtick.FormatStrFormatter("%.0f"))
    _save(fig, "01_equity_curves.png")


# ── 2. Drawdown chart ─────────────────────────────────────────────────────────
def plot_drawdown(portfolio_eq: pd.Series) -> None:
    from analysis import compute_drawdown_series
    if portfolio_eq is None or len(portfolio_eq) < 2:
        return
    dd = compute_drawdown_series(portfolio_eq)
    fig, ax = plt.subplots(figsize=(14, 4))
    ax.fill_between(pd.to_datetime(dd.index), dd.values, 0,
                    color="crimson", alpha=0.5, label="Drawdown")
    ax.plot(pd.to_datetime(dd.index), dd.values, color="crimson", lw=0.8)
    ax.set_title("Portfolio Drawdown (%)", fontsize=13)
    ax.set_ylabel("Drawdown %")
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    _save(fig, "02_drawdown.png")


# ── 3. Monthly returns heatmap ────────────────────────────────────────────────
def plot_monthly_heatmap(portfolio_eq: pd.Series,
                         title: str = "Monthly Returns (%) — Portfolio") -> None:
    if portfolio_eq is None or len(portfolio_eq) < 2:
        return

    monthly = portfolio_eq.resample("ME").last().pct_change().dropna() * 100
    if monthly.empty:
        return

    pivot = pd.DataFrame({
        "year":  monthly.index.year,
        "month": monthly.index.month,
        "ret":   monthly.values,
    }).pivot(index="year", columns="month", values="ret")

    month_labels = ["Jan","Feb","Mar","Apr","May","Jun",
                    "Jul","Aug","Sep","Oct","Nov","Dec"]
    n_cols = pivot.shape[1]
    pivot.columns = month_labels[:n_cols]

    fig, ax = plt.subplots(figsize=(14, max(4, pivot.shape[0] * 0.55)))
    vmax = max(abs(pivot.values[~np.isnan(pivot.values)]).max(), 1)
    sns.heatmap(pivot, annot=True, fmt=".1f", center=0,
                cmap="RdYlGn", vmin=-vmax, vmax=vmax,
                linewidths=0.5, ax=ax, cbar_kws={"label": "Return %"})
    ax.set_title(title, fontsize=13)
    ax.set_xlabel("")
    ax.set_ylabel("Year")
    _save(fig, "03_monthly_heatmap.png")


# ── 4. Win rate by year ───────────────────────────────────────────────────────
def plot_winrate_by_year(all_trades_df: pd.DataFrame) -> None:
    if all_trades_df.empty:
        return
    df = all_trades_df.copy()
    df["year"] = pd.to_datetime(df["exit_date"]).dt.year
    wr = df.groupby("year").apply(
        lambda g: (g["pnl_pct"] > 0).mean() * 100
    ).reset_index()
    wr.columns = ["year", "win_rate"]

    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ["#2ecc71" if w >= 50 else "#e74c3c" for w in wr["win_rate"]]
    ax.bar(wr["year"].astype(str), wr["win_rate"], color=colors, width=0.6)
    ax.axhline(50, color="grey", ls="--", lw=1)
    ax.set_title("Win Rate by Year (%)", fontsize=13)
    ax.set_ylabel("Win Rate %")
    ax.set_ylim(0, 100)
    for bar, v in zip(ax.patches, wr["win_rate"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                f"{v:.0f}%", ha="center", fontsize=9)
    _save(fig, "04_winrate_by_year.png")


# ── 5. Profit factor by signal type ──────────────────────────────────────────
def plot_pf_by_signal(all_trades_df: pd.DataFrame) -> None:
    if all_trades_df.empty:
        return
    from analysis import breakdown_by_signal
    bds = breakdown_by_signal(all_trades_df)
    if not bds:
        return

    sigs = list(bds.keys())
    pfs  = [min(bds[s]["profit_factor"], 10) for s in sigs]  # cap at 10

    fig, ax = plt.subplots(figsize=(9, 5))
    colors = ["#27ae60" if pf >= 1 else "#e74c3c" for pf in pfs]
    ax.bar(sigs, pfs, color=colors, width=0.5)
    ax.axhline(1.0, color="grey", ls="--", lw=1)
    ax.set_title("Profit Factor by Signal Type", fontsize=13)
    ax.set_ylabel("Profit Factor")
    for bar, v in zip(ax.patches, pfs):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                f"{v:.2f}", ha="center", fontsize=10)
    _save(fig, "05_pf_by_signal.png")


# ── 6. Trade PnL distribution ─────────────────────────────────────────────────
def plot_trade_distribution(all_trades_df: pd.DataFrame) -> None:
    if all_trades_df.empty:
        return
    pnl = all_trades_df["pnl_pct"].values

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(pnl, bins=60, color="#3498db", edgecolor="white", alpha=0.8)
    ax.axvline(0, color="grey", ls="--", lw=1.5)
    ax.axvline(pnl.mean(), color="orange", ls="--", lw=1.5,
               label=f"Mean {pnl.mean():.2f}%")
    ax.set_title("Trade PnL Distribution (%)", fontsize=13)
    ax.set_xlabel("PnL per Trade (%)")
    ax.set_ylabel("Count")
    ax.legend()
    _save(fig, "06_trade_distribution.png")


# ── 7. Monte Carlo fan chart ──────────────────────────────────────────────────
def plot_mc_fan(median: np.ndarray,
                p5: np.ndarray,
                p95: np.ndarray,
                actual_eq: pd.Series | None = None) -> None:
    x = np.arange(len(median))
    fig, ax = plt.subplots(figsize=(12, 5))

    ax.fill_between(x, p5, p95, alpha=0.25, color="#3498db", label="5th–95th pct")
    ax.plot(x, median, color="#2980b9", lw=2,  label="Median")
    ax.plot(x, p5,     color="#2980b9", lw=0.8, ls="--")
    ax.plot(x, p95,    color="#2980b9", lw=0.8, ls="--")

    if actual_eq is not None and len(actual_eq) > 1:
        # Scale actual equity to match x-axis (trades not dates)
        ax.plot(np.linspace(0, len(median) - 1, len(actual_eq)),
                actual_eq.values, color="black", lw=1.8, label="Actual")

    ax.axhline(100, color="grey", ls="--", lw=1)
    ax.set_title("Monte Carlo Equity Fan Chart (10 000 simulations)", fontsize=13)
    ax.set_xlabel("Trade #")
    ax.set_ylabel("Equity (start = 100)")
    ax.legend()
    _save(fig, "07_monte_carlo_fan.png")


# ── 8. Parameter sensitivity ──────────────────────────────────────────────────
def plot_sensitivity(sens_results: dict) -> None:
    """One subplot per parameter — Sharpe vs parameter value."""
    curves = sens_results.get("curves", {})
    if not curves:
        return

    n = len(curves)
    cols  = min(n, 4)
    rows  = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols,
                             figsize=(5 * cols, 4 * rows))
    axes_flat = np.array(axes).flatten() if n > 1 else [axes]

    base_sharpe = sens_results.get("base_sharpe", 0)

    for ax, (param, curve) in zip(axes_flat, curves.items()):
        xs = [v for v, _ in curve]
        ys = [s for _, s in curve]
        ax.plot(xs, ys, marker="o", lw=2, color="#2c3e50")
        ax.axhline(base_sharpe, color="grey", ls="--", lw=1,
                   label=f"Base {base_sharpe:.2f}")
        ax.set_title(param, fontsize=10)
        ax.set_xlabel("Value")
        ax.set_ylabel("IS Sharpe")
        ax.legend(fontsize=8)

    # Hide unused axes
    for ax in axes_flat[n:]:
        ax.set_visible(False)

    fig.suptitle("Parameter Sensitivity (IS Sharpe)", fontsize=13, y=1.01)
    fig.tight_layout()
    _save(fig, "08_sensitivity.png")


# ── 9. Correlation heatmap ────────────────────────────────────────────────────
def plot_correlation_heatmap(trade_return_matrix: pd.DataFrame) -> None:
    """Heatmap of inter-stock monthly return correlations."""
    if trade_return_matrix.empty or trade_return_matrix.shape[1] < 2:
        return

    corr = trade_return_matrix.corr()
    # Shorten labels
    corr.columns = [c.replace(".NS", "") for c in corr.columns]
    corr.index   = [c.replace(".NS", "") for c in corr.index]

    fig, ax = plt.subplots(figsize=(10, 8))
    mask = np.triu(np.ones_like(corr, dtype=bool))
    sns.heatmap(corr, mask=mask, annot=True, fmt=".2f",
                cmap="coolwarm", center=0, vmin=-1, vmax=1,
                square=True, linewidths=0.5, ax=ax,
                cbar_kws={"shrink": 0.8})
    ax.set_title("Inter-Stock Monthly Return Correlation", fontsize=13)
    _save(fig, "09_correlation_heatmap.png")


# ── 10. Nifty rolling correlation ─────────────────────────────────────────────
def plot_nifty_corr(rolling_corr: pd.Series) -> None:
    if rolling_corr is None or rolling_corr.dropna().empty:
        return
    fig, ax = plt.subplots(figsize=(12, 4))
    rc = rolling_corr.dropna()
    ax.plot(rc.index, rc.values, color="#8e44ad", lw=1.5)
    ax.axhline(0, color="grey", ls="--", lw=1)
    ax.fill_between(rc.index, rc.values, 0,
                    where=(rc.values > 0), alpha=0.3, color="#2ecc71")
    ax.fill_between(rc.index, rc.values, 0,
                    where=(rc.values < 0), alpha=0.3, color="#e74c3c")
    ax.set_title("Rolling 60-bar Correlation: Strategy vs Nifty50", fontsize=13)
    ax.set_ylabel("Correlation")
    ax.set_ylim(-1, 1)
    _save(fig, "10_nifty_rolling_corr.png")


# ── 11. Per-stock win-rate bars ────────────────────────────────────────────────
def plot_per_stock_summary(metrics_dict: dict) -> None:
    """Bar chart of Sharpe and Win Rate per ticker."""
    tickers = [t.replace(".NS", "") for t in metrics_dict.keys()]
    sharpes = [metrics_dict[t].get("sharpe", 0) for t in metrics_dict]
    wrs     = [metrics_dict[t].get("win_rate", 0) for t in metrics_dict]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    colors_s = ["#27ae60" if s > 0 else "#e74c3c" for s in sharpes]
    ax1.bar(tickers, sharpes, color=colors_s, width=0.6)
    ax1.axhline(0, color="grey", ls="--", lw=1)
    ax1.set_title("Sharpe Ratio per Stock", fontsize=11)
    ax1.set_ylabel("Sharpe")
    ax1.tick_params(axis="x", rotation=45)

    colors_w = ["#27ae60" if w >= 50 else "#e74c3c" for w in wrs]
    ax2.bar(tickers, wrs, color=colors_w, width=0.6)
    ax2.axhline(50, color="grey", ls="--", lw=1)
    ax2.set_title("Win Rate per Stock (%)", fontsize=11)
    ax2.set_ylabel("Win Rate %")
    ax2.set_ylim(0, 100)
    ax2.tick_params(axis="x", rotation=45)

    fig.tight_layout()
    _save(fig, "11_per_stock_summary.png")
