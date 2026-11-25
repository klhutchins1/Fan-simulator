"""RV-4 promote #75/#76: fan_noise_curle / fan_noise_cv are thin CLIs over fansim.acoustics.farfield."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

from fansim.acoustics import farfield as ff

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(path.stem + "_promote", path)
    old = sys.argv[:]
    sys.argv = [str(path)]
    try:
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        assert spec.loader
        spec.loader.exec_module(mod)
    finally:
        sys.argv = old
    return mod


@pytest.mark.parametrize("script", ("fan_noise_curle.py", "fan_noise_cv.py"))
def test_scripts_do_not_redefine_a_weighting_or_dipole(script):
    mod = _load(script)
    assert not hasattr(mod, "a_weight_db"), "A-weighting belongs in fansim.acoustics.farfield"
    assert getattr(mod, "a_weighting_db", None) is ff.a_weighting_db
    assert getattr(mod, "dipole_pressure", None) is ff.dipole_pressure


def test_curle_script_observer_matches_farfield_at_two_metres():
    """Was a latent r^2 bug; promote must use dipole_pressure (1/r)."""
    mod = _load("fan_noise_curle.py")
    t = np.linspace(0.0, 0.05, 501)
    dt = float(t[1] - t[0])
    F = np.zeros((len(t), 3))
    F[:, 2] = 0.05 * np.cos(2 * np.pi * 50.0 * t)
    p1, _ = mod.observer_pressure(t, F, (0.0, 0.0, 1.0), r_obs=1.0)
    p2, _ = mod.observer_pressure(t, F, (0.0, 0.0, 1.0), r_obs=2.0)
    assert np.max(np.abs(p1 - ff.dipole_pressure(F, dt, r_obs=1.0))) <= 1e-9 * np.max(np.abs(p1))
    assert np.max(np.abs(p2 - ff.dipole_pressure(F, dt, r_obs=2.0))) <= 1e-9 * np.max(np.abs(p2))
    assert np.max(np.abs(p1)) / np.max(np.abs(p2)) == pytest.approx(2.0, rel=1e-6)
