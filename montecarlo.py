"""
montecarlo.py — Monte Carlo simulation module.

Bootstraps 10,000 equity paths by sampling trade returns
with replacement. Reports distribution of outcomes.
"""

import numpy as np
import pandas as pd


def run_monte_carlo(trade_pnls,
                    n_simulations: int = 10_000,
                    initial_equity: float = 100.0,
                    seed: int = 42) -> dict | None:
    """
    Bootstrap Monte Carlo simulation.

    Args:
        trade_pnls     : 1-D array-like of trade PnL percentages.
        n_simulations  : number of simulated paths.
        initial_equity : starting equity value.
        seed           : RNG seed for reproducibility.

    Returns:
        dict of simulation summary statistics, or None if too few trades.
    """
    pnls = np.asarray(trade_pnls, dtype=np.float64)
    n_trades = len(pnls)
    if n_trades < 10:
        print("  [WARN] Too few trades for Monte Carlo — skipping.")
        return None

    factors = 1.0 + pnls / 100.0
    rng     = np.random.default_rng(seed)

    final_equities = np.empty(n_simulations)
    max_drawdowns  = np.empty(n_simulations)

    for sim in range(n_simulations):
        sampled = rng.choice(factors, size=n_trades, replace=True)
        curve   = initial_equity * np.cumprod(sampled)

        final_equities[sim] = curve[-1]

        peak = np.maximum.accumulate(curve)
        dd   = (curve - peak) / peak * 100.0
        max_drawdowns[sim] = dd.min()

    pct_profitable = float((final_equities > initial_equity).mean() * 100.0)

    return dict(
        n_simulations       = n_simulations,
        n_trades            = n_trades,
        initial_equity      = initial_equity,
        median_final_equity = float(np.median(final_equities)),
        p5_final_equity     = float(np.percentile(final_equities,  5)),
        p95_final_equity    = float(np.percentile(final_equities, 95)),
        mean_max_drawdown   = float(np.mean(max_drawdowns)),
        p95_max_drawdown    = float(np.percentile(max_drawdowns,  95)),
        pct_profitable      = pct_profitable,
        # Raw arrays for plotting
        final_equities      = final_equities,
        max_drawdowns       = max_drawdowns,
    )


def compute_mc_bands(trade_pnls,
                     n_simulations: int = 1_000,
                     initial_equity: float = 100.0,
                     seed: int = 42) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute median, 5th and 95th percentile equity paths for fan chart.

    Returns:
        (median_curve, p5_curve, p95_curve) — each of length n_trades+1.
    """
    pnls     = np.asarray(trade_pnls, dtype=np.float64)
    n_trades = len(pnls)
    if n_trades < 2:
        dummy = np.full(n_trades + 1, initial_equity)
        return dummy, dummy, dummy

    factors    = 1.0 + pnls / 100.0
    rng        = np.random.default_rng(seed)
    all_curves = np.empty((n_simulations, n_trades + 1))
    all_curves[:, 0] = initial_equity

    for sim in range(n_simulations):
        sampled           = rng.choice(factors, size=n_trades, replace=True)
        all_curves[sim, 1:] = initial_equity * np.cumprod(sampled)

    median = np.median(all_curves, axis=0)
    p5     = np.percentile(all_curves,  5, axis=0)
    p95    = np.percentile(all_curves, 95, axis=0)

    return median, p5, p95


def print_mc_summary(mc: dict) -> None:
    print(f"\n  Monte Carlo ({mc['n_simulations']:,} sims × "
          f"{mc['n_trades']} trades)")
    print(f"  Median final equity : {mc['median_final_equity']:.1f}")
    print(f"  5th pct  equity     : {mc['p5_final_equity']:.1f}")
    print(f"  95th pct equity     : {mc['p95_final_equity']:.1f}")
    print(f"  95th pct max DD     : {mc['p95_max_drawdown']:.1f} %")
    print(f"  % Profitable paths  : {mc['pct_profitable']:.1f} %")
