## Why

Stage 7 of `python main.py` has been broken since `68a70b3`. That commit
switched the Monte Carlo to `run_monte_carlo_portfolio()` but left
`print_mc_summary()` reading `mc['n_trades']`, a key only the old per-trade
function returned. The `KeyError` is caught by the stage's broad `except` and
printed as `[WARN] Portfolio replay / Monte Carlo failed: 'n_trades'`. That
hides two things:

- the console Monte Carlo summary never prints;
- `compute_mc_bands()` never runs, so the fan chart `07_monte_carlo_fan.png` is
  never drawn.

Fixing only the key would bring back a misleading chart. The fan bands
compound every trade one after another (the ~22x-leverage chaining behind the
old 10^22 equity figures). The bands start at the account's starting capital,
but the "Actual" overlay, axis label and reference line all assume
"start = 100". So the fan has to be rebuilt on the same portfolio bootstrap the
summary uses.

## What Changes

- `print_mc_summary()` reads only keys `run_monte_carlo_portfolio()` returns.
  It labels the drawdown figure as the worst-5% drawdown, matching the
  markdown report, and prints rupee amounts with % change from the start.
- `run_monte_carlo_portfolio()` also returns the 5th, 50th and 95th percentile
  equity paths over the horizon, from the paths it already simulates. Draws,
  seed and every existing summary value stay identical.
- The fan chart plots those portfolio paths: rupee equity against trading days
  ahead, with a reference line at starting capital. The trade-indexed
  "Actual" overlay goes. A 9.5-year in-sample curve can't share an axis with a
  one-year forward projection.
- **BREAKING** (internal API): remove `compute_mc_bands()`. Its only caller is
  `main.py`, and it is the trade-chaining method this change retires.
  `plot_mc_fan()` changes signature.
- In `main.py`, the Monte Carlo step gets its own `try`, so a failure there no
  longer hides the portfolio replay, and a summary failure no longer stops the
  chart.
- Add unit tests for the summary, the bands, and unchanged summary values.

Not in scope: moving the hardcoded horizon (250) and simulation count (10,000)
from `main.py` into `strategy.yaml`; changing the markdown report's Monte Carlo
section, which already reads the right keys.

## Capabilities

### New Capabilities
- `monte-carlo-projection`: the one-year forward Monte Carlo of the
  capital-limited portfolio. Covers its console summary and fan chart, and the
  rule that both come from portfolio daily returns, never from chained trades.

### Modified Capabilities

None. No existing spec covers Monte Carlo output.

## Impact

- Code: `montecarlo.py`, `charts.py` (`plot_mc_fan`), `main.py` (stage 7 and the
  stage 9 chart call), new `tests/test_montecarlo.py`.
- Outputs: stage 7 prints a Monte Carlo summary instead of a `[WARN]`;
  `results/charts/07_monte_carlo_fan.png` (under `CHARTS_DIR`) is produced
  again, with new content. The markdown report's Monte Carlo numbers are
  unchanged, because the bootstrap draws are the same.
- No change to signals, trades, the backtester, the portfolio replay, config,
  or audit logs.
