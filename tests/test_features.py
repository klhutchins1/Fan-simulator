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


def test_dimple_preserves_camber_line():
    """#116: Dimples must thin thickness about the camber line yc_mm, not shift camber."""
    from fansim.geometry.airfoil import _naca_camber_line, naca4
    from fansim.geometry.blade import _section_loop

    chord = 40.0
    loop, x = naca4(0.08, 0.4, 0.08, 60, return_chord_param=True)
    if np.allclose(loop[0], loop[-1]):
        loop, x = loop[:-1], x[:-1]
    a = (loop[:, 0] - 0.5) * chord
    b = loop[:, 1] * chord
    yc_mm = _naca_camber_line(x, 0.08, 0.4)[0] * chord
    feat = Features(dimple_amp=0.3, dimple_rows=4, dimple_cols=4)
    _, b2 = apply_features(x, a, b, r_frac=0.0, chord=chord, feat=feat, yc_mm=yc_mm)

    i_le = int(np.argmin(x))
    half_t0 = np.array([0.5 * (b[i_le - k] - b[i_le + k]) for k in range(1, i_le)])
    half_t2 = np.array([0.5 * (b2[i_le - k] - b2[i_le + k]) for k in range(1, i_le)])
    mid2 = np.array([0.5 * (b2[i_le - k] + b2[i_le + k]) for k in range(1, i_le)])
    yc_inner = np.array([yc_mm[i_le - k] for k in range(1, i_le)])
    np.testing.assert_allclose(mid2, yc_inner, atol=1e-9)
    assert float(np.min(half_t2 / np.maximum(half_t0, 1e-9))) < 0.80

    # Also verify _section_loop passes yc_mm through to apply_features (at stagger=0, z == b).
    x_s, pts_base = _section_loop(
        r=40.0, r_frac=0.0, chord=chord, stagger_deg=0.0, thickness=0.08,
        max_camber=0.08, camber_pos=0.4, sweep=0.0, skew=0.0, le_sweep=0.0,
        lean_deg=0.0, n_chord=60, features=Features(),
    )
    _, pts_dimp = _section_loop(
        r=40.0, r_frac=0.0, chord=chord, stagger_deg=0.0, thickness=0.08,
        max_camber=0.08, camber_pos=0.4, sweep=0.0, skew=0.0, le_sweep=0.0,
        lean_deg=0.0, n_chord=60, features=feat,
    )
    j_le = int(np.argmin(x_s))
    for k in range(1, j_le):
        mid_base = 0.5 * (pts_base[j_le - k].z + pts_base[j_le + k].z)
        mid_dimp = 0.5 * (pts_dimp[j_le - k].z + pts_dimp[j_le + k].z)
        assert abs(mid_dimp - mid_base) < 1e-9


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
