"""The airfoil LE leads (was placed back-to-front before 2026-09-29).

As-built rotation is omega_z=+1 (moving +theta = +t), pumping -Z (air enters from +Z), so the
blade's leading side is +t / upstream +Z. Chordwise placement must put x=0 (LE) there, without
changing stagger, concave side, handedness or the direction proof.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import trimesh

from fansim.audit.direction import prove_direction, tip_lead_sign
from fansim.geometry import build_impeller, export_stl
from fansim.geometry.blade import _section_loop
from fansim.geometry.config import load_blade_params
from fansim.geometry.features import Features
from fansim.validation.section_compare import measure_sections

_ROOT = Path(__file__).resolve().parents[1]
_STOCK_PARAMS = _ROOT / "config" / "problems" / "a12x25_reference.yaml"


def _loop(stagger: float, rf: float = 0.5, **kw):
    return _section_loop(
        r=40.0, r_frac=rf, chord=30.0, stagger_deg=stagger, thickness=0.06,
        max_camber=0.04, camber_pos=0.4, sweep=0.0, skew=0.0, le_sweep=0.0,
        lean_deg=0.0, n_chord=48, features=Features(), **kw)


def test_section_le_leads_upstream_for_as_built_rotation():
    x, pts = _loop(30.0)  # lean 0: circumferential t == world y at x = r
    le, te = pts[int(np.argmin(x))], pts[int(np.argmax(x))]
    assert le.y > te.y  # LE has larger t (leads for +theta rotation)
    assert le.z > te.z  # LE is upstream (+Z; the fan pumps -Z)


def test_opposite_swirl_section_le_leads_for_negative_theta():
    """CROR rear (negative stagger, spins -theta): LE leads toward -t."""
    x, pts = _loop(-30.0)
    le, te = pts[int(np.argmin(x))], pts[int(np.argmax(x))]
    assert le.y < te.y


def test_tip_notches_bite_toward_le():
    """Notches remove chord from the TE side: the TE moves toward the LE."""
    x0, p0 = _loop(30.0, rf=0.90)
    x1, p1 = _loop(30.0, rf=0.90, tip_notch_count=3, tip_notch_depth_mm=3.0)
    dy = np.array([q1.y - q0.y for q0, q1 in zip(p0, p1)])
    assert dy.max() > 0.5 and dy.min() > -1e-9  # only shifts toward +t (LE side)
    assert dy[int(np.argmax(x0))] >= dy[int(np.argmin(x0))]  # TE end moves, LE stays


@pytest.mark.slow
def test_stock_built_section_camber_pos_matches_recipe(tmp_path):
    params = load_blade_params(_STOCK_PARAMS)
    stl = tmp_path / "stock_impeller.stl"
    export_stl(build_impeller(params), stl)
    mesh = trimesh.load(str(stl), force="mesh")

    rows = [r for r in measure_sections(stl) if 0.55 <= r["r_frac"] <= 0.75 and r["n_blades"]]
    assert rows
    for r in rows:
        assert abs(r["camber_pos"] - 0.40) < 0.1, r

    p = prove_direction(mesh)
    assert p.verdict == "CONCLUSIVE", p.note
    assert (p.omega_sign, p.pump_sign, p.chirality) == (+1, -1, -1)
    assert tip_lead_sign(mesh) == +1


def test_fitted_stock_blade_is_trimmed_to_tip_cylinder():
    """Regression: an empty first OCCT intersect left the blade untrimmed (r=60 > 54.5)."""
    from fansim.cockpit.placement import fit_envelope
    from fansim.fan_spec import get_fan_spec
    from fansim.geometry.blade import build_blade_solid
    from fansim.optimize.search_space import blade_from_flat, stock_blade_flat

    spec = get_fan_spec("a12x25")
    p = blade_from_flat(fit_envelope(stock_blade_flat("a12x25"), spec).flat)
    verts, _ = build_blade_solid(p).tessellate(0.05)
    assert max(np.hypot(v.x, v.y) for v in verts) <= p.tip_radius + 0.05
