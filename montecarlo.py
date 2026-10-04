"""
montecarlo.py — Monte Carlo simulation module.

run_monte_carlo_portfolio() resamples DAILY returns of the capital-constrained
portfolio (core/portfolio.py), so its output describes a real account. The
console summary and the fan chart both come from its paths.

Never project by compounding per-trade returns one after another. The
backtester runs each ticker independently, so ~115 trades are open at once at
~19.5% of equity each; chaining them implies roughly 22x leverage. That is what
produced the nonsense 10^22 equity and -99.5% drawdown figures in earlier
reports.
"""

import numpy as np


def run_monte_carlo_portfolio(daily_returns,
                              horizon_days: int = 250,
                              n_simulations: int = 10_000,
                              initial_equity: float = 100_000.0,
                              block_days: int = 20,
                              seed: int = 42) -> dict | None:
    """
    Block-bootstrap Monte Carlo on portfolio daily returns.

    Resamples contiguous blocks of realised daily returns rather than single
    days, which preserves the short-run autocorrelation and volatility
    clustering that an i.i.d. bootstrap destroys — drawdowns from an i.i.d.
    bootstrap are optimistic for exactly that reason.

    Args:
        daily_returns  : 1-D array-like of daily portfolio returns as fractions
                         (0.01 = +1%), e.g. result.equity.pct_change().dropna().
        horizon_days   : length of each simulated path in trading days
                         (250 ~ one year).
        n_simulations  : number of simulated paths.
        initial_equity : starting equity in rupees.
        block_days     : block length for the moving-block bootstrap.
        seed           : RNG seed for reproducibility.

    Returns:
        dict of summary statistics, or None if there is too little history.
        band_p5 / band_median / band_p95 are the per-day 5th/50th/95th
        percentile equity paths, length horizon_days + 1, starting at
        initial_equity on day 0. They come from the same paths as the
        final-equity percentiles, so band_median[-1] == median_final_equity.
    """
    rets = np.asarray(daily_returns, dtype=np.float64)
    rets = rets[np.isfinite(rets)]
    n = len(rets)
    if n < 60:
        print("  [WARN] Too few daily returns for portfolio Monte Carlo — skipping.")
        return None

    block = int(max(1, min(block_days, n)))
    n_blocks = int(np.ceil(horizon_days / block))
    rng = np.random.default_rng(seed)

    final_equities = np.empty(n_simulations)
    max_drawdowns  = np.empty(n_simulations)
    paths          = np.empty((n_simulations, horizon_days + 1))
    paths[:, 0]    = initial_equity

    for sim in range(n_simulations):
        starts = rng.integers(0, n - block + 1, size=n_blocks)
        path = np.concatenate([rets[s:s + block] for s in starts])[:horizon_days]
        curve = initial_equity * np.cumprod(1.0 + path)
        paths[sim, 1:] = curve

        final_equities[sim] = curve[-1]
        # Peak starts at day 1, not initial_equity, so a day-1 loss is not
        # counted. Kept as-is so reported drawdowns stay unchanged.
        peak = np.maximum.accumulate(curve)
        max_drawdowns[sim] = ((curve - peak) / peak * 100.0).min()

    band_p5, band_median, band_p95 = np.percentile(paths, [5, 50, 95], axis=0)

    return dict(
        n_simulations       = n_simulations,
        horizon_days        = horizon_days,
        block_days          = block,
        n_observed_days     = n,
        initial_equity      = initial_equity,
        median_final_equity = float(np.median(final_equities)),
        p5_final_equity     = float(np.percentile(final_equities,  5)),
        p95_final_equity    = float(np.percentile(final_equities, 95)),
        mean_max_drawdown   = float(np.mean(max_drawdowns)),
        # Drawdowns are negative, so the drawdown exceeded only 5% of the time is
        # the 5th percentile, not the 95th. Taking the 95th would report the
        # MILDEST tail and understate the risk.
        p95_max_drawdown    = float(np.percentile(max_drawdowns,  5)),
        pct_profitable      = float((final_equities > initial_equity).mean() * 100.0),
        final_equities      = final_equities,
        max_drawdowns       = max_drawdowns,
        band_p5             = band_p5,
        band_median         = band_median,
        band_p95            = band_p95,
    )


def print_mc_summary(mc: dict) -> None:
    """Console summary of a run_monte_carlo_portfolio() result."""
    init = mc["initial_equity"]

    def _eq(v: float) -> str:
        return f"Rs {v:>14,.0f}  ({v / init - 1:+.1%})"

    print(f"\n  Monte Carlo ({mc['n_simulations']:,} paths × "
          f"{mc['horizon_days']} days, {mc['block_days']}-day blocks over "
          f"{mc['n_observed_days']:,} observed days)")
    print(f"  Median final equity : {_eq(mc['median_final_equity'])}")
    print(f"  5th pct  equity     : {_eq(mc['p5_final_equity'])}")
    print(f"  95th pct equity     : {_eq(mc['p95_final_equity'])}")
    print(f"  Mean max drawdown   : {mc['mean_max_drawdown']:.1f} %")
    print(f"  Worst-5% drawdown   : {mc['p95_max_drawdown']:.1f} %")
    print(f"  % Profitable paths  : {mc['pct_profitable']:.1f} %")
