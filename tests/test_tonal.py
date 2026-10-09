"""Tests for blade-passing tonal analysis (fansim.acoustics.tonal) + uneven-spacing geometry."""

import math

import numpy as np
import pytest

from fansim.acoustics.tonal import (
    blade_passing_modes,
    peak_tone_amplitude,
    peak_tone_reduction_db,
    tonal_peak_ratio,
)
from fansim.structural.balance import balanced_uneven_spacing, equal_spacing, is_balanced


def test_equal_spacing_concentrates_at_bpf():
    n = 7
    ang = equal_spacing(n)
    m, amp = blade_passing_modes(ang, m_max=3 * n)
    # amplitude ~ N exactly at m = N, 2N, 3N; ~0 elsewhere
    assert amp[n - 1] == pytest.approx(n, abs=1e-9)     # m = N
    assert amp[2 * n - 1] == pytest.approx(n, abs=1e-9)  # m = 2N
    off = amp[[i for i in range(len(m)) if (i + 1) % n != 0]]
    assert np.max(off) < 1e-9
    assert tonal_peak_ratio(ang) == pytest.approx(1.0)   # fully concentrated
    assert peak_tone_reduction_db(ang) == pytest.approx(0.0, abs=1e-9)


@pytest.mark.parametrize("n", [5, 6, 7, 9, 11])
def test_uneven_spacing_lowers_peak_tone(n):
    rng = np.random.default_rng(3)
    ang = balanced_uneven_spacing(n, spread=0.6, rng=rng)
    assert is_balanced(ang, tol=1e-6)                    # still balanced
    assert tonal_peak_ratio(ang) < 1.0                   # peak tone is spread out
    assert peak_tone_reduction_db(ang) < 0.0             # quieter peak (dB)


def test_more_spread_generally_lowers_peak():
    # averaged over seeds, larger spread -> lower peak-tone ratio
    def mean_ratio(spread):
        return np.mean([tonal_peak_ratio(balanced_uneven_spacing(9, spread=spread,
                        rng=np.random.default_rng(s))) for s in range(12)])
    assert mean_ratio(0.6) < mean_ratio(0.15)


def test_peak_tone_amplitude_bounded_by_n():
    ang = balanced_uneven_spacing(8, spread=0.5, rng=np.random.default_rng(1))
    assert peak_tone_amplitude(ang) <= 8 + 1e-9


def test_uneven_impeller_builds_watertight():
    """The geometry engine must build a watertight impeller with a custom (uneven) blade pattern."""
    import tempfile
    from pathlib import Path

    from fansim.geometry import BladeParams, build_impeller, export_stl, set_uneven_spacing, watertight_report

    p = BladeParams(n_blades=7)
    set_uneven_spacing(p, spread=0.25, rng=np.random.default_rng(0))
    assert p.blade_angles_deg is not None and len(p.blade_angles_deg) == 7
    stl = export_stl(build_impeller(p), Path(tempfile.mkdtemp()) / "uneven.stl")
    assert watertight_report(stl).ok


def test_wrong_angle_count_raises():
    from fansim.geometry import BladeParams, build_impeller

    p = BladeParams(n_blades=7, blade_angles_deg=[0.0, 50.0, 100.0])  # only 3 for 7 blades
    with pytest.raises(ValueError):
        build_impeller(p)


def test_spacing_dof_round_trips_deterministically():
    """with_spacing samples a spacing pattern; blade_from_flat must reproduce it exactly + balanced."""
    import optuna

    from fansim.optimize.search_space import blade_from_flat, suggest_params

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    st = optuna.create_study()
    st.optimize(lambda t: (suggest_params(t, with_spacing=True), 0.0)[1], n_trials=6)
    for t in st.trials:
        assert "spacing_spread" in t.params and "spacing_seed" in t.params
        bp = blade_from_flat(t.params)
        if bp.blade_angles_deg is not None:
            assert len(bp.blade_angles_deg) == bp.n_blades
            assert is_balanced(np.radians(bp.blade_angles_deg), tol=1e-6)
            # reconstructing again gives identical angles (deterministic from spread+seed)
            assert blade_from_flat(t.params).blade_angles_deg == bp.blade_angles_deg
