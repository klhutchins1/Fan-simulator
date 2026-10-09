"""Scratch prototypes for leads #9 (Balla&Vad plate polar + post-stall), #8 (Koch stall cap),
#6 (Carter deviation), #11 (Ning-style bracketed solve). Mirrors fansim.fan_bem.operating_point/pq_curve
with switches; does NOT edit src. Run from the project root with the project venv."""
from __future__ import annotations
import math, os, sys
from dataclasses import dataclass, field
import numpy as np
sys.path.insert(0, os.getcwd())
from fansim import fan_bem as FB
from fansim.fan_bem import FanPoint, FanCurve, _interp_geometry, _effective_tip_gap_mm, RHO_AIR, NU_AIR, \
    SLIP, K_FRICTION, K_TIP_LEAK, N_ITER_MAX
from fansim.propeller.bemt import _cl_cd
from fansim.cfd.metrics import CFM_PER_M3S

# ---------------- #9 Balla & Vad (2021) cambered plate, Eqs (2)-(7); f/c in %, alpha in deg.
# Valid: alpha 0..10 deg, f/c 0..8 %, Re 6e4..3e5 (we EXTRAPOLATE to Re~1.5-4e4). Rows j (camber power), cols i (alpha power).
_A = np.array([[7.95e-3, 6.48e-2, 1.55e-2, -1.38e-3], [8.99e-2, 1.61e-2, -4.83e-3, 3.45e-4], [9.76e-4, -1.70e-3, 3.46e-4, -2.30e-5]])
_B = np.array([[1.03e-7, -5.40e-8, 4.16e-8, -3.46e-9], [-7.60e-7, 9.32e-8, -5.61e-9, 5.40e-10], [1.62e-7, -2.13e-8, 4.99e-10, 5.77e-12]])
_C = np.array([[1.81e-2, -5.21e-3, 2.43e-3, -3.37e-5], [1.67e-3, 8.35e-4, -8.91e-4, 5.41e-5], [-7.27e-5, -1.02e-4, 8.75e-5, -6.18e-6]])
_D = np.array([[-2.04e-7, -1.81e-8, -2.16e-10, 3.66e-10], [9.84e-8, 4.72e-9, -1.23e-9, -6.05e-11], [-1.24e-8, -6.74e-10, 2.44e-10, -4.53e-12]])


def _poly(M, fc, a):
    return sum(M[j, i] * fc ** j * a ** i for j in range(3) for i in range(4))


def bv_plate(alpha_deg, camber, re, re_floor=None):
    fc = min(max(100.0 * camber, 0.0), 8.0)
    a = min(max(alpha_deg, 0.0), 10.0)
    r = re if re_floor is None else max(re, re_floor)
    cl = _poly(_A, fc, a) - _poly(_B, fc, a) * (3e5 - r)
    cd = _poly(_C, fc, a) - _poly(_D, fc, a) * (3e5 - r)
    return cl, max(cd, 0.005)


CD_90 = 1.8   # flat-plate drag at 90 deg (low-AR plates ~1.2-2.0); Viterna-style post-stall


def poststall_wrap(cl_s, cd_s, a_s_deg, alpha_deg):
    """Viterna-Corrigan extension beyond the model edge a_s (deg), blending from (cl_s, cd_s) to flat plate."""
    a = math.radians(alpha_deg); a_s = math.radians(a_s_deg)
    B1 = CD_90
    A1 = B1 / 2.0
    A2 = (cl_s - B1 * math.sin(a_s) * math.cos(a_s)) * math.sin(a_s) / max(math.cos(a_s) ** 2, 1e-6)
    B2 = (cd_s - B1 * math.sin(a_s) ** 2) / max(math.cos(a_s), 1e-6)
    ca = max(abs(math.cos(a)), 1e-3)
    cl = A1 * math.sin(2 * a) + A2 * ca ** 2 / max(abs(math.sin(a)), 1e-3) * math.copysign(1, math.sin(a))
    cd = B1 * math.sin(a) ** 2 + B2 * ca
    return cl, max(cd, cd_s)


def polar(alpha_rad, camb, re, mode, is_plate):
    a = math.degrees(alpha_rad)
    if mode == "current":
        return _cl_cd(alpha_rad, camb, re=re)
    if mode in ("bv", "bv_ps") and is_plate:
        lo, hi = 0.0, 10.0
        if lo <= a <= hi or mode == "bv":
            return bv_plate(a, camb, re)
        edge = hi if a > hi else lo
        cl_s, cd_s = bv_plate(edge, camb, re)
        if a < lo:   # negative incidence: linear lift slope continuation down to -6 deg, then plate
            slope = (bv_plate(1.0, camb, re)[0] - bv_plate(0.0, camb, re)[0])
            if a >= -6.0:
                return cl_s + slope * a, cd_s * (1 + 0.02 * a * a)
            cl_s, cd_s, edge = cl_s - 6 * slope, cd_s * 1.72, -6.0
        return poststall_wrap(cl_s, cd_s, edge, a)
    # airfoil sections (or "ps" on any section): current polar inside its stall band, Viterna outside
    if mode in ("bv_ps", "ps"):
        rr = max(float(re), 5000.0); fz = math.log10(rr / 20000.0)
        stall = max(8.0, min(15.0, 10.0 + 3.0 * fz))
        cl0, cd0 = _cl_cd(alpha_rad, camb, re=re)
        if -stall <= a <= stall:
            return cl0, cd0
        edge = stall if a > stall else -stall
        cl_s, cd_s = _cl_cd(math.radians(edge), camb, re=re)
        return poststall_wrap(cl_s, cd_s, edge, a)
    return _cl_cd(alpha_rad, camb, re=re)


# ---------------- #6 Carter's rule
def naca_camber_angle_deg(m, p=0.4):
    return math.degrees(math.atan(2 * m / p) + math.atan(2 * m / (1 - p)))


def carter_turning_fraction(stagger_deg, camber, c, s, alpha_deg, cpos=0.4):
    """1 - delta/Delta: share of the blade's ideal turning the flow actually gets (Carter 1950)."""
    th = naca_camber_angle_deg(camber, cpos)
    exit_from_axial = 90.0 - min(stagger_deg + th / 2.0, 89.0)     # exit metal angle from axial
    m = 0.23 + max(exit_from_axial, 0.0) / 500.0                   # circular-arc, a/c = 0.5
    sigma = max(c / s, 0.05)
    delta = m * th / math.sqrt(sigma)
    turn = th + max(alpha_deg - 0.0, 0.0)                          # ideal turning ~ camber + incidence
    if turn <= 0.5:
        return 1.0
    return max(0.3, min(1.0, 1.0 - delta / turn))


# ---------------- #8 Koch (1981) stalling static-pressure-rise coefficient, APPROXIMATION
# The paper is paywalled. Ch_ref vs L/g2 is a smooth fit to the commonly reproduced Koch curve
# (~0.6 at L/g2=0.2 falling to ~0.35 at L/g2~1.5); Re and clearance corrections simplified.
def koch_ch(L_over_g2, re, eps_over_g=0.0):
    x = min(max(L_over_g2, 0.1), 3.0)
    ch = 0.42 * x ** -0.33
    ch = min(ch, 0.65)
    ch *= min(1.0, (max(re, 1e4) / 1.3e5) ** 0.1)     # low-Re knockdown (~0.86 at 3e4)
    ch *= max(0.6, 1.0 - 1.5 * eps_over_g)            # tip-clearance knockdown
    return ch


@dataclass
class Opts:
    polar: str = "current"       # current | bv | bv_ps | ps
    carter: bool = False
    carter_ref: float = 1.0      # normaliser so Stock keeps its calibrated SLIP
    koch: bool = False
    solver: str = "fixed"        # fixed | bracket
    koch_scale: float = 1.0
    axial_force: bool = False  # static rise from blade AXIAL force (cl cos phi - cd sin phi), not Euler-minus-swirl


def _solve_vth(fn, U, solver):
    """fn(vth) -> vth_new. fixed: mirror of fan_bem. bracket: root of g(v)=fn(v)-v on [0, 0.95U] (Ning-style)."""
    if solver == "fixed":
        vth = 0.0
        for _ in range(N_ITER_MAX):
            vn = fn(vth)
            if abs(vn - vth) < 1e-3:
                return vn, True
            vth = 0.5 * vth + 0.5 * vn
        return vth, False
    lo, hi = 0.0, 0.95 * U
    g = lambda v: fn(v) - v
    glo, ghi = g(lo), g(hi)
    if glo <= 0:
        return 0.0, True
    if ghi >= 0:
        return hi, True
    # scan for first sign change (guards multiple roots), then bisection/secant -> guaranteed
    xs = np.linspace(lo, hi, 9); gs = [g(x) for x in xs]
    for a, b, ga, gb in zip(xs, xs[1:], gs, gs[1:]):
        if ga > 0 >= gb:
            lo, hi, glo, ghi = a, b, ga, gb
            break
    for _ in range(60):
        mid = 0.5 * (lo + hi); gm = g(mid)
        if gm > 0: lo = mid
        else: hi = mid
        if hi - lo < 1e-5: break
    return 0.5 * (lo + hi), True


def operating_point(params, rpm, flow_m3s, o: Opts, n_elem=20, rho=RHO_AIR, tip_gap_mm=None, stator=False, detail=False):
    tip_gap_mm = _effective_tip_gap_mm(params, tip_gap_mm)
    hub_r, tip_r = params.hub_radius / 1000.0, params.tip_radius / 1000.0
    B = int(params.n_blades); omega = rpm * 2.0 * math.pi / 60.0
    area = math.pi * (tip_r ** 2 - hub_r ** 2)
    Vx = flow_m3s / area if area > 0 else 0.0
    chord_fn, stag_fn, camb_fn = _interp_geometry(params)
    st = sorted(params.stations, key=lambda s: s.r_frac)
    cpos_fn = lambda rf: float(np.interp(rf, [s.r_frac for s in st], [s.camber_pos for s in st]))
    is_plate = str(getattr(params, "section_family", "naca") or "naca") == "plate"
    edges = np.linspace(hub_r, tip_r, n_elem + 1)
    dp0 = swirl = power = mass = 0.0; cap_num = 0.0; conv = True; alphas = []; ax_num_list = []
    for i in range(n_elem):
        r = 0.5 * (edges[i] + edges[i + 1]); dr = edges[i + 1] - edges[i]
        rf = (r - hub_r) / (tip_r - hub_r) if tip_r > hub_r else 0.0
        U = omega * r; c = chord_fn(rf) / 1000.0; beta = math.radians(stag_fn(rf)); camb = camb_fn(rf)
        dm = rho * max(Vx, 0.0) * 2 * math.pi * r * dr
        denom = rho * max(Vx, 0.05) * 2 * math.pi * r

        def fn(vth):
            vth_m = 0.5 * vth
            phi = math.atan2(Vx, max(U - vth_m, 0.05)); W = math.hypot(Vx, U - vth_m)
            re = W * c / NU_AIR
            cl, cd = polar(beta - phi, camb, re, o.polar, is_plate)
            f = 0.5 * rho * W * W * c * B * (cl * math.sin(phi) + cd * math.cos(phi))
            return max(0.0, min(f / denom if denom > 0 else vth, 0.95 * U))
        vth, ok = _solve_vth(fn, U, o.solver) if B > 0 else (0.0, True)
        conv = conv and ok
        phi = math.atan2(Vx, max(U - 0.5 * vth, 0.05)); alphas.append(math.degrees(beta - phi))
        leak = 1.0
        if rf > 0.65:
            leak *= max(0.2, 1.0 - K_TIP_LEAK * (tip_gap_mm / 1000.0) / max(c, 1e-3))
        slip = SLIP
        s_pitch = 2 * math.pi * r / max(B, 1)
        if o.carter and B > 0:
            slip = SLIP * carter_turning_fraction(math.degrees(beta), camb, c, s_pitch, math.degrees(beta - phi),
                                                  cpos_fn(rf)) / o.carter_ref
            slip = min(slip, 0.95)
        vth_eff = slip * leak * vth
        if o.axial_force and B > 0:
            vm = 0.5 * vth; ph = math.atan2(Vx, max(U - vm, 0.05)); Wv = math.hypot(Vx, U - vm)
            cl_, cd_ = polar(beta - ph, camb, Wv * c / NU_AIR, o.polar, is_plate)
            fx = 0.5 * rho * Wv * Wv * c * B * (cl_ * math.cos(ph) - cd_ * math.sin(ph))   # axial force / span
            cap_ax = globals().setdefault("_AX", {})
            ax_num_list.append(slip * leak * fx * dr)
        dp0 += rho * U * vth_eff * dm; swirl += 0.5 * rho * vth_eff ** 2 * dm
        power += dm * U * vth; mass += dm
        if o.koch and B > 0:
            th = naca_camber_angle_deg(camb, cpos_fn(rf))
            ex = math.radians(min(math.degrees(beta) + th / 2.0, 90.0))
            g2 = s_pitch * math.sin(ex)                                # exit passage width
            W1 = math.hypot(Vx, U)
            ch = koch_ch(c / max(g2, 1e-4), W1 * c / NU_AIR, (tip_gap_mm / 1000.0) / max(g2, 1e-4) if rf > 0.65 else 0.0)
            cap_num += o.koch_scale * ch * 0.5 * rho * W1 * W1 * (2 * math.pi * r * dr)
    if mass <= 0:
        return FanPoint(0, 0, 0, 0, 0, 0, conv)
    dpt = dp0 / mass
    dps = dpt - (0 if stator else swirl / mass) - K_FRICTION * 0.5 * rho * Vx * Vx
    if o.axial_force and B > 0:
        dps = sum(ax_num_list) / area - K_FRICTION * 0.5 * rho * Vx * Vx
    if o.koch and B > 0:
        cap = cap_num / area                                          # area-averaged stall static rise
        dps = min(dps, cap - K_FRICTION * 0.5 * rho * Vx * Vx)
    fc = flow_m3s * CFM_PER_M3S
    eff = flow_m3s * max(dps, 0) / power if power > 1e-6 else 0.0
    p = FanPoint(round(fc, 1), flow_m3s, round(dps, 2), round(dpt, 2), round(eff, 3), round(power, 2), conv)
    if detail:
        return p, alphas
    return p


def pq_curve(params, rpm, o: Opts, n_points=22, n_elem=20, tip_gap_mm=None):
    tip_gap_mm = _effective_tip_gap_mm(params, tip_gap_mm)
    tip_r, hub_r = params.tip_radius / 1000.0, params.hub_radius / 1000.0
    area = math.pi * (tip_r ** 2 - hub_r ** 2); v_tip = rpm * 2 * math.pi / 60 * tip_r
    q_max = 0.6 * v_tip * area
    pts = [operating_point(params, rpm, float(q), o, n_elem=n_elem, tip_gap_mm=tip_gap_mm)
           for q in np.linspace(0.02 * q_max, q_max, n_points)]
    free = None                                   # QA-3-safe: None when there is no crossing
    for a, b in zip(pts, pts[1:]):
        if a.dp_static_pa > 0.0 >= b.dp_static_pa:
            t = a.dp_static_pa / (a.dp_static_pa - b.dp_static_pa)
            free = round(a.flow_cfm + t * (b.flow_cfm - a.flow_cfm), 1); break
    from fansim.analyze.fan_curve import shut_off_pa
    sh = shut_off_pa([{"cfm": p.flow_cfm, "static_pa": p.dp_static_pa} for p in pts],
                     q_near_zero=max(5.0, 0.15 * (free or pts[-1].flow_cfm)))
    peak = max(pts, key=lambda p: p.efficiency)
    return FanCurve(pts, free, round(sh, 2) if sh is not None else None, peak.efficiency, peak.flow_cfm,
                    all(p.converged for p in pts))
