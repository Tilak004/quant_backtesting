# NSE Swing Strategy — Backtest Summary Report

Generated on: 2026-04-11 12:31

## Universe
HDFCBANK, INFY, ICICIBANK, SBIN, WIPRO, SUNPHARMA, LT, BHARTIARTL, DIXON, BSE, CANBK, BEL, HAL, TITAN, BAJFINANCE, HCLTECH, TRENT, PERSISTENT, SIEMENS, RELIANCE, NTPC, ONGC, POWERGRID, ITC, NESTLEIND, BRITANNIA, M&M, MARUTI, HEROMOTOCO, TATASTEEL, JINDALSTEL, HINDALCO, COALINDIA, CIPLA, DRREDDY, APOLLOHOSP, ETERNAL, TATAELXSI, KPITTECH, KOTAKBANK, AXISBANK, INDUSINDBK, BANDHANBNK, BAJAJFINSV, CHOLAFIN, MUTHOOTFIN, TCS, TECHM, MPHASIS, LTIM, COFORGE, OFSS, ABB, BHEL, CUMMINSIND, THERMAX, POLYCAB, KEI, PIDILITIND, AARTIIND, NAVINFLUOR, ALKYLAMINE, HAVELLS, VOLTAS, VGUARD, DMART, NYKAA, TORNTPHARM, AUROPHARMA, LALPATHLAB, METROPOLIS, IPCALAB, BPCL, IOC, GAIL, TATAPOWER, ADANIGREEN, ADANIPORTS, HDFCLIFE, SBILIFE, ICICIGI, ULTRACEMCO, SHREECEM, AMBUJACEM, ACC, INDUSTOWER, IDEA, ZEEL

## Combined Portfolio (all stocks, default params, 2019–2026)

| Metric            | Value           |
|-------------------|-----------------|
| Total Trades      | 2484 |
| Win Rate          | 50.5% |
| Avg Win           | +8.16% |
| Avg Loss          | -5.44% |
| Win/Loss Ratio    | 1.50 |
| Profit Factor     | 1.53 |
| Expectancy/trade  | +1.43% |
| Sharpe (ann.)     | 3.23 |
| Sortino (ann.)    | 13.54 |
| Max Drawdown      | -98.2% |
| Binomial Z-stat   | 0.48 (p=0.6301) |

**Inter-stock avg ρ** : 0.051  | **Adj. Z** : 0.21  | **Adj. p** : 0.8369

## Walk-Forward Optimisation
- IS Sharpe  : 3.42
- OOS Sharpe : 3.38
- OOS/IS     : 99%
- Overfitting: ✓ No

Best IS parameters:
  - sl_mult: 1.5
  - tp_mult_long: 3.5
  - adx_long: 12
  - adx_short: 20
  - rsi_pb_lo: 35
  - rsi_pb_hi: 58
  - vol_mult_long: 1.1

## Monte Carlo (10 000 simulations, combined trades)
- Median final equity : 445788343887799.9
- 5th pct equity      : 1518187690009.7
- 95th pct max DD     : -53.2%
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