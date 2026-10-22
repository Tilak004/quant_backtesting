## Why

A full-codebase audit (2026-10-04) found dead code, unused variables and
misleading labels/docstrings alongside real bugs. The real bugs change
backtest, signal or ledger numbers and need their own reviewed changes. This
change takes only the cosmetic subset, so it can land first with zero risk to
any result and shrink the diff the behavioural fixes are reviewed against.

Cosmetic here means: **no number, signal, trade, ledger row, email field value
or log row changes.** Anything that would move an output is out of scope.

## What Changes

- Remove dead functions with no callers anywhere in the repo:
  `analysis.compute_monthly_returns`, `montecarlo.run_monte_carlo`,
  `optimization.rolling_walk_forward`, `core.portfolio.clear_caches`,
  `core.pattern_scanner._slope`, `core.fundamental_scorer._has_two_years`,
  `core.ml.xgb_scorer.get_threshold`.
- Remove dead names: `EXIT_ENC` (`core/ml/feature_builder.py`), `BAD_YEARS`
  (`tools/decay_analysis.py`), the never-read `_cached_threshold` load in
  `core/ml/xgb_scorer.py`, and the unused `depth_tol` parameter of
  `detect_inv_head_shoulders`.
- Remove unused locals in `dashboard.py`: `score_pct`, `qroa`, `avg_vals`,
  `total_pnl`, `info_f`.
- Fix the ruff B904 in `core/ml/xgb_scorer.py` (`raise ... from None`).
- Correct wrong text that misdescribes the code:
  - plain-text email says `Score x/6`; the score is out of 7;
  - screener banner stamps `IST` on whatever the local clock is (UTC on CI);
  - `config/strategy.yaml` breadth block comment says "Off by default" while
    the value is `true` (comment only; value untouched, so no
    `config_version` bump);
  - `detect_inv_head_shoulders` docstring says head 10-30% lower; code uses
    8-40%;
  - comments and docs that reference the removed functions.

Not in scope (tracked for later changes): breakeven `<= 0`, silent
`except: pass`, the global `warnings.filterwarnings("ignore")`, the
`trades_OOS_best.csv` glob, and every finding that alters results.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. No spec-level behaviour changes; `skip_specs: true` is set.

## Impact

- Files: `analysis.py`, `montecarlo.py`, `optimization.py`, `core/portfolio.py`,
  `core/pattern_scanner.py`, `core/fundamental_scorer.py`,
  `core/ml/xgb_scorer.py`, `core/ml/feature_builder.py`,
  `tools/decay_analysis.py`, `dashboard.py`, `bot/notifier.py`, `bot/main.py`,
  `config/strategy.yaml` (comment only), `_bmad-output/.../architecture.md`
  (stale reference).
- Public API: removed functions had no callers, so nothing in the repo breaks.
  An external notebook that imported one would.
- Outputs: none change. The test suite (123 passing) and `ruff check .` must
  stay green.
