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
from tqdm import tqdm

# ── Import project modules ────────────────────────────────────────────────────
from data         import download_all_data, TICKERS, NIFTY_TICKER
from indicators   import prepare_indicators
from backtester   import run_backtest
from core.config  import load_config
from core.logging import log_backtest_run
from core.backtest_inputs import build_regime
from analysis     import (compute_metrics, compute_equity_curve,
                          compute_portfolio_equity, breakdown_by_exit, breakdown_by_signal,
                          breakdown_by_year, breakdown_by_regime,
                          adjusted_z_test, build_trade_return_matrix,
                          nifty_rolling_corr, print_metrics)
from optimization import run_grid_search, run_oos_evaluation, sensitivity_analysis
from montecarlo   import run_monte_carlo_portfolio, print_mc_summary
from core.portfolio import simulate_portfolio
from charts       import (plot_equity_curves, plot_drawdown,
                          plot_monthly_heatmap, plot_winrate_by_year,
                          plot_pf_by_signal, plot_trade_distribution,
                          plot_mc_fan, plot_sensitivity,
                          plot_correlation_heatmap, plot_nifty_corr,
                          plot_per_stock_summary)

warnings.filterwarnings("ignore")

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

    # Shared with tools/edge_reality_check.py so both feed identical inputs.
    nifty_ind, nifty_regime = build_regime(nifty_raw)
    if nifty_regime is not None:
        pct_bull = nifty_regime.mean() * 100
        print(f"  Nifty regime filter : {pct_bull:.0f}% of bars in bull regime (Nifty > EMA200)")

    # ── STAGE 3: Backtest ─────────────────────────────────────────────────────
    _hdr(3, "Running Backtest (default parameters)")
    all_trades:     dict[str, pd.DataFrame] = {}
    equity_curves:  dict[str, pd.Series]    = {}
    metrics_dict:   dict[str, dict]         = {}

    for ticker in tqdm(available, desc="  Backtesting", ncols=70):
        try:
            trades = run_backtest(ind_dfs[ticker], ticker=ticker,
                                  market_regime=nifty_regime)
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

    run_id = log_backtest_run(
        n_trades=combined_metrics["n_trades"],
        sharpe=combined_metrics["sharpe"],
        win_rate=combined_metrics["win_rate"],
        profit_factor=combined_metrics["profit_factor"],
        max_dd=combined_metrics["max_dd"],
        start_date="2016-01-01",
        end_date="2026-04-30",
        results_path=RESULTS_DIR,
    )
    print(f"\n  [LOG] Backtest run logged  run_id={run_id[:8]}…")

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
    best_params = load_config().to_params_dict()
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

    # ── STAGE 7: Portfolio Replay & Monte Carlo ───────────────────────────────
    _hdr(7, "Portfolio Replay & Monte Carlo")
    port_result = None
    mc_result   = None
    _cfg     = load_config()
    _mc_init = _cfg.starting_capital
    try:
        if not combined_df.empty:
            # The capital-constrained replay is the only figure here that
            # describes a real account: one book of starting_capital rupees,
            # max_positions slots, round-trip costs deducted at exit, and profits
            # compounding into the size of later positions. Anything pooled from
            # the per-ticker runs instead implies ~115 concurrent positions at
            # ~19.5% of equity each, i.e. roughly 22x leverage.
            port_result = simulate_portfolio(combined_df)
            pm = port_result.metrics
            n_sig = pm["n_taken"] + pm["n_skipped"]
            print(f"  Account      : Rs {_mc_init:,.0f} start, "
                  f"{_cfg.max_positions} slots, {_cfg.max_gross_pct:.0f}% max gross")
            print(f"  Signals      : took {pm['n_taken']:,} of {n_sig:,} "
                  f"({pm['fill_rate']:.1f}% fill)")
            print(f"  CAGR {pm['cagr']:.2f}%   Sharpe {pm['sharpe']:.2f}   "
                  f"MaxDD {pm['max_dd']:.2f}%   TotRet {pm['total_return']:.1f}%")
    except Exception as exc:
        print(f"  [WARN] Portfolio replay failed: {exc}")

    # Separate blocks so one failure does not hide the steps after it. The fan
    # chart (stage 9) is drawn from mc_result even if the summary print fails.
    if port_result is not None:
        try:
            daily = port_result.equity.pct_change().dropna()
            mc_result = run_monte_carlo_portfolio(
                daily.values, horizon_days=250, n_simulations=10_000,
                initial_equity=_mc_init)
        except Exception as exc:
            print(f"  [WARN] Monte Carlo failed: {exc}")
    if mc_result:
        try:
            print_mc_summary(mc_result)
        except Exception as exc:
            print(f"  [WARN] Monte Carlo summary failed: {exc}")

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
        if mc_result:
            plot_mc_fan(mc_result)
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
        optim_results, mc_result, adj, combined_df, port_result
    )

    # ── Final table ───────────────────────────────────────────────────────────
    _print_final_table(available, metrics_dict, combined_metrics)


# ── Summary report writer ─────────────────────────────────────────────────────
def _trade_span(combined_df) -> str:
    """Return the real tested period, e.g. "2016-10 to 2026-04 (9.5 years)".

    Falls back to "period unavailable" rather than inventing a range, so the
    report never states a span the trades do not support.
    """
    if combined_df is None or combined_df.empty:
        return "period unavailable"
    entries = pd.to_datetime(combined_df["entry_date"], errors="coerce").dropna()
    exits   = pd.to_datetime(combined_df["exit_date"],  errors="coerce").dropna()
    if entries.empty:
        return "period unavailable"
    first = entries.min()
    last  = max(entries.max(), exits.max()) if not exits.empty else entries.max()
    years = (last - first).days / 365.25
    return f"{first:%Y-%m} to {last:%Y-%m} ({years:.1f} years)"


def _write_summary_report(available, metrics_dict, combined_metrics,
                           optim_results, mc_result, adj_z, combined_df,
                           port_result=None) -> None:
    cm = combined_metrics
    # Derive the tested period from the trades themselves. It used to be a
    # hardcoded "2019-2026" string, which drifted out of step with the data as
    # the universe and history grew.
    span = _trade_span(combined_df)
    cfg  = load_config()
    lines = [
        "# NSE Swing Strategy — Backtest Summary Report",
        f"\nGenerated on: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}",
        f"\n## Universe\n{', '.join(t.replace('.NS','') for t in available)}",
    ]

    # ── Headline: the account-level result ────────────────────────────────────
    if port_result is not None:
        pm    = port_result.metrics
        n_sig = pm["n_taken"] + pm["n_skipped"]
        lines += [
            f"\n## Account Results — single book, {span}",
            "",
            f"One account of ₹{cfg.starting_capital:,.0f}, at most "
            f"{cfg.max_positions} open positions, {cfg.max_gross_pct:.0f}% max "
            f"gross exposure, {(cfg.commission_pct + cfg.slippage_pct) * 2:.2%} "
            "round-trip costs deducted, profits compounding into later position "
            "sizes. **These are the only numbers in this report that describe a "
            "tradeable account.**",
            "",
            "| Metric            | Value           |",
            "|-------------------|-----------------|",
            f"| CAGR              | {pm['cagr']:.2f}% |",
            f"| Total Return      | {pm['total_return']:.1f}% |",
            f"| Sharpe (ann.)     | {pm['sharpe']:.2f} |",
            f"| Sortino (ann.)    | {pm.get('sortino', 0):.2f} |",
            f"| Max Drawdown      | {pm['max_dd']:.2f}% |",
            f"| Signals taken     | {pm['n_taken']:,} of {n_sig:,} ({pm['fill_rate']:.1f}% fill) |",
            f"| Years             | {pm.get('years', 0):.1f} |",
            "",
            f"Only {pm['fill_rate']:.1f}% of signals are fundable at this capital. "
            "The remainder are skipped for want of a free slot or free cash, so "
            "the per-trade statistics below describe a far larger opportunity set "
            "than any single account can act on.",
        ]

    lines += [
        f"\n## Per-Trade Statistics (all {len(available)} stocks, default params, {span})",
        "",
        "⚠ **Not account figures.** Each ticker is backtested independently with "
        "no shared capital, so ~115 positions can be open at once at ~19.5% of "
        "equity each — roughly 22x leverage. Sharpe here is annualised by "
        "√(trades per year), which overstates it by about √(concurrent "
        "positions), and the drawdown is measured against peaks the account "
        "never reaches. Treat this section as signal quality only.",
        "",
        "",
        "| Metric            | Value           |",
        "|-------------------|-----------------|",
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
        f"| Expectancy t-stat | {cm['z_stat']:.2f} (p={cm['p_value']:.4f}) |",
        "| *(H0: mean return = 0, one-tailed. p < 0.05 = statistically significant edge)* | |",
        "",
    ]
    # adj_z is None when the correlation stage failed. Say so rather than
    # crashing the whole report, which is what used to happen.
    if adj_z:
        lines.append(
            f"**Inter-stock avg ρ** : {adj_z.get('avg_rho', 0):.3f}  "
            f"| **Adj. Z** : {adj_z.get('z_adj', 0):.2f}  "
            f"| **Adj. p** : {adj_z.get('p_adj', 1):.4f}")
    else:
        lines.append("_Correlation-adjusted significance unavailable — "
                     "the correlation stage did not complete._")

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

    # Monte Carlo — block bootstrap on the account's daily returns
    if mc_result:
        init = mc_result["initial_equity"]
        hz   = mc_result["horizon_days"]
        lines += [
            f"\n## Monte Carlo — one year ahead ({mc_result['n_simulations']:,} paths)",
            "",
            f"Moving-block bootstrap ({mc_result['block_days']}-day blocks) over "
            f"the {mc_result['n_observed_days']:,} realised daily returns of the "
            f"account above, projected {hz} trading days forward. Blocks rather "
            "than single days, so volatility clustering survives the resampling.",
            "",
            f"- Starting capital    : ₹{init:,.0f}",
            f"- Median final equity : ₹{mc_result['median_final_equity']:,.0f}  "
            f"({mc_result['median_final_equity']/init - 1:+.1%})",
            f"- 5th pct equity      : ₹{mc_result['p5_final_equity']:,.0f}  "
            f"({mc_result['p5_final_equity']/init - 1:+.1%})",
            f"- 95th pct equity     : ₹{mc_result['p95_final_equity']:,.0f}  "
            f"({mc_result['p95_final_equity']/init - 1:+.1%})",
            f"- Mean max drawdown   : {mc_result['mean_max_drawdown']:.1f}%",
            f"- Worst-5% drawdown   : {mc_result['p95_max_drawdown']:.1f}%",
            f"- % profitable paths  : {mc_result['pct_profitable']:.1f}%",
        ]

    # Verdict — graded on the account-level result, not the pooled per-trade one.
    # Sharpe here is the portfolio Sharpe (~1.0-1.3 realistic), so the threshold
    # is far lower than the inflated trade-based figure would suggest.
    pf  = cm["profit_factor"]
    exp = cm["expectancy"]
    sig_expectancy = cm["p_value"] < 0.05          # t-test on pnl_on_equity > 0

    if port_result is not None:
        sh, dd = port_result.metrics["sharpe"], port_result.metrics["max_dd"]
        if sh > 1.0 and dd > -35.0 and exp > 0 and sig_expectancy:
            verdict = ("✅ PROMISING — account-level Sharpe "
                       f"{sh:.2f} at {dd:.1f}% max drawdown, with a statistically "
                       "significant positive expectancy. Paper-trade before going live.")
        elif sh > 0.5 and exp > 0:
            verdict = (f"⚠ MARGINAL — account-level Sharpe {sh:.2f} at {dd:.1f}% "
                       "max drawdown. Positive but not yet robust enough to size up.")
        else:
            verdict = (f"❌ INSUFFICIENT EDGE — account-level Sharpe {sh:.2f} at "
                       f"{dd:.1f}% max drawdown does not justify the risk.")
    else:
        verdict = ("⚠ NO ACCOUNT-LEVEL RESULT — the portfolio replay did not run, "
                   "so no tradeable figure is available. The per-trade statistics "
                   f"above (profit factor {pf:.2f}, expectancy {exp:+.2f}%) describe "
                   "signal quality only.")

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
