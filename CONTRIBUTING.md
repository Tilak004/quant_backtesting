# Contributing

This is a quantitative research project. A change that looks harmless can
quietly move a backtest number, so the bar for proof is higher than usual.
Read [CLAUDE.md](CLAUDE.md) first. It has the architecture rules and the
**Known measurement traps** section, and both apply to every change.

## Current status

The strategy **FAILS** the pre-registered edge reality check under realistic
fills (see `results/edge_check/edge_reality_report.md`). Until a new
entry/exit passes the same check:

- don't add live-signal, paper-ledger parity or ops work on top of the
  current strategy;
- research work should use the realistic fill model (`next_open` entry,
  gap-aware exits) and start from the liquid subset.

## Setup

```bash
pip install -r requirements.txt
```

Python 3.11 (the version CI uses). Email alerts also need a `.env`: copy
`.env.example` to `.env` and fill in values. Never commit `.env`.

## Before opening a PR

CI (`.github/workflows/ci.yml`) runs both of these on every push and PR to
`master`. Both must pass:

```bash
ruff check .        # zero errors; rule set pinned in ruff.toml
pytest tests/
```

If the change touches the backtest, signals, fills or sizing, also run:

```bash
python main.py                       # full pipeline = engine integration test
python tools/run_portfolio.py        # account-level figures
python tools/edge_reality_check.py --limit 20   # smoke test; full run ~25 min
```

Put before/after figures in the PR description. Any figure that describes a
real account must come from `core/portfolio.py`, not from pooled per-ticker
results.

## Rules that reviewers check

- **Config, not constants.** Strategy parameters live in
  `config/strategy.yaml` and are read through `load_config()`. If you change
  any parameter, bump `config_version`.
- **No lookahead.** Indicators and patterns use only data up to bar `t`. No
  `.shift(-n)`, and no ranking of trades by an in-sample model.
- **Data through the cache.** Use `core/data.py` (`fetch_or_load()`), not
  `yfinance` directly.
- **Audit logs are append-only.** Never truncate or rewrite files in `logs/`.
- **No silent failures.** No `except Exception: pass`; at least
  `warnings.warn(str(e))`.
- **Pandas 2.0.** Use `.reindex(idx).ffill()`, not `method="ffill"`; no
  `inplace=True`.
- **Breakeven is not a loss.** Loss filters use `pnl_pct < 0`.
- **Tests.** A bug fix comes with a test that fails without the fix.

## Spec-driven changes (OpenSpec)

Anything that changes behaviour or output goes through OpenSpec:

1. Propose: `openspec/changes/<change-name>/` with `proposal.md`, `design.md`,
   `tasks.md` and delta specs under `specs/<capability>/spec.md`.
2. Implement the tasks and tick them off in `tasks.md`.
3. Archive: sync the delta specs into `openspec/specs/` and move the change to
   `openspec/changes/archive/YYYY-MM-DD-<change-name>/`.

Purely cosmetic changes (dead code, comments, typos), where no number, signal,
trade, ledger row or log row changes, can set `skip_specs: true`.

## Commits

Use conventional prefixes, as in the existing history: `feat:`, `fix:`,
`chore:`, `docs:`, `test:`. Keep the subject short and say what changed in
results terms where it matters (e.g. "report account-level results, not
22x-leveraged pooled ones").

The daily screener workflow commits `logs/paper_trades.csv` with
`[skip ci]`. Don't hand-edit that ledger.

## Never commit

- `.env` or any credentials. The `.gitignore` line for `.env` must not have a
  trailing comment, because `#` only starts a comment at the start of a line.
- Cached data (`data/raw/`, `data/fundamentals/`) or large generated results.
