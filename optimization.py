"""
optimization.py — Walk-forward optimisation and sensitivity analysis.

Objective: PORTFOLIO Sharpe from a daily mark-to-market equity curve of a single
Rs 1,00,000 account with a real capital limit and a liquidity floor.

Why not trade-based Sharpe (the previous objective)
---------------------------------------------------
The old scorer was `mean(pnl_pct)/std * sqrt(n_trades / years)` over all tickers
pooled. Three defects, all of which biased the search:

  1. TRADE-COUNT BIAS. `n_trades` counted parallel positions across 869 tickers
     as if they were sequential. Two parameter sets with identical per-trade
     quality scored differently purely on how many trades they fired — 4x the
     trades bought a 2x higher "Sharpe" for free. The optimiser was structurally
     rewarded for loosening filters.
  2. WRONG QUANTITY. It used `pnl_pct` (return on position) rather than
     `pnl_on_equity`, so position sizing was invisible.
  3. UNAFFORDABLE TRADES. No portfolio constraint and no liquidity floor, so it
     tuned for an account holding ~115 concurrent positions at ~2237% of equity,
     in stocks that cannot absorb the order.

Every candidate is now scored on money a real account could have made.
Expect the resulting numbers to be LOWER than the old ones. That is the point.

Also here:
  - expected_max_sharpe(): the multiple-testing haircut. With N trials the best
    result is partly luck; this is the bar a winner must clear.
  - sensitivity_analysis(): prefer broad plateaus over narrow spikes.
"""

import itertools

import numpy as np
import pandas as pd
from scipy.stats import norm
from tqdm import tqdm

from analysis import compute_metrics
from backtester import run_backtest
from core.config import load_config
from core.portfolio import attach_turnover, simulate_portfolio

# ── Date splits ───────────────────────────────────────────────────────────────
IS_START  = "2016-01-01"
IS_END    = "2020-12-31"
OOS_START = "2021-01-01"
OOS_END   = "2026-04-30"

# ── Portfolio settings used to SCORE every candidate ──────────────────────────
# These are held fixed during the search — they define the account we are
# optimising for, not parameters being optimised.
OPT_CAPITAL      = 100_000.0
OPT_MAX_POS      = 15
OPT_POS_PCT      = 6.5
OPT_MIN_TURNOVER = 25e7          # Rs 25 crore/day median — tradeable names only
OPT_COST         = 0.0020        # round-trip; realistic at this liquidity tier

# ── Parameter grid ────────────────────────────────────────────────────────────
# Keep this SMALL. 3^7 = 2,187 combinations was the old grid; at that many trials
# the winner is mostly luck (see expected_max_sharpe). Two or three parameters at
# a time, coarse steps.
PARAM_GRID = {
    "sl_mult":      [1.5, 2.0, 2.5],
    "tp_mult_long": [2.5, 3.0, 3.5],
    "adx_long":     [15, 18, 21],
}

OVERFIT_THRESHOLD = 0.60   # OOS / IS Sharpe must exceed this


# ── Multiple-testing haircut ──────────────────────────────────────────────────

def expected_max_sharpe(n_trials: int, sharpe_std: float) -> float:
    """
    Expected best Sharpe from `n_trials` searches when NO strategy has any edge.

    Standard result for the maximum of N iid normals (Bailey & Lopez de Prado).
    If your best grid result does not clear this, you found noise.
    """
    if n_trials < 2 or sharpe_std <= 0:
        return 0.0
    g = 0.5772156649  # Euler-Mascheroni
    z1 = norm.ppf(1.0 - 1.0 / n_trials)
    z2 = norm.ppf(1.0 - 1.0 / (n_trials * np.e))
    return float(sharpe_std * ((1.0 - g) * z1 + g * z2))


# ── Scoring one parameter set ─────────────────────────────────────────────────

_BREADTH_CACHE: dict[int, "pd.Series"] = {}


def _breadth_for(ind_dfs: dict) -> "pd.Series":
    """
    Universe breadth for this ind_dfs, computed once per search.

    It is cross-sectional over the whole universe and independent of any strategy
    parameter, so recomputing it per combo would be pure waste.
    """
    key = id(ind_dfs)
    if key not in _BREADTH_CACHE:
        from analysis import compute_universe_breadth
        _BREADTH_CACHE[key] = compute_universe_breadth(ind_dfs)
    return _BREADTH_CACHE[key]


def _run_combo(ind_dfs: dict, params: dict, start: str, end: str) -> dict:
    """
    Backtest every ticker with `params`, then replay the trades against ONE
    account with a capital limit and liquidity floor. Returns portfolio metrics.
    """
    br = _breadth_for(ind_dfs) if params.get("breadth_gate_enabled") else None

    rows: list[dict] = []
    for ticker, df in ind_dfs.items():
        sub = df.loc[start:end]
        if len(sub) < 50:
            continue
        rows.extend(run_backtest(sub, params=params, ticker=ticker, breadth=br))

    if len(rows) < 5:
        return {"sharpe": -999.0, "cagr": -999.0, "n_trades": 0, "n_taken": 0}

    t = pd.DataFrame(rows)
    if OPT_MIN_TURNOVER > 0:
        t = attach_turnover(t, window=60)
        t = t[t.turnover >= OPT_MIN_TURNOVER]
    if len(t) < 5:
        return {"sharpe": -999.0, "cagr": -999.0, "n_trades": len(rows), "n_taken": 0}

    try:
        res = simulate_portfolio(
            t, max_positions=OPT_MAX_POS, max_position_pct=OPT_POS_PCT,
            starting_capital=OPT_CAPITAL, round_trip_cost=OPT_COST,
        )
    except Exception as e:
        import warnings
        warnings.warn(f"Portfolio sim failed for {params}: {e}")
        return {"sharpe": -999.0, "cagr": -999.0, "n_trades": len(rows), "n_taken": 0}

    m = res.metrics
    return {
        "sharpe":   m["sharpe"],
        "cagr":     m["cagr"],
        "max_dd":   m["max_dd"],
        "n_trades": len(rows),
        "n_taken":  m["n_taken"],
        "equity":   res.equity,
    }


# ── Grid search ───────────────────────────────────────────────────────────────

def run_grid_search(ind_dfs: dict, verbose: bool = True) -> list[dict]:
    """Exhaustive grid search on IS data, scored on portfolio Sharpe."""
    keys    = list(PARAM_GRID.keys())
    combos  = list(itertools.product(*PARAM_GRID.values()))
    n_total = len(combos)

    print(f"\n  Grid search: {n_total:,} combinations x {len(ind_dfs)} tickers")
    print(f"  IS window : {IS_START} -> {IS_END}")
    print(f"  Objective : portfolio Sharpe (Rs {OPT_CAPITAL:,.0f}, "
          f"{OPT_MAX_POS} positions, >= Rs {OPT_MIN_TURNOVER/1e7:.0f} cr/day, "
          f"{OPT_COST*100:.2f}% costs)")

    results = []
    for combo in tqdm(combos, desc="  Optimising", ncols=70):
        params = load_config().to_params_dict()
        params.update(dict(zip(keys, combo)))
        res = _run_combo(ind_dfs, params, IS_START, IS_END)
        results.append({
            "params":    params.copy(),
            "is_sharpe": res["sharpe"],
            "is_cagr":   res.get("cagr", 0.0),
            "is_maxdd":  res.get("max_dd", 0.0),
            "is_trades": res["n_trades"],
            "is_taken":  res.get("n_taken", 0),
        })

    results.sort(key=lambda x: x["is_sharpe"], reverse=True)

    # Multiple-testing haircut
    valid = [r["is_sharpe"] for r in results if r["is_sharpe"] > -900]
    if len(valid) > 2:
        haircut = expected_max_sharpe(len(valid), float(np.std(valid, ddof=1)))
        best = results[0]["is_sharpe"]
        print(f"\n  Multiple-testing check ({len(valid)} valid trials):")
        print(f"    best IS Sharpe          : {best:.3f}")
        print(f"    expected best if NO edge: {haircut:.3f}")
        if best <= haircut:
            print("    => Best result is INDISTINGUISHABLE FROM NOISE. "
                  "Do not deploy these parameters.")
        else:
            print(f"    => clears the noise bar by {best - haircut:.3f}")

    if verbose:
        print("\n  Top-5 parameter sets (IS portfolio Sharpe):")
        for k, r in enumerate(results[:5], 1):
            p = r["params"]
            print(f"  #{k}  Sharpe={r['is_sharpe']:6.2f}  CAGR={r['is_cagr']:6.1f}%  "
                  f"maxDD={r['is_maxdd']:6.1f}%  taken={r['is_taken']:4d}  "
                  f"sl={p['sl_mult']}  tp={p['tp_mult_long']}  adx={p['adx_long']}")

    return results


# ── OOS evaluation ────────────────────────────────────────────────────────────

def run_oos_evaluation(ind_dfs: dict, best_params: dict,
                       is_sharpe: float) -> dict:
    """Run the best IS params on OOS data, scored the same way."""
    print(f"\n  OOS evaluation: {OOS_START} -> {OOS_END}")

    all_trades: list[dict] = []
    for ticker, df in ind_dfs.items():
        sub = df.loc[OOS_START:OOS_END]
        if len(sub) < 50:
            continue
        all_trades.extend(run_backtest(sub, params=best_params, ticker=ticker))

    if not all_trades:
        print("  [WARN] No OOS trades generated.")
        return {"oos_sharpe": 0.0, "overfit": True}

    res = _run_combo(ind_dfs, best_params, OOS_START, OOS_END)
    tdf = pd.DataFrame(all_trades)
    trade_metrics = compute_metrics(tdf)   # kept for the report / charts

    ratio   = res["sharpe"] / is_sharpe if is_sharpe not in (0, -999.0) else 0.0
    overfit = ratio < OVERFIT_THRESHOLD

    print(f"  OOS trades (signals) : {res['n_trades']}")
    print(f"  OOS trades (funded)  : {res['n_taken']}")
    print(f"  OOS portfolio Sharpe : {res['sharpe']:.2f}   CAGR {res['cagr']:.1f}%")
    print(f"  IS  portfolio Sharpe : {is_sharpe:.2f}")
    print(f"  OOS/IS ratio         : {ratio:.2%}  -> "
          f"{'OVERFIT WARNING' if overfit else 'OK'}")

    return {
        "oos_trades":  all_trades,
        "oos_metrics": trade_metrics,
        "oos_sharpe":  res["sharpe"],
        "oos_cagr":    res["cagr"],
        "is_sharpe":   is_sharpe,
        "ratio":       ratio,
        "overfit":     overfit,
    }


# ── Sensitivity analysis ──────────────────────────────────────────────────────

def sensitivity_analysis(ind_dfs: dict,
                         base_params: dict | None = None) -> dict:
    """
    Vary each grid parameter +/-20% around its base value.

    Use these curves to SELECT parameters, not just to sanity-check them: prefer
    the centre of a broad plateau over a narrow peak, even if the peak scores
    higher. A spike will not survive live.
    """
    if base_params is None:
        base_params = load_config().to_params_dict()

    base_sharpe = _run_combo(ind_dfs, base_params, IS_START, IS_END)["sharpe"]
    print(f"\n  Sensitivity analysis  (base IS portfolio Sharpe = {base_sharpe:.2f})")

    results: dict[str, list[tuple]] = {}
    for param in PARAM_GRID:
        base_val = base_params[param]
        curve = []
        for d in (-0.20, -0.10, 0.0, +0.10, +0.20):
            test_val = base_val * (1.0 + d)
            if isinstance(base_val, int):
                test_val = max(1, int(round(test_val)))
            p = base_params.copy()
            p[param] = test_val
            curve.append((test_val, _run_combo(ind_dfs, p, IS_START, IS_END)["sharpe"]))

        worst    = min(curve[0][1], curve[-1][1])
        pct_drop = (base_sharpe - worst) / abs(base_sharpe) if base_sharpe else 0
        flag     = "FRAGILE — narrow peak, prefer a plateau" if pct_drop > 0.30 else ""
        print(f"  {param:<18}: base={base_val}  worst+/-20% Sharpe={worst:.2f}  "
              f"drop={pct_drop:.0%}  {flag}")
        results[param] = curve

    return {"base_sharpe": base_sharpe, "curves": results}
