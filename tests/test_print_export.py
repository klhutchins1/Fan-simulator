# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
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
    gripped = dataclasses.replace(base, grip_count=20, grip_dia_mm=0.8, grip_clearance_mm=0.35)
    v_over = export_print_ready(p, tmp_path / "over.stl", mount=over).volume_mm3
    v_grip = export_print_ready(p, tmp_path / "grip.stl", mount=gripped).volume_mm3
    assert v_grip > v_over, "grip pads must fuse material back into the oversize cup"
    assert v_grip < solid_v


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
    assert back.motor_mount.grip_count == 20 and back.motor_mount.grip_dia_mm == 0.8


def test_readme_flags_placeholder_bore(tmp_path):
    p = _simple_params()
    rep = export_print_ready(p, tmp_path / "b.stl", bore=BoreSpec(bore_dia_mm=5.0))
    bal = balance_summary(p, 2000)
    md = print_readme("t", p, "PETG", rep, bal, recommend_print_settings("PETG"),
                      BoreSpec(bore_dia_mm=5.0), {"cfm_free": 80.0})
    assert "PLACEHOLDER" in md and "5.00 mm" in md and "Balance" in md
