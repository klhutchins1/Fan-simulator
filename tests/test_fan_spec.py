"""Tests for the fan-model constraint spec (fansim.fan_spec)."""

import pytest

import dataclasses

from fansim.fan_spec import (
    A12X25,
    FanSpec,
    check_build,
    check_power,
    estimate_weight_g,
    fan_spec_from_dict,
    fan_spec_names,
    fan_spec_to_dict,
    get_fan_spec,
    load_fan_models_dir,
    load_fan_spec,
    over_spec_flags,
    save_fan_spec,
)


def test_a12x25_power_budget():
    # 12 V x 0.14 A = 1.68 W electrical; x0.50 efficiency (audit 2026-10-10) = 0.84 W shaft,
    # above Stock's ~0.77 W, so Stock runs at its rated 2000 rpm like the real fan.
    assert A12X25.max_power_w == pytest.approx(1.68)
    assert A12X25.max_shaft_power_w == pytest.approx(0.84)


def test_registry():
    assert "a12x25" in fan_spec_names()
    assert "delta_afc1212de" in fan_spec_names()
    assert get_fan_spec("a12x25").name == "Noctua NF-A12x25"
    with pytest.raises(KeyError):
        get_fan_spec("nope")


def test_delta_is_a_different_regime():
    """The Delta industrial fan (different company) must be a genuinely different envelope."""
    delta = get_fan_spec("delta_afc1212de")
    assert delta.max_power_w == pytest.approx(19.2)          # 12 V x 1.60 A
    assert delta.max_power_w > 10 * A12X25.max_power_w  # ~11x the electrical budget
    assert delta.max_shaft_power_w > 5 * A12X25.max_shaft_power_w  # 9x shaft (a12x25 motor 0.50, Delta 0.40)
    assert delta.rpm == 3900.0
    assert delta.depth_mm[1] == 38.0                          # 38 mm thick vs 25 mm
    # a 2 W / 30 mm-deep design is REJECTED on the Noctua but fits the Delta
    assert not check_power(A12X25, 2.0)[0]
    assert check_power(delta, 2.0)[0]
    assert not check_build(A12X25, 115, 43, 30, 15)[0]        # too deep for the 25 mm Noctua
    assert check_build(delta, 115, 43, 30, 15)[0]             # fine in the 38 mm Delta


def test_weight_estimate():
    # 10000 mm^3 of PETG (1270 kg/m^3) = 12.7 g at 100% infill
    assert estimate_weight_g(10000.0, "PETG", infill_frac=1.0) == pytest.approx(12.7, rel=1e-3)
    # Default FDM fill is sparse (roadmap §2.4)
    from fansim.fan_spec import DEFAULT_PRINT_INFILL
    assert estimate_weight_g(10000.0, "PETG") == pytest.approx(
        12.7 * DEFAULT_PRINT_INFILL, rel=1e-3)
    assert estimate_weight_g(10000.0, "PETG", infill_frac=0.5) == pytest.approx(6.35, rel=1e-3)


def test_weight_estimate_resin_defaults_solid():
    from fansim.fan_spec import _default_infill_frac

    assert _default_infill_frac("PETG") == pytest.approx(0.20)
    assert _default_infill_frac("PLA") == pytest.approx(0.20)
    assert _default_infill_frac("RESIN") == pytest.approx(1.0)
    assert _default_infill_frac("ABS_RESIN") == pytest.approx(1.0)


def test_check_build_pass_and_fail():
    ok, _ = check_build(A12X25, tip_dia_mm=108, hub_dia_mm=43, depth_mm=22, weight_g=15)
    assert ok
    assert not check_build(A12X25, 115, 43, 22, 15)[0]        # too big diameter (>110 mm frame)
    assert not check_build(A12X25, 108, 43, 30, 15)[0]        # too deep
    assert not check_build(A12X25, 108, 43, 22, 80)[0]        # too heavy
    ok, reason = check_build(A12X25, 108, 20, 22, 15)         # hub too small
    assert not ok and "hub" in reason


def test_check_power_gate():
    assert check_power(A12X25, 0.4)[0]                        # within budget
    over_ok, reason = check_power(A12X25, 2.0)               # a high-flow design (~2 W shaft)
    assert not over_ok and "shaft" in reason


def test_custom_fan_model():
    # a bigger fan model with more power headroom accepts what the A12x25 rejects
    big = FanSpec(name="Big", tip_dia_mm=(80, 200), hub_dia_mm=(20, 100), depth_mm=(10, 60),
                  rpm=3000, voltage_v=24.0, max_current_a=0.5, motor_efficiency=0.5)
    assert check_power(big, 2.0)[0]                           # 24*0.5*0.5 = 6 W budget
    assert check_build(big, 150, 50, 40)[0]


def test_leeway_allows_over_nominal_but_flags_it():
    strict = A12X25
    loose = dataclasses.replace(A12X25, leeway_tip_dia_mm=3.0, leeway_depth_mm=4.0)
    # a 112 mm tip (past the 110 frame) is REJECTED strictly, ALLOWED within 3 mm leeway
    assert not check_build(strict, 112, 43, 22)[0]
    assert check_build(loose, 112, 43, 22)[0]
    assert not check_build(loose, 115, 43, 22)[0]            # beyond leeway -> still rejected
    flags = over_spec_flags(loose, tip_dia_mm=112, depth_mm=27)
    assert any("tip" in f for f in flags) and any("depth" in f for f in flags)


def test_over_voltage_leeway_raises_power_budget():
    strict = A12X25                                          # ~0.67 W shaft
    boosted = dataclasses.replace(A12X25, over_voltage_v=12.0)  # 24 V -> ~1.34 W shaft
    assert not check_power(strict, 1.0)[0]
    assert check_power(boosted, 1.0)[0]
    assert boosted.max_shaft_power_w == A12X25.max_shaft_power_w   # nominal unchanged
    assert boosted.max_shaft_power_w_leeway > boosted.max_shaft_power_w
    assert "over-power" in over_spec_flags(A12X25, 108, 22, shaft_power_w=1.0)[0]


def test_yaml_round_trip_and_import(tmp_path):
    p = tmp_path / "myfan.yaml"
    save_fan_spec(A12X25, p)
    back = load_fan_spec(p)
    assert back.name == A12X25.name
    assert back.tip_dia_mm == A12X25.tip_dia_mm             # tuple preserved
    assert back.max_shaft_power_w == pytest.approx(A12X25.max_shaft_power_w)
    # dict round-trip
    assert fan_spec_from_dict(fan_spec_to_dict(A12X25)).rpm == A12X25.rpm
    # directory import registers by filename stem
    d = tmp_path / "models"
    d.mkdir()
    save_fan_spec(dataclasses.replace(A12X25, name="Imported"), d / "imported.yaml")
    assert "imported" in load_fan_models_dir(d)
    assert get_fan_spec("imported").name == "Imported"
