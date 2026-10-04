## 1. Baseline and caller re-check

- [x] 1.1 Run `pytest tests/` and `ruff check .`; record the pass count (expect 123) and zero ruff errors as the baseline. Also record the config hash: `python -c "from core.config import load_config; from core.logging import _params_hash; print(_params_hash(load_config()))"`
- [x] 1.2 Re-grep every removal target as a bare string across the repo (code, tests, tools, `.bat`, `.github/`, docs, excluding `openspec/`): `compute_monthly_returns`, `run_monte_carlo`, `rolling_walk_forward`, `clear_caches`, `_slope`, `_has_two_years`, `get_threshold`, `_cached_threshold`, `EXIT_ENC`, `BAD_YEARS`, `depth_tol`, `score_pct`, `qroa`, `avg_vals`, `total_pnl`, `info_f`. Stop and report any caller, `getattr`, or string import found outside the definition site

## 2. Remove dead functions

- [x] 2.1 Delete `compute_monthly_returns` from `analysis.py`
- [x] 2.2 Delete `run_monte_carlo` from `montecarlo.py`, and reword the comment above `p95_max_drawdown` (around line 83) so it explains the 5th-percentile choice without pointing at the removed function
- [x] 2.3 Delete `rolling_walk_forward` from `optimization.py`
- [x] 2.4 Delete `clear_caches` from `core/portfolio.py`
- [x] 2.5 Delete `_slope` from `core/pattern_scanner.py`
- [x] 2.6 Delete `_has_two_years` from `core/fundamental_scorer.py`
- [x] 2.7 Delete `get_threshold` and the never-read `_cached_threshold` global and its load in `_load_model` from `core/ml/xgb_scorer.py`; leave the training code that writes the threshold file untouched
- [x] 2.8 Remove imports left unused by 2.1-2.7 (ruff F401 will flag them)

## 3. Remove dead names and unused locals

- [x] 3.1 Delete `EXIT_ENC` from `core/ml/feature_builder.py`
- [x] 3.2 Delete `BAD_YEARS` from `tools/decay_analysis.py`
- [x] 3.3 Remove the `depth_tol` parameter from `detect_inv_head_shoulders` in `core/pattern_scanner.py` and fix its docstring to say the head is 8-40% lower (match the code)
- [x] 3.4 Remove unused locals `score_pct`, `qroa`, `avg_vals`, `total_pnl`, `info_f` in `dashboard.py`; where the right-hand side has no side effect, delete the whole statement
- [x] 3.5 Fix ruff B904 in `core/ml/xgb_scorer.py` with `raise ... from None`

## 4. Correct misleading text

- [x] 4.1 Confirm the audit-log config hash is computed from parsed values (`core/logging.py` `_params_hash` uses `cfg.to_params_dict()`), and that `to_params_dict()` does not include raw YAML text. If it does, skip 4.2 and note why
- [x] 4.2 In `config/strategy.yaml` (breadth block, ~line 100), change the "Off by default" comment to match the value `true`. Comment only; do not touch any value or `config_version`
- [x] 4.3 In `bot/notifier.py` plain-text email (~line 588), change `Score {s['score']}/6` to `/7`; grep the notifier for any other `/6` score label and fix it the same way
- [x] 4.4 In `bot/main.py` banner (~line 63), compute the time with `datetime.now(ZoneInfo("Asia/Kolkata"))` so the `IST` label is true on UTC runners
- [x] 4.5 In `_bmad-output/planning-artifacts/architecture.md` (~line 322), drop `run_monte_carlo` from the `montecarlo.py` description; fix any other doc or comment that names a function removed in section 2

## 5. Verify

- [x] 5.1 Run `pytest tests/`; pass count must equal the 1.1 baseline
- [x] 5.2 Run `ruff check .`; zero errors
- [x] 5.3 Re-run the 1.2 grep; only `openspec/` hits remain
- [x] 5.4 Run `python bot/main.py --dry-run --tickers WIPRO.NS` and check the banner prints IST time and the run completes
- [x] 5.5 Re-run the 1.1 hash command; it must print the same hash as the baseline
- [x] 5.6 Commit with a message listing every removed function and name so each can be restored from git (deferred: user chose not to commit; changes left in working tree)
