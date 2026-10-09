"""Feature-layer tests: perturbation math (fast) and watertight featured impellers (slow)."""

from __future__ import annotations

import numpy as np
import pytest

from fansim.geometry import build_impeller, export_stl, watertight_report
from fansim.geometry.blade import BladeParams
from fansim.geometry.features import Features, apply_features


def test_features_off_by_default():
    assert not Features().active
    assert Features(tubercle_amp=0.1, tubercle_waves=0).active is False  # needs both
    assert Features(tubercle_amp=0.1, tubercle_waves=4).active is True


def test_required_resolution_scales_with_waves_and_caps():
    f = Features(serration_amp=0.05, serration_waves=12)
    assert f.required_span_sections(12) >= 12
    assert f.required_span_sections(12) <= Features.MAX_SPAN_SECTIONS


def test_tubercle_moves_leading_edge_only():
    x = np.array([0.0, 0.5, 1.0])          # LE, mid, TE
    a = (x - 0.5) * 20.0                     # chordwise, chord=20
    b = np.array([0.0, 1.0, 0.0])
    feat = Features(tubercle_amp=0.1, tubercle_waves=4)
    # r_frac where cos(2*pi*4*r)=1 -> maximal LE shift
    a2, b2 = apply_features(x, a, b, r_frac=0.0, chord=20.0, feat=feat)
    assert a2[0] != a[0]           # leading edge moved
    assert a2[2] == pytest.approx(a[2])  # trailing edge unchanged
    assert b2[1] == pytest.approx(b[1])  # thickness unchanged (no dimples)


def test_dimple_thins_section():
    x = np.linspace(0, 1, 20)
    a = (x - 0.5) * 20.0
    b = np.full_like(x, 2.0)
    feat = Features(dimple_amp=0.3, dimple_rows=4, dimple_cols=4)
    _, b2 = apply_features(x, a, b, r_frac=0.0, chord=20.0, feat=feat)
    assert b2.min() < b.min()      # some points thinned
    assert (b2 > 0).all()          # but never non-positive


@pytest.mark.slow
@pytest.mark.parametrize("feat", [
    Features(tubercle_amp=0.08, tubercle_waves=6),
    Features(serration_amp=0.05, serration_waves=8),
    Features(dimple_amp=0.3, dimple_rows=5, dimple_cols=5),
])
def test_featured_impeller_is_watertight(tmp_path, feat):
    stl = export_stl(build_impeller(BladeParams(features=feat)), tmp_path / "f.stl")
    rep = watertight_report(stl)
    assert rep.ok, f"featured impeller not watertight: {rep}"
