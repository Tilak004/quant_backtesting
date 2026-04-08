# NSE Swing Strategy — Backtest Summary Report

Generated on: 2026-04-08 15:44

## Universe
RELIANCE, HDFCBANK, INFY, ICICIBANK, SBIN, WIPRO, SUNPHARMA, LT, BHARTIARTL, DIXON, BSE, CANBK, BEL, HAL, TITAN, BAJFINANCE, HCLTECH, KOTAKBANK, TRENT, PERSISTENT, POLYCAB, SIEMENS

## Combined Portfolio (all stocks, default params, 2019–2026)

| Metric            | Value           |
|-------------------|-----------------|
| Total Trades      | 586 |
| Win Rate          | 55.5% |
| Avg Win           | +7.90% |
| Avg Loss          | -5.20% |
| Win/Loss Ratio    | 1.52 |
| Profit Factor     | 1.89 |
| Expectancy/trade  | +2.07% |
| Sharpe (ann.)     | 2.86 |
| Sortino (ann.)    | 12.25 |
| Max Drawdown      | -73.9% |
| Binomial Z-stat   | 2.64 (p=0.0082) |

**Inter-stock avg ρ** : 0.076  | **Adj. Z** : 1.64  | **Adj. p** : 0.1004

## Walk-Forward Optimisation
- IS Sharpe  : 2.89
- OOS Sharpe : 2.55
- OOS/IS     : 88%
- Overfitting: ✓ No

Best IS parameters:
  - sl_mult: 1.5
  - tp_mult_long: 3.0
  - adx_long: 12
  - adx_short: 20
  - rsi_pb_lo: 35
  - rsi_pb_hi: 62
  - vol_mult_long: 1.05

## Monte Carlo (10 000 simulations, combined trades)
- Median final equity : 4201357.8
- 5th pct equity      : 291880.2
- 95th pct max DD     : -31.4%
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