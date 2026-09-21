from __future__ import annotations
import math
import pytest


def test_hover_power_budget_minutes_scale_with_wh():
    from fansim.propeller.power import hover_power_budget
    a = hover_power_budget(
        all_up_weight_n=19.6133,  # 2 kg
        n_rotors=4,
        tip_radius_m=0.0635,
        figure_of_merit=0.70,
        battery_wh=50.0,
    )
    b = hover_power_budget(
        all_up_weight_n=19.6133,
        n_rotors=4,
        tip_radius_m=0.0635,
        figure_of_merit=0.70,
        battery_wh=100.0,
    )
    assert a["power_model"] == "momentum_fm"
    assert a["hover_minutes"] is not None and b["hover_minutes"] is not None
    assert b["hover_minutes"] == pytest.approx(2.0 * a["hover_minutes"], rel=1e-9)
    assert a["eta_elec"] == pytest.approx(0.70)


def test_hover_power_budget_bemt_shaft_override():
    from fansim.propeller.power import hover_power_budget
    out = hover_power_budget(
        all_up_weight_n=20.0,
        n_rotors=4,
        tip_radius_m=0.05,
        figure_of_merit=0.7,
        shaft_power_w=100.0,  # per rotor
        battery_wh=None,
    )
    assert out["power_model"] == "bemt_shaft"
    assert out["shaft_power_w"] == pytest.approx(100.0)
    assert out["elec_power_w_total"] == pytest.approx(400.0 / 0.70)


def test_quorum_q1_fom_identity():
    """FM = T^1.5 / (P sqrt(2 rho A)) rearranges with hover_power_budget."""
    from fansim.propeller.power import RHO_AIR, hover_power_budget
    T = 5.0
    R = 0.06
    A = math.pi * R * R
    FM = 0.65
    P_i = T ** 1.5 / math.sqrt(2.0 * RHO_AIR * A)
    P_shaft = P_i / FM
    # AUW = 4 rotors * T
    out = hover_power_budget(
        all_up_weight_n=4.0 * T,
        n_rotors=4,
        tip_radius_m=R,
        figure_of_merit=FM,
        eta_elec=1.0,  # isolate shaft
    )
    assert out["shaft_power_w"] == pytest.approx(P_shaft, rel=1e-9)
    # recover FM from T, P, A
    fm_back = (T ** 1.5 / math.sqrt(2.0 * RHO_AIR * A)) / out["shaft_power_w"]
    assert fm_back == pytest.approx(FM, rel=1e-9)


def test_cli_evaluate_prop_power_declares_modes():
    from tests._cli_parsers import load_build_parser

    ap = load_build_parser("evaluate_prop_power.py")()
    help_text = ap.format_help()
    assert "hover-budget" in help_text or "hover_budget" in help_text or "--mode" in help_text


def test_pythrust_available_false_when_missing(monkeypatch):
    import fansim.propeller.power as power
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "pythrust" or name.startswith("pythrust."):
            raise ImportError("blocked")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    if hasattr(power, "_pythrust_ok"):
        monkeypatch.setattr(power, "_pythrust_ok", None)
    assert power.pythrust_available() is False
    with pytest.raises(power.PropulsionExtraMissing):
        power.solve_catalog_operating_point(
            motor={
                "kv_rpm_per_v": 1900,
                "resistance_ohm": 0.05,
                "no_load_current_a": 1.0,
                "current_max_a": 40,
            },
            battery_voltage_v=22.2,
            diameter_in=5.0,
            pitch_in=4.5,
        )
