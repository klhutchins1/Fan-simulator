"""Tests for the calibrated loading-noise proxy (fansim.acoustics.loading)."""

import numpy as np
import pytest

from fansim.acoustics import (
    calibrate_loading_proxy,
    loading_noise_proxy,
    loading_proxy_from_rans,
)


def test_proxy_increases_with_blade_count():
    # c0 > 0: more blades -> higher (louder) loading-noise estimate
    lo = loading_noise_proxy(5, 0.01)
    hi = loading_noise_proxy(9, 0.01)
    assert hi > lo


def test_from_rans_divides_by_blade_count():
    assert loading_proxy_from_rans(7, 0.07) == pytest.approx(loading_noise_proxy(7, 0.01))


def test_calibrate_recovers_a_known_linear_relation():
    # synthetic exact relation band = 3*nB - 50*tpb + 10; calibrate must recover it
    nb = np.array([5, 6, 7, 8, 9, 10, 11], float)
    tpb = np.array([0.012, 0.010, 0.009, 0.008, 0.007, 0.006, 0.005])
    band = 3.0 * nb - 50.0 * tpb + 10.0
    c0, c1, c2 = calibrate_loading_proxy(nb, tpb, band)
    assert c0 == pytest.approx(3.0, abs=1e-6)
    assert c1 == pytest.approx(-50.0, abs=1e-6)
    assert c2 == pytest.approx(10.0, abs=1e-6)
    # and the recalibrated proxy reproduces the data
    pred = [loading_noise_proxy(int(n), t, (c0, c1, c2)) for n, t in zip(nb, tpb)]
    assert np.allclose(pred, band, atol=1e-6)


def test_calibrate_needs_enough_points():
    with pytest.raises(ValueError):
        calibrate_loading_proxy([5, 6], [0.01, 0.009], [40.0, 41.0])


def test_beats_proudman_on_opt_noise_data():
    """Sanity: the packaged proxy should out-rank Proudman on the 7 calibration finalists."""
    import json
    from pathlib import Path

    from scipy.stats import spearmanr

    run = Path(__file__).resolve().parent.parent / "runs" / "opt_noise"
    if not (run / "finalist_noise.json").exists():
        pytest.skip("opt_noise LBM finalist scores not present")
    pro = {r["trial"]: r for r in json.loads((run / "pareto.json").read_text())}
    lbm = {r["trial"]: r for r in json.loads((run / "finalist_noise.json").read_text())}
    band, proxy, proud = [], [], []
    for t in sorted(lbm):
        raw = json.loads((run / "trials" / f"trial_{t:04d}" / "result.json").read_text())["raw"]["free"]
        nb = pro[t]["n_blades"]
        band.append(lbm[t]["noise_dba_band"])
        proxy.append(loading_proxy_from_rans(nb, raw["thrust_n"]))
        proud.append(pro[t]["noise_swl"])
    r_proxy = abs(spearmanr(proxy, band).statistic)
    r_proud = abs(spearmanr(proud, band).statistic)
    assert r_proxy > r_proud  # loading proxy tracks LBM better than Proudman
