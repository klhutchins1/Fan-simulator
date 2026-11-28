"""RV-3 Module 7 regression & invariant tests for fansim/structural/* and fansim/acoustics/*."""

from __future__ import annotations

import math
import warnings
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from fansim.acoustics.case import _parse_time_dir, read_case
from fansim.acoustics.farfield import (
    a_weighting_db,
    blade_pass_frequency,
    dba_from_pressure,
    dipole_pressure,
    force_from_cv,
    peak_tone_over_harmonics,
    tone_level_db,
)
from fansim.acoustics.fwh import (
    PATCH_N,
    analyze_patches_csv,
    analyze_permeable_csv,
    cv_box_from_dia_mm,
    loading_pressure_compact,
    loading_pressure_panels,
    noise_from_compact_force,
    noise_from_permeable_panels,
)
from fansim.acoustics.loading import (
    calibrate,
    loading_noise_proxy,
    loading_proxy_from_rans,
    loading_proxy_operating,
)
from fansim.acoustics.tip_loading import (
    noise_hint_from_case,
    tip_loading_swl_db,
    tip_speed_ms,
)
from fansim.acoustics.tonal import (
    blade_passing_modes,
    peak_tone_amplitude,
    peak_tone_reduction_db,
    tonal_peak_ratio,
)
from fansim.geometry.blade import BladeParams, RadialStation
from fansim.structural import (
    CANTILEVER_LAMBDA,
    MIN_F1_OVER_BPF,
    FlutterReport,
    Unbalance,
    balanced_uneven_spacing,
    beam_aspect_ratio,
    centrifugal_root_stress,
    couple_unbalance,
    deflection_report,
    first_bending_hz,
    flutter_report,
    is_balanced,
    max_blades_for_margin,
    residual_force,
    root_bending_stress,
    static_unbalance,
    tip_deflection_mm,
    tip_deflection_point_load_mm,
)


def _prismatic(
    chord_mm: float = 12.0,
    t_frac: float = 0.10,
    hub: float = 20.0,
    tip: float = 60.0,
    rpm: float = 2000.0,
    n_blades: int = 7,
) -> BladeParams:
    sts = [RadialStation(r, chord_mm, 30.0, thickness=t_frac) for r in (0.0, 0.5, 1.0)]
    return replace(
        BladeParams(),
        stations=sts,
        hub_radius=hub,
        tip_radius=tip,
        rpm=rpm,
        n_blades=n_blades,
    )


# ------------------------------------------------------------------ structural.stress
def test_centrifugal_rejects_nan_negative_and_inverted_radii():
    with pytest.raises(ValueError, match="rpm"):
        centrifugal_root_stress(_prismatic(rpm=float("nan")))
    with pytest.raises(ValueError, match="rpm"):
        centrifugal_root_stress(_prismatic(rpm=-500.0))
    with pytest.raises(ValueError, match="hub_radius"):
        centrifugal_root_stress(_prismatic(hub=60.0, tip=40.0))
    with pytest.raises(ValueError, match="hub_radius"):
        centrifugal_root_stress(_prismatic(hub=-1.0, tip=40.0))
    with pytest.raises(ValueError, match="adhesion_k"):
        centrifugal_root_stress(_prismatic(), adhesion_k=0.0)
    with pytest.raises(ValueError, match="adhesion_k"):
        centrifugal_root_stress(_prismatic(), adhesion_k=float("nan"))
    with pytest.raises(ValueError, match="min_safety_factor"):
        centrifugal_root_stress(_prismatic(), min_safety_factor=0.0)


def test_centrifugal_zero_rpm_and_native_float_fields():
    rep = centrifugal_root_stress(_prismatic(rpm=0.0))
    assert rep.ok is True
    assert rep.sigma_root_mpa == 0.0
    assert math.isinf(rep.safety_factor)
    assert type(rep.sigma_root_mpa) is float
    assert type(rep.yield_mpa) is float
    assert type(rep.safety_factor) is float


# ------------------------------------------------------------------ structural.deflection
def test_deflection_rejects_nan_bad_station_empty_and_inverted_radii():
    with pytest.raises(ValueError, match="station"):
        beam_aspect_ratio(_prismatic(), station="root")
    with pytest.raises(ValueError, match="stations"):
        beam_aspect_ratio(replace(_prismatic(), stations=[]))
    with pytest.raises(ValueError, match="hub_radius"):
        tip_deflection_mm(_prismatic(hub=70.0, tip=50.0))
    with pytest.raises(ValueError, match="load_pa"):
        tip_deflection_mm(_prismatic(), load_pa=float("nan"))
    with pytest.raises(ValueError, match="force_n"):
        tip_deflection_point_load_mm(_prismatic(), force_n=float("nan"))
    with pytest.raises(ValueError, match="load_pa"):
        root_bending_stress(_prismatic(), load_pa=float("nan"))
    with pytest.raises(ValueError, match="adhesion_k"):
        root_bending_stress(_prismatic(), adhesion_k=-0.5)
    with pytest.raises(ValueError, match="min_safety_factor"):
        root_bending_stress(_prismatic(), min_safety_factor=0.0)
    with pytest.raises(ValueError, match="tip_gap_mm"):
        deflection_report(_prismatic(), tip_gap_mm=-0.1)
    with pytest.raises(ValueError, match="tip_gap_mm"):
        deflection_report(_prismatic(), tip_gap_mm=float("nan"))


def test_deflection_zero_load_invariant():
    p = _prismatic()
    assert tip_deflection_mm(p, load_pa=0.0) == 0.0
    assert tip_deflection_point_load_mm(p, force_n=0.0) == 0.0
    rb = root_bending_stress(p, load_pa=0.0)
    assert rb.ok and rb.sigma_root_mpa == 0.0 and math.isinf(rb.safety_factor)


# ------------------------------------------------------------------ structural.flutter
def test_flutter_exported_and_guards_nan_and_zero_margin():
    assert CANTILEVER_LAMBDA == pytest.approx(1.875104)
    assert MIN_F1_OVER_BPF == pytest.approx(1.2)
    rep = flutter_report(_prismatic())
    assert isinstance(rep, FlutterReport)
    assert type(first_bending_hz(_prismatic())) is float

    with pytest.raises(ValueError, match="rpm"):
        flutter_report(_prismatic(rpm=float("nan")))
    with pytest.raises(ValueError, match="rpm"):
        flutter_report(_prismatic(rpm=-100.0))
    with pytest.raises(ValueError, match="n_blades"):
        flutter_report(_prismatic(n_blades=-1))
    with pytest.raises(ValueError, match="min_margin"):
        flutter_report(_prismatic(), min_margin=0.0)
    with pytest.raises(ValueError, match="min_margin"):
        max_blades_for_margin(400.0, 2000.0, min_margin=0.0)
    with pytest.raises(ValueError, match="min_margin"):
        max_blades_for_margin(400.0, 2000.0, min_margin=-1.0)
    with pytest.raises(ValueError, match="finite"):
        max_blades_for_margin(float("nan"), 2000.0)
    with pytest.raises(ValueError, match="stations"):
        first_bending_hz(replace(_prismatic(), stations=[]))
    with pytest.raises(ValueError, match="hub_radius"):
        first_bending_hz(_prismatic(hub=70.0, tip=50.0))


def test_flutter_resin_uses_isotropic_modulus():
    p = _prismatic()
    f_resin = first_bending_hz(p, material="RESIN")
    f_petg = first_bending_hz(p, material="PETG")
    # E_eff(RESIN)/rho(RESIN) = 2.5/1100 vs PETG (2.1*0.7)/1270 -> RESIN is stiffer & lighter
    assert f_resin > f_petg


# ------------------------------------------------------------------ P1C (#123) structural math
def test_centrifugal_tapered_matches_numerical_integral_and_stock_v3():
    """#123 S1: tapered centrifugal integral matches numerical integration and raises Stock v3 ~1.48x."""
    from fansim.geometry.config import load_blade_params
    from fansim.manufacturability.materials import MATERIALS

    # Outward-flaring blade: root c=18, t=0.14 (A~45.36), tip c=36, t=0.07 (A~90.72, 2x root)
    outward = replace(
        _prismatic(hub=20.0, tip=60.0, rpm=6000.0),
        stations=[
            RadialStation(0.0, 18.0, 30.0, thickness=0.14),
            RadialStation(1.0, 36.0, 30.0, thickness=0.07),
        ],
    )
    inward = replace(
        _prismatic(hub=20.0, tip=60.0, rpm=6000.0),
        stations=[
            RadialStation(0.0, 36.0, 30.0, thickness=0.07),
            RadialStation(1.0, 18.0, 30.0, thickness=0.14),
        ],
    )
    rho = MATERIALS["PETG"].density_kg_m3
    w = 6000.0 * 2.0 * math.pi / 60.0
    r_hub, r_tip = 0.020, 0.060
    r_grid = np.linspace(r_hub, r_tip, 200_001)
    u = (r_grid - r_hub) / (r_tip - r_hub)
    uniform_mpa = 0.5 * rho * w**2 * (r_tip**2 - r_hub**2) / 1e6

    for blade, c0, t0, c1, t1, expect_above in (
        (outward, 0.018, 0.14, 0.036, 0.07, True),
        (inward, 0.036, 0.07, 0.018, 0.14, False),
    ):
        c = c0 + (c1 - c0) * u
        tau = t0 + (t1 - t0) * u
        area = c * (tau * c)
        expected_mpa = rho * w**2 * float(np.trapezoid(area * r_grid, r_grid)) / area[0] / 1e6
        rep = centrifugal_root_stress(blade, material="PETG")
        assert rep.sigma_root_mpa == pytest.approx(expected_mpa, rel=1e-6)
        if expect_above:
            assert rep.sigma_root_mpa > uniform_mpa
        else:
            assert rep.sigma_root_mpa < uniform_mpa

    stock = load_blade_params(Path("config/problems/a12x25_reference.yaml"))
    stock_rep = centrifugal_root_stress(stock, material="PETG")
    w_s = stock.rpm * 2.0 * math.pi / 60.0
    unif_s = 0.5 * rho * w_s**2 * ((stock.tip_radius * 1e-3) ** 2 - (stock.hub_radius * 1e-3) ** 2) / 1e6
    ratio = stock_rep.sigma_root_mpa / unif_s
    assert 1.40 <= ratio <= 1.55, f"expected Stock v3 taper ratio ~1.48x, got {ratio:.3f}x"

    with pytest.raises(ValueError, match="stations"):
        centrifugal_root_stress(replace(_prismatic(), stations=[]))


def test_root_bending_uses_root_station_and_tapered_moment():
    """#123 S2: root_bending_stress uses root section modulus and tapered M = dP * int c(s) s ds."""
    from fansim.geometry.config import load_blade_params

    # Linearly outward-flaring plate blade (c_root=18 mm, c_tip=36 mm, constant t=2.0 mm)
    c_r, c_t = 18.0, 36.0
    t_const = 2.0
    hub, tip = 20.0, 60.0
    L = (tip - hub) * 1e-3
    tapered = replace(
        _prismatic(hub=hub, tip=tip),
        section_family="plate",
        stations=[
            RadialStation(0.0, c_r, 30.0, thickness=t_const / c_r),
            RadialStation(1.0, c_t, 30.0, thickness=t_const / c_t),
        ],
    )
    load_pa = 20.0
    rep = root_bending_stress(tapered, material="PETG", load_pa=load_pa)
    # Exact analytical integral: M = dP * L^2 * (c_root/6 + c_tip/3); Z_root = c_root * t^2 / 6
    moment = load_pa * (L**2) * ((c_r * 1e-3) / 6.0 + (c_t * 1e-3) / 3.0)
    z_root = (c_r * 1e-3) * ((t_const * 1e-3) ** 2) / 6.0
    expected_mpa = moment / z_root / 1e6
    assert rep.sigma_root_mpa == pytest.approx(expected_mpa, rel=1e-9)

    # Stock v3 (plate): ~1.53x higher than old tip-station estimate 3 * load * L^2 / t_tip^2
    stock = load_blade_params(Path("config/problems/a12x25_reference.yaml"))
    s_rep = root_bending_stress(stock, material="PETG", load_pa=10.0)
    tip_st = max(stock.stations, key=lambda s: s.r_frac)
    t_tip_m = tip_st.thickness * tip_st.chord * 1e-3
    L_s = (stock.tip_radius - stock.hub_radius) * 1e-3
    old_tip_mpa = (3.0 * 10.0 * L_s**2 / (t_tip_m**2)) / 1e6
    ratio = s_rep.sigma_root_mpa / old_tip_mpa
    assert 1.45 <= ratio <= 1.65, f"expected Stock v3 root bending ratio ~1.53x, got {ratio:.3f}x"


def test_section_family_naca_vs_plate_shape_factors():
    """#123 S3: NACA 4-digit K_A/K_I match airfoil.naca4 polygon and scale deflection/stress/f1."""
    from fansim.geometry.airfoil import naca4
    from fansim.structural.deflection import NACA_AREA_K, NACA_INERTIA_K

    pts = naca4(0.0, 0.4, 0.10, n_points=400)
    x0, y0 = pts[:-1, 0], pts[:-1, 1]
    x1, y1 = pts[1:, 0], pts[1:, 1]
    cross = x0 * y1 - x1 * y0
    area = 0.5 * abs(float(np.sum(cross)))
    ix = abs(float(np.sum((y0**2 + y0 * y1 + y1**2) * cross))) / 12.0
    assert NACA_AREA_K == pytest.approx(area / 0.10, rel=1e-3)
    assert NACA_INERTIA_K == pytest.approx(ix / (0.10**3 / 12.0), rel=1e-3)

    plate = replace(_prismatic(chord_mm=12.0, t_frac=0.10, hub=20.0, tip=60.0), section_family="plate")
    naca = replace(plate, section_family="naca")

    assert tip_deflection_mm(naca, "PETG", 20.0) / tip_deflection_mm(plate, "PETG", 20.0) == pytest.approx(
        1.0 / NACA_INERTIA_K, rel=1e-9
    )
    assert tip_deflection_point_load_mm(naca, 0.5, "PETG") / tip_deflection_point_load_mm(
        plate, 0.5, "PETG"
    ) == pytest.approx(1.0 / NACA_INERTIA_K, rel=1e-9)
    assert root_bending_stress(naca, "PETG", 20.0).sigma_root_mpa / root_bending_stress(
        plate, "PETG", 20.0
    ).sigma_root_mpa == pytest.approx(1.0 / NACA_INERTIA_K, rel=1e-9)
    assert first_bending_hz(naca, "PETG") / first_bending_hz(plate, "PETG") == pytest.approx(
        math.sqrt(NACA_INERTIA_K / NACA_AREA_K), rel=1e-9
    )

    with pytest.raises(ValueError, match="section family"):
        tip_deflection_mm(replace(plate, section_family="bogus"), "PETG", 10.0)


def test_resin_skips_layer_adhesion_knockdown_in_stress_and_bending():
    """#123 S4: isotropic RESIN keeps adhesion_k=1.0 by default; FDM filaments keep 0.60."""
    from fansim.manufacturability.materials import MATERIALS
    from fansim.structural.stress import LAYER_ADHESION_K

    p = _prismatic(rpm=60000.0, tip=120.0)
    c_resin = centrifugal_root_stress(p, material="RESIN")
    assert c_resin.adhesion_k == pytest.approx(1.0)
    assert c_resin.yield_mpa == pytest.approx(MATERIALS["RESIN"].yield_strength_mpa)
    assert not c_resin.ok and "layer-adhesion" not in c_resin.reason

    b_resin = root_bending_stress(_prismatic(), material="RESIN", load_pa=1e6)
    assert b_resin.adhesion_k == pytest.approx(1.0)
    assert b_resin.yield_mpa == pytest.approx(MATERIALS["RESIN"].yield_strength_mpa)
    assert not b_resin.ok and "layer-adhesion" not in b_resin.reason

    for fdm in ("PETG", "PLA", "ABS", "PLA+", "TPU"):
        assert centrifugal_root_stress(_prismatic(), material=fdm).adhesion_k == pytest.approx(LAYER_ADHESION_K)
        assert root_bending_stress(_prismatic(), material=fdm, load_pa=10.0).adhesion_k == pytest.approx(
            LAYER_ADHESION_K
        )


# ------------------------------------------------------------------ structural.balance
def test_balance_guards_impossible_masses_empty_and_mismatched_z():
    # Impossible masses: triangle inequality violated (10 > 1 + 1) must raise, not return unbalanced
    with pytest.raises(ValueError, match="cannot statically balance"):
        balanced_uneven_spacing(3, spread=0.2, rng=np.random.default_rng(0), masses=[10.0, 1.0, 1.0])

    with pytest.raises(ValueError, match="spread"):
        balanced_uneven_spacing(5, spread=-0.1)
    with pytest.raises(ValueError, match="non-empty"):
        static_unbalance([])
    with pytest.raises(ValueError, match="finite"):
        static_unbalance([0.0, float("nan")])
    with pytest.raises(ValueError, match=">= 0"):
        static_unbalance([0.0, math.pi], masses=[-1.0, 1.0])
    with pytest.raises(ValueError, match="z_positions"):
        couple_unbalance([0.0, math.pi], [1.0])
    with pytest.raises(ValueError, match="unbalance_mr"):
        residual_force(-0.01, 100.0)

    # Unbalance.balanced matches is_balanced boundary (<= 1e-6)
    u = Unbalance(magnitude=1e-6, angle_rad=0.0, normalized=1e-6)
    assert u.balanced is True


# ------------------------------------------------------------------ acoustics.farfield
def test_farfield_normalizes_r_hat_and_guards_invalid_inputs():
    dt = 1.0 / 20000.0
    t = np.arange(0.0, 0.05, dt)
    F = np.column_stack([np.zeros_like(t), np.zeros_like(t), 0.05 * np.sin(2 * math.pi * 200 * t)])
    p_unit = dipole_pressure(F, dt, r_hat=(0.0, 0.0, 1.0), r_obs=1.0)
    p_scaled = dipole_pressure(F, dt, r_hat=(0.0, 0.0, 3.0), r_obs=1.0)
    assert np.allclose(p_unit, p_scaled, atol=1e-12)

    with pytest.raises(ValueError, match="r_hat"):
        dipole_pressure(F, dt, r_hat=(0.0, 0.0, 0.0))
    with pytest.raises(ValueError, match="r_obs"):
        dipole_pressure(F, dt, r_obs=0.0)
    with pytest.raises(ValueError, match="c0"):
        dipole_pressure(F, dt, c0=-343.0)
    with pytest.raises(ValueError, match="dt"):
        dipole_pressure(F, 0.0)
    with pytest.raises(ValueError, match="frequency"):
        a_weighting_db(-100.0)
    with pytest.raises(ValueError, match="n_blades"):
        blade_pass_frequency(-1, 2000.0)
    with pytest.raises(ValueError, match="rpm"):
        blade_pass_frequency(7, -100.0)
    with pytest.raises(ValueError, match="at least 2"):
        force_from_cv([0.0], np.zeros((1, 3)), np.zeros((1, 3)))


def test_farfield_zero_pressure_returns_neg_inf_without_warning():
    dt = 1.0 / 8192.0
    zeros = np.zeros(512)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        dba = dba_from_pressure(zeros, dt)
        tone = tone_level_db(zeros, dt, 200.0)
        peak = peak_tone_over_harmonics(zeros, dt, 33.333)
    assert dba == float("-inf") and type(dba) is float
    assert tone == float("-inf") and type(tone) is float
    assert peak == float("-inf") and type(peak) is float
    assert not [w for w in caught if issubclass(w.category, RuntimeWarning)]


# ------------------------------------------------------------------ acoustics.fwh
def test_fwh_validation_r_hat_normalization_and_csv_rpm_forwarding(tmp_path: Path):
    dt = 1.0 / 20000.0
    t = np.arange(0.0, 0.25, dt)
    n_blades, rpm = 9, 2000.0
    bpf = blade_pass_frequency(n_blades, rpm)  # 300 Hz (distinct from default 7*2000/60=233.3 Hz)
    Fz = 0.02 * np.sin(2.0 * math.pi * bpf * t)
    F = np.column_stack([np.zeros_like(t), np.zeros_like(t), Fz])

    p_unit = loading_pressure_compact(F, dt, r_hat=(0.0, 0.0, 1.0), r_obs=1.0)
    p_scaled = loading_pressure_compact(F, dt, r_hat=(0.0, 0.0, 5.0), r_obs=1.0)
    assert np.allclose(p_unit, p_scaled, atol=1e-12)

    with pytest.raises(ValueError, match="dia_mm"):
        cv_box_from_dia_mm(0.0)
    with pytest.raises(ValueError, match="r_obs"):
        loading_pressure_compact(F, dt, r_obs=-1.0)
    with pytest.raises(ValueError, match="c0"):
        loading_pressure_panels(t, [], c0=0.0)
    with pytest.raises(ValueError, match="shape"):
        loading_pressure_panels(t, [{"r0": (0, 0, 0), "f": F[:-5]}])
    with pytest.raises(ValueError, match="at least 2"):
        noise_from_compact_force([0.0], np.zeros((1, 3)))
    with pytest.raises(ValueError, match="at least 2"):
        noise_from_permeable_panels([0.0], [])

    # Six-face CSV with 9-blade 1500 RPM tone: forwarding n_blades/rpm captures 225 Hz peak
    perm_csv = tmp_path / "perm.csv"
    hdr = "t_s," + ",".join(f"F{i}{c}" for i in range(6) for c in "xyz")
    rows = [hdr]
    for k, tk in enumerate(t):
        cols = [f"{tk:.9g}"] + ["0"] * 12 + ["0", "0", f"{Fz[k]:.9g}"] + ["0", "0", "0"]
        rows.append(",".join(cols))
    perm_csv.write_text("\n".join(rows) + "\n", encoding="utf-8")

    m_9 = analyze_permeable_csv(perm_csv, dia_mm=110.5, n_blades=n_blades, rpm=rpm)
    m_default = analyze_permeable_csv(perm_csv, dia_mm=110.5)
    assert m_9["bpf_tone_db"] > m_default["bpf_tone_db"] + 15.0

    # 24-patch CSV also forwards n_blades and rpm
    patch_csv = tmp_path / "patches.csv"
    n_p = 6 * PATCH_N * PATCH_N
    hdr_p = "t_s," + ",".join(f"P{i}{c}" for i in range(n_p) for c in "xyz")
    rows_p = [hdr_p]
    for k, tk in enumerate(t):
        cols = [f"{tk:.9g}"] + ["0"] * (3 * n_p)
        cols[1 + 16 * 3 + 2] = f"{Fz[k]:.9g}"
        rows_p.append(",".join(cols))
    patch_csv.write_text("\n".join(rows_p) + "\n", encoding="utf-8")

    mp_9 = analyze_patches_csv(patch_csv, dia_mm=110.5, n_blades=n_blades, rpm=rpm)
    mp_default = analyze_patches_csv(patch_csv, dia_mm=110.5)
    assert mp_9["analogy"] == "fwh_patches"
    assert mp_9["bpf_tone_db"] > mp_default["bpf_tone_db"] + 15.0


# ------------------------------------------------------------------ acoustics.case
def test_case_parse_time_dir_handles_scientific_notation(tmp_path: Path):
    assert _parse_time_dir("0") == 0.0
    assert _parse_time_dir("500") == 500.0
    assert _parse_time_dir("0.0025") == pytest.approx(0.0025)
    assert _parse_time_dir("1e-05") == pytest.approx(1e-5)
    assert _parse_time_dir("2.5e-03") == pytest.approx(2.5e-3)
    assert _parse_time_dir("processor0") is None
    assert _parse_time_dir("constant") is None
    assert _parse_time_dir("-1.0") is None
    assert _parse_time_dir("nan") is None
    assert _parse_time_dir("inf") is None

    # Only time dir "0" present -> clear FileNotFoundError
    (tmp_path / "0").mkdir()
    with pytest.raises(FileNotFoundError, match="no reconstructed non-zero time dir"):
        read_case(tmp_path)


# ------------------------------------------------------------------ acoustics.loading
def test_loading_proxy_validation():
    with pytest.raises(ValueError, match="n_blades"):
        loading_noise_proxy(0, 0.01)
    with pytest.raises(ValueError, match="n_blades"):
        loading_proxy_from_rans(0, 0.07)
    with pytest.raises(ValueError, match="thrust"):
        loading_noise_proxy(7, float("nan"))
    with pytest.raises(ValueError, match="derate"):
        loading_proxy_operating(7, 0.07, derate=-0.5)
    with pytest.raises(ValueError, match="derate"):
        loading_proxy_operating(7, 0.07, derate=float("nan"))
    with pytest.raises(ValueError, match="equal length"):
        calibrate([5, 6, 7], [0.01, 0.02], [40.0, 41.0, 42.0])
    with pytest.raises(ValueError, match="finite"):
        calibrate([5, 6, 7], [0.01, float("nan"), 0.03], [40.0, 41.0, 42.0])


# ------------------------------------------------------------------ acoustics.tip_loading
def test_tip_loading_validation_and_missing_geometry_returns_none(tmp_path: Path, monkeypatch):
    with pytest.raises(ValueError, match="rpm"):
        tip_speed_ms(-1000.0, 54.5)
    with pytest.raises(ValueError, match="tip_radius_mm"):
        tip_speed_ms(2000.0, -54.5)
    with pytest.raises(ValueError, match="finite"):
        tip_loading_swl_db(float("nan"), 50.0)
    with pytest.raises(ValueError, match="finite"):
        tip_loading_swl_db(11.4, float("nan"))

    # Negative actual_rpm in _eval_result.json returns None (not a silently clamped dB)
    (tmp_path / "_eval_result.json").write_text('{"cfm_free": 55.0, "actual_rpm": -2000.0}')
    assert noise_hint_from_case(tmp_path) is None

    # OSError / ValueError from load_case_radii_omega returns None instead of crashing
    (tmp_path / "_eval_result.json").write_text('{"cfm_free": 55.0, "actual_rpm": 2000.0}')
    monkeypatch.setattr(
        "fansim.cfd.spanwise.load_case_radii_omega",
        lambda _p: (_ for _ in ()).throw(OSError("unreadable case")),
    )
    assert noise_hint_from_case(tmp_path) is None


# ------------------------------------------------------------------ acoustics.tonal
def test_tonal_guards_empty_nan_and_m_max():
    with pytest.raises(ValueError, match="non-empty"):
        blade_passing_modes([])
    with pytest.raises(ValueError, match="finite"):
        peak_tone_reduction_db([0.0, float("nan")])
    with pytest.raises(ValueError, match="m_max"):
        blade_passing_modes([0.0, math.pi], m_max=0)
    with pytest.raises(ValueError, match="m_max"):
        blade_passing_modes([0.0, math.pi], m_max=-4)

    ang = balanced_uneven_spacing(7, spread=0.4, rng=np.random.default_rng(7))
    assert is_balanced(ang, tol=1e-6)
    amp = peak_tone_amplitude(ang)
    ratio = tonal_peak_ratio(ang)
    red_db = peak_tone_reduction_db(ang)
    assert type(amp) is float and type(ratio) is float and type(red_db) is float
    assert 0.0 < ratio < 1.0 and red_db < 0.0
