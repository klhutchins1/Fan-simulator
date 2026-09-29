"""Audit #5: structural models vs closed-form beam / rotating-bar / vibration solutions.

Tolerances were pre-registered in docs/validation/audits/2026-09-29-audit-05-structural.md
before any comparison:
  deflection (uniform load)  rel err <= 2% vs q L^4 / (8 E I) on a prismatic beam
  tip point load, sigma=Mc/I no code exists -> verified only for the FE harness used here (<= 0.1%)
  centrifugal root stress    rel err <= 1e-6 vs closed form and vs numerical integral of rho w^2 r dr
  first bending frequency    rel err <= 1% vs (1.875^2/2pi) sqrt(EI/(rho A L^4)); <= 1% vs Hermite FE
  balance                    residual <= 1e-8 normalized; couple/force exact to 1e-9
  material properties        inside published datasheet ranges (see MATERIAL_RANGES)
Expectations are computed in mm / N / MPa here; the code under test works in SI.
"""

from __future__ import annotations

import math
from dataclasses import replace

import numpy as np
import pytest

from fansim.geometry.blade import BladeParams, RadialStation
from fansim.manufacturability.fdm_rules import check_printability
from fansim.manufacturability.materials import MATERIALS
from fansim.optimize.print_penalty import apply_print_penalty
from fansim.structural import balance as B
from fansim.structural.deflection import deflection_report, tip_deflection_mm
from fansim.structural.flutter import CANTILEVER_LAMBDA, first_bending_hz, flutter_report
from fansim.structural.flutter import max_blades_for_margin
from fansim.structural.stress import FDM_E_K, centrifugal_root_stress

DEFL_TOL = 0.02
STRESS_TOL = 1e-6
FREQ_TOL = 0.01


def prismatic(chord_mm=12.0, t_frac=0.10, hub=20.0, tip=60.0, rpm=2000.0, n=5) -> BladeParams:
    sts = [RadialStation(r, chord_mm, 30.0, thickness=t_frac) for r in (0.0, 0.5, 1.0)]
    return replace(BladeParams(), stations=sts, hub_radius=hub, tip_radius=tip, rpm=rpm, n_blades=n)


def e_eff_mpa(material):  # FDM knockdown applies to non-resin materials
    return MATERIALS[material].youngs_modulus_gpa * 1e3 * FDM_E_K


# ---- Euler-Bernoulli Hermite FE cantilever (independent of closed forms) ----------------------
def _fe(EI, rhoA, L, n=40):
    l = L / n
    nd = 2 * (n + 1)
    K = np.zeros((nd, nd))
    M = np.zeros((nd, nd))
    f = np.zeros(nd)
    ke = EI / l**3 * np.array([[12, 6*l, -12, 6*l], [6*l, 4*l*l, -6*l, 2*l*l],
                               [-12, -6*l, 12, -6*l], [6*l, 2*l*l, -6*l, 4*l*l]])
    me = rhoA * l / 420 * np.array([[156, 22*l, 54, -13*l], [22*l, 4*l*l, 13*l, -3*l*l],
                                    [54, 13*l, 156, -22*l], [-13*l, -3*l*l, -22*l, 4*l*l]])
    for e in range(n):
        s = slice(2 * e, 2 * e + 4)
        K[s, s] += ke
        M[s, s] += me
        f[s] += np.array([l / 2, l * l / 12, l / 2, -l * l / 12])
    return K[2:, 2:], M[2:, 2:], f[2:]


def fe_tip_uniform(EI, L, q):
    K, _, f = _fe(EI, 1.0, L)
    return float(np.linalg.solve(K, q * f)[-2])


def fe_tip_point(EI, L, P):
    K, _, _ = _fe(EI, 1.0, L)
    F = np.zeros(K.shape[0])
    F[-2] = P
    return float(np.linalg.solve(K, F)[-2])


def fe_f1(EI, rhoA, L):
    K, M, _ = _fe(EI, rhoA, L)
    w2 = np.sort(np.linalg.eigvals(np.linalg.solve(M, K)).real)
    return math.sqrt(w2[0]) / (2 * math.pi)


# ---- structural.deflection ---------------------------------------------------------------------
@pytest.mark.parametrize("material", ["PETG", "PLA", "ABS"])
@pytest.mark.parametrize("chord,tf,load", [(12.0, 0.10, 20.0), (25.0, 0.06, 5.0), (8.0, 0.2, 100.0)])
def test_uniform_load_tip_deflection_closed_form(material, chord, tf, load):
    p = prismatic(chord, tf)
    L = p.tip_radius - p.hub_radius                       # mm
    t = tf * chord                                        # mm
    I = chord * t**3 / 12.0                               # mm^4
    q = load * 1e-6 * chord                               # N/mm  (Pa = 1e-6 N/mm^2)
    expected = q * L**4 / (8 * e_eff_mpa(material) * I)   # mm
    got = tip_deflection_mm(p, material, load)
    assert got == pytest.approx(expected, rel=DEFL_TOL)
    assert got == pytest.approx(expected, rel=1e-9)       # in fact exact
    fe = fe_tip_uniform(e_eff_mpa(material) * I, L, q)
    assert fe == pytest.approx(expected, rel=1e-3)        # independent FE agrees with the closed form


def test_deflection_scaling_and_units():
    p = prismatic()
    d = tip_deflection_mm(p, "PETG", 10.0)
    assert tip_deflection_mm(p, "PETG", 20.0) == pytest.approx(2 * d, rel=1e-12)      # linear in load
    p2 = prismatic(tip=20.0 + 2 * 40.0)
    assert tip_deflection_mm(p2, "PETG", 10.0) == pytest.approx(16 * d, rel=1e-9)     # L^4
    p3 = prismatic(t_frac=0.20)                                                        # q fixed, I x8
    assert tip_deflection_mm(p3, "PETG", 10.0) == pytest.approx(d / 8, rel=1e-9)
    # absolute anchor, SI hand numbers: c=10 mm, t=1 mm, L=40 mm, 100 Pa, PETG E=2.1e9*0.7
    pa = prismatic(10.0, 0.10, hub=20.0, tip=60.0)
    E, c, tt, L = 2.1e9 * 0.7, 0.010, 0.001, 0.040
    delta_m = (100.0 * c) * L**4 / (8 * E * (c * tt**3 / 12))
    assert tip_deflection_mm(pa, "PETG", 100.0) == pytest.approx(delta_m * 1e3, rel=1e-9)


def test_tip_point_load_closed_form_via_fe_harness():
    # No point-load function exists in fansim; verify the FE harness reproduces PL^3/(3EI).
    EI, L, P = 2.0e3, 40.0, 0.5
    assert fe_tip_point(EI, L, P) == pytest.approx(P * L**3 / (3 * EI), rel=1e-3)


def test_root_bending_stress_not_in_code():
    # sigma = M c / I: no function in fansim computes root bending stress (roadmap note).
    import fansim.structural as S
    assert not any("bend" in n.lower() and "stress" in n.lower() for n in dir(S))


def test_deflection_report_gate_logic():
    p = prismatic()
    d = tip_deflection_mm(p, "PETG", 30.0)
    assert deflection_report(p, d * 1.01, material="PETG", load_pa=30.0).ok
    r = deflection_report(p, d * 0.99, material="PETG", load_pa=30.0)
    assert not r.ok and "PETG" in r.reason
    assert deflection_report(p, 0.0, material="PETG", load_pa=30.0).gap_frac == math.inf


# ---- structural.centrifugal --------------------------------------------------------------------
@pytest.mark.parametrize("rpm,hub,tip,material", [(2000, 21.5, 56.5, "PETG"), (12000, 10, 60, "PLA"),
                                                 (30000, 5, 100, "ABS")])
def test_centrifugal_root_stress_closed_form(rpm, hub, tip, material):
    p = prismatic(hub=hub, tip=tip, rpm=rpm)
    rep = centrifugal_root_stress(p, material)
    w = rpm * 2 * math.pi / 60
    rho = MATERIALS[material].density_kg_m3
    closed_pa = rho * w**2 * ((tip * 1e-3) ** 2 - (hub * 1e-3) ** 2) / 2
    r = np.linspace(hub * 1e-3, tip * 1e-3, 200001)
    y = rho * w**2 * r
    integral_pa = float(np.sum((y[1:] + y[:-1]) / 2 * np.diff(r)))
    assert rep.sigma_root_mpa * 1e6 == pytest.approx(closed_pa, rel=STRESS_TOL)
    assert rep.sigma_root_mpa * 1e6 == pytest.approx(integral_pa, rel=STRESS_TOL)
    # unit consistency: MPa, allowable = yield*0.6, SF = allowable / sigma
    assert rep.yield_mpa == pytest.approx(MATERIALS[material].yield_strength_mpa * 0.6)
    assert rep.safety_factor == pytest.approx(rep.yield_mpa / rep.sigma_root_mpa, rel=1e-9)


def test_centrifugal_independent_of_cross_section_and_ok_flag():
    a = centrifugal_root_stress(prismatic(chord_mm=5, t_frac=0.05, rpm=20000), "PETG")
    b = centrifugal_root_stress(prismatic(chord_mm=40, t_frac=0.2, rpm=20000), "PETG")
    assert a.sigma_root_mpa == pytest.approx(b.sigma_root_mpa, rel=1e-12)
    assert centrifugal_root_stress(prismatic(rpm=2000), "PETG").ok
    assert not centrifugal_root_stress(prismatic(rpm=60000, tip=120.0), "PLA").ok


# ---- structural.flutter (resonance gate) -------------------------------------------------------
def test_cantilever_lambda_is_first_root():
    lam = CANTILEVER_LAMBDA
    assert math.cos(lam) * math.cosh(lam) + 1 == pytest.approx(0.0, abs=1e-5)


@pytest.mark.parametrize("material", ["PETG", "PLA", "ABS"])
@pytest.mark.parametrize("chord,tf,hub,tip", [(12.0, 0.10, 20.0, 60.0), (30.0, 0.05, 21.5, 56.5),
                                              (8.0, 0.2, 10.0, 90.0)])
def test_first_bending_frequency_closed_form(material, chord, tf, hub, tip):
    p = prismatic(chord, tf, hub, tip)
    m = MATERIALS[material]
    L = (tip - hub) * 1e-3
    c = chord * 1e-3
    t = tf * c
    E = m.youngs_modulus_gpa * 1e9 * FDM_E_K
    EI = E * c * t**3 / 12
    rhoA = m.density_kg_m3 * c * t
    expected = (1.875104**2 / (2 * math.pi)) * math.sqrt(EI / (rhoA * L**4))
    got = first_bending_hz(p, material)
    assert got == pytest.approx(expected, rel=FREQ_TOL)
    assert fe_f1(EI, rhoA, L) == pytest.approx(got, rel=FREQ_TOL)   # independent FE eigenvalue


def test_flutter_report_bpf_and_margin():
    p = prismatic(n=7, rpm=3000)
    r = flutter_report(p, "PETG")
    assert r.bpf_hz == pytest.approx(7 * 3000 / 60)
    assert r.rpm_hz == pytest.approx(50.0)
    assert r.margin == pytest.approx(r.f1_hz / r.bpf_hz)
    assert r.ok == (r.margin >= 1.2)
    n = max_blades_for_margin(r.f1_hz, 3000)
    assert n * 50 * 1.2 <= r.f1_hz < (n + 1) * 50 * 1.2
    assert not flutter_report(prismatic(n=7, rpm=3000), "TPU").ok


def test_flutter_is_resonance_gate_not_flutter():
    import fansim.structural.flutter as fl
    assert "not flutter" in " ".join(fl.__doc__.split()).replace("not flutter derivatives","not flutter")     # module name overstates: only f1 vs BPF is computed


# ---- structural.balance ------------------------------------------------------------------------
@pytest.mark.parametrize("n", [2, 3, 5, 7, 12])
def test_equal_spacing_balanced_and_sum_of_phasors(n):
    a = B.equal_spacing(n)
    assert abs(np.exp(1j * a).sum()) < 1e-12
    assert B.is_balanced(a)


def test_unbalance_values_exact():
    u = B.static_unbalance([0.0], masses=[2.0], radii=[0.05])
    assert u.magnitude == pytest.approx(0.1) and u.normalized == pytest.approx(1.0)
    u = B.static_unbalance([0.0, math.pi / 2], masses=[1, 1], radii=[1, 1])
    assert u.magnitude == pytest.approx(math.sqrt(2)) and u.angle_rad == pytest.approx(math.pi / 4)
    mr, ang = B.required_counterweight([0.0, 0.0], masses=[1, 1], radii=[0.1, 0.1])
    assert mr == pytest.approx(0.2) and ang == pytest.approx(math.pi)
    assert B.residual_force(0.001, 100.0) == pytest.approx(10.0)          # F = U w^2
    assert B.couple_unbalance([0.0, math.pi], [1.0, -1.0]) == pytest.approx(2.0)
    assert B.couple_unbalance([0.0, math.pi], [1.0, 1.0]) == pytest.approx(0.0, abs=1e-12)


@pytest.mark.parametrize("n", [4, 6, 5, 7, 9])
@pytest.mark.parametrize("spread", [0.2, 0.6])
def test_balanced_uneven_spacing_is_balanced_and_uneven(n, spread):
    a = B.balanced_uneven_spacing(n, spread, rng=np.random.default_rng(3))
    assert B.is_balanced(a, tol=1e-8)
    gaps = np.diff(np.concatenate([a, [a[0] + 2 * math.pi]]))
    assert gaps.max() - gaps.min() > 1e-3


def test_balanced_uneven_with_masses_and_counterweight_nulls():
    m = [1.0, 1.2, 0.9, 1.1, 1.0]
    a = B.balanced_uneven_spacing(5, 0.3, rng=np.random.default_rng(1), masses=m)
    assert B.is_balanced(a, m, tol=1e-8)
    a2 = B.equal_spacing(5)
    mr, ang = B.required_counterweight(a2, masses=m)
    ang2 = np.append(a2, ang)
    m2 = np.append(m, mr)
    assert B.static_unbalance(ang2, masses=m2).magnitude < 1e-9


# ---- material properties vs datasheet ranges ---------------------------------------------------
# Ranges (E GPa, yield MPa, density kg/m3, HDT@0.45MPa C). Sources: NatureWorks Ingeo 3D850 TDS
# (PLA E ~3.5 GPa, yield ~60 MPa, 1240 kg/m3); Eastman Amphora / generic PETG TDS (E 2.0-2.2 GPa,
# yield ~50 MPa, 1270 kg/m3, HDT ~70 C); ASTM D638 / ISO 527 generic ABS (E 1.8-2.6, yield 33-45,
# 1040-1060, HDT 90-105); NinjaFlex / TPU 85A-95A TDS (E ~0.01-0.1 GPa, 1120-1220 kg/m3).
# Printed FDM parts sit 10-40% below moulded values (Ahn 2002; Tymrak 2014).
MATERIAL_RANGES = {
    "PLA": dict(E=(2.7, 4.0), Y=(35, 70), rho=(1200, 1290), hdt=(50, 65)),
    "PLA+": dict(E=(2.2, 3.6), Y=(35, 65), rho=(1200, 1290), hdt=(50, 70)),
    "PETG": dict(E=(1.8, 2.4), Y=(35, 55), rho=(1250, 1300), hdt=(65, 80)),
    "ABS": dict(E=(1.6, 2.6), Y=(30, 45), rho=(1030, 1070), hdt=(85, 105)),
    "TPU": dict(E=(0.005, 0.10), Y=(10, 55), rho=(1100, 1230), hdt=(40, 90)),
}


@pytest.mark.parametrize("name", list(MATERIAL_RANGES))
def test_material_properties_within_datasheet_ranges(name):
    m, r = MATERIALS[name], MATERIAL_RANGES[name]
    assert r["E"][0] <= m.youngs_modulus_gpa <= r["E"][1]
    assert r["Y"][0] <= m.yield_strength_mpa <= r["Y"][1]
    assert r["rho"][0] <= m.density_kg_m3 <= r["rho"][1]
    assert r["hdt"][0] <= m.heat_deflection_c <= r["hdt"][1]


# ---- print penalty / printability --------------------------------------------------------------
def test_print_penalty_fsi_factor_bounds_and_monotone():
    prev = 1.0
    for frac in (0.0, 0.1, 0.5, 1.0, 5.0):
        cf, cl, eta, s = apply_print_penalty(60.0, 40.0, 0.3, tip_deflection_mm=frac, tip_gap_mm=1.0)
        k = s["print_k_fsi"]
        assert 0.90 <= k <= 1.0 and k <= prev
        assert cf == pytest.approx(60.0 * 0.95 * k)
        prev = k
    assert apply_print_penalty(60, 40, 0.3, enabled=False)[3] == {}


def test_fdm_min_wall_is_thickness_times_chord_in_mm():
    p = prismatic(chord_mm=10.0, t_frac=0.05)           # 0.5 mm wall < 0.8 mm body floor
    rep = check_printability(p)
    assert rep.min_section_thickness_mm == pytest.approx(0.5)
    assert not rep.printable
    assert check_printability(prismatic(chord_mm=10.0, t_frac=0.10)).printable
