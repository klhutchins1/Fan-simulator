"""Flat dicts carry the full station recipe (roadmap §23.1: Stock was cut from 7 stations to 3)."""

import dataclasses
import json

import pytest

from fansim.geometry.blade import BladeParams, RadialStation
from fansim.geometry.config import load_blade_params
from fansim.optimize.search_space import (
    FLAT_STATIONS,
    blade_from_flat,
    blade_to_flat,
    stock_blade_flat,
)

STOCK_YAML = "config/problems/a12x25_reference.yaml"


def _by_r(stations):
    return sorted(stations, key=lambda s: s.r_frac)


def test_stock_flat_round_trips_all_seven_stations_exactly():
    yaml = load_blade_params(STOCK_YAML)
    built = blade_from_flat(json.loads(json.dumps(stock_blade_flat("a12x25"))))
    assert len(yaml.stations) == len(built.stations) == 7
    for a, b in zip(_by_r(yaml.stations), built.stations):
        assert dataclasses.asdict(a) == dataclasses.asdict(b)


def test_slot_edit_shifts_the_recipe_with_interpolated_deltas():
    flat = stock_blade_flat("a12x25")
    base = {s.r_frac: s for s in blade_from_flat(flat).stations}
    edited = dict(flat, stagger_mid=flat["stagger_mid"] + 3.0)
    got = {s.r_frac: s for s in blade_from_flat(edited).stations}
    r_root, r_mid, r_tip = flat["station_slot_r"]
    assert got[r_mid].stagger_deg == pytest.approx(base[r_mid].stagger_deg + 3.0)
    assert got[r_root].stagger_deg == pytest.approx(base[r_root].stagger_deg)
    assert got[r_tip].stagger_deg == pytest.approx(base[r_tip].stagger_deg)
    between = [r for r in got if r_root < r < r_mid]
    for r in between:  # linear ramp from 0 at the root to +3 at mid
        assert got[r].stagger_deg == pytest.approx(base[r].stagger_deg + 3.0 * r / r_mid)
    # other fields untouched
    assert all(got[r].chord == base[r].chord for r in got)


def test_camber_pos_edit_is_uniform():
    flat = stock_blade_flat("a12x25")
    base = blade_from_flat(flat).stations
    got = blade_from_flat(dict(flat, camber_pos=flat["camber_pos"] + 0.05)).stations
    assert [g.camber_pos - b.camber_pos for g, b in zip(got, base)] == pytest.approx([0.05] * 7)


def test_three_station_designs_stay_three_slot_only():
    bp = BladeParams(n_blades=7, stations=[
        RadialStation(0.0, 30, 30), RadialStation(0.5, 40, 30), RadialStation(1.0, 35, 25)])
    flat = blade_to_flat(bp)
    assert FLAT_STATIONS not in flat
    assert len(blade_from_flat(flat).stations) == 3


def test_three_station_recipe_with_a_swept_root_is_carried():
    bp = BladeParams(n_blades=7, stations=[
        RadialStation(0.0, 30, 30, sweep=1.0), RadialStation(0.5, 40, 30),
        RadialStation(1.0, 35, 25)])
    assert blade_from_flat(blade_to_flat(bp)).stations[0].sweep == 1.0


def test_old_flats_without_the_payload_build_as_before():
    flat = stock_blade_flat("a12x25")
    legacy = {k: v for k, v in flat.items() if not k.startswith("station")}
    assert [s.r_frac for s in blade_from_flat(legacy).stations] == [0.0, 0.5, 1.0]
