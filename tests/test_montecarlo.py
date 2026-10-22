"""
Portfolio Monte Carlo: summary figures, percentile bands, console summary and
fan chart (openspec change fix-mc-summary-keyerror).
"""

import numpy as np
import pytest

import charts
from montecarlo import print_mc_summary, run_monte_carlo_portfolio

INIT = 1_000_000.0

# Recorded from run_monte_carlo_portfolio() before the bands were added, on
# _returns() with default horizon/sims/block and seed 42. Adding the bands
# must not move any of these.
PINNED = {
    "median_final_equity": 1057278.1557014154,
    "p5_final_equity":     832415.608018164,
    "p95_final_equity":    1358265.1368526516,
    "mean_max_drawdown":   -14.061923863543873,
    "p95_max_drawdown":    -24.24257711049235,
    "pct_profitable":      65.19,
}


def _returns() -> np.ndarray:
    return np.random.default_rng(0).normal(0.0005, 0.01, 500)


@pytest.fixture(scope="module")
def mc() -> dict:
    return run_monte_carlo_portfolio(_returns(), initial_equity=INIT)


def test_summary_values_unchanged(mc):
    for key, want in PINNED.items():
        assert mc[key] == pytest.approx(want, rel=1e-12), key


def test_bands_shape_start_and_order(mc):
    h = mc["horizon_days"]
    for key in ("band_p5", "band_median", "band_p95"):
        assert len(mc[key]) == h + 1
        assert mc[key][0] == INIT
    assert np.all(mc["band_p5"] <= mc["band_median"])
    assert np.all(mc["band_median"] <= mc["band_p95"])


def test_band_median_ends_at_median_final_equity(mc):
    assert mc["band_median"][-1] == mc["median_final_equity"]


def test_deterministic(mc):
    again = run_monte_carlo_portfolio(_returns(), initial_equity=INIT)
    for key in PINNED:
        assert again[key] == mc[key]
    for key in ("band_p5", "band_median", "band_p95"):
        np.testing.assert_array_equal(again[key], mc[key])


def test_print_summary(mc, capsys):
    print_mc_summary(mc)
    out = capsys.readouterr().out
    assert "Worst-5% drawdown" in out
    assert f"{mc['median_final_equity']:,.0f}" in out
    assert mc["p95_max_drawdown"] <= mc["mean_max_drawdown"]


def test_too_little_history(capsys):
    assert run_monte_carlo_portfolio(np.full(59, 0.001)) is None
    assert "Too few daily returns" in capsys.readouterr().out


def test_fan_chart_written(mc, tmp_path, monkeypatch):
    monkeypatch.setattr(charts, "CHARTS_DIR", str(tmp_path))
    charts.plot_mc_fan(mc)
    assert (tmp_path / "07_monte_carlo_fan.png").stat().st_size > 0
