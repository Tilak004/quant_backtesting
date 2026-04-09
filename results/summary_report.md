# NSE Swing Strategy — Backtest Summary Report

Generated on: 2026-04-08 22:13

## Universe
HDFCBANK, INFY, ICICIBANK, SBIN, WIPRO, SUNPHARMA, LT, BHARTIARTL, DIXON, BSE, CANBK, BEL, HAL, TITAN, BAJFINANCE, HCLTECH, TRENT, PERSISTENT, SIEMENS, RELIANCE, NTPC, ONGC, POWERGRID, ITC, NESTLEIND, BRITANNIA, M&M, MARUTI, HEROMOTOCO, TATASTEEL, JINDALSTEL, HINDALCO, COALINDIA, CIPLA, DRREDDY, APOLLOHOSP, TATAELXSI, KPITTECH

## Combined Portfolio (all stocks, default params, 2019–2026)

| Metric            | Value           |
|-------------------|-----------------|
| Total Trades      | 1131 |
| Win Rate          | 53.0% |
| Avg Win           | +7.68% |
| Avg Loss          | -5.15% |
| Win/Loss Ratio    | 1.49 |
| Profit Factor     | 1.68 |
| Expectancy/trade  | +1.65% |
| Sharpe (ann.)     | 2.66 |
| Sortino (ann.)    | 10.77 |
| Max Drawdown      | -79.1% |
| Binomial Z-stat   | 1.99 (p=0.0463) |

**Inter-stock avg ρ** : 0.068  | **Adj. Z** : 1.06  | **Adj. p** : 0.2880

## Walk-Forward Optimisation
- IS Sharpe  : 2.35
- OOS Sharpe : 3.03
- OOS/IS     : 129%
- Overfitting: ✓ No

Best IS parameters:
  - sl_mult: 2.0
  - tp_mult_long: 3.5
  - adx_long: 12
  - adx_short: 20
  - rsi_pb_lo: 35
  - rsi_pb_hi: 62
  - vol_mult_long: 1.1

## Monte Carlo (10 000 simulations, combined trades)
- Median final equity : 812587143.4
- 5th pct equity      : 20376678.5
- 95th pct max DD     : -39.9%
- % profitable paths  : 100.0%

## Overall Verdict
⚠ MARGINAL — some edge present but not statistically robust. Further refinement needed.

## Key Risks
- NSE-specific risks: circuit breakers, settlement delays, SEBI rule changes.
- Strategy tested on daily bars (not 3H); execution may differ on live 3H data.
- SL/TP fills assumed at exact levels — slippage may be worse in practice.
- Short selling in India requires F&O or margin; many retail accounts cannot short stocks directly.
- Parameter fragility: check sensitivity charts — fragile params need wider search or removal.

## Suggested Improvements
1. Re-run on 3H intraday data once yfinance / other data source provides sufficient history.
2. Add a volatility filter (e.g. skip entries when ATR/close ratio is extreme).
3. Consider position-size scaling by ATR so larger-ATR trades risk the same INR amount.
4. Sector rotation: weight allocation by recent relative strength vs Nifty.
5. Test alternative trend filter: use Supertrend or higher-TF MA in place of EMA200.