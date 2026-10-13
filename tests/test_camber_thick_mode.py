"""Stock camber + thick_mode round-trip through blade_to/from_flat (§12.1–12.2)."""

from __future__ import annotations

from fansim.geometry.blade import BladeParams, RadialStation
from fansim.geometry.features import Features
from fansim.optimize.search_space import blade_from_flat, blade_to_flat, stock_blade_flat


def test_blade_to_flat_preserves_station_camber():
    p = BladeParams(
        stations=[
            RadialStation(0.0, 18.0, 40.0, 0.08, max_camber=0.05),
            RadialStation(0.5, 25.0, 30.0, 0.05, max_camber=0.06),
            RadialStation(1.0, 38.0, 22.0, 0.03, max_camber=0.04),
        ]
    )
    flat = blade_to_flat(p)
    assert flat["camber_root"] == 0.05
    assert flat["camber_mid"] == 0.06
    assert flat["camber_tip"] == 0.04
    assert flat["max_camber"] == 0.06  # mid alias for older consumers


def test_blade_from_flat_uses_per_station_camber():
    flat = blade_to_flat(BladeParams())
    flat = dict(flat, camber_root=0.01, camber_mid=0.03, camber_tip=0.05, max_camber=0.99)
    bp = blade_from_flat(flat, Features())
    st = sorted(bp.stations, key=lambda s: s.r_frac)
    assert abs(st[0].max_camber - 0.01) < 1e-12
    assert abs(st[1].max_camber - 0.03) < 1e-12
    assert abs(st[2].max_camber - 0.05) < 1e-12


def test_blade_from_flat_falls_back_to_max_camber():
    flat = blade_to_flat(BladeParams())
    for k in ("camber_root", "camber_mid", "camber_tip"):
        flat.pop(k, None)
    flat["max_camber"] = 0.042
    bp = blade_from_flat(flat, Features())
    assert all(abs(s.max_camber - 0.042) < 1e-12 for s in bp.stations)


def test_a12x25_stock_keeps_root_mid_camber_split():
    # a12x25_reference.yaml is the v3 wrapped-section refit (27.4, 2026-10-13): per-station camber is
    # 0.0235/0.0478/0.0445 root/mid/tip (refit with the hub-cut correction) (v2 planar was 0.037/0.0834/0.0971). What this guards is that the
    # split survives the blade_to_flat -> blade_from_flat round-trip (not collapsed to one value).
    flat = stock_blade_flat("a12x25")
    assert abs(float(flat["camber_root"]) - 0.0235) < 1e-9
    assert abs(float(flat["camber_mid"]) - 0.0478) < 1e-9
    assert abs(float(flat["camber_tip"]) - 0.0445) < 1e-9
    bp = blade_from_flat(flat, Features())
    # Since §23.1 the flat carries all 7 recipe stations, so every station keeps its own camber.
    from fansim.geometry.config import load_blade_params

    yaml = sorted(load_blade_params("config/problems/a12x25_reference.yaml").stations,
                  key=lambda s: s.r_frac)
    st = sorted(bp.stations, key=lambda s: s.r_frac)
    assert [s.max_camber for s in st] == [s.max_camber for s in yaml]
    assert abs(st[0].max_camber - 0.0235) < 1e-9
    mid = min(st, key=lambda s: abs(s.r_frac - 0.5))
    assert abs(mid.max_camber - 0.0478) < 1e-9


def test_blade_to_flat_emits_thick_mode():
    flat = blade_to_flat(BladeParams())
    assert flat["thick_mode"] in ("uniform", "tapered")
    assert float(flat["thick_mm"]) > 0.0
    # Default BladeParams stations are tapered t/c with unequal wall mm.
    assert flat["thick_mode"] == "tapered"


def test_near_uniform_recipe_walls_are_not_forced_uniform():
    """v3 Stock walls are 2.47/2.51/2.47 mm. The 0.12 mm picker called that 'uniform' and the editor
    then rewrote the recipe t/c to one 2.48 mm wall (mid -1 %). Only walls equal up to rounding are
    uniform; a design made in uniform mode still is."""
    import dataclasses

    from fansim.geometry.config import load_blade_params
    from fansim.optimize.search_space import UNIFORM_WALL_TOL_MM, blade_to_flat

    stock = load_blade_params("config/problems/a12x25_reference.yaml")
    assert blade_to_flat(stock)["thick_mode"] == "tapered"
    walls = [dataclasses.replace(s, thickness=round(2.4 / s.chord, 4)) for s in stock.stations]
    assert blade_to_flat(dataclasses.replace(stock, stations=walls))["thick_mode"] == "uniform"
    assert UNIFORM_WALL_TOL_MM <= 0.02
