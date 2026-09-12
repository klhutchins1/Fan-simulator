# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
import math
from pathlib import Path

import optuna

from fansim.cockpit.placement import blade_max_dia
from fansim.geometry.blade import BladeParams, SHROUD_DEFAULT_MM
from fansim.manufacturability.fdm_rules import check_printability
from fansim.optimize.search_space import blade_from_flat, suggest_params


def test_zero_shroud_is_same_diameter_as_today():
    p = BladeParams()
    assert getattr(p, "shroud_thick_mm", None) == 0.0
    open_dia = blade_max_dia(p)
    p.shroud_thick_mm = 0.0
    assert blade_max_dia(p) == open_dia


def test_shroud_grows_diameter_by_twice_thickness():
    p = BladeParams()
    open_dia = blade_max_dia(p)
    p.shroud_thick_mm = SHROUD_DEFAULT_MM
    assert abs(blade_max_dia(p) - (open_dia + 2.0 * SHROUD_DEFAULT_MM)) < 1e-6


def test_thin_shroud_is_unprintable():
    p = BladeParams()
    p.shroud_thick_mm = 0.4
    r = check_printability(p)
    assert r.printable is False
    assert "shroud" in r.reason.lower()


def test_nudge_off_zero_snaps_to_min_printable_wall():
    """Cockpit slider step used to land on 0.2 mm — a hair-thin ring that still draws."""
    from fansim.geometry.blade import SHROUD_MIN_WALL_MM, normalize_shroud_thick_mm

    assert normalize_shroud_thick_mm(0.0) == 0.0
    assert normalize_shroud_thick_mm(0.2) == SHROUD_MIN_WALL_MM
    p = blade_from_flat({
        "n_blades": 7, "chord_root": 34, "chord_mid": 44, "chord_tip": 38,
        "stagger_root": 26, "stagger_mid": 26, "stagger_tip": 22,
        "sweep_mid": 3, "sweep_tip": 5, "max_camber": 0.05,
        "shroud_thick_mm": 0.2,
    })
    assert p.shroud_thick_mm == SHROUD_MIN_WALL_MM
    assert check_printability(p).printable


def test_preview_note_for_thin_shroud_does_not_blame_tip_thickness():
    from fansim.manufacturability.fdm_rules import preview_unprintable_note

    note = preview_unprintable_note("shroud wall 0.20 mm < min wall 0.80 mm")
    assert "Shroud thickness" in note
    assert "Thickness tip" not in note


def test_default_shroud_on_baseline_is_printable():
    p = BladeParams()
    p.shroud_thick_mm = SHROUD_DEFAULT_MM
    assert check_printability(p).printable


def test_preview_volume_grows_with_shroud():
    from fansim.geometry.blade import build_impeller_preview

    open_mesh, open_vol = build_impeller_preview(BladeParams())
    p = BladeParams()
    p.shroud_thick_mm = SHROUD_DEFAULT_MM
    _, sh_vol = build_impeller_preview(p)
    assert sh_vol > open_vol


def test_bem_shrouded_shutoff_beats_open_tip():
    from fansim.fan_bem import pq_curve

    open_c = pq_curve(BladeParams(), rpm=2000)
    p = BladeParams()
    p.shroud_thick_mm = SHROUD_DEFAULT_MM
    sh_c = pq_curve(p, rpm=2000)
    assert sh_c.shutoff_dp_pa > open_c.shutoff_dp_pa


def test_bem_partial_ring_matches_open_tip():
    from fansim.fan_bem import pq_curve

    open_c = pq_curve(BladeParams(), rpm=2000)
    p = BladeParams()
    p.shroud_thick_mm = SHROUD_DEFAULT_MM
    p.shroud_height_frac = 0.3
    part_c = pq_curve(p, rpm=2000)
    assert part_c.shutoff_dp_pa == open_c.shutoff_dp_pa


def test_blade_from_flat_roundtrips_shroud():
    p = blade_from_flat({
        "n_blades": 7, "chord_root": 34, "chord_mid": 44, "chord_tip": 38,
        "stagger_root": 26, "stagger_mid": 26, "stagger_tip": 22,
        "sweep_mid": 3, "sweep_tip": 5, "max_camber": 0.05,
        "shroud_thick_mm": SHROUD_DEFAULT_MM,
    })
    assert p.shroud_thick_mm == SHROUD_DEFAULT_MM


def test_blade_from_flat_defaults_height_full():
    p = blade_from_flat({
        "n_blades": 7, "chord_root": 34, "chord_mid": 44, "chord_tip": 38,
        "stagger_root": 26, "stagger_mid": 26, "stagger_tip": 22,
        "sweep_mid": 3, "sweep_tip": 5, "max_camber": 0.05,
        "shroud_thick_mm": SHROUD_DEFAULT_MM,
    })
    assert p.shroud_height_frac == 1.0


def test_blade_from_flat_roundtrips_height_frac():
    p = blade_from_flat({
        "n_blades": 7, "chord_root": 34, "chord_mid": 44, "chord_tip": 38,
        "stagger_root": 26, "stagger_mid": 26, "stagger_tip": 22,
        "sweep_mid": 3, "sweep_tip": 5, "max_camber": 0.05,
        "shroud_thick_mm": SHROUD_DEFAULT_MM,
        "shroud_height_frac": 0.3,
    })
    assert p.shroud_height_frac == 0.3


def test_blade_from_flat_defaults_shroud_off():
    p = blade_from_flat({
        "n_blades": 7, "chord_root": 34, "chord_mid": 44, "chord_tip": 38,
        "stagger_root": 26, "stagger_mid": 26, "stagger_tip": 22,
        "sweep_mid": 3, "sweep_tip": 5, "max_camber": 0.05,
    })
    assert p.shroud_thick_mm == 0.0


def test_suggest_params_stamps_default_shroud():
    study = optuna.create_study(directions=["maximize", "maximize", "maximize"])
    p = suggest_params(study.ask(), with_shroud=True)
    assert p.shroud_thick_mm == SHROUD_DEFAULT_MM


def test_run_optimization_declares_shroud_flag():
    text = Path("scripts/run_optimization.py").read_text(encoding="utf-8")
    assert "--shroud" in text
    assert "★" not in text
