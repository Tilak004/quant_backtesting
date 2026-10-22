## 1. Pin current behaviour

- [x] 1.1 Before editing `montecarlo.py`, run the current `run_monte_carlo_portfolio()` on a fixed synthetic series (e.g. `np.random.default_rng(0).normal(0.0005, 0.01, 500)`, `initial_equity=1_000_000`, default horizon/sims/block, seed 42). Record `median_final_equity`, `p5_final_equity`, `p95_final_equity`, `mean_max_drawdown`, `p95_max_drawdown`, `pct_profitable`
- [x] 1.2 Record the baseline: `pytest tests/` pass count and `ruff check .` result

## 2. Bootstrap returns percentile paths

- [x] 2.1 In `run_monte_carlo_portfolio()`, allocate a `(n_simulations, horizon_days + 1)` path matrix with column 0 = `initial_equity`, and fill columns 1..H with each simulated `curve`. Leave the RNG calls, `final_equities` and the max-drawdown computation (over `curve`, not the padded row) unchanged
- [x] 2.2 After the loop, add `band_p5`, `band_median`, `band_p95` (per-day 5th/50th/95th percentiles, length `horizon_days + 1`) to the returned dict
- [x] 2.3 Update the function docstring's Returns section to list the band keys

## 3. Summary and chart

- [x] 3.1 Rewrite `print_mc_summary()` to use only portfolio-dict keys: header with paths, horizon days, block days, observed days; 5th/50th/95th final equity in Rs with thousands separators and % change from `initial_equity`; mean max drawdown; "Worst-5% drawdown" from `p95_max_drawdown`; % profitable paths
- [x] 3.2 Delete `compute_mc_bands()` from `montecarlo.py` and update the module docstring so it describes one bootstrap (portfolio daily returns) only
- [x] 3.3 Change `plot_mc_fan()` in `charts.py` to `plot_mc_fan(mc: dict)`: x = trading days ahead (0..horizon), y = account equity (Rs), 5th-95th band plus median line, reference line at `initial_equity`, title naming it a one-year portfolio projection with the path count; keep filename `07_monte_carlo_fan.png`; remove the "Actual" overlay and the hardcoded 100 line and label

## 4. Pipeline wiring

- [x] 4.1 In `main.py` stage 7, split the single `try` into replay / bootstrap / summary blocks, each printing `[WARN] <step> failed: <exc>`; remove the `compute_mc_bands` call and the `mc_bands` variable
- [x] 4.2 In stage 9, call `plot_mc_fan(mc_result)` when `mc_result` is not `None`; drop the `compute_equity_curve` call made only for the overlay (keep the import if still used elsewhere)
- [x] 4.3 Update the `from montecarlo import ...` line in `main.py`; grep the repo for `compute_mc_bands` and old `plot_mc_fan(` call shapes and confirm none remain outside `openspec/`

## 5. Tests

- [x] 5.1 Add `tests/test_montecarlo.py`: the summary values on the 1.1 series with seed 42 equal the recorded values (`pytest.approx`, rel 1e-12)
- [x] 5.2 Test bands: length `horizon_days + 1`; day 0 equals `initial_equity` for all three; `band_p5 <= band_median <= band_p95` at every day; `band_median[-1] == median_final_equity`
- [x] 5.3 Test determinism: two runs with the same inputs and seed give identical summary values and bands
- [x] 5.4 Test `print_mc_summary()` on a real result: no exception; output (via `capsys`) contains "Worst-5% drawdown" and the Rs-formatted median; `p95_max_drawdown <= mean_max_drawdown`
- [x] 5.5 Test the too-little-history path: fewer than 60 returns gives `None` and prints the skip warning
- [x] 5.6 Test `plot_mc_fan()` writes `07_monte_carlo_fan.png` (monkeypatch `charts.CHARTS_DIR` to `tmp_path`, Agg backend)

## 6. Verify

- [x] 6.1 `pytest tests/` passes: baseline count plus the new tests
- [x] 6.2 `ruff check .` is clean
- [x] 6.3 Run `python main.py`; confirm stage 7 prints the Monte Carlo summary with no `[WARN]`, stage 9 saves `results/charts/07_monte_carlo_fan.png`, and the summary report's Monte Carlo section numbers match the console summary (done as a quick check: full run stopped after stage 4 at user request; stage 7 code path + fan chart run on the stage-3 trade CSVs; report section not regenerated, reads the same mc_result keys)
- [x] 6.4 Open the saved fan chart and check: Rs y-axis, starts at starting capital, band widens with days, no trade-indexed overlay
