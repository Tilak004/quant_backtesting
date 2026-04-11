# NSE Swing Trading System

A complete end-to-end swing trading system for NSE (National Stock Exchange of India) built in three layers:
**Pine Script** for visual chart analysis → **Python backtester** for strategy validation → **Alert bot** for automated daily screening.

---

## What this does

| Layer | Tool | Purpose |
|---|---|---|
| Visual | TradingView Pine Script | See signals, EMA mesh, SL/TP lines live on any NSE chart |
| Validation | Python backtester | Test the strategy on 10 years of daily data across 185 stocks |
| Automation | Python alert bot | Scan all stocks every morning, email signals with trade levels |

The bot emails you every weekday at 11 AM with any stocks that fired a signal — entry price, stop loss, take profit, conviction score. You open the chart, confirm with your own TA, and place the trade manually.

---

## Strategy logic

The strategy is a **trend-following swing system** based on three entry types, all requiring a confirmed bull/bear trend first.

### Trend filter — all four must be true
- EMA 21 > EMA 50 (green mesh)
- EMA 50 > EMA 200 (above long-term trend)
- EMA 21 slope rising over 5 bars
- EMA 50 slope rising over 5 bars

### Entry signals (longs)
| Signal | Trigger |
|---|---|
| **PB-L** | Price pulls back to touch EMA 21, closes above it with a bullish candle |
| **PB50-L** | Deeper pullback to EMA 50, closes above with a bullish candle |
| **BO-L** | Price breaks out above the 12-bar swing high with a strong close |

### Quality filters
- ADX ≥ 12 — trend has enough strength
- Volume ≥ 1.1× 20-day average — institutional participation confirmed
- RSI in healthy zone — not overbought at entry
- Candle closes in top 50% of day's range

### Risk management (Walk-Forward Optimised)
- **Stop Loss** — Entry − ATR × 1.5
- **Take Profit** — Entry + ATR × 3.5
- **Risk/Reward** — ~1:2.33 on average
- ATR (Average True Range) is used so volatile stocks get proportionally wider levels

### Conviction score (0–6)
Each of these adds 1 point: bull trend active · ADX confirmed · volume confirmed · RSI in zone · bullish candle · price above weekly EMA 50.

---

## Backtest results (2019–2026, 185 NSE stocks, daily bars)

| Metric | Value |
|---|---|
| Total trades | 2,484 |
| Win rate | 50.5% |
| Avg win / avg loss | +8.16% / −5.44% |
| Profit factor | 1.53 |
| Expectancy per trade | +1.43% |
| Sharpe ratio (ann.) | 3.23 |
| Sortino ratio (ann.) | 13.54 |
| Walk-forward OOS/IS | 99% — no overfitting |
| Monte Carlo profitable | 100% of 10,000 simulations |

**Top performers:** ALKYLAMINE, WIPRO, TECHM, BHARTIARTL, PERSISTENT, BHEL, CANBK

**Excluded from live alerts** (statistically significant negative edge): CIPLA, KOTAKBANK, ACC, SHREECEM, ZEEL

---

## Project structure

```
├── pine_script.pine          # TradingView strategy (3H timeframe)
├── data.py                   # Download historical data from Yahoo Finance
├── indicators.py             # EMA, RSI, ADX, ATR, Volume, Weekly EMA computation
├── backtester.py             # Bar-by-bar backtest engine
├── optimization.py           # Walk-forward + grid search optimiser
├── analysis.py               # Statistics: Sharpe, Sortino, drawdown, Monte Carlo
├── charts.py                 # Result visualisations
├── main.py                   # Run the full backtest pipeline
│
├── bot/
│   ├── universe.py           # Stock watchlist — edit this to add/remove stocks
│   ├── config.py             # Strategy parameters (WFO best-fit)
│   ├── signal_engine.py      # Detect signals on today's bar
│   ├── screener.py           # Fetch data + scan all stocks
│   ├── notifier.py           # Build and send HTML email alerts
│   ├── main.py               # Run a scan immediately
│   └── scheduler.py          # Auto-fire at 11 AM IST Mon–Fri
│
├── run_screener.bat          # Windows Task Scheduler launcher
├── requirements.txt          # Backtest dependencies
├── requirements_bot.txt      # Bot additional dependencies
└── .env.example              # Email credentials template (copy → .env, never commit)
```

---

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
pip install -r requirements_bot.txt
```

### 2. Configure email credentials
```bash
# Copy the template
copy .env.example .env

# Edit .env and fill in:
# GMAIL_SENDER       — Gmail address that sends alerts
# GMAIL_APP_PASS     — 16-char App Password (myaccount.google.com/apppasswords)
# ALERT_RECIPIENTS   — comma-separated recipient addresses
```

### 3. Run the backtester
```bash
python main.py
```
Results are saved to `results/` — trade CSVs, charts, and a summary report.

### 4. Run the alert bot

**Single scan (now):**
```bash
python bot/main.py
```

**Dry run (no email):**
```bash
python bot/main.py --dry-run
```

**Test specific tickers:**
```bash
python bot/main.py --tickers WIPRO.NS PERSISTENT.NS --dry-run
```

**Start daily scheduler (11 AM IST, Mon–Fri):**
```bash
python bot/scheduler.py
```

**Auto-start on Windows login (Task Scheduler):**
Add `run_screener.bat` as a Task Scheduler trigger at login/startup.

---

## Adding more stocks

Open `bot/universe.py` and append tickers to the relevant section:
```python
"ZOMATO.NS", "PAYTM.NS", "DELHIVERY.NS",   # add here
```
Tickers must use Yahoo Finance format with `.NS` suffix.

---

## Important notes

- **Timeframe mismatch:** The Pine Script is tuned for 3H bars; the backtester uses daily bars (yfinance only provides free intraday data for the last 60 days). Use the bot alert to identify *which* stock to look at, then open the 3H chart on TradingView to time the actual entry.
- **Short selling:** Backtest includes short signals, but NSE short selling requires F&O or margin account. The bot reports short signals but you decide if your account supports it.
- **Not financial advice:** This is a quantitative research and learning project. Always do your own analysis before placing any trade.

---

## Data source

Historical data is fetched from **Yahoo Finance** via `yfinance` using `.NS` suffixed tickers (e.g. `WIPRO.NS`). No NSE subscription or scraping required.

---

## License

MIT — free to use, modify, and share.
