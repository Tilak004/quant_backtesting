## Context

See proposal.md (Why). Current state:

- `run_monte_carlo_portfolio()` (`montecarlo.py`) runs a moving-block
  bootstrap over the replay's daily returns. Each loop pass builds a
  `horizon_days` equity curve and keeps only its final value and max drawdown.
  The full curves are thrown away.
- `print_mc_summary()` was written for the old per-trade dict. It reads
  `n_trades`, prints bare floats, and labels the worst-tail drawdown "95th pct".
- `compute_mc_bands()` chains per-trade returns. Its only caller is `main.py`.
- `plot_mc_fan()` (`charts.py`) takes trade-indexed arrays and hardcodes
  "start = 100".
- In `main.py` stage 7, one `try` wraps the replay, the bootstrap, the summary
  and the bands, so the first failure skips everything after it.
- The markdown report (`_write_summary_report`) reads named keys from
  `mc_result` and already works.

## Goals / Non-Goals

**Goals:**
- Same random draws, so every figure the report already shows stays
  byte-identical.
- Summary and fan come from the same simulated paths.

**Non-Goals:**
- Changing the bootstrap method, block length, horizon or path count.
- Overlaying realised equity on the fan.
- Moving the Monte Carlo settings into `strategy.yaml`.

## Decisions

1. **Keep the paths inside the existing loop, then take percentiles per day.**
   Keep a `(n_simulations, horizon_days + 1)` matrix, with column 0 set to
   `initial_equity`. Fill columns 1..H with each `curve` as it's built. After
   the loop, take `np.percentile(..., [5, 50, 95], axis=0)` and return the
   results as `band_p5`, `band_median`, `band_p95`.
   - The RNG calls don't change, so the draws match exactly.
   - 10,000 x 251 float64 is about 20 MB, briefly. That's fine for a batch job.
   - The median band's last point is `np.median` of the same final equities,
     so it equals `median_final_equity` exactly (spec scenario).
   - Alternative: a second bootstrap pass just for the bands. Rejected: it
     doubles the runtime and the bands could disagree with the summary.
   - Alternative: return the full matrix. Rejected: callers only need three
     paths, and the report dict shouldn't carry 20 MB.

2. **Max drawdown stays computed over `curve`, not the padded row.**
   Today the peak starts at `curve[0]`, the equity after day 1. A drawdown
   computed over the padded row (peak from `initial_equity`) would count a
   day-1 loss and change `mean_max_drawdown` and `p95_max_drawdown`. That
   breaks Goal 1. A drawdown that counts a day-1 loss is arguably more
   correct, but it is a behaviour change for a separate change. Record it as a
   follow-up.

3. **Rewrite `print_mc_summary()` against the portfolio dict.**
   The header gives paths, horizon, block length and observed days. Rupee
   values print with thousands separators and % change from `initial_equity`.
   The labels match the markdown report ("Worst-5% drawdown"). The summary
   uses only keys the portfolio function always returns.

4. **Delete `compute_mc_bands()`; `plot_mc_fan()` takes the result dict.**
   New signature: `plot_mc_fan(mc: dict)`. It reads the three bands,
   `initial_equity`, `horizon_days` and `n_simulations`. The x-axis is
   "Trading days ahead" and the y-axis is "Account equity (Rs)", with a
   reference line at `initial_equity`. The title says it is a one-year
   portfolio projection. The filename stays `07_monte_carlo_fan.png`.
   - Passing the dict keeps chart and summary tied to the same object.
   - Alternative: keep `compute_mc_bands()` and point it at daily returns.
     Rejected: it would be a second bootstrap (see 1).

5. **Drop the "Actual" overlay.** The realised curve covers 9.5 years in
   sample. The fan is a one-year forward projection on an x-axis that starts
   today. Any rescaling to fit them on one axis would be invented. The
   realised CAGR is already printed in stage 7.

6. **Separate `try` blocks in stage 7.** Use three blocks:
   - replay;
   - bootstrap, which sets `mc_result`;
   - summary print.

   Each catches and prints `[WARN] <step> failed: <exc>`, which matches the
   current style and isn't a silent pass. Stage 9 draws the fan whenever
   `mc_result` is not `None`. `mc_bands` goes away. A replay failure still
   skips the bootstrap, because it has no input.

## Risks / Trade-offs

- [Same seed but a reordered RNG call changes every figure] → Mitigation:
  before editing, task 1.1 records reference values from the current code on
  a fixed synthetic series. A test then pins them.
- [20 MB transient allocation] → Mitigation: it's within limits for a batch
  run. If it ever matters, use `float32` or fewer paths for the bands.
- [External code calls `compute_mc_bands()` or the old `plot_mc_fan()`
  signature] → Mitigation: repo grep shows `main.py` is the only caller. The
  proposal marks it **BREAKING** (internal).
- [Full `python main.py` is slow, so a regression could slip through]
  → Mitigation: unit tests cover the summary, the bands and the pinned values.
  One full run confirms stage 7 and the chart end to end.

## Migration Plan

No data migration. Rollback is reverting the commit. The chart file is just
regenerated on the next run.

## Open Questions

- Follow-up (not this change): should the max drawdown include the day-1 move
  from starting capital (Decision 2)?
