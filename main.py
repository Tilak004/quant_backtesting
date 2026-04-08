"""
main.py — Full pipeline orchestrator.

Run with:   python main.py
            python main.py --force-download     (re-fetch all data)
            python main.py --skip-optim         (skip walk-forward optimisation)
"""

import os
import sys
import argparse
import warnings
import traceback

import pandas as pd
import numpy as np
from tqdm import tqdm

warnings.filterwarnings("ignore")

# ── Import project modules ────────────────────────────────────────────────────
from data         import download_all_data, TICKERS, NIFTY_TICKER
from indicators   import prepare_indicators
from backtester   import run_backtest, DEFAULT_PARAMS
from analysis     import (compute_metrics, compute_equity_curve,
                          compute_portfolio_equity, compute_monthly_returns,
                          breakdown_by_exit, breakdown_by_signal,
                          breakdown_by_year, breakdown_by_regime,
                          adjusted_z_test, build_trade_return_matrix,
                          nifty_rolling_corr, print_metrics)
from optimization import run_grid_search, run_oos_evaluation, sensitivity_analysis
from montecarlo   import run_monte_carlo, compute_mc_bands, print_mc_summary
from charts       import (plot_equity_curves, plot_drawdown,
                          plot_monthly_heatmap, plot_winrate_by_year,
                          plot_pf_by_signal, plot_trade_distribution,
                          plot_mc_fan, plot_sensitivity,
                          plot_correlation_heatmap, plot_nifty_corr,
                          plot_per_stock_summary)

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(BASE_DIR, "results")


# ── Helper: section header ────────────────────────────────────────────────────
def _hdr(n: int, title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  STAGE {n} — {title}")
    print(f"{'='*60}")


# ── Main pipeline ─────────────────────────────────────────────────────────────
def main(force_download: bool = False, skip_optim: bool = False) -> None:

    # ── STAGE 1: Data ─────────────────────────────────────────────────────────
    _hdr(1, "Download & Cache Market Data")
    all_tickers  = TICKERS + [NIFTY_TICKER]
    raw_data     = download_all_data(all_tickers, force_download=force_download)

    # Separate Nifty from strategy tickers
    nifty_raw    = raw_data.pop(NIFTY_TICKER, None)
    available    = [t for t in TICKERS if t in raw_data]

    if not available:
        print("[FATAL] No ticker data available. Exiting.")
        sys.exit(1)

    print(f"\n  Strategy tickers available : {len(available)} / {len(TICKERS)}")
    if nifty_raw is not None:
        print(f"  Nifty50 data             : {len(nifty_raw):,} bars")

    # ── STAGE 2: Indicators ───────────────────────────────────────────────────
    _hdr(2, "Computing Indicators")
    ind_dfs: dict[str, pd.DataFrame] = {}

    for ticker in tqdm(available, desc="  Indicators", ncols=70):
        try:
            ind_dfs[ticker] = prepare_indicators(raw_data[ticker])
            print(f"  [OK] {ticker}: indicators computed")
        except Exception as exc:
            print(f"  [SKIP] {ticker}: indicator error — {exc}")

    nifty_ind = None
    if nifty_raw is not None:
        try:
            nifty_ind = prepare_indicators(nifty_raw)
        except Exception:
            pass

    # ── STAGE 3: Backtest ─────────────────────────────────────────────────────
    _hdr(3, "Running Backtest (default parameters)")
    all_trades:     dict[str, pd.DataFrame] = {}
    equity_curves:  dict[str, pd.Series]    = {}
    metrics_dict:   dict[str, dict]         = {}

    for ticker in tqdm(available, desc="  Backtesting", ncols=70):
        try:
            trades = run_backtest(ind_dfs[ticker], ticker=ticker)
            tdf    = pd.DataFrame(trades) if trades else pd.DataFrame()

            # Save per-ticker CSV
            csv_path = os.path.join(RESULTS_DIR, f"trades_{ticker.replace('.','_')}.csv")
            tdf.to_csv(csv_path, index=False)

            all_trades[ticker]    = tdf
            equity_curves[ticker] = compute_equity_curve(tdf)
            metrics_dict[ticker]  = compute_metrics(tdf)

            n = len(tdf)
            wr = metrics_dict[ticker]["win_rate"]
            sh = metrics_dict[ticker]["sharpe"]
            print(f"  {ticker:<18}: {n:>3} trades  WR={wr:.0f}%  Sharpe={sh:.2f}")
        except Exception as exc:
            print(f"  [SKIP] {ticker}: backtest error — {exc}")
            traceback.print_exc()

    # ── STAGE 4: Statistical Analysis ─────────────────────────────────────────
    _hdr(4, "Statistical Analysis")

    # Combined portfolio
    portfolio_eq = compute_portfolio_equity(all_trades)
    combined_df  = pd.concat(
        [v for v in all_trades.values() if not v.empty],
        ignore_index=True
    )
    combined_metrics = compute_metrics(combined_df)

    print("\n  ── COMBINED PORTFOLIO ─────────────────────────────────")
    print_metrics("PORTFOLIO", combined_metrics)

    # Detailed breakdowns
    print("\n  Breakdown by exit reason:")
    for reason, bd in breakdown_by_exit(combined_df).items():
        print(f"    {reason:<12}: n={bd['count']:3}  WR={bd['win_rate']:.0f}%  "
              f"avg={bd['avg_pnl']:+.2f}%")

    print("\n  Breakdown by signal type:")
    for sig, bd in breakdown_by_signal(combined_df).items():
        print(f"    {sig:<10}: n={bd['count']:3}  WR={bd['win_rate']:.0f}%  "
              f"avg={bd['avg_pnl']:+.2f}%  PF={bd['profit_factor']:.2f}")

    print("\n  Breakdown by year:")
    for yr, bd in breakdown_by_year(combined_df).items():
        print(f"    {yr}: n={bd['count']:3}  WR={bd['win_rate']:.0f}%  "
              f"total={bd['total_pnl']:+.1f}%")

    print("\n  Breakdown by market regime:")
    for regime, bd in breakdown_by_regime(combined_df, nifty_ind).items():
        print(f"    {regime:<8}: n={bd['count']:3}  WR={bd['win_rate']:.0f}%  "
              f"avg={bd['avg_pnl']:+.2f}%")

    # Inter-stock correlation correction
    print("\n  Adjusted Z-test (inter-stock correlation):")
    adj = adjusted_z_test(all_trades)
    print(f"    Avg inter-stock ρ : {adj['avg_rho']:.3f}")
    print(f"    Effective N        : {adj.get('ess', 0):.0f}")
    print(f"    Raw Z              : {adj['z_raw']:.2f}")
    print(f"    Adjusted Z         : {adj['z_adj']:.2f}  "
          f"p={adj['p_adj']:.4f}"
          + ("  *** SIGNIFICANT ***" if adj['p_adj'] < 0.05 else ""))

    # Per-ticker detailed metrics
    print("\n  Per-stock metrics:")
    for ticker in available:
        if ticker in metrics_dict:
            print_metrics(ticker, metrics_dict[ticker])

    # ── STAGE 5: Walk-Forward Optimisation ────────────────────────────────────
    _hdr(5, "Walk-Forward Optimisation")
    best_params = DEFAULT_PARAMS.copy()
    optim_results = None

    if skip_optim:
        print("  [SKIP] Optimisation skipped via --skip-optim flag.")
    else:
        print("\n  This grid search tests 2,187 parameter combinations.")
        print("  It may take 3–10 minutes depending on your hardware.")
        print("  Press ENTER to continue, or type 'skip' to skip.\n")
        try:
            ans = input("  >>> ").strip().lower()
        except EOFError:
            ans = ""

        if ans == "skip":
            print("  Optimisation skipped.")
        else:
            try:
                grid_results = run_grid_search(ind_dfs, verbose=True)
                best         = grid_results[0]
                best_params  = best["params"]
                is_sharpe    = best["is_sharpe"]

                optim_results = run_oos_evaluation(ind_dfs, best_params, is_sharpe)
                optim_results["grid_results"] = grid_results

                # Save OOS trades
                if "oos_trades" in optim_results and optim_results["oos_trades"]:
                    oos_df = pd.DataFrame(optim_results["oos_trades"])
                    oos_df.to_csv(
                        os.path.join(RESULTS_DIR, "trades_OOS_best.csv"),
                        index=False
                    )
            except Exception as exc:
                print(f"  [WARN] Optimisation failed: {exc}")
                traceback.print_exc()

    # ── STAGE 6: Sensitivity Analysis ─────────────────────────────────────────
    _hdr(6, "Sensitivity Analysis")
    sens_results = None
    try:
        sens_results = sensitivity_analysis(ind_dfs, base_params=best_params)
    except Exception as exc:
        print(f"  [WARN] Sensitivity analysis failed: {exc}")

    # ── STAGE 7: Monte Carlo ──────────────────────────────────────────────────
    _hdr(7, "Monte Carlo Simulation")
    mc_result = None
    mc_bands  = (None, None, None)
    try:
        if not combined_df.empty:
            pnls      = combined_df["pnl_pct"].values
            mc_result = run_monte_carlo(pnls, n_simulations=10_000)
            if mc_result:
                print_mc_summary(mc_result)
                mc_bands = compute_mc_bands(pnls, n_simulations=1_000)
    except Exception as exc:
        print(f"  [WARN] Monte Carlo failed: {exc}")

    # ── STAGE 8: Correlation & Regime ─────────────────────────────────────────
    _hdr(8, "Correlation & Regime Analysis")
    trade_return_matrix = build_trade_return_matrix(all_trades)
    rolling_corr = None
    if nifty_raw is not None and not portfolio_eq.empty:
        try:
            rolling_corr = nifty_rolling_corr(portfolio_eq, nifty_raw)
            print("  Rolling 60-bar Nifty correlation computed.")
        except Exception as exc:
            print(f"  [WARN] Nifty correlation failed: {exc}")

    # ── STAGE 9: Charts ───────────────────────────────────────────────────────
    _hdr(9, "Generating Charts")
    try:
        plot_equity_curves(equity_curves, portfolio_eq)
        plot_drawdown(portfolio_eq)
        plot_monthly_heatmap(portfolio_eq)
        if not combined_df.empty:
            plot_winrate_by_year(combined_df)
            plot_pf_by_signal(combined_df)
            plot_trade_distribution(combined_df)
        if mc_bands[0] is not None:
            actual_eq = compute_equity_curve(combined_df)
            plot_mc_fan(*mc_bands, actual_eq=actual_eq)
        if sens_results:
            plot_sensitivity(sens_results)
        if not trade_return_matrix.empty:
            plot_correlation_heatmap(trade_return_matrix)
        if rolling_corr is not None:
            plot_nifty_corr(rolling_corr)
        plot_per_stock_summary(metrics_dict)
    except Exception as exc:
        print(f"  [WARN] Chart generation error: {exc}")
        traceback.print_exc()

    # ── STAGE 10: Summary Report ──────────────────────────────────────────────
    _hdr(10, "Summary Report")
    _write_summary_report(
        available, metrics_dict, combined_metrics,
        optim_results, mc_result, adj
    )

    # ── Final table ───────────────────────────────────────────────────────────
    _print_final_table(available, metrics_dict, combined_metrics)


# ── Summary report writer ─────────────────────────────────────────────────────
def _write_summary_report(available, metrics_dict, combined_metrics,
                           optim_results, mc_result, adj_z) -> None:
    cm = combined_metrics
    lines = [
        "# NSE Swing Strategy — Backtest Summary Report",
        f"\nGenerated on: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}",
        f"\n## Universe\n{', '.join(t.replace('.NS','') for t in available)}",
        "\n## Combined Portfolio (all stocks, default params, 2019–2026)",
        "",
        f"| Metric            | Value           |",
        f"|-------------------|-----------------|",
        f"| Total Trades      | {cm['n_trades']} |",
        f"| Win Rate          | {cm['win_rate']:.1f}% |",
        f"| Avg Win           | {cm['avg_win']:+.2f}% |",
        f"| Avg Loss          | {cm['avg_loss']:+.2f}% |",
        f"| Win/Loss Ratio    | {cm['win_loss_ratio']:.2f} |",
        f"| Profit Factor     | {cm['profit_factor']:.2f} |",
        f"| Expectancy/trade  | {cm['expectancy']:+.2f}% |",
        f"| Sharpe (ann.)     | {cm['sharpe']:.2f} |",
        f"| Sortino (ann.)    | {cm['sortino']:.2f} |",
        f"| Max Drawdown      | {cm['max_dd']:.1f}% |",
        f"| Binomial Z-stat   | {cm['z_stat']:.2f} (p={cm['p_value']:.4f}) |",
        "",
        f"**Inter-stock avg ρ** : {adj_z.get('avg_rho', 0):.3f}  "
        f"| **Adj. Z** : {adj_z.get('z_adj', 0):.2f}  "
        f"| **Adj. p** : {adj_z.get('p_adj', 1):.4f}",
    ]

    # OOS
    if optim_results:
        oos_m = optim_results.get("oos_metrics", {})
        ratio = optim_results.get("ratio", 0)
        of    = optim_results.get("overfit", True)
        lines += [
            "\n## Walk-Forward Optimisation",
            f"- IS Sharpe  : {optim_results.get('is_sharpe', 0):.2f}",
            f"- OOS Sharpe : {oos_m.get('sharpe', 0):.2f}",
            f"- OOS/IS     : {ratio:.0%}",
            f"- Overfitting: {'⚠ YES — OOS Sharpe < 60% of IS' if of else '✓ No'}",
            "",
            "Best IS parameters:",
        ]
        if optim_results.get("grid_results"):
            bp = optim_results["grid_results"][0]["params"]
            for k, v in bp.items():
                if k in ("sl_mult","tp_mult_long","adx_long","adx_short",
                         "rsi_pb_lo","rsi_pb_hi","vol_mult_long"):
                    lines.append(f"  - {k}: {v}")

    # Monte Carlo
    if mc_result:
        lines += [
            "\n## Monte Carlo (10 000 simulations, combined trades)",
            f"- Median final equity : {mc_result['median_final_equity']:.1f}",
            f"- 5th pct equity      : {mc_result['p5_final_equity']:.1f}",
            f"- 95th pct max DD     : {mc_result['p95_max_drawdown']:.1f}%",
            f"- % profitable paths  : {mc_result['pct_profitable']:.1f}%",
        ]

    # Verdict
    sh = cm["sharpe"]
    wr = cm["win_rate"]
    pf = cm["profit_factor"]
    sig = adj_z.get("p_adj", 1) < 0.05

    if sh > 0.8 and pf > 1.3 and wr > 50 and sig:
        verdict = "✅ PROMISING — strategy shows positive edge. Recommend paper-trading before going live."
    elif sh > 0.4 and pf > 1.1:
        verdict = "⚠ MARGINAL — some edge present but not statistically robust. Further refinement needed."
    else:
        verdict = "❌ INSUFFICIENT EDGE — strategy does not show reliable statistical edge on historical data."

    lines += [
        "\n## Overall Verdict",
        verdict,
        "",
        "## Key Risks",
        "- NSE-specific risks: circuit breakers, settlement delays, SEBI rule changes.",
        "- Strategy tested on daily bars (not 3H); execution may differ on live 3H data.",
        "- SL/TP fills assumed at exact levels — slippage may be worse in practice.",
        "- Short selling in India requires F&O or margin; many retail accounts cannot short stocks directly.",
        "- Parameter fragility: check sensitivity charts — fragile params need wider search or removal.",
        "",
        "## Suggested Improvements",
        "1. Re-run on 3H intraday data once yfinance / other data source provides sufficient history.",
        "2. Add a volatility filter (e.g. skip entries when ATR/close ratio is extreme).",
        "3. Consider position-size scaling by ATR so larger-ATR trades risk the same INR amount.",
        "4. Sector rotation: weight allocation by recent relative strength vs Nifty.",
        "5. Test alternative trend filter: use Supertrend or higher-TF MA in place of EMA200.",
    ]

    report_path = os.path.join(RESULTS_DIR, "summary_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  Report saved → {report_path}")


# ── Final summary table ────────────────────────────────────────────────────────
def _print_final_table(available, metrics_dict, combined_metrics) -> None:
    print("\n" + "=" * 110)
    print("  FINAL RESULTS — ALL STOCKS")
    print("=" * 110)

    header = (f"{'Ticker':<16} {'Trades':>6} {'WinRate':>8} "
              f"{'AvgWin':>8} {'AvgLoss':>9} {'PF':>6} "
              f"{'Sharpe':>8} {'Sortino':>8} {'MaxDD':>8} "
              f"{'Expect':>8} {'p-val':>7}")
    print(header)
    print("-" * 110)

    for ticker in available:
        m = metrics_dict.get(ticker, {})
        if not m or m["n_trades"] == 0:
            print(f"  {ticker:<14} — no trades")
            continue
        print(
            f"  {ticker.replace('.NS',''):<14} "
            f"{m['n_trades']:>6} "
            f"{m['win_rate']:>7.1f}% "
            f"{m['avg_win']:>+7.2f}% "
            f"{m['avg_loss']:>+8.2f}% "
            f"{min(m['profit_factor'], 99):>6.2f} "
            f"{m['sharpe']:>8.2f} "
            f"{m['sortino']:>8.2f} "
            f"{m['max_dd']:>7.1f}% "
            f"{m['expectancy']:>+7.2f}% "
            f"{m['p_value']:>7.4f}"
        )

    print("-" * 110)
    cm = combined_metrics
    print(
        f"  {'PORTFOLIO':<14} "
        f"{cm['n_trades']:>6} "
        f"{cm['win_rate']:>7.1f}% "
        f"{cm['avg_win']:>+7.2f}% "
        f"{cm['avg_loss']:>+8.2f}% "
        f"{min(cm['profit_factor'], 99):>6.2f} "
        f"{cm['sharpe']:>8.2f} "
        f"{cm['sortino']:>8.2f} "
        f"{cm['max_dd']:>7.1f}% "
        f"{cm['expectancy']:>+7.2f}% "
        f"{cm['p_value']:>7.4f}"
    )
    print("=" * 110)
    print("\n  All results saved to:  results/")
    print("  All charts saved to:   results/charts/")
    print()


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NSE Swing Backtester")
    parser.add_argument("--force-download", action="store_true",
                        help="Re-download all data even if cache exists")
    parser.add_argument("--skip-optim", action="store_true",
                        help="Skip walk-forward optimisation")
    args = parser.parse_args()

    main(force_download=args.force_download,
         skip_optim=args.skip_optim)
