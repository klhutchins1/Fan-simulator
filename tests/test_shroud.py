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


def test_run_optimization_has_no_shroud_height_flag():
    text = Path("scripts/run_optimization.py").read_text(encoding="utf-8")
    assert "--shroud" in text
    assert "--shroud-height" not in text
    assert "--shroud-partial" not in text
    assert "★" not in text


def test_ring_wall_contains_every_tip_section_point():
    """The bore must sit inside the WHOLE tip chord, not just the LE/TE corners.

    Sizing the bore off the max hypot (LE/TE corners) leaves mid-chord — which sits near
    tip_radius — outside the ring, i.e. an open channel to the outside."""
    from fansim.geometry.blade import (
        SHROUD_EMBED_MM, open_tip_rmax_mm, tip_section_points, tip_section_rmin_mm)

    p = BladeParams()
    p.shroud_thick_mm = SHROUD_DEFAULT_MM
    r_out = open_tip_rmax_mm(p) + p.shroud_thick_mm
    r_in = tip_section_rmin_mm(p) - SHROUD_EMBED_MM

    radii = [math.hypot(v.x, v.y) for v in tip_section_points(p)]
    assert radii, "tip section must have points"
    assert min(radii) > r_in + 1e-9, "tip section dips inside the bore — open channel"
    assert max(radii) < r_out - 1e-9, "tip section pokes through the outer wall"


def test_ring_bore_is_below_the_corner_only_radius():
    """Guard against regressing to inner = open_tip_rmax_mm - embed (corner-only contact).

    Uses cylindrical_tip=False so LE/TE corners still bulge past tip_radius (the case the
    bore-sizing rule exists for). With trim on, rmin≈rmax and this inequality does not apply.
    """
    from fansim.geometry.blade import (
        SHROUD_EMBED_MM, open_tip_rmax_mm, tip_section_rmin_mm)

    p = BladeParams()
    p.cylindrical_tip = False
    assert tip_section_rmin_mm(p) < open_tip_rmax_mm(p) - SHROUD_EMBED_MM


def _tell_fake_trial(study: optuna.Study, shroud: float | None) -> None:
    t = study.ask()
    t.suggest_int("n_blades", 7, 7)
    t.set_user_attr("feasible", True)
    t.set_user_attr("n_blades", 7)
    if shroud is not None:
        t.set_user_attr("shroud_thick_mm", shroud)
    study.tell(t, [10.0, 5.0, 1.0])


def test_pareto_summary_carries_shroud_thick():
    from fansim.optimize.search_space import OBJECTIVE_DIRECTIONS
    from fansim.optimize.study import pareto_summary

    study = optuna.create_study(directions=list(OBJECTIVE_DIRECTIONS))
    _tell_fake_trial(study, SHROUD_DEFAULT_MM)
    row = pareto_summary(study)[0]
    assert row["shroud_thick_mm"] == SHROUD_DEFAULT_MM
    # params carries it too: downstream tooling rebuilds designs via blade_from_flat(params).
    assert row["params"]["shroud_thick_mm"] == SHROUD_DEFAULT_MM


def test_pareto_summary_without_shroud_attr_stays_open_tip():
    from fansim.optimize.search_space import OBJECTIVE_DIRECTIONS
    from fansim.optimize.study import pareto_summary

    study = optuna.create_study(directions=list(OBJECTIVE_DIRECTIONS))
    _tell_fake_trial(study, None)
    row = pareto_summary(study)[0]
    assert row["shroud_thick_mm"] == 0.0
    assert row["params"]["shroud_thick_mm"] == 0.0


def test_load_designs_merges_shroud_user_attr(tmp_path):
    from fansim.cockpit.data import load_designs
    from fansim.optimize.search_space import OBJECTIVE_DIRECTIONS

    storage = f"sqlite:///{(tmp_path / 'study.db').as_posix()}"
    study = optuna.create_study(study_name="s", storage=storage,
                                directions=list(OBJECTIVE_DIRECTIONS))
    _tell_fake_trial(study, SHROUD_DEFAULT_MM)
    d = load_designs(tmp_path)[0]
    assert d.params["shroud_thick_mm"] == SHROUD_DEFAULT_MM


def test_height_frac_defaults_to_full():
    p = BladeParams()
    assert p.shroud_height_frac == 1.0


def test_thick_off_ignores_height_frac():
    from fansim.geometry.blade import shroud_axial_range

    p = BladeParams()
    p.shroud_height_frac = 0.3
    assert shroud_axial_range(p) is None
    open_dia = blade_max_dia(p)
    p.shroud_thick_mm = 0.0
    assert blade_max_dia(p) == open_dia


def test_full_frac_matches_tip_z_span():
    from fansim.geometry.blade import shroud_axial_range, tip_section_points

    p = BladeParams()
    p.shroud_thick_mm = SHROUD_DEFAULT_MM
    p.shroud_height_frac = 1.0
    zs = [v.z for v in tip_section_points(p)]
    lo, hi = shroud_axial_range(p)
    assert abs(lo - min(zs)) < 1e-9 and abs(hi - max(zs)) < 1e-9


def test_partial_band_is_te_anchored():
    from fansim.geometry.blade import shroud_axial_range, tip_le_te_z, tip_section_points

    p = BladeParams()
    p.shroud_thick_mm = SHROUD_DEFAULT_MM
    p.shroud_height_frac = 0.3
    z_le, z_te = tip_le_te_z(p)
    lo, hi = shroud_axial_range(p)
    span = max(v.z for v in tip_section_points(p)) - min(v.z for v in tip_section_points(p))
    assert abs((hi - lo) - 0.3 * span) < 1e-6
    if z_te >= z_le:
        assert abs(hi - z_te) < 1e-6
    else:
        assert abs(lo - z_te) < 1e-6


def test_zero_frac_clamps_to_min_wall():
    from fansim.geometry.blade import SHROUD_MIN_WALL_MM, shroud_axial_range

    p = BladeParams()
    p.shroud_thick_mm = SHROUD_DEFAULT_MM
    p.shroud_height_frac = 0.0
    lo, hi = shroud_axial_range(p)
    assert abs((hi - lo) - SHROUD_MIN_WALL_MM) < 1e-6


def test_partial_frac_does_not_change_od():
    p = BladeParams()
    open_dia = blade_max_dia(p)
    p.shroud_thick_mm = SHROUD_DEFAULT_MM
    p.shroud_height_frac = 0.3
    assert abs(blade_max_dia(p) - (open_dia + 2.0 * SHROUD_DEFAULT_MM)) < 1e-6


def test_preview_partial_ring_is_shorter_than_full():
    from fansim.geometry.blade import build_impeller_preview

    full = BladeParams()
    full.shroud_thick_mm = SHROUD_DEFAULT_MM
    full.shroud_height_frac = 1.0
    _, v_full = build_impeller_preview(full)
    part = BladeParams()
    part.shroud_thick_mm = SHROUD_DEFAULT_MM
    part.shroud_height_frac = 0.3
    _, v_part = build_impeller_preview(part)
    assert v_part > 0
    assert v_part < v_full


def test_cockpit_declares_shroud_height_slider():
    # 09-11 fan-tab extract moved Design widgets out of app.py into fan_tab.py.
    text = Path("fansim/cockpit/fan_tab.py").read_text(encoding="utf-8")
    assert "e_shroud_height" in text
    assert '"Shroud height"' in text or "'Shroud height'" in text
    assert "trailing edge" in text.lower()
    assert "shroud_height_frac" in text
    assert "e_shroud_thick == 0" in text
