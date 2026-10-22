---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
lastStep: 8
status: 'complete'
completedAt: '2026-04-23'
inputDocuments: ['codebase-exploration']
workflowType: 'architecture'
project_name: 'quant_backtest'
user_name: 'Shast'
date: '2026-04-23'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
- FR1: Unified data layer — single download/cache mechanism shared by backtester and screener
- FR2: Single strategy config source (`config/strategy.yaml`) consumed by backtester, screener, and Pine Script export
- FR3: Backtesting pipeline (data → indicators → backtest → optimization → Monte Carlo → report)
- FR4: Daily screening pipeline (data → indicators → signal detection → email alert)
- FR5: Pipeline CLI — run full backtest, run screener, or run both in sequence
- FR6: Structured audit logging — every backtest run, signal, and data fetch logged to CSV with timestamp + params reference

**Non-Functional Requirements:**
- NFR1: Zero lookahead bias — indicators always causal, never look forward
- NFR2: Consistency — backtester and screener use identical indicator/signal logic from shared modules
- NFR3: Credentials outside version control (.env gitignored, never committed)
- NFR4: Graceful degradation — delisted/missing tickers skipped without crashing pipeline
- NFR5: Single virtualenv — one `requirements.txt` for the entire project
- NFR6: Deterministic replay — any backtest or signal run reproducible given same config + cached data
- NFR7: Operational visibility — when system breaks, root cause diagnosable from logs in minutes

**Scale & Complexity:**
- Primary domain: Python data pipeline / CLI tool (no web UI, no multi-tenancy)
- Complexity level: Medium — single-user desktop, but financially consequential
- Estimated architectural components: 5 (config, data, indicators/signals, backtest engine, screener/notifier)

### Technical Constraints & Dependencies
- Python 3.13, yfinance for market data, ta-lib for technical indicators
- Gmail SMTP with App Password for notifications
- TradingView Pine Script v5 for live charting (manual parameter sync acceptable)
- Windows desktop environment — no cloud deployment required

### Cross-Cutting Concerns Identified
- **Strategy parameters**: defined once in `config/strategy.yaml`, imported by all consumers
- **Ticker universe**: single source (`universe.py` or `stocks_list.csv`) shared by backtester and screener
- **Data caching**: single `data/` layer, one download function, one cache path, timestamped fetches
- **Audit logging**: `logs/backtest_runs.csv`, `logs/signals.csv`, `logs/fetch_log.csv` — immutable, append-only rows
- **Credentials**: `.env` with python-dotenv, gitignored, never hardcoded

### Multi-Agent Perspectives Summary
- **Winston (Architect)**: Single YAML config is the foundational decision. Explicit data contract between backtester and bot is non-negotiable. Don't over-engineer — shared config first, operational maturity follows.
- **Mary (Analyst)**: Parameter governance and audit trail are underweighted. Every live signal must be traceable to the backtest params that validated it. Operational runbook needed.
- **John (PM)**: The one job is "Parameter → Signal → Alert → Record." Ship minimum viable: YAML + CSV logs + consistent params. Don't build an orchestrator.
- **Amelia (Dev)**: YAML config (~2h), structured CSV logging (~5h), cached data fetches (~4h), test suite (~2h). Total ~15h to ship everything. Steps 1–4 in order, non-negotiable test coverage.

## Starter Template Evaluation

### Primary Technology Domain
Python data pipeline / CLI tool — existing codebase refactor, not a greenfield project.
No framework starter applies. Decisions are about module structure and tooling choices.

### Structural Pattern: Flat Package with Domain Separation

Target layout after refactoring:

```
quant_backtest/
├── config/
│   └── strategy.yaml          # Single source of truth for all parameters
├── core/
│   ├── data.py                # Unified data download + cache layer
│   ├── indicators.py          # Shared indicator computation (already exists)
│   ├── universe.py            # Single ticker universe (merged from bot/universe.py)
│   └── signals.py             # Signal detection (merged from bot/signal_engine.py)
├── backtest/
│   ├── engine.py              # Bar-by-bar backtester (from backtester.py)
│   ├── optimization.py        # Walk-forward + grid search
│   ├── montecarlo.py          # Monte Carlo simulation
│   └── analysis.py            # Metrics, breakdowns, charts
├── screener/
│   ├── scanner.py             # Daily screener (from bot/screener.py)
│   └── notifier.py            # HTML email alerts (from bot/notifier.py)
├── logs/
│   ├── backtest_runs.csv      # Immutable audit log of every backtest run
│   ├── signals.csv            # Immutable audit log of every signal fired
│   └── fetch_log.csv          # Data fetch log (timestamp, symbol, hash)
├── data/raw/                  # Cached OHLCV CSVs (already exists)
├── results/                   # Backtest output charts + reports (already exists)
├── .env                       # Credentials — gitignored
├── requirements.txt           # Single merged dep file
└── pipeline.py                # CLI entrypoint: run backtest / screener / both
```

### Tooling Decisions
- Config loading: PyYAML
- Config validation: pydantic v2 (catches bad param values at load time)
- Logging: Python stdlib logging + CSV append for audit trail
- Testing: pytest (no existing test suite — must be added)
- Env management: python-dotenv (already used in bot/)
- Linting: ruff

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- D1: Pydantic v2 `StrategyConfig` model as single validated config object
- D2: Shared `core/data.py` with `fetch_or_load()` — one cache, both consumers
- D3: `.env` gitignored; `data/raw/` gitignored

**Important Decisions (Shape Architecture):**
- D4: Typer CLI for `pipeline.py` with subcommands: `backtest`, `screen`, `both`
- D5: stdlib `csv.writer` for append-only audit logs (no new dependency)

**Deferred Decisions (Post-MVP):**
- Pine Script auto-generation from config (manual sync acceptable for now)
- Multi-strategy support

### Data Architecture

**D1 — Config: Pydantic v2 `StrategyConfig`**
- Format: `config/strategy.yaml` with named sections (entry, exit, filters, universe)
- Loader: `core/config.py` reads YAML → validates via Pydantic v2 model at startup
- Validation catches: type errors, out-of-range values (`rsi_pb_lo < rsi_pb_hi`), missing required fields
- Both `backtest/engine.py` and `screener/scanner.py` receive a `StrategyConfig` object — never a raw dict
- Version field in YAML: `config_version: "1.0"` — bump on any param change

**D2 — Unified Data Layer: `core/data.py`**
- Single function: `fetch_or_load(ticker: str, force: bool = False) -> pd.DataFrame`
- Cache path: `data/raw/{ticker}.csv` (existing location, unchanged)
- Staleness threshold: 24 hours (configurable in `strategy.yaml`)
- All fetches logged to `logs/fetch_log.csv`: `(timestamp, ticker, source, rows, cache_hit, data_hash)`
- Bot `screener/scanner.py` calls `core/data.py` — never calls yfinance directly
- Backtester calls same function — cache is shared

### Security

**D3 — Credentials & Gitignore**
- `.env` holds: `GMAIL_SENDER`, `GMAIL_APP_PASS`, `ALERT_RECIPIENTS`
- `.gitignore` entries added: `.env`, `data/raw/`, `logs/`, `results/`, `__pycache__/`, `*.pyc`
- `data/raw/` excluded from version control (large CSVs, regenerable)
- Loaded via `python-dotenv` in `screener/notifier.py` only — no other module touches credentials

### API & Communication Patterns

**D4 — CLI: Typer subcommands**
```
pipeline backtest          # full backtest pipeline
pipeline backtest --skip-optim
pipeline screen            # run screener + send email
pipeline screen --dry-run  # print signals, no email
pipeline both              # backtest → update config → screen
```
- `pipeline.py` is the single human-facing entrypoint
- Programmatic imports remain available for scripting

### Infrastructure & Deployment

**D5 — Audit Logging: stdlib csv.writer, append-only**
- Three log files, all in `logs/`:
  - `backtest_runs.csv`: `run_id, timestamp, config_version, params_hash, start_date, end_date, n_trades, sharpe, results_path`
  - `signals.csv`: `signal_id, timestamp, ticker, signal_type, direction, entry_price, sl, tp, score, config_version, params_hash, fetch_timestamp`
  - `fetch_log.csv`: `timestamp, ticker, source, rows, cache_hit, data_hash`
- Rows are immutable once written — never updated in place
- `run_id` / `signal_id` = `uuid4()` for traceability

### Decision Impact Analysis

**Implementation Sequence:**
1. `core/config.py` + `config/strategy.yaml` + Pydantic model (unblocks everything else)
2. `core/data.py` unified fetch/cache + `logs/fetch_log.csv`
3. Audit log writers (`logs/backtest_runs.csv`, `logs/signals.csv`)
4. Refactor `backtest/` to consume `StrategyConfig` from `core/config.py`
5. Refactor `screener/` to consume `StrategyConfig` + `core/data.py`
6. `pipeline.py` Typer CLI wiring all stages
7. `.gitignore` + `.env` hygiene
8. pytest suite covering config validation, data layer, signal detection

**Cross-Component Dependencies:**
- `core/config.py` → required by `backtest/engine.py`, `screener/scanner.py`, `pipeline.py`
- `core/data.py` → required by `backtest/engine.py`, `screener/scanner.py`
- `core/signals.py` → required by `backtest/engine.py` AND `screener/scanner.py` (shared signal logic)
- `logs/` writers → required by `backtest/engine.py`, `screener/scanner.py`, `core/data.py`

## Implementation Patterns & Consistency Rules

### Naming Patterns

**Python conventions (all modules):**
- Files and directories: `snake_case` (e.g. `signal_engine.py`, `backtest/`)
- Classes: `PascalCase` (e.g. `StrategyConfig`, `SignalResult`)
- Functions and variables: `snake_case` (e.g. `fetch_or_load`, `rsi_pb_lo`)
- Constants: `UPPER_SNAKE_CASE` (e.g. `CACHE_TTL_HOURS`, `LOG_DIR`)
- Private helpers: leading underscore (e.g. `_compute_atr()`)
- Test files: `tests/test_<module>.py`

**DataFrame column names:** always `snake_case` — never camelCase
**Log CSV column names:** `snake_case`, all lowercase
**Dates:** `pd.Timestamp` internally; ISO string `YYYY-MM-DD` in CSVs and logs

### Structure Patterns

**Module import layering — no circular imports:**
```
config  ←  core  ←  backtest
                 ←  screener
pipeline imports all of the above
```
- `core/` NEVER imports from `backtest/` or `screener/`
- `backtest/` NEVER imports from `screener/` and vice versa
- `pipeline.py` is the only file that imports from both

**Config loading — always via `core/config.py`:**
```python
# CORRECT:
from core.config import load_config
cfg = load_config()   # returns validated StrategyConfig

# WRONG — never parse YAML directly anywhere else:
import yaml
params = yaml.safe_load(open("config/strategy.yaml"))
```

**Data fetching — always via `core/data.py`:**
```python
# CORRECT:
from core.data import fetch_or_load
df = fetch_or_load("RELIANCE.NS")

# WRONG — never call yfinance directly from screener or backtest:
import yfinance as yf
df = yf.download("RELIANCE.NS")
```

### Format Patterns

**Signal return type** — always a dataclass, never a raw dict:
```python
@dataclass
class SignalResult:
    ticker: str
    signal_type: str        # "PB-L" | "PB50-L" | "BO-L" | "PB-S" | "BO-S"
    direction: str          # "long" | "short"
    entry_price: float
    sl: float
    tp: float
    score: int              # 0–6
    bar_date: pd.Timestamp
```

**Log rows** — written as dicts to `csv.DictWriter`, keys match column names exactly

### Process Patterns

**Error handling:**
- Pipeline stages: catch per-ticker, log warning, continue — never crash the full run
- Config loading: let `pydantic.ValidationError` propagate — fail fast at startup
- Data fetch: retry once on network error, then skip ticker with WARNING log
- Email: catch SMTP errors, write `status=FAILED` row to `logs/signals.csv`

**Logging levels:**
- `INFO` — stage start/end, tickers processed, signals found
- `WARNING` — skipped tickers, cache misses, retried fetches
- `ERROR` — failed stages, uncaught exceptions (never silently swallowed)
- `DEBUG` — per-bar calculations (off by default)

**Idempotency:** Running `pipeline screen` twice on the same day appends duplicate rows — deduplication is the consumer's responsibility. Never delete or update existing log rows.

### Test Patterns

```
tests/
├── test_config.py       # Pydantic validation, bad params, missing fields
├── test_data.py         # cache hit/miss, fetch logging, staleness
├── test_signals.py      # known OHLCV bar → expected signal type
├── test_backtest.py     # known trade sequence → expected metrics
└── test_notifier.py     # email rendering (no actual send)
```
- Backtester/signal tests use fixed synthetic OHLCV data — never live data
- No mocking of `core/data.py` in integration tests — use real cache

### All AI Agents MUST:
1. Import config only via `core/config.py` — never parse YAML directly
2. Import data only via `core/data.py` — never call yfinance directly
3. Return typed dataclasses from signal/trade functions — never raw dicts
4. Write audit log rows via the shared log writer — never open CSVs directly
5. Follow module layering — no circular imports
6. Add pytest tests for every new function in `core/`, `backtest/`, `screener/`
7. Use `snake_case` for all identifiers and CSV column names

## Project Structure & Boundaries

### Complete Project Directory Structure

```
quant_backtest/
│
├── config/
│   └── strategy.yaml          # D1 — single source of truth for all strategy params
│                              #       sections: entry, exit, filters, universe, system
│
├── core/                      # Shared layer — imported by both backtest/ and screener/
│   ├── __init__.py
│   ├── config.py              # load_config() → StrategyConfig (Pydantic v2 model)
│   ├── data.py                # fetch_or_load(ticker, force) → pd.DataFrame
│   ├── indicators.py          # prepare_indicators(df) → df with all TA columns
│   ├── signals.py             # detect_signals(df, cfg) → list[SignalResult]
│   ├── universe.py            # load_universe() → list[str]
│   └── logging.py             # get_logger(), CSV audit log writers
│
├── backtest/
│   ├── __init__.py
│   ├── engine.py              # run_backtest(df, cfg) → list[TradeResult]
│   ├── analysis.py            # compute_metrics, breakdowns, equity curves
│   ├── optimization.py        # run_grid_search, run_oos_evaluation
│   ├── montecarlo.py          # run_monte_carlo_portfolio, print_mc_summary
│   └── charts.py              # all 11 chart generators
│
├── screener/
│   ├── __init__.py
│   ├── scanner.py             # scan_universe(cfg) → list[SignalResult]
│   └── notifier.py            # send_alert(signals, cfg) → None
│
├── logs/                      # append-only CSV audit trail (gitignored)
│   ├── backtest_runs.csv
│   ├── signals.csv
│   └── fetch_log.csv
│
├── data/
│   └── raw/                   # cached OHLCV CSVs — gitignored
│       └── {TICKER}.csv
│
├── results/                   # backtest outputs — gitignored
│   ├── charts/
│   ├── trades_*.csv
│   └── summary_report.md
│
├── tests/
│   ├── conftest.py            # shared fixtures: synthetic OHLCV, sample StrategyConfig
│   ├── test_config.py
│   ├── test_data.py
│   ├── test_signals.py
│   ├── test_backtest.py
│   └── test_notifier.py
│
├── pipeline.py                # Typer CLI: backtest / screen / both subcommands
├── requirements.txt           # single merged dep file
├── .env                       # credentials — GITIGNORED
├── .env.example               # safe template committed to repo
├── .gitignore
└── pine_script.pine           # TradingView reference — manual sync
```

### Architectural Boundaries

**Module Layering:**
```
┌─────────────────────────────────────────┐
│              pipeline.py                │  ← only human-facing entrypoint
└──────────┬──────────────────┬───────────┘
           │                  │
    ┌──────▼──────┐    ┌──────▼──────┐
    │  backtest/  │    │  screener/  │
    └──────┬──────┘    └──────┬──────┘
           └────────┬─────────┘
              ┌─────▼──────┐
              │   core/    │  ← config, data, indicators, signals, universe
              └────────────┘
```

**Data Flow — Backtest Pipeline:**
```
strategy.yaml → core/config.py → StrategyConfig
data/raw/*.csv ← core/data.py ──────────────────┐
                                                 ▼
                               core/indicators.py → DataFrame
                                                 ▼
                               backtest/engine.py → list[TradeResult]
                                    ▼             ▼              ▼
                             analysis.py   optimization.py   charts.py
                                    ▼
                          logs/backtest_runs.csv
```

**Data Flow — Screening Pipeline:**
```
strategy.yaml → core/config.py → StrategyConfig
yfinance API → core/data.py → data/raw/*.csv → DataFrame
                    ▼
             logs/fetch_log.csv
                                  core/indicators.py → DataFrame
                                         ▼
                                  core/signals.py → list[SignalResult]
                                         ▼
                    ┌────────────────────┤
             logs/signals.csv    screener/notifier.py → Gmail → email
```

### Requirements to Structure Mapping

| Requirement | File(s) |
|---|---|
| FR1: Unified data layer | `core/data.py` |
| FR2: Single config source | `config/strategy.yaml` + `core/config.py` |
| FR3: Backtest pipeline | `backtest/engine.py`, `analysis.py`, `optimization.py`, `montecarlo.py`, `charts.py` |
| FR4: Screening pipeline | `screener/scanner.py`, `screener/notifier.py`, `core/signals.py` |
| FR5: Pipeline CLI | `pipeline.py` (Typer) |
| FR6: Audit logging | `core/logging.py` → `logs/*.csv` |
| NFR1: No lookahead bias | `core/indicators.py` |
| NFR2: Shared logic | `core/indicators.py`, `core/signals.py` |
| NFR3: Credentials outside git | `.env` + `.gitignore` + `.env.example` |
| NFR5: Single requirements | `requirements.txt` |
| NFR6: Deterministic replay | `core/data.py` cache + `logs/fetch_log.csv` |

### External Integration Points

| Integration | Location | Auth |
|---|---|---|
| yfinance market data | `core/data.py` only | None (public API) |
| Gmail SMTP | `screener/notifier.py` only | App Password from `.env` |
| TradingView Pine Script | `pine_script.pine` — manual sync | N/A |

## Architecture Validation Results

### Coherence: ✅ PASS
All decisions are compatible. No contradictions. Module layering enforced throughout.
Pydantic v2 + Typer are naturally aligned (Typer >= 0.9 depends on Pydantic v2).

### Requirements Coverage: ✅ PASS — 13/13 requirements covered

| # | Requirement | Covered By |
|---|---|---|
| FR1 | Unified data layer | `core/data.py` |
| FR2 | Single config source | `config/strategy.yaml` + `core/config.py` |
| FR3 | Backtest pipeline | `backtest/` |
| FR4 | Screening pipeline | `screener/` + `core/signals.py` |
| FR5 | Pipeline CLI | `pipeline.py` (Typer) |
| FR6 | Audit logging | `core/logging.py` → `logs/*.csv` |
| NFR1 | Zero lookahead bias | `core/indicators.py` |
| NFR2 | Shared logic | `core/indicators.py`, `core/signals.py` |
| NFR3 | Credentials outside git | `.env` + `.gitignore` |
| NFR4 | Graceful degradation | Per-ticker exception handling pattern |
| NFR5 | Single requirements file | `requirements.txt` |
| NFR6 | Deterministic replay | `core/data.py` cache + `fetch_log.csv` hash |
| NFR7 | Operational visibility | Three structured CSV audit logs |

### Implementation Readiness: ✅ READY

### Architecture Completeness Checklist

- [x] Project context analyzed from existing codebase
- [x] Scale and complexity assessed (medium, single-user desktop)
- [x] D1: Pydantic v2 StrategyConfig — single validated config object
- [x] D2: Shared `core/data.py` — one cache, both consumers
- [x] D3: `.env` + `data/raw/` gitignored
- [x] D4: Typer CLI with `backtest` / `screen` / `both` subcommands
- [x] D5: stdlib `csv.writer` append-only audit logs
- [x] Naming conventions (snake_case throughout)
- [x] Module layering rules (no circular imports)
- [x] Typed dataclasses for `SignalResult` / `TradeResult`
- [x] Error handling per-tier
- [x] Complete directory tree with every FR mapped to a file
- [x] Data flow diagrams for both pipelines

### Gap Analysis

**Important (resolve in first sprint):**
- `core/signals.py` merge rule: *signal detection* (does this bar trigger?) belongs in `core/signals.py`; *trade state machine* (open position, move SL, exit) stays in `backtest/engine.py`
- `config/strategy.yaml` must be authored first — it's the unblocking dependency

**Post-MVP:**
- `pipeline both` auto-update behaviour for optimized params
- Pine Script auto-generation from `strategy.yaml`

### Implementation Handoff

**First three steps (strict order):**
1. Create `config/strategy.yaml` — merge all params from `backtester.py:DEFAULT_PARAMS` + `bot/config.py`
2. Create `core/config.py` with Pydantic v2 `StrategyConfig` model and `load_config()`
3. Verify both load and validate cleanly — this unblocks all other work

**Key risk:** Merging signal detection into `core/signals.py` must preserve zero-lookahead-bias.
Rule: detect signals only on `df.iloc[-2]` (last completed bar), never `df.iloc[-1]` (live/open bar).
