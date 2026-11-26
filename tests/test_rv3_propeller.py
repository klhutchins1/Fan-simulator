"""RV-3 Module 5 verification & regression tests for fansim.propeller.bemt and polars."""

from __future__ import annotations

import ast
import math
from pathlib import Path

import pytest

from fansim.audit.registry import load_registry
from fansim.geometry.blade import BladeParams, RadialStation
from fansim.physics import air
from fansim.propeller import bemt as B
from fansim.propeller import polars as P
from fansim.propeller.bemt import PropPerf, analyze
from fansim.propeller.bemt_catalog import UIUC_DIR, load_uiuc_geometry_blade
from fansim.propeller.polar import nondim


def _simple_blade(
    *,
    n_blades: int = 2,
    hub_mm: float = 20.0,
    tip_mm: float = 100.0,
    chord_mm: float = 15.0,
    twist_deg: float = 20.0,
    thickness: float = 0.12,
    camber: float = 0.04,
) -> BladeParams:
    stations = [
        RadialStation(0.0, chord_mm, twist_deg, thickness, camber, 0.4),
        RadialStation(1.0, chord_mm, twist_deg, thickness, camber, 0.4),
    ]
    return BladeParams(
        n_blades=n_blades,
        hub_radius=hub_mm,
        tip_radius=tip_mm,
        stations=stations,
    )


# ------------------------------------------------------------------ single-source air constants


def test_bemt_air_constants_single_sourced_from_physics_air():
    assert B.RHO_AIR == air.RHO_ISA
    assert B.NU_AIR == air.NU_AIR
    assert B.C_AIR == air.C0_AIR
    assert B.G == 9.80665

    src = Path("fansim/propeller/bemt.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported_from_prop_spec = [
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "fansim.prop_spec"
        for alias in node.names
    ]
    assert "C_AIR" not in imported_from_prop_spec


# ------------------------------------------------------------------ analytical BEMT checks


def test_single_element_bemt_matches_closed_form_equations(monkeypatch):
    """On a 1-element constant-(cl, cd) rotor, verify exact force/momentum/power/FM/eta identities."""
    cl_const, cd_const = 0.6, 0.02
    monkeypatch.setattr(
        B,
        "_section_aero",
        lambda alpha, camber, re=None, thickness=0.12: (cl_const, cd_const, False, 1.5),
    )
    monkeypatch.setattr(
        B,
        "_compressibility_cl_cd",
        lambda cl, cd, mach, *, stalled=False, cl_cap=None: (cl, cd),
    )

    blade = _simple_blade(n_blades=2, hub_mm=20.0, tip_mm=100.0, chord_mm=15.0, twist_deg=25.0)
    rpm = 6000.0
    v_fwd = 5.0
    perf = analyze(blade, rpm, v_forward=v_fwd, n_elem=1)
    assert perf.converged is True

    omega = rpm * 2.0 * math.pi / 60.0
    R = 0.100
    r = 0.060  # midpoint of [0.020, 0.100]
    dr = 0.080
    c = 0.015
    rho = B.RHO_AIR
    U = omega * r

    # Recover (vi, vth) independently from the exact element equations
    vi, vth = 2.0, 0.0
    for _ in range(200):
        Vax = v_fwd + vi
        Vt = U - 0.5 * vth
        phi = math.atan2(Vax, Vt)
        W2 = Vax * Vax + Vt * Vt
        f = (2.0 / 2.0) * (R - r) / (r * math.sin(phi))
        F = (2.0 / math.pi) * math.acos(math.exp(-min(f, 20.0)))
        dT = 0.5 * rho * W2 * c * 2 * (cl_const * math.cos(phi) - cd_const * math.sin(phi))
        f_th = 0.5 * rho * W2 * c * 2 * (cl_const * math.sin(phi) + cd_const * math.cos(phi))
        vi_new = dT / (4.0 * math.pi * r * rho * abs(Vax) * F)
        vth_new = f_th / (2.0 * math.pi * r * rho * abs(Vax))
        if abs(vi_new - vi) < 1e-12 and abs(vth_new - vth) < 1e-12:
            break
        vi = 0.5 * (vi + vi_new)
        vth = 0.5 * (vth + vth_new)

    expected_T = dT * dr
    expected_Q = f_th * r * dr
    expected_P = expected_Q * omega
    expected_eta = expected_T * v_fwd / expected_P
    expected_fm = (expected_T**1.5 / math.sqrt(2.0 * rho * math.pi * R * R)) / expected_P

    assert perf.thrust_n == pytest.approx(expected_T, rel=1e-4)
    assert perf.torque_nm == pytest.approx(expected_Q, rel=1e-4)
    assert perf.power_w == pytest.approx(perf.torque_nm * omega, rel=1e-12)
    assert perf.thrust_g == pytest.approx(perf.thrust_n / 9.80665 * 1000.0, rel=1e-12)
    assert perf.efficiency_g_per_w == pytest.approx(perf.thrust_g / perf.power_w, rel=1e-12)
    assert perf.prop_efficiency == pytest.approx(expected_eta, rel=1e-4)
    assert perf.figure_of_merit_raw == pytest.approx(expected_fm, rel=1e-4)

    # Nondim consistency with fansim.propeller.polar.nondim
    nd = nondim(perf.thrust_n, perf.power_w, rpm=rpm, diameter_m=2.0 * R, v_inf=v_fwd, rho=rho)
    assert perf.prop_efficiency == pytest.approx(nd["eta"], rel=1e-12)


# ------------------------------------------------------------------ bemt bug-fix regression tests


@pytest.mark.parametrize(
    "kwargs, blade_override",
    [
        ({"rpm": -100.0}, None),
        ({"rpm": float("nan")}, None),
        ({"rpm": float("inf")}, None),
        ({"rpm": 6000.0, "v_forward": -1.0}, None),
        ({"rpm": 6000.0, "v_forward": float("nan")}, None),
        ({"rpm": 6000.0, "rho": 0.0}, None),
        ({"rpm": 6000.0, "rho": -1.225}, None),
        ({"rpm": 6000.0, "rho": float("inf")}, None),
        ({"rpm": 6000.0, "n_elem": 0}, None),
        ({"rpm": 6000.0, "n_elem": -4}, None),
        ({"rpm": 6000.0}, BladeParams(n_blades=-1, hub_radius=10.0, tip_radius=50.0, stations=_simple_blade().stations)),
        ({"rpm": 6000.0}, BladeParams(n_blades=2, hub_radius=10.0, tip_radius=50.0, stations=[])),
        ({"rpm": 6000.0}, BladeParams(n_blades=2, hub_radius=-5.0, tip_radius=50.0, stations=_simple_blade().stations)),
        ({"rpm": 6000.0}, BladeParams(n_blades=2, hub_radius=50.0, tip_radius=50.0, stations=_simple_blade().stations)),
        ({"rpm": 6000.0}, BladeParams(n_blades=2, hub_radius=60.0, tip_radius=50.0, stations=_simple_blade().stations)),
    ],
)
def test_analyze_rejects_invalid_inputs(kwargs, blade_override):
    blade = blade_override if blade_override is not None else _simple_blade()
    with pytest.raises(ValueError):
        analyze(blade, **kwargs)


def test_analyze_zero_rpm_static_has_exact_zero_thrust_and_power():
    blade = _simple_blade()
    p = analyze(blade, rpm=0.0, v_forward=0.0)
    assert isinstance(p, PropPerf)
    assert p.thrust_n == 0.0
    assert p.torque_nm == 0.0
    assert p.power_w == 0.0
    assert p.thrust_g == 0.0
    assert p.efficiency_g_per_w == 0.0
    assert p.figure_of_merit == 0.0
    assert p.figure_of_merit_raw == 0.0
    assert p.prop_efficiency is None
    assert p.converged is True


def test_analyze_zero_blades_returns_exact_zeros():
    blade = _simple_blade(n_blades=0)
    p = analyze(blade, rpm=6000.0)
    assert p.thrust_n == 0.0 and p.torque_nm == 0.0 and p.power_w == 0.0
    assert p.converged is True


def test_analyze_returns_native_python_floats():
    blade = load_uiuc_geometry_blade(UIUC_DIR / "apcsf_9x4.7_geom.txt", 9.0)
    p = analyze(blade, rpm=6026.0, v_forward=5.0)
    for field_name in (
        "thrust_n",
        "torque_nm",
        "power_w",
        "rpm",
        "v_forward",
        "thrust_g",
        "efficiency_g_per_w",
        "figure_of_merit",
        "figure_of_merit_raw",
        "prop_efficiency",
    ):
        val = getattr(p, field_name)
        assert type(val) is float, f"{field_name} has type {type(val).__name__}, expected float"
    assert type(p.converged) is bool


def test_analyze_reynolds_scales_with_custom_rho(monkeypatch):
    """At constant kinematics, halving rho doubles kinematic viscosity nu = mu/rho and halves Re."""
    seen_re: list[float] = []

    def spy_aero(alpha, camber, re=None, thickness=0.12):
        assert re is not None
        seen_re.append(float(re))
        return (0.5, 0.02, False, 1.4)

    monkeypatch.setattr(B, "_section_aero", spy_aero)
    blade = _simple_blade()

    seen_re.clear()
    analyze(blade, rpm=6000.0, rho=B.RHO_AIR, n_elem=4)
    re_sea = seen_re[0]  # first iteration uses identical initial guess (vi=2, vth=0)

    seen_re.clear()
    analyze(blade, rpm=6000.0, rho=0.5 * B.RHO_AIR, n_elem=4)
    re_alt = seen_re[0]

    assert re_alt == pytest.approx(0.5 * re_sea, rel=1e-12)


# ------------------------------------------------------------------ polars bug-fix regression tests


@pytest.mark.parametrize(
    "alpha_rad, camber, re, thickness",
    [
        (float("nan"), 0.04, 80000.0, 0.12),
        (float("inf"), 0.04, 80000.0, 0.12),
        (-float("inf"), 0.04, 80000.0, 0.12),
        (0.1, float("nan"), 80000.0, 0.12),
        (0.1, 0.04, 80000.0, float("nan")),
        (0.1, 0.04, float("nan"), 0.12),
        (0.1, 0.04, float("inf"), 0.12),
    ],
)
def test_section_table_returns_none_on_nonfinite_inputs(alpha_rad, camber, re, thickness):
    assert P.section_table(alpha_rad, camber, re, thickness=thickness) is None
    assert P.cl_cd_table(alpha_rad, camber, re, thickness=thickness) is None


@pytest.mark.parametrize(
    "camber, thickness",
    [
        (float("nan"), 0.12),
        (float("inf"), 0.12),
        (0.04, float("nan")),
        (0.04, -float("inf")),
    ],
)
def test_family_for_camber_rejects_nonfinite(camber, thickness):
    with pytest.raises(ValueError):
        P.family_for_camber(camber, thickness)


def test_parse_csv_single_row_and_malformed_validation(tmp_path):
    # Single-row CSV must return 1-D arrays usable by _interp_alpha
    one = tmp_path / "one.csv"
    one.write_text("alpha_deg,cl,cd\n4.0,0.65,0.03\n", encoding="utf-8")
    a, cl, cd = P._parse_csv(one)
    assert a.ndim == 1 and len(a) == 1
    assert P._interp_alpha(4.0, a, cl, cd) == (pytest.approx(0.65), pytest.approx(0.03))
    assert P._interp_alpha(10.0, a, cl, cd) == (pytest.approx(0.65), pytest.approx(0.03))

    # Empty CSV (header only) must raise ValueError
    empty = tmp_path / "empty.csv"
    empty.write_text("alpha_deg,cl,cd\n", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        P._parse_csv(empty)

    # Unsorted alpha_deg must raise ValueError
    unsorted = tmp_path / "unsorted.csv"
    unsorted.write_text("alpha_deg,cl,cd\n5.0,0.6,0.03\n2.0,0.3,0.02\n", encoding="utf-8")
    with pytest.raises(ValueError, match="strictly increasing"):
        P._parse_csv(unsorted)

    # Non-finite values must raise ValueError
    nan_csv = tmp_path / "nan.csv"
    nan_csv.write_text("alpha_deg,cl,cd\n0.0,nan,0.02\n5.0,0.6,0.03\n", encoding="utf-8")
    with pytest.raises(ValueError, match="non-finite"):
        P._parse_csv(nan_csv)


def test_polars_re_log10_interpolation_and_bounds():
    P.clear_polar_cache()
    tables = P.load_polar_family("naca4412")
    a8, cl8, cd8 = tables[80000.0]
    a16, cl16, cd16 = tables[160000.0]
    c8, d8 = P._interp_alpha(4.0, a8, cl8, cd8)
    c16, d16 = P._interp_alpha(4.0, a16, cl16, cd16)

    # 75% in log10 space between 8e4 and 1.6e5
    w = 0.75
    re_w = 10.0 ** ((1.0 - w) * math.log10(80000.0) + w * math.log10(160000.0))
    row = P.section_table(math.radians(4.0), 0.04, re_w)
    assert row is not None
    assert row[0] == pytest.approx((1.0 - w) * c8 + w * c16, rel=1e-12)
    assert row[1] == pytest.approx((1.0 - w) * d8 + w * d16, rel=1e-12)

    # Above upper Re clamps to 1.6e5
    hi = P.section_table(math.radians(4.0), 0.04, 500000.0)
    at_top = P.section_table(math.radians(4.0), 0.04, 160000.0)
    assert hi == at_top

    # Below lower Re returns None
    assert P.section_table(math.radians(4.0), 0.04, 39999.9) is None


# ------------------------------------------------------------------ audit registry hygiene


def test_registry_propeller_bemt_depends_on_polars_and_no_stale_exempt():
    reg = load_registry()
    bemt_unit = reg.units["propeller.bemt"]
    assert "propeller.polars" in bemt_unit.depends_on
    assert "propeller.neuralfoil_polars" in bemt_unit.depends_on
    assert "propeller.polar_coefficients" in bemt_unit.depends_on
    assert "fansim.propeller.polars:PolarPoint" not in reg.exempt
