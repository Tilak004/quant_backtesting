## Context

See proposal.md for why. The audit used `vulture --min-confidence 60`, ruff
with extra rules (F401/F841/F811/B904/B023/B008), and a repo-wide grep of every
candidate (tests, tools, `.bat`, workflows, docs). ruff F401 already reports
zero unused imports. Several vulture hits were false positives and stay:
`_check_rsi_ranges` (pydantic validator), the `pipeline.py` Typer commands
(registered by decorator), and `tests/legacy/*` (imported by the fills test).

## Goals / Non-Goals

**Goals:**
- Remove only code proven unreferenced, and fix only text that contradicts the
  code.
- Keep every output byte-identical.

**Non-Goals:**
- Fixing bugs inside the dead code. Deleting it removes them.
- Surfacing values that are computed but not shown. That is a UI change.
- Reconfiguring ruff. The B023/B008 hits are false positives, so no rule change.

## Decisions

1. **Delete dead functions that contain bugs; don't fix them.**
   `compute_monthly_returns` raises on a series starting mid-year, and
   `run_monte_carlo` reports the mildest drawdown tail. Nothing calls either.
   - Fixing them would add untested behaviour, and git history keeps them if
     anyone needs them back.
   - Alternative considered: keep `run_monte_carlo` as the "trade-resample
     variant" its docstring mentions. Rejected, because a known-wrong
     alternative is worse than none. The comment at `montecarlo.py:83` that
     points to it gets reworded.

2. **`qroa` and `avg_vals` in `dashboard.py`: delete, don't display.**
   - Showing ROA on the signal card or avg P&L on the tier bar is arguably
     useful, but it changes what users see, which breaks this change's
     "no output change" rule.
   - It can be a one-line follow-up.

3. **`BAD_YEARS`: delete the constant, don't write the comparison.**
   Writing the good-vs-bad-years aggregate is new analysis output. Note the
   idea in the follow-up list instead.

4. **`get_threshold` and the `_cached_threshold` load: remove both.**
   - The saved threshold file is still written by training. Only the dead read
     path goes.
   - The live gate keeps using `ml_min_score` from config, exactly as today.

5. **IST banner: compute the time in `Asia/Kolkata` via `zoneinfo`.** On local
   Windows runs (already IST) the printed time is unchanged. On the UTC CI
   runner, the label stops being wrong.
   - This is the only item that changes a printed value. It changes the
     console banner, not a signal, email or log row.
   - Alternative: drop the "IST" suffix. Rejected, because the banner is meant
     to show market time.

6. **`strategy.yaml`: edit only the comment.** No parameter changes, so
   `config_version` stays 1.7, and the config hash in audit logs is unaffected
   as long as the hash covers parsed values rather than raw text. The
   implementer must verify this before editing (task 4.1).

## Risks / Trade-offs

- [An external script or notebook imports a removed function] → Mitigation:
  repo-wide grep finds no callers. The commit message lists each removal so
  it's easy to restore from git.
- [Removing `depth_tol` breaks a keyword caller] → Mitigation: grep shows no
  caller passes it. `scan_patterns` calls with defaults.
- [A "dead" name is reached dynamically (getattr, string import)] → Mitigation:
  grep for each name as a string too, not just as a call.
- [The config hash is computed over raw YAML text] → Mitigation: task 4.1
  checks this first. If it is, leave the comment untouched.
