"""Fast tests for the print-export path (no CFD, no Docker)."""

from __future__ import annotations

import dataclasses

from fansim.geometry.blade import BladeParams, RadialStation, set_uneven_spacing
from fansim.manufacturability.print_export import (
    BoreSpec,
    balance_summary,
    bore_hub,
    export_print_ready,
    print_readme,
    recommend_print_settings,
)
from fansim.geometry import build_impeller


def _simple_params(n_blades: int = 5) -> BladeParams:
    stations = [
        RadialStation(0.0, 30.0, 26.0, 0.10, 0.02, 0.4, 0.0, 0.0, 0.0),
        RadialStation(0.5, 34.0, 26.0, 0.08, 0.02, 0.4, 2.0, 0.0, 10.0),
        RadialStation(1.0, 30.0, 22.0, 0.06, 0.02, 0.4, 4.0, 0.0, 20.0),
    ]
    return BladeParams(n_blades=n_blades, stations=stations)


def test_export_solid_is_watertight(tmp_path):
    rep = export_print_ready(_simple_params(), tmp_path / "solid.stl")
    assert rep.ok and rep.n_bodies == 1 and rep.volume_mm3 > 0
    step = tmp_path / "solid.step"
    assert step.is_file() and step.stat().st_size > 100
    # ISO-10303 header
    head = step.read_text(encoding="utf-8", errors="ignore")[:80]
    assert "ISO-10303" in head or "HEADER" in head


def test_export_can_skip_step(tmp_path):
    export_print_ready(_simple_params(), tmp_path / "no_step.stl", also_step=False)
    assert not (tmp_path / "no_step.step").exists()


def test_bore_removes_material_and_stays_watertight(tmp_path):
    p = _simple_params()
    solid = export_print_ready(p, tmp_path / "solid.stl")
    bored = export_print_ready(p, tmp_path / "bored.stl", bore=BoreSpec(bore_dia_mm=5.0))
    assert bored.ok, "bored hub must stay a single watertight body"
    assert bored.volume_mm3 < solid.volume_mm3, "a through-bore must remove material"


def test_bore_hub_direct_and_set_screw(tmp_path):
    model = build_impeller(_simple_params())
    v0 = model.val().Volume()
    bored = bore_hub(model, BoreSpec(bore_dia_mm=4.0, set_screw_dia_mm=2.5))
    assert bored.val().Volume() < v0


def test_zero_bore_is_noop():
    model = build_impeller(_simple_params())
    same = bore_hub(model, BoreSpec(bore_dia_mm=0.0))
    assert abs(same.val().Volume() - model.val().Volume()) < 1e-6


def test_even_spacing_is_balanced():
    b = balance_summary(_simple_params(7), rpm=2000)
    assert b["balanced"] and b["even_spacing"]
    assert b["normalized_unbalance"] <= 1e-6


def test_balanced_uneven_spacing_still_balanced():
    p = _simple_params(6)
    set_uneven_spacing(p, spread=0.3)
    b = balance_summary(p, rpm=2000)
    # balanced_uneven_spacing is self-balancing by construction (or falls back to even)
    assert b["balanced"], "balanced-uneven pattern should null the static unbalance"


def test_broken_pattern_reports_counterweight():
    p = _simple_params(4)
    p.blade_angles_deg = [0.0, 80.0, 170.0, 260.0]  # deliberately lopsided -> residual
    b = balance_summary(p, rpm=2000)
    assert not b["balanced"]
    assert b["counterweight_mr"] > 0 and b["residual_force_rel"] > 0


def test_print_settings_defaults_and_petg():
    s = recommend_print_settings("PETG")
    assert s["material"] == "PETG" and s["nozzle_c"] == 240 and s["bed_c"] == 80
    assert s["wall_loops"] >= 1 and s["layer_height_mm"] > 0
    # unknown material falls back to the default
    assert recommend_print_settings("UNOBTANIUM")["material"] == "PETG"


def test_motor_mount_carves_when_hub_fits(tmp_path):
    from fansim.fan_spec import get_fan_spec
    mount = get_fan_spec("a12x25").motor_mount
    p = dataclasses.replace(_simple_params(), hub_radius=30.0)  # wide enough for the cup
    solid = export_print_ready(p, tmp_path / "solid.stl")
    carved = export_print_ready(p, tmp_path / "carved.stl", mount=mount)
    assert carved.mount_fits is True
    assert carved.ok, "carved cup must stay watertight"
    assert carved.volume_mm3 < solid.volume_mm3, "the cavity must remove material"
    assert "grip" in (carved.mount_msg or "").lower()


def test_motor_mount_grips_add_back_vs_smooth_cup(tmp_path):
    from fansim.fan_spec import get_fan_spec
    base = get_fan_spec("a12x25").motor_mount
    p = dataclasses.replace(_simple_params(), hub_radius=30.0)
    solid_v = export_print_ready(p, tmp_path / "solid.stl").volume_mm3
    over = dataclasses.replace(base, grip_count=0, grip_clearance_mm=0.35)
    gripped = dataclasses.replace(base, grip_count=20, grip_dia_mm=2.4, grip_clearance_mm=0.35)
    v_over = export_print_ready(p, tmp_path / "over.stl", mount=over).volume_mm3
    v_grip = export_print_ready(p, tmp_path / "grip.stl", mount=gripped).volume_mm3
    assert v_grip > v_over, "grip pads must fuse material back into the oversize cup"
    assert v_grip < solid_v


def test_motor_mount_grips_do_not_protrude_below_rear_face():
    """Fused grip pads must stay flush with the hub rear (−Z) face, not poke out the back.

    They reuse the cavity *cutter's* z-range, which overshoots the face by ``eps`` for a clean
    subtractive break — correct for a cut, but the *fused* pads must not inherit that overshoot
    (it would leave a ring of little nubs sticking below the hub).
    """
    from fansim.fan_spec import get_fan_spec
    from fansim.manufacturability.print_export import build_impeller_with_mount

    mount = get_fan_spec("a12x25").motor_mount
    p = dataclasses.replace(_simple_params(), hub_radius=30.0)  # wide enough for the cup
    aero = build_impeller(p)
    carved, fits, _msg = build_impeller_with_mount(p, mount)
    assert fits
    zmin_aero = aero.val().BoundingBox().zmin
    zmin_carved = carved.val().BoundingBox().zmin
    # The cup cut/bore only remove material; the only thing that can extend the model below the
    # aero rear face is a fused grip pad. It must not.
    assert zmin_carved >= zmin_aero - 0.05, (
        f"grip pads protrude {zmin_aero - zmin_carved:.3f} mm below the hub rear face"
    )


def test_motor_mount_refuses_small_hub(tmp_path):
    from fansim.fan_spec import get_fan_spec
    mount = get_fan_spec("a12x25").motor_mount
    p = _simple_params()
    p.hub_radius = 15.0  # < 19.8 mm needed for the 37.25 mm cup + 1.2 mm wall
    rep = export_print_ready(p, tmp_path / "small.stl", mount=mount)
    assert rep.mount_fits is False
    assert "too small" in rep.mount_msg


def test_fan_spec_motor_mount_roundtrips():
    from fansim.fan_spec import fan_spec_from_dict, fan_spec_to_dict, get_fan_spec
    spec = get_fan_spec("a12x25")
    assert spec.motor_mount is not None and spec.motor_mount.cavity_dia_mm == 37.25
    back = fan_spec_from_dict(fan_spec_to_dict(spec))
    assert back.motor_mount.cavity_dia_mm == 37.25 and back.motor_mount.rear_bore_dia_mm == 20.0
    assert back.motor_mount.grip_count == 20 and back.motor_mount.grip_dia_mm == 2.4
    assert back.motor_mount.grip_protrude_mm == 0.7


def test_readme_flags_placeholder_bore(tmp_path):
    p = _simple_params()
    rep = export_print_ready(p, tmp_path / "b.stl", bore=BoreSpec(bore_dia_mm=5.0))
    bal = balance_summary(p, 2000)
    md = print_readme("t", p, "PETG", rep, bal, recommend_print_settings("PETG"),
                      BoreSpec(bore_dia_mm=5.0), {"cfm_free": 80.0})
    assert "PLACEHOLDER" in md and "5.00 mm" in md and "Balance" in md


def _qa18_short_hub_params():
    import json
    from pathlib import Path

    from fansim.geometry.features import Features
    from fansim.optimize.search_space import blade_from_flat
    d = json.loads((Path(__file__).parent / "data" / "qa18_short_hub_flat.json").read_text(encoding="utf-8"))
    return blade_from_flat(d["flat"], Features(**d["features"]))


def test_mount_hub_params_grows_short_hub_to_mount_minimum():
    """QA-18: a hub shorter than the cup must be grown before carving (min_hub_height_mm)."""
    from fansim.fan_spec import get_fan_spec
    from fansim.geometry.blade import _hub_axial_range
    from fansim.manufacturability.print_export import mount_hub_params

    mount = get_fan_spec("a12x25").motor_mount
    p = _qa18_short_hub_params()
    z0, z1 = _hub_axial_range(p)
    assert z1 - z0 < 13.0  # the repro really is shorter than the 13 mm cup
    grown, note = mount_hub_params(p, mount)
    g0, g1 = _hub_axial_range(grown)
    assert g1 - g0 >= 15.0 - 1e-6
    assert "hub" in note and "15.0" in note
    same, note2 = mount_hub_params(grown, mount)  # already tall enough: unchanged, no note
    assert same is grown and note2 == ""


def test_motor_cup_has_a_floor_on_a_short_hub():
    """QA-18 end to end: the carved cup on a formerly too-short hub leaves solid above 13 mm."""
    import cadquery as cq

    from fansim.fan_spec import get_fan_spec
    from fansim.manufacturability.print_export import build_impeller_with_mount

    mount = get_fan_spec("a12x25").motor_mount
    carved, fits, msg = build_impeller_with_mount(_qa18_short_hub_params(), mount)
    assert fits, msg
    solid = carved.val()
    zmin = solid.BoundingBox().zmin
    # Between the rear bore (r 10) and the cavity wall (r 18.6) the floor sits 13 mm above the face.
    probe = cq.Vector(14.0, 0.0, zmin + mount.cavity_depth_mm + 0.5)
    assert solid.isInside(probe), "cup goes straight through the hub (no floor)"
