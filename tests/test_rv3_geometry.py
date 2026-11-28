"""RV-3 long-form geometry review tests for ``fansim/geometry/airfoil.py`` and ``blade.py``.

Covers first-principles analytical verification of airfoil sections, 3-D coordinate/sign/handedness
conventions, lazy CadQuery isolation, edge-case input validation, and regression tests for every
bug fixed in RV-3 module 4.
"""

from __future__ import annotations

import copy
import math
import subprocess
import sys

import numpy as np
import pytest

from fansim.geometry.airfoil import (
    SECTION_NACA,
    SECTION_PLATE,
    naca4,
    rounded_plate,
    section_loop_2d,
)
from fansim.geometry.blade import (
    THICK_SCALE_LO,
    BladeParams,
    RadialStation,
    Vec,
    _interp_stations,
    _section_loop,
    _thick_scale_kw,
    apply_tip_shape,
    apply_winglet,
    blade_solidity,
    build_blade_solid,
    build_hub,
    clip_blade_below,
    fuse_impeller,
    min_blade_wall_mm,
    validate_blade_params,
)
from fansim.geometry.features import Features

# ---------------------------------------------------------------------------
# 1. First-principles analytical airfoil checks (Abbott & von Doenhoff 1959)
# ---------------------------------------------------------------------------


def test_naca4_exact_thickness_and_closed_te():
    """NACA 0012 closed-TE formula: exact closure at x=1 and max thickness 0.12 near x=0.3."""
    t = 0.12
    loop, xp = naca4(0.0, 0.4, t, n_points=101, return_chord_param=True)
    # Closed loop: first and last points are TE (1, 0)
    assert np.allclose(loop[0], [1.0, 0.0], atol=1e-12)
    assert np.allclose(loop[-1], [1.0, 0.0], atol=1e-12)
    # Exact formula on upper surface (indices 0..100, TE -> LE)
    x_u = xp[:101]
    y_u = loop[:101, 1]
    yt_ref = 5.0 * t * (
        0.2969 * np.sqrt(x_u)
        - 0.1260 * x_u
        - 0.3516 * x_u**2
        + 0.2843 * x_u**3
        - 0.1036 * x_u**4
    )
    assert np.allclose(y_u, yt_ref, atol=1e-12)
    assert np.allclose(loop[:101, 0], x_u, atol=1e-12)
    # Exact symmetry between upper and lower surfaces
    y_l = loop[100:, 1]
    assert np.allclose(y_l, -y_u[::-1], atol=1e-12)
    # Peak thickness within 1% of nominal t at x ~ 0.30
    assert (loop[:, 1].max() - loop[:, 1].min()) == pytest.approx(t, rel=0.01)


def test_naca4_camber_line_exact_peak_at_p():
    """NACA 4412: meanline peak equals m=0.04 at x=p=0.4 with zero slope (yu+yl)/2 = m."""
    m, p, t = 0.04, 0.4, 0.12
    # Evaluate with dense grid; check midpoint at exact x = p via upper+lower pairing
    loop, xp = naca4(m, p, t, n_points=201, return_chord_param=True)
    upper = loop[:201][::-1]  # LE -> TE
    lower = loop[200:]  # LE -> TE
    x_le_te = xp[:201][::-1]
    # Exact meanline: (upper + lower) / 2 = (x, yc) because ±yt*(sin, cos) cancel identically!
    mean_x = 0.5 * (upper[:, 0] + lower[:, 0])
    mean_y = 0.5 * (upper[:, 1] + lower[:, 1])
    assert np.allclose(mean_x, x_le_te, atol=1e-12)
    yc_ref = np.where(
        x_le_te < p,
        (m / p**2) * (2 * p * x_le_te - x_le_te**2),
        (m / (1 - p) ** 2) * ((1 - 2 * p) + 2 * p * x_le_te - x_le_te**2),
    )
    assert np.allclose(mean_y, yc_ref, atol=1e-12)
    assert float(mean_y.max()) == pytest.approx(m, abs=1e-4)
    assert float(x_le_te[int(np.argmax(mean_y))]) == pytest.approx(p, abs=0.01)


def test_loop_ordering_and_capped_loft_le_index_parity():
    """Both naca4 and rounded_plate place LE at exact index n // 2 after dropping closure."""
    for fam in (SECTION_NACA, SECTION_PLATE):
        loop, xp = section_loop_2d(
            fam, max_camber=0.04, camber_pos=0.4, thickness=0.08, n_points=60,
            return_chord_param=True,
        )
        assert np.allclose(loop[0], loop[-1])
        xp_open = xp[:-1]
        n = len(xp_open)
        assert n % 2 == 0, f"{fam} open loop length must be even for _capped_loft pairing"
        le = n // 2
        assert xp_open[0] == pytest.approx(1.0, abs=1e-12)
        assert xp_open[le] == pytest.approx(0.0, abs=1e-12)
        assert int(np.argmin(xp_open)) == le


# ---------------------------------------------------------------------------
# 2. First-principles 3-D placement, signs, units, and solidity checks
# ---------------------------------------------------------------------------


def test_section_loop_exact_stagger_camber_and_mirror_symmetry():
    """Positive and negative stagger sections are exact t -> -t mirrors with matching Z."""
    kw = {
        "r": 40.0,
        "r_frac": 0.5,
        "chord": 32.0,
        "thickness": 0.08,
        "max_camber": 0.05,
        "camber_pos": 0.4,
        "sweep": 2.0,
        "skew": 0.0,
        "le_sweep": 1.5,
        "lean_deg": 0.0,
        "n_chord": 60,
        "features": Features(),
        "wrap": False,
    }
    x_pos, pts_pos = _section_loop(stagger_deg=30.0, le_skew=3.0, **kw)
    x_neg, pts_neg = _section_loop(stagger_deg=-30.0, le_skew=-3.0, **kw)
    assert np.allclose(x_pos, x_neg)
    for p, q in zip(pts_pos, pts_neg):
        assert p.x == pytest.approx(q.x, abs=1e-12)
        assert p.y == pytest.approx(-q.y, abs=1e-12)
        assert p.z == pytest.approx(q.z, abs=1e-12)
    # Chord vector (TE -> LE) makes exact 30 deg angle with rotation plane (when le_sweep=le_skew=0)
    x0, pts0 = _section_loop(stagger_deg=30.0, le_skew=0.0, **{**kw, "le_sweep": 0.0})
    le, te = pts0[int(np.argmin(x0))], pts0[int(np.argmax(x0))]
    dt = le.y - te.y
    dz = le.z - te.z
    assert math.hypot(dt, dz) == pytest.approx(32.0, abs=1e-9)
    assert math.degrees(math.atan2(dz, dt)) == pytest.approx(30.0, abs=1e-9)


def test_blade_solidity_exact_analytical_formula():
    """Projected solidity B * c * cos(beta) / (2 * pi * r) at hub, mid, tip."""
    from fansim.geometry.blade import r_frac_at_radius

    # With root_embed=0, physical hub/mid/tip sit directly at r_frac = 0.0, 0.5, 1.0.
    p0 = BladeParams(
        n_blades=9,
        hub_radius=20.0,
        tip_radius=60.0,
        root_embed=0.0,
        stations=[
            RadialStation(0.0, chord=25.0, stagger_deg=45.0),
            RadialStation(0.5, chord=35.0, stagger_deg=30.0),
            RadialStation(1.0, chord=30.0, stagger_deg=20.0),
        ],
    )
    sol0 = blade_solidity(p0)
    assert sol0["hub"] == pytest.approx(9 * 25.0 * math.cos(math.radians(45.0)) / (2 * math.pi * 20.0))
    assert sol0["mid"] == pytest.approx(9 * 35.0 * math.cos(math.radians(30.0)) / (2 * math.pi * 40.0))
    assert sol0["tip"] == pytest.approx(9 * 30.0 * math.cos(math.radians(20.0)) / (2 * math.pi * 60.0))

    # #117: With root_embed > 0, blade_solidity reads chord & stagger at the CAD builder's
    # r_frac_at_radius(r) for the exposed physical radii (r_hub, r_mid, r_tip).
    p = BladeParams(
        n_blades=9,
        hub_radius=20.0,
        tip_radius=60.0,
        root_embed=4.0,
        stations=p0.stations,
    )
    sol = blade_solidity(p)
    # r0 = 16, span = 44 -> f(20) = 4/44 = 1/11; f(40) = 24/44 = 6/11; f(60) = 1.0
    f_hub = r_frac_at_radius(p, 20.0)
    f_mid = r_frac_at_radius(p, 40.0)
    c_hub = 25.0 + (35.0 - 25.0) * (f_hub / 0.5)
    b_hub = 45.0 + (30.0 - 45.0) * (f_hub / 0.5)
    c_mid = 35.0 + (30.0 - 35.0) * ((f_mid - 0.5) / 0.5)
    b_mid = 30.0 + (20.0 - 30.0) * ((f_mid - 0.5) / 0.5)
    assert sol["hub"] == pytest.approx(9 * c_hub * math.cos(math.radians(b_hub)) / (2 * math.pi * 20.0))
    assert sol["mid"] == pytest.approx(9 * c_mid * math.cos(math.radians(b_mid)) / (2 * math.pi * 40.0))
    assert sol["tip"] == pytest.approx(sol0["tip"])


# ---------------------------------------------------------------------------
# 3. Bug fix: lazy CadQuery import & Vec on pure-math paths
# ---------------------------------------------------------------------------


def test_blade_pure_math_paths_do_not_import_cadquery():
    """Importing blade.py and running pure-math helpers must not trigger eager OCCT/CadQuery import."""
    code = """
import sys
from fansim.geometry.blade import (
    BladeParams,
    Vec,
    _hub_axial_range,
    _root_axial_span,
    _section_loop,
    _section_points_3d,
    blade_hang_below_hub_mm,
    blade_solidity,
    open_tip_rmax_mm,
    tip_le_te_z,
    validate_blade_params,
)
from fansim.geometry.features import Features

p = BladeParams(section_wrap="cylinder")
validate_blade_params(p)
blade_solidity(p)
open_tip_rmax_mm(p)
blade_hang_below_hub_mm(p)
_hub_axial_range(p)
_root_axial_span(p)
tip_le_te_z(p)
pts = _section_points_3d(
    r=40.0, r_frac=0.5, chord=30.0, stagger_deg=25.0, thickness=0.06,
    max_camber=0.04, camber_pos=0.4, sweep=0.0, skew=0.0, le_sweep=0.0,
    lean_deg=10.0, n_chord=30, features=Features(), wrap=True,
)
assert isinstance(pts[0], Vec), f"expected Vec, got {type(pts[0])}"
assert "cadquery" not in sys.modules, "cadquery was eagerly imported on pure-math path"
assert "OCP" not in sys.modules, "OCP was eagerly imported on pure-math path"
"""
    res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)
    assert res.returncode == 0, f"stdout:\n{res.stdout}\nstderr:\n{res.stderr}"


def test_vec_is_lightweight_3tuple_with_xyz_attributes():
    v = Vec(1.5, -2.0, 3.25)
    assert (v.x, v.y, v.z) == (1.5, -2.0, 3.25)
    assert isinstance(v, tuple) and tuple(v) == (1.5, -2.0, 3.25)


# ---------------------------------------------------------------------------
# 4. Bug fix: falsy-zero in _thick_scale_kw
# ---------------------------------------------------------------------------


def test_thick_scale_kw_preserves_zero_for_plate_and_clamps_for_naca():
    """0.0 is a valid sharp knife edge for plate (must NOT become 1.0 via `or 1.0`)."""
    plate_both_zero = BladeParams(
        section_family=SECTION_PLATE, le_thick_scale=0.0, te_thick_scale=0.0
    )
    kw = _thick_scale_kw(plate_both_zero)
    assert kw["te_thick_scale"] == pytest.approx(0.0)
    assert kw["le_thick_scale"] == pytest.approx(0.0)

    plate_le_zero = BladeParams(
        section_family=SECTION_PLATE, le_thick_scale=0.0, te_thick_scale=0.25
    )
    kw2 = _thick_scale_kw(plate_le_zero)
    assert kw2["te_thick_scale"] == pytest.approx(0.25)
    assert kw2["le_thick_scale"] == pytest.approx(0.0)

    naca_zero = BladeParams(section_family=SECTION_NACA, le_thick_scale=0.0, te_thick_scale=0.0)
    kw3 = _thick_scale_kw(naca_zero)
    assert kw3["le_thick_scale"] == pytest.approx(THICK_SCALE_LO)
    assert kw3["te_thick_scale"] == pytest.approx(THICK_SCALE_LO)


# ---------------------------------------------------------------------------
# 5. Bug fix: build_blade_solid forwards _trim_tip through chord realisation
# ---------------------------------------------------------------------------


def test_build_blade_solid_forwards_trim_tip_false(monkeypatch):
    """Calling build_blade_solid(p, _trim_tip=False) must NOT silently trim on recursive call."""
    import fansim.geometry.blade as gb
    import fansim.geometry.chord_realisation as cr

    called = {"trim": 0}
    real_trim = gb._trim_blade_to_tip_cylinder

    def spy_trim(blade, tip_radius):
        called["trim"] += 1
        return real_trim(blade, tip_radius)

    # Avoid slow full fixed-point measurement: pass params through with chord_basis="loft"
    monkeypatch.setattr(cr, "prepare_loft_chords", lambda p: copy.deepcopy(p))
    monkeypatch.setattr(gb, "_trim_blade_to_tip_cylinder", spy_trim)

    p = BladeParams(cylindrical_tip=True, n_span=6, n_chord=20)
    solid = build_blade_solid(p, _trim_tip=False)
    assert solid is not None
    assert called["trim"] == 0, "build_blade_solid dropped _trim_tip=False across recursive call"


# ---------------------------------------------------------------------------
# 6. Bug fix: fuse_impeller checks single-solid invariant after shroud ring fuse
# ---------------------------------------------------------------------------


def test_fuse_impeller_rejects_unjoined_shroud_ring(monkeypatch):
    """If fusing the shroud ring leaves >1 solid, fuse_impeller must raise RuntimeError."""
    import fansim.geometry.blade as gb
    from fansim.resources import TIERS

    class _FakeShape:
        def __init__(self, n_solids: int):
            self._n = n_solids

        def Faces(self):
            return [object()] * 6

        def Solids(self):
            return [object()] * self._n

        def clean(self):
            return self

    def fake_fuse(base, tools, *, parallel):
        # Hub + blades succeeds (1 solid), but fusing the ring returns 2 detached solids
        if len(tools) == 1 and base is not hub:
            return _FakeShape(2)
        return _FakeShape(1)

    hub = _FakeShape(1)
    blades = [_FakeShape(1), _FakeShape(1)]
    ring = _FakeShape(1)
    monkeypatch.setattr(gb, "_fuse", fake_fuse)
    tier = next(t for t in TIERS if t.name == "8gb")
    with pytest.raises(RuntimeError, match="shroud ring"):
        fuse_impeller(hub, blades, ring, tier=tier)


# ---------------------------------------------------------------------------
# 7. Bug fix: input validation in airfoil.py and blade.py
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_camber": 0.02, "camber_pos": 0.4, "thickness": 0.10, "n_points": 1},
        {"max_camber": 0.02, "camber_pos": 0.4, "thickness": 0.10, "n_points": 0},
        {"max_camber": 0.02, "camber_pos": 0.4, "thickness": -0.05, "n_points": 40},
        {"max_camber": math.nan, "camber_pos": 0.4, "thickness": 0.10, "n_points": 40},
        {"max_camber": 0.02, "camber_pos": math.inf, "thickness": 0.10, "n_points": 40},
        {"max_camber": 0.02, "camber_pos": 0.4, "thickness": math.nan, "n_points": 40},
    ],
)
def test_naca4_rejects_invalid_inputs(kwargs):
    with pytest.raises(ValueError):
        naca4(**kwargs)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"thickness": 0.0, "n_points": 40},
        {"thickness": -0.05, "n_points": 40},
        {"thickness": math.nan, "n_points": 40},
        {"thickness": 0.08, "n_points": 1},
        {"thickness": 0.08, "n_points": 40, "max_camber": math.nan},
        {"thickness": 0.08, "n_points": 40, "te_face": math.inf},
    ],
)
def test_rounded_plate_rejects_invalid_inputs(kwargs):
    with pytest.raises(ValueError):
        rounded_plate(**kwargs)


def test_section_loop_2d_rejects_unknown_family():
    with pytest.raises(ValueError, match="unknown airfoil section family"):
        section_loop_2d("bogus_family", max_camber=0.02, camber_pos=0.4, thickness=0.08)


@pytest.mark.parametrize(
    "kw, match",
    [
        ({"root_embed": -1.0}, "root_embed"),
        ({"root_embed": 21.5}, "root_embed"),
        ({"root_embed": 25.0}, "root_embed"),
        ({"root_embed": math.nan}, "root_embed"),
        ({"n_span": 1}, "n_span"),
        ({"n_chord": 1}, "n_chord"),
        ({"n_blades": 2, "blade_angles_deg": [0.0, math.nan]}, "blade_angles_deg"),
        ({"hub_axial_margin": -0.5}, "hub_axial_margin"),
        ({"hub_height_mm": 0.0}, "hub_height_mm"),
        ({"shroud_thick_mm": -1.0}, "shroud_thick_mm"),
        ({"shroud_height_frac": 1.5}, "shroud_height_frac"),
        ({"hub_nose_mm": -2.0}, "hub_nose_mm"),
        ({"blade_z_mm": math.nan}, "blade_z_mm"),
    ],
)
def test_validate_blade_params_rejects_edge_cases(kw, match):
    with pytest.raises(ValueError, match=match):
        validate_blade_params(BladeParams(**kw))


def test_wrapped_section_loop_rejects_nonpositive_radius():
    with pytest.raises(ValueError, match="r > 0"):
        _section_loop(
            r=0.0, r_frac=0.0, chord=20.0, stagger_deg=25.0, thickness=0.08,
            max_camber=0.02, camber_pos=0.4, sweep=0.0, skew=0.0, le_sweep=0.0,
            lean_deg=0.0, n_chord=30, features=Features(), wrap=True,
        )


def test_min_blade_wall_mm_empty_stations_raises_clear_error():
    with pytest.raises(ValueError, match="station"):
        min_blade_wall_mm(BladeParams(stations=[]))


def test_apply_tip_shape_and_winglet_edge_guards():
    p = apply_tip_shape(BladeParams(), tip_round=0.5, start_frac=0.80, n=0)
    assert max(s.r_frac for s in p.stations) == pytest.approx(1.0)

    short_tip = BladeParams(
        stations=[RadialStation(0.0, 30.0, 25.0), RadialStation(0.7, 30.0, 25.0)]
    )
    out = apply_winglet(short_tip, span_frac=0.85, sweep_add=3.0)
    rfs = [s.r_frac for s in out.stations]
    assert rfs == sorted(rfs)


# ---------------------------------------------------------------------------
# 8. Bug fix: no silently swallowed exceptions in blade.py
# ---------------------------------------------------------------------------


def test_interp_stations_pchip_duplicate_rfrac_warns_before_fallback():
    p = BladeParams(
        span_interp="pchip",
        stations=[
            RadialStation(0.0, 30.0, 25.0),
            RadialStation(0.5, 35.0, 25.0),
            RadialStation(0.5, 36.0, 25.0),
            RadialStation(1.0, 32.0, 22.0),
        ],
    )
    with pytest.warns(RuntimeWarning, match="PCHIP"):
        it = _interp_stations(p, 9)
    assert len(it["chord"]) == 9


def test_build_hub_rejects_unknown_profile_and_warns_on_nose_failure(monkeypatch):
    with pytest.raises(ValueError, match="hub_profile"):
        build_hub(BladeParams(hub_profile="ogive", hub_nose_mm=5.0), -10.0, 10.0)

    import cadquery as cq

    monkeypatch.setattr(cq.Workplane, "revolve", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.warns(RuntimeWarning, match="cone"):
        solid = build_hub(BladeParams(hub_profile="cone", hub_nose_mm=5.0), -10.0, 10.0)
    assert solid is not None and solid.Volume() > 0.0


def test_clip_blade_below_chains_cause_on_failure():
    """When all clip attempts fail, RuntimeError chains the underlying exception."""

    class _BadBBox:
        xmin, xmax, ymin, ymax, zmin, zmax = -20.0, 20.0, -20.0, 20.0, -20.0, 5.0

    class _BadBlade:
        def BoundingBox(self):
            return _BadBBox()

        def cut(self, _other):
            raise ValueError("occt cut failed")

        def copy(self):
            return self

        def fix(self):
            return self

    with pytest.raises(RuntimeError, match="hub-face clip failed") as excinfo:
        clip_blade_below(BladeParams(clip_below_hub=True), _BadBlade(), z_floor=-10.0)
    assert isinstance(excinfo.value.__cause__, ValueError)


# ---------------------------------------------------------------------------
# Issue #118: Geometry code health fixes
# ---------------------------------------------------------------------------


def test_rounded_plate_upper_lower_exact_mirror_symmetry():
    """#118 item 5: uncambered rounded_plate must be bit-symmetric upper vs lower."""
    loop = rounded_plate(0.10, n_points=80, max_camber=0.0, le_radius_frac=0.6, te_radius_frac=0.3)
    assert len(loop) % 2 == 1
    le_idx = len(loop) // 2
    assert loop[le_idx, 0] == pytest.approx(0.0, abs=1e-12)
    upper = loop[: le_idx + 1]
    lower_rev = loop[le_idx:][::-1]
    np.testing.assert_allclose(upper[:, 0], lower_rev[:, 0], atol=1e-12)
    np.testing.assert_allclose(upper[:, 1], -lower_rev[:, 1], atol=1e-12)


def test_apply_tip_shape_inserts_shoulder_at_start_frac():
    """#118 item 2: chord taper must start at start_frac, not jump from mid-span r_frac=0.5."""
    p = BladeParams(
        stations=[
            RadialStation(0.0, 30.0, 30.0),
            RadialStation(0.5, 40.0, 26.0),
            RadialStation(1.0, 40.0, 22.0),
        ]
    )
    apply_tip_shape(p, tip_round=0.8, start_frac=0.80, n=4)
    r_fracs = [s.r_frac for s in p.stations]
    assert any(abs(rf - 0.80) < 1e-9 for rf in r_fracs), f"missing shoulder at 0.80: {r_fracs}"
    shoulder = next(s for s in p.stations if abs(s.r_frac - 0.80) < 1e-9)
    assert shoulder.chord == pytest.approx(40.0, abs=1e-9)


def test_thick_scale_kw_defaults_missing_section_wrap_to_planar():
    """#118 item 6: missing section_wrap must default to planar (matching BladeParams)."""
    from types import SimpleNamespace

    stub = SimpleNamespace(section_family="naca", le_thick_scale=1.0, te_thick_scale=1.0)
    kw = _thick_scale_kw(stub)
    assert kw["wrap"] is False


def test_shroud_axial_range_uses_realized_chord_for_partial_shroud():
    """#118 item 1: partial shroud_axial_range anchors to realized TE inside realized tip z-span."""
    from fansim.geometry.blade import _tip_z_span, shroud_axial_range, tip_le_te_z
    from fansim.geometry.chord_realisation import prepare_loft_chords

    p = BladeParams(
        cylindrical_tip=True,
        section_wrap="planar",
        shroud_thick_mm=2.0,
        shroud_height_frac=0.5,
        stations=[
            RadialStation(0.0, 30.0, 35.0, 0.08, 0.04, 0.4),
            RadialStation(0.5, 42.0, 30.0, 0.06, 0.05, 0.4),
            RadialStation(1.0, 48.0, 25.0, 0.04, 0.05, 0.4),
        ],
    )
    z0, z1 = _tip_z_span(p)
    realized = prepare_loft_chords(p)
    z_le, z_te = tip_le_te_z(realized)
    sh = shroud_axial_range(p)
    assert sh is not None
    assert sh[0] >= z0 - 1e-6 and sh[1] <= z1 + 1e-6
    anchor = sh[1] if z_te >= z_le else sh[0]
    assert anchor == pytest.approx(z_te, abs=1e-6)


def test_build_hub_cone_has_no_annular_step_at_z_top():
    """#118 item 3: cone nose volume must match exact cylinder + flush frustum (no 1.24 mm step)."""
    R, z_bot, z_top, nose = 21.5, -10.0, 10.0, 8.0
    p = BladeParams(hub_radius=R, hub_profile="cone", hub_nose_mm=nose)
    solid = build_hub(p, z_bot, z_top)
    # Exact cylinder + frustum (r_bottom=R, r_top=0.5, height=nose), minus negligible 0.1 mm axis pinhole.
    cyl_vol = math.pi * R * R * (z_top - z_bot)
    cone_vol = (math.pi * nose / 3.0) * (R * R + R * 0.5 + 0.5 * 0.5)
    expected = cyl_vol + cone_vol
    assert solid.Volume() == pytest.approx(expected, rel=1e-3)


def test_build_impeller_preview_volume_matches_fused_without_root_embed_double_count():
    """#118 item 4: preview volume should not double-count root-embedded blade overlap."""
    from fansim.geometry.blade import build_impeller, build_impeller_preview

    p = BladeParams(n_blades=5, root_embed=4.0, n_span=5, n_chord=20)
    _, prev_vol = build_impeller_preview(p, screen=False)
    fused_vol = float(build_impeller(p).val().Volume())
    # Preview volume must match true fused solid volume within 1% (not inflated by root embed).
    assert prev_vol == pytest.approx(fused_vol, rel=0.01)


# ---------------------------------------------------------------------------
# Issues #116 / #117 (P1A): signed negative camber & builder radius mapping
# ---------------------------------------------------------------------------


def test_negative_max_camber_reflects_naca4_and_rounded_plate():
    """#117A: negative max_camber must produce exact vertical reflection, not symmetric zero-camber."""
    pos, xp_pos = naca4(0.04, 0.4, 0.12, n_points=61, return_chord_param=True)
    neg, xp_neg = naca4(-0.04, 0.4, 0.12, n_points=61, return_chord_param=True)
    np.testing.assert_allclose(xp_neg, xp_pos, atol=1e-12)
    i_le = len(pos) // 2
    assert neg[i_le, 0] == pytest.approx(0.0, abs=1e-12)
    # Upper of -m equals lower of +m reflected across y=0, and vice versa.
    np.testing.assert_allclose(neg[: i_le + 1, 0], pos[i_le:, 0][::-1], atol=1e-12)
    np.testing.assert_allclose(neg[: i_le + 1, 1], -pos[i_le:, 1][::-1], atol=1e-12)
    np.testing.assert_allclose(neg[i_le:, 0], pos[: i_le + 1, 0][::-1], atol=1e-12)
    np.testing.assert_allclose(neg[i_le:, 1], -pos[: i_le + 1, 1][::-1], atol=1e-12)

    p_pos = rounded_plate(0.08, n_points=60, max_camber=0.05, camber_pos=0.4)
    p_neg = rounded_plate(0.08, n_points=60, max_camber=-0.05, camber_pos=0.4)
    j_le = len(p_pos) // 2
    np.testing.assert_allclose(p_neg[: j_le + 1, 0], p_pos[j_le:, 0][::-1], atol=1e-12)
    np.testing.assert_allclose(p_neg[: j_le + 1, 1], -p_pos[j_le:, 1][::-1], atol=1e-12)
    # Not silently symmetric: peak meanline height equals -0.05.
    assert float(np.min(0.5 * (p_neg[: j_le + 1, 1] + p_neg[j_le:, 1][::-1]))) < -0.045


def test_radius_mapping_helpers_and_fan_bem_follow_root_embed():
    """#117B: shared builder radius helpers round-trip and fan_bem reads built radii."""
    from fansim.fan_bem import operating_point
    from fansim.geometry.blade import r_frac_at_radius, radius_at_r_frac, station_root_radius

    p_embed0 = BladeParams(
        n_blades=7,
        hub_radius=20.0,
        tip_radius=55.0,
        root_embed=0.0,
        stations=[
            RadialStation(0.0, chord=15.0, stagger_deg=45.0, max_camber=0.04),
            RadialStation(0.5, chord=30.0, stagger_deg=30.0, max_camber=0.06),
            RadialStation(1.0, chord=35.0, stagger_deg=20.0, max_camber=0.05),
        ],
    )
    p_embed6 = BladeParams(
        n_blades=7,
        hub_radius=20.0,
        tip_radius=55.0,
        root_embed=6.0,
        stations=p_embed0.stations,
    )
    assert station_root_radius(p_embed6) == pytest.approx(14.0)
    for f in (0.0, 0.25, 0.5, 0.75, 1.0):
        r = radius_at_r_frac(p_embed6, f)
        assert r_frac_at_radius(p_embed6, r) == pytest.approx(f, abs=1e-12)
    assert r_frac_at_radius(p_embed6, 20.0) == pytest.approx(6.0 / 41.0, abs=1e-12)
    assert r_frac_at_radius(p_embed6, 55.0) == pytest.approx(1.0, abs=1e-12)

    # fan_bem must reflect the CAD shift when root_embed changes (exposed span sees larger chords/lower stagger).
    op0 = operating_point(p_embed0, rpm=2000.0, flow_m3s=0.015)
    op6 = operating_point(p_embed6, rpm=2000.0, flow_m3s=0.015)
    assert abs(op6.dp_static_pa - op0.dp_static_pa) > 0.1


