# CLAUDE.md — NSE Swing Trading System

## Project overview

Three-tier quantitative trading system for NSE (Indian equities):

1. **Backtester** (`main.py` + `backtester.py`) — validates strategy on ~9.5 years (2016-10 — 2026-04) of daily OHLCV across 869 stocks
2. **Live screener** (`bot/`) — scans 2,258 NSE stocks each morning, emails actionable signals
3. **Dashboard** (`dashboard.py`) — Streamlit UI for signals, scorecard, patterns, fundamentals

## Entry points

| File | Purpose | How to run |
|---|---|---|
| `main.py` | Full backtest pipeline | `python main.py` |
| `pipeline.py` | Unified Typer CLI | `python pipeline.py [backtest\|screen\|both\|config]` |
| `bot/main.py` | Live screener + email | `python bot/main.py [--dry-run] [--tickers X.NS]` |
| `dashboard.py` | Streamlit dashboard | `streamlit run dashboard.py` |
| `test_fundamental.py` | Fundamental scorer smoke test | `python test_fundamental.py` |
| `tests/` | Pytest suite | `pytest tests/` |

## Configuration

`config/strategy.yaml` is the **single source of truth** for all strategy parameters (RSI thresholds, ADX minimum, ATR multipliers, position sizing, execution costs, backtest fill model under `execution:`, pre-registered edge-check criteria under `edge_check:`). It is versioned and loaded via `core/config.py` (`StrategyConfig` Pydantic model).

**Never hardcode strategy parameters in Python files.** Always read from `core/config.py` via `load_config()`.

## Architecture rules

- **No lookahead bias** — all indicators in `indicators.py` and `core/patterns.py` are strictly causal (only use data available at bar `t` to produce values at bar `t`). Never use `.shift(-n)` or future prices.
- **Cache layer** — use `core/data.py` (`fetch_or_load()`) for all data fetching, not raw `yfinance` calls. Both the backtester and live screener share this layer to guarantee identical data.
- **Append-only audit logs** — `core/logging.py` writes one row per backtest run / signal / data fetch to `logs/`. Never truncate these files.
- **Config hash** — each audit log row includes a config version hash so results are traceable to the exact parameter set.
- **Config version** — `config_version` is a first-class field on `StrategyConfig` (read from top-level key in `strategy.yaml`). Audit logs write the real version (e.g. `"1.3"`), not a hardcoded default. Bump `config_version` in `strategy.yaml` whenever any parameter changes.
- **NaN bar handling** — the backtester force-closes any open position that hits a NaN indicator bar, recording exit reason `DATA_GAP`. Positions are never left orphaned.
- **Pandas 2.0 compat** — use `.reindex(idx).ffill()` not `.reindex(idx, method="ffill")`. Use `df = df.ffill().dropna()` not `inplace=True`.

## Key modules — where things live

| What you need | File |
|---|---|
| Signal detection logic | `bot/signal_engine.py` (live bar), `backtester.py` (historical) |
| Indicator computation | `indicators.py` |
| Chart pattern detection | `core/pattern_scanner.py` (11+ patterns), `core/patterns.py` (S/R, pivots) |
| Fundamental quality score | `core/fundamental_scorer.py` |
| ML scoring | `core/ml/xgb_scorer.py`, `core/ml/feature_builder.py` |
| Stock universe | `bot/universe.py` (live), `data.py` (backtest ticker list) |
| Historical performance lookup | `core/scorecard.py` |
| Email alert builder | `bot/notifier.py` |
| Paper trading | `core/paper_trader.py` |
| Walk-forward optimisation | `optimization.py` |
| Monte Carlo projection (portfolio daily-return bootstrap, summary, fan chart) | `montecarlo.py`, `charts.py` (`plot_mc_fan`) |
| Portfolio replay (capital limit, liquidity) | `core/portfolio.py`, `tools/run_portfolio.py` |
| Backtest fill model (entry/exit fills, gaps) | `backtester.py` (`execution:` in `strategy.yaml`) |
| Shared backtest input prep (cache, indicators, regime) | `core/backtest_inputs.py` |
| Edge reality check (fill scenarios, cost headroom, verdict) | `tools/edge_reality_check.py` |
| Full parameter inventory | `docs/PARAMETERS.md` |

## Data

- Source: Yahoo Finance via `yfinance`, tickers use `.NS` suffix (e.g. `WIPRO.NS`)
- Daily OHLCV cache: `data/raw/` (auto-created)
- Fundamental cache: `data/fundamentals/` JSON per ticker, refreshed every 90 days
- Backtest universe: 869 NSE stocks defined in `data.py`, grouped by sector
- Screener universe: 2,258 stocks from `stocks_list.csv`

## Email alerts

Requires a `.env` file in the project root (never commit this):
```
GMAIL_SENDER=you@gmail.com
GMAIL_APP_PASS=xxxx xxxx xxxx xxxx   # 16-char Google App Password
ALERT_RECIPIENTS=you@gmail.com,other@gmail.com
```

Copy `.env.example` → `.env` and fill in values.

## Testing

```bash
pytest tests/                  # unit tests (config, data, logging, signals)
python test_fundamental.py     # fundamental scorer integration test
python main.py                 # full backtest = integration test for the engine
python tools/run_portfolio.py  # portfolio replay with a real capital limit
python tools/edge_reality_check.py  # fill-scenario verdict (~25 min; --limit N to smoke-test)
ruff check .                   # linting (pip install ruff; zero errors expected; vendor/ and .claude/ excluded in ruff.toml)
```

## Known measurement traps

- **Per-ticker backtest ≠ a real account.** `backtester.py` runs one ticker at a
  time with no portfolio limit. Pooling per-ticker results implies ~115
  concurrent positions and ~2,237% of equity deployed. Any figure describing a
  real account must come from `core/portfolio.py`.
- **Trade-based Sharpe is inflated.** `analysis.py` annualises by
  `sqrt(trades_per_year)`, which is only valid for sequential non-overlapping
  trades. With overlapping correlated positions it overstates Sharpe by roughly
  `sqrt(concurrent positions)`. Realistic portfolio Sharpe is ~1.0-1.3.
- **`results/trades_OOS_best.csv` is not a per-ticker file.** It is the
  optimiser's aggregate under a *different* parameter set, and ~56% of its rows
  duplicate trades in the per-ticker CSVs. Exclude it when globbing
  `trades_*.csv` (`core/ml/feature_builder.py` does).
- **Slippage of 0.05%/side is optimistic** for the illiquid tail of the universe.
  The edge disappears near 1% round-trip. Check with `tools/liquidity_screen.py`.
- **Never Monte Carlo by chaining per-trade returns.** Compounding trades one
  after another reproduces the ~22x pooled leverage (old 10^22 equity
  figures). `run_monte_carlo_portfolio()` block-bootstraps the
  capital-limited portfolio's daily returns; the summary and fan chart must
  both come from those paths. Spec: `openspec/specs/monte-carlo-projection/`.
- **Ranking trades by an in-sample model is lookahead.** Use
  `walk_forward_scores()` from `core/ml/xgb_scorer.py`, never the production
  model's own scores, when a score decides which trades to take.
- **The default fill model is optimistic, and the edge FAILS without it.**
  `execution.entry_fill: signal_close` / `exit_fill: close_at_level` fill at
  the signal bar's own close and book SL at the stop even when price gapped
  through. Under next-open entry + gap-aware intraday exits (config 1.6,
  `tools/edge_reality_check.py`) the pre-registered verdict is **FAILS**:
  one-account CAGR -17.8%, Sharpe -0.65, max DD -89% at 0.15%/side slippage,
  vs baseline +22.0% / 1.01 and Nifty price CAGR 11.5%. Negative in both
  2016-20 and 2021+. Mean P&L per trade falls from +1.64% (baseline) to
  +0.30% (realistic, 0.05% slippage), ~+0.1% at 0.15%.
  **Cost headroom is nil**: realistic CAGR is already negative at 0.05%/side;
  baseline falls to the benchmark at ~0.37%/side. Only the >= Rs 25 cr/day
  causal-liquidity subset stays positive (CAGR 6.6%, Sharpe 0.43, still below
  benchmark). Any result produced in default fill modes overstates the edge.
  Report: `results/edge_check/edge_reality_report.md`.
  **Next step (pre-registered rule for FAILS):** pause the live-signal and
  paper-ledger work; do not build parity/ops on this strategy. Research new
  entries/exits under the realistic fill model (start from the liquid subset),
  and judge them with the same tool before any live use.

## What NOT to do

- Don't commit `.env` (contains Gmail credentials). It was tracked and pushed
  once already because `.gitignore` had an **inline comment** on the `.env` line
  — `#` only starts a comment at the START of a line, so the pattern matched
  nothing. Never put trailing comments on a `.gitignore` pattern.
- Don't hardcode RSI/ADX/ATR values in Python — use `config/strategy.yaml`
- Don't add lookahead bias to indicators (no future data, no `.shift(-n)`)
- Don't call `yfinance` directly in new code — go through `core/data.py`
- Don't truncate or delete files in `logs/` — they are append-only audit trails
- Don't swallow exceptions silently (`except Exception: pass`) — at minimum `warnings.warn(str(e))`
- Don't use `reindex(method="ffill")` or `inplace=True` — both deprecated in pandas 2.0
- Don't use `open(path)` without a context manager — always `with open(path) as f:`
- Don't count breakeven trades (`pnl_pct == 0`) as losses — use `< 0` not `<= 0` for loss filters
