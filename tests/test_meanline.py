"""§20.4 meanline Cordier sizing, velocity triangles, Lieblein / de Haller gates."""

from __future__ import annotations

import math

import pytest

from fansim.optimize.meanline import (
    CAMBER_MAX,
    CFM_PER_M3S,
    DE_HALLER_LIMIT,
    DF_LIMIT,
    DutyPoint,
    axial_cz,
    camber_from_turning_rad,
    cfm_to_m3s,
    cordier_delta_opt,
    de_haller_ratio,
    format_meanline_seed,
    lieblein_df,
    preserve_sign,
    seed_from_duty,
    solidity,
    specific_diameter,
    specific_speed,
    stagger_from_disk_deg,
    station_magnitudes,
    suggest_tip_diameter_m,
)
from fansim.physics.air import RHO_AMCA


def test_cfm_to_m3s_known():
    # 2118.882 CFM = 1 m³/s by definition of CFM_PER_M3S
    assert cfm_to_m3s(CFM_PER_M3S) == pytest.approx(1.0)


def test_specific_speed_hand_calc():
    # ω=100 rad/s, Q=0.01 m³/s, Y=100 J/kg
    # σ = 100 * sqrt(0.01) / 100^0.75 = 10 / (100^0.75)
    y = 100.0
    expected = 100.0 * math.sqrt(0.01) / (y ** 0.75)
    assert specific_speed(100.0, 0.01, y) == pytest.approx(expected)
    assert expected == pytest.approx(0.316227766, rel=1e-6)


def test_specific_diameter_hand_calc():
    # D=0.12, Q=0.0283, Y=19.083 (≈22.9 Pa / 1.2)
    y = 22.9 / RHO_AMCA
    q = 60.1 / CFM_PER_M3S
    d = 0.12
    expected = d * (y ** 0.25) / math.sqrt(q)
    assert specific_diameter(d, q, y) == pytest.approx(expected)


def test_cordier_delta_opt_decreases_with_sigma():
    assert cordier_delta_opt(1.0) > cordier_delta_opt(2.0) > cordier_delta_opt(3.0)


def test_suggest_tip_diameter_positive_for_a12x25_ish():
    duty = DutyPoint(cfm=60.1, dp_pa=22.9, rpm=2000.0)
    d = suggest_tip_diameter_m(duty)
    # PC axial tip OD should land in a plausible cm-scale band
    assert 0.05 < d < 0.25


def test_axial_cz_annulus():
    # Q=0.01, hub=0.02, tip=0.05 → A = π(0.0025-0.0004)=π*0.0021
    q = 0.01
    a = math.pi * (0.05**2 - 0.02**2)
    assert axial_cz(q, 0.02, 0.05) == pytest.approx(q / a)


def test_solidity_seven_blades():
    # N=7, c=0.04 m, r=0.04 m → s=2πr/N, σ=c/s
    r, c, n = 0.04, 0.04, 7
    s = 2.0 * math.pi * r / n
    assert solidity(n, c, r) == pytest.approx(c / s)


def test_lieblein_df_and_de_haller_known():
    w1, w2, dcu, sol = 20.0, 15.0, 5.0, 1.0
    # DF = (1 - 15/20) + 5/(2*1*20) = 0.25 + 0.125 = 0.375
    assert lieblein_df(w1, w2, dcu, sol) == pytest.approx(0.375)
    assert de_haller_ratio(w1, w2) == pytest.approx(0.75)
    assert de_haller_ratio(w1, w2) >= DE_HALLER_LIMIT
    assert lieblein_df(w1, w2, dcu, sol) <= DF_LIMIT


def test_lieblein_df_fails_when_highly_diffusing():
    # Heavy diffusion: W2<<W1 and large ΔCu / low solidity
    df = lieblein_df(30.0, 10.0, 15.0, 0.4)
    assert df > DF_LIMIT


def test_camber_from_turning():
    # 20° turning → ε=π/9 → m=ε/4
    eps = math.radians(20.0)
    assert camber_from_turning_rad(eps) == pytest.approx(eps / 4.0)
    assert camber_from_turning_rad(math.radians(80.0)) == pytest.approx(CAMBER_MAX)


def test_stagger_from_disk_convention():
    # Both β from axial = 60° → mean 60° → disk stagger = 30°
    b = math.radians(60.0)
    assert stagger_from_disk_deg(b, b) == pytest.approx(30.0)


def test_preserve_sign_does_not_flip():
    assert preserve_sign(26.0, 33.5) == pytest.approx(33.5)
    assert preserve_sign(-26.0, 33.5) == pytest.approx(-33.5)
    assert preserve_sign(0.0, 22.0) == pytest.approx(22.0)


def test_seed_free_vortex_magnitudes_and_gates():
    duty = DutyPoint(cfm=50.0, dp_pa=15.0, rpm=2000.0)
    seed = seed_from_duty(
        duty,
        hub_radius_mm=18.5,
        tip_radius_mm=55.0,
        n_blades=7,
        chord_root_mm=34.0,
        chord_mid_mm=44.0,
        chord_tip_mm=38.0,
        vortex="free",
    )
    assert seed.vortex == "free"
    assert seed.sigma > 0.0
    assert len(seed.stations) == 3
    mags = station_magnitudes(seed)
    for k, v in mags.items():
        assert v >= 0.0, k
    # Free vortex: Cu ∝ 1/r so tip Cu < root Cu
    assert seed.stations[0].cu2_mps > seed.stations[2].cu2_mps
    # Free vortex Euler: U·Cu = Y constant
    y = duty.specific_work
    for st in seed.stations:
        assert st.u_mps * st.cu2_mps == pytest.approx(y, rel=1e-5)


def test_seed_forced_vortex_cu_grows_with_r():
    duty = DutyPoint(cfm=50.0, dp_pa=15.0, rpm=2000.0)
    seed = seed_from_duty(
        duty,
        hub_radius_mm=18.5,
        tip_radius_mm=55.0,
        n_blades=7,
        chord_root_mm=34.0,
        chord_mid_mm=44.0,
        chord_tip_mm=38.0,
        vortex="forced",
    )
    assert seed.stations[0].cu2_mps < seed.stations[2].cu2_mps


def test_format_mentions_section():
    duty = DutyPoint(cfm=60.0, dp_pa=20.0, rpm=1800.0)
    seed = seed_from_duty(
        duty,
        hub_radius_mm=18.0,
        tip_radius_mm=55.0,
        n_blades=7,
        chord_root_mm=30.0,
        chord_mid_mm=40.0,
        chord_tip_mm=35.0,
    )
    text = "\n".join(format_meanline_seed(seed))
    assert "§20.4" in text
    assert "stagger" in text
