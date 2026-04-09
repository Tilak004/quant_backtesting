"""
optimization.py — Walk-forward optimization and sensitivity analysis.

In-sample  : 2019-01-01 → 2022-12-31
Out-of-sample: 2023-01-01 → 2026-04-30

Grid search maximises annualised Sharpe ratio on IS data.
Reports top-5 parameter sets and runs the best on OOS.
Flags overfitting if OOS Sharpe < 60 % of IS Sharpe.
"""

import itertools
import numpy as np
import pandas as pd
from tqdm import tqdm

from backtester import run_backtest, DEFAULT_PARAMS
from analysis  import compute_metrics

# ── Date splits ───────────────────────────────────────────────────────────────
IS_START  = "2016-01-01"
IS_END    = "2020-12-31"
OOS_START = "2021-01-01"
OOS_END   = "2026-04-30"

# ── Parameter grid ────────────────────────────────────────────────────────────
PARAM_GRID = {
    "sl_mult":       [1.5, 2.0, 2.5],
    "tp_mult_long":  [2.5, 3.0, 3.5],
    "adx_long":      [12,  15,  18 ],
    "adx_short":     [20,  25,  30 ],
    "rsi_pb_lo":     [35,  38,  42 ],
    "rsi_pb_hi":     [58,  62,  65 ],
    "vol_mult_long": [1.0, 1.05,1.1],
}

OVERFIT_THRESHOLD = 0.60   # OOS Sharpe / IS Sharpe must exceed this


# ── Helper: run all tickers for one param set ─────────────────────────────────
def _run_combo(ind_dfs: dict, params: dict,
               start: str, end: str) -> dict:
    """Run backtester for all tickers over a date window with given params."""
    all_pnl: list[float] = []
    for ticker, df in ind_dfs.items():
        sub = df.loc[start:end]
        if len(sub) < 50:
            continue
        trades = run_backtest(sub, params=params, ticker=ticker)
        all_pnl.extend(t["pnl_pct"] for t in trades)

    if len(all_pnl) < 5:
        return {"sharpe": -999.0, "n_trades": 0}

    pnl = np.array(all_pnl)
    n   = len(pnl)
    std = pnl.std(ddof=1)
    if std == 0:
        return {"sharpe": 0.0, "n_trades": n}

    # Estimate annualisation: assume ~252 trading days, IS window ~4 years
    try:
        years          = max((pd.Timestamp(end) - pd.Timestamp(start)).days / 365.25, 0.1)
        tpy            = n / years
    except Exception:
        tpy = 12.0
    sharpe = (pnl.mean() / std) * np.sqrt(tpy)

    return {"sharpe": sharpe, "n_trades": n, "pnl": pnl}


# ── Grid search ───────────────────────────────────────────────────────────────
def run_grid_search(ind_dfs: dict,
                    verbose: bool = True) -> list[dict]:
    """
    Exhaustive grid search on IS data.
    Returns list of result dicts sorted by IS Sharpe (descending).
    """
    keys   = list(PARAM_GRID.keys())
    values = list(PARAM_GRID.values())
    combos = list(itertools.product(*values))
    n_total = len(combos)

    print(f"\n  Grid search: {n_total:,} combinations × "
          f"{len(ind_dfs)} tickers  (IS: {IS_START} → {IS_END})")

    results = []
    for combo in tqdm(combos, desc="  Optimising", ncols=70):
        params = DEFAULT_PARAMS.copy()
        params.update(dict(zip(keys, combo)))

        res = _run_combo(ind_dfs, params, IS_START, IS_END)
        results.append({
            "params":    params.copy(),
            "is_sharpe": res["sharpe"],
            "is_trades": res["n_trades"],
        })

    results.sort(key=lambda x: x["is_sharpe"], reverse=True)

    if verbose:
        print(f"\n  Top-5 parameter sets (IS Sharpe):")
        for k, r in enumerate(results[:5], 1):
            p = r["params"]
            print(
                f"  #{k}  Sharpe={r['is_sharpe']:.2f}  n={r['is_trades']}  "
                f"sl={p['sl_mult']}  tp={p['tp_mult_long']}  "
                f"adx_l={p['adx_long']}  adx_s={p['adx_short']}  "
                f"rsi_lo={p['rsi_pb_lo']}  rsi_hi={p['rsi_pb_hi']}  "
                f"vol={p['vol_mult_long']}"
            )

    return results


# ── OOS evaluation ────────────────────────────────────────────────────────────
def run_oos_evaluation(ind_dfs: dict,
                       best_params: dict,
                       is_sharpe: float) -> dict:
    """
    Run best IS params on OOS data. Return metrics and overfitting flag.
    """
    print(f"\n  OOS evaluation: {OOS_START} → {OOS_END}")

    all_trades: list[dict] = []
    for ticker, df in ind_dfs.items():
        sub = df.loc[OOS_START:OOS_END]
        if len(sub) < 50:
            continue
        trades = run_backtest(sub, params=best_params, ticker=ticker)
        all_trades.extend(trades)

    if not all_trades:
        print("  [WARN] No OOS trades generated.")
        return {"oos_sharpe": 0.0, "overfit": True}

    tdf = pd.DataFrame(all_trades)
    m   = compute_metrics(tdf)

    ratio     = m["sharpe"] / is_sharpe if is_sharpe != 0 else 0.0
    overfit   = ratio < OVERFIT_THRESHOLD
    flag      = "⚠ OVERFIT WARNING" if overfit else "✓ OK"

    print(f"  OOS Trades   : {m['n_trades']}")
    print(f"  OOS Sharpe   : {m['sharpe']:.2f}")
    print(f"  IS Sharpe    : {is_sharpe:.2f}")
    print(f"  OOS/IS ratio : {ratio:.2%}  →  {flag}")

    return {
        "oos_trades":  all_trades,
        "oos_metrics": m,
        "oos_sharpe":  m["sharpe"],
        "is_sharpe":   is_sharpe,
        "ratio":       ratio,
        "overfit":     overfit,
    }


# ── Sensitivity analysis ──────────────────────────────────────────────────────
def sensitivity_analysis(ind_dfs: dict,
                         base_params: dict | None = None) -> dict:
    """
    Vary each optimised parameter individually ±20 % from base value,
    keeping all others fixed. Report Sharpe at each value.
    Flag parameters where ±20 % change causes >30 % Sharpe drop.
    """
    if base_params is None:
        base_params = DEFAULT_PARAMS.copy()

    base_res    = _run_combo(ind_dfs, base_params, IS_START, IS_END)
    base_sharpe = base_res["sharpe"]

    print(f"\n  Sensitivity analysis  (base IS Sharpe = {base_sharpe:.2f})")

    results: dict[str, list[tuple]] = {}  # param → [(value, sharpe), ...]

    for param in PARAM_GRID.keys():
        base_val = base_params[param]
        deltas   = [-0.20, -0.10, 0.0, +0.10, +0.20]
        curve    = []

        for d in deltas:
            test_val = base_val * (1.0 + d)
            # Round integers
            if isinstance(base_val, int):
                test_val = max(1, int(round(test_val)))
            p       = base_params.copy()
            p[param] = test_val
            res     = _run_combo(ind_dfs, p, IS_START, IS_END)
            curve.append((test_val, res["sharpe"]))

        # Fragility flag: does ±20 % change drop Sharpe by >30 %?
        extremes   = [curve[0][1], curve[-1][1]]
        worst      = min(extremes)
        pct_drop   = (base_sharpe - worst) / abs(base_sharpe) if base_sharpe != 0 else 0
        fragile    = pct_drop > 0.30

        flag = "⚠ FRAGILE" if fragile else ""
        print(f"  {param:<18}: base={base_val}  worst±20%Δ Sharpe={worst:.2f}  "
              f"drop={pct_drop:.0%}  {flag}")
        results[param] = curve

    return {"base_sharpe": base_sharpe, "curves": results}
