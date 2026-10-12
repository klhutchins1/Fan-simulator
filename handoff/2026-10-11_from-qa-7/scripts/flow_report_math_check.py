"""Task G (round 7): independent synthetic-field checks of fansim/cfd/flow_report.py (pre-registered G1/G2).
Expected values are derived by hand from the spec definitions, not from the code under test."""
import math, warnings
import numpy as np
from fansim.cfd.flow_report import FlowSamples, compute_metrics, FlowReportUnavailable, PLANE_Z_FRAC, N_BANDS
HUB, TIP, ZF = 0.02, 0.06, 0.0
ZE, ZI = ZF + PLANE_Z_FRAC * TIP, ZF - PLANE_Z_FRAC * TIP
res = []
def rec(name, got, exp, tol=1e-6, kind="rel"):
    if exp is None or got is None or (isinstance(exp, float) and math.isnan(exp)):
        ok = (got is None and exp is None) or (got is not None and exp is not None and math.isnan(got) and math.isnan(exp))
    elif kind == "abs":
        ok = abs(got - exp) <= tol
    else:
        ok = abs(got - exp) <= tol * max(abs(exp), 1e-30)
    res.append((name, ok, got, exp)); print(("PASS " if ok else "FAIL ") + name, got, exp)
def ring(n_r=50, n_t=72, z=ZE, r0=HUB, r1=TIP):
    """Samples at cell centres of an annular grid, weight = cell area x dz (exact annulus area)."""
    re = np.linspace(r0, r1, n_r + 1); rc = 0.5 * (re[1:] + re[:-1])
    t = (np.arange(n_t) + 0.5) * 2 * math.pi / n_t
    R, T = np.meshgrid(rc, t, indexing="ij")
    A = (np.pi * (re[1:] ** 2 - re[:-1] ** 2) / n_t)[:, None] * np.ones_like(T)
    pts = np.column_stack([R.ravel() * np.cos(T.ravel()), R.ravel() * np.sin(T.ravel()), np.full(R.size, z)])
    return pts, R.ravel(), T.ravel(), A.ravel() * 1e-3
def field(uz_e, uth_e=0.0, p_e=0.0, uz_i=None, p_i=0.0, n_r=50, extra=None):
    pe, Re, Te, we = ring(n_r=n_r, z=ZE); pi, Ri, Ti, wi = ring(n_r=n_r, z=ZI)
    uz_e = np.broadcast_to(uz_e(Re) if callable(uz_e) else uz_e, Re.shape).astype(float)
    uth_e = np.broadcast_to(uth_e(Re) if callable(uth_e) else uth_e, Re.shape).astype(float)
    uz_i = np.broadcast_to(uz_e.mean() if uz_i is None else (uz_i(Ri) if callable(uz_i) else uz_i), Ri.shape).astype(float)
    ue = np.column_stack([-uth_e * np.sin(Te), uth_e * np.cos(Te), uz_e])
    ui = np.column_stack([np.zeros_like(Ri), np.zeros_like(Ri), uz_i])
    p_e = np.broadcast_to(p_e(Re) if callable(p_e) else p_e, Re.shape).astype(float)
    p_i = np.broadcast_to(p_i(Ri) if callable(p_i) else p_i, Ri.shape).astype(float)
    return (np.vstack([pe, pi]), np.vstack([ue, ui]), np.concatenate([p_e, p_i]), np.concatenate([we, wi]), Re, we)
def run(f, k=None, om=None):
    pts, u, p, w = f[:4]
    return compute_metrics(FlowSamples(pts=pts, u=u, p=p, w=w, k=k, omega=om), hub_r=HUB, tip_r=TIP, z_fan=ZF)

# G1-1 backflow: outer annulus with area share exactly s has Uz=-1
rb = math.sqrt(TIP**2 - 0.10 * (TIP**2 - HUB**2))     # area share 10 %, but cell centres -> use cell weights for exact expectation
f = field(lambda R: np.where(R > rb, -1.0, 2.0)); m = run(f)
Re, we = f[4], f[5]; exp = we[Re > rb].sum() / we.sum()
rec("backflow share (cell-weighted, ~0.10)", m.backflow_frac, exp)
rec("net_reversed False", float(m.net_reversed), 0.0, kind="abs")
# G1-2 swirl: Uz=3, Utheta=4 -> 16/25; sign of swirl irrelevant
rec("swirl 3-4-5", run(field(3.0, 4.0)).swirl_frac, 16 / 25)
rec("swirl negative spin", run(field(3.0, -4.0)).swirl_frac, 16 / 25)
rec("pure swirl", run(field(0.0, 4.0)).swirl_frac, 1.0)
# G1-3 dead air: inner region Uz=0.05, else 2.0 -> dead where |Uz| < 0.1*mean
rd = HUB + 0.3 * (TIP - HUB)
f = field(lambda R: np.where(R < rd, 0.05, 2.0)); m = run(f); Re, we = f[4], f[5]
uz = np.where(Re < rd, 0.05, 2.0); mean = (uz * we).sum() / we.sum()
exp = we[np.abs(uz) < 0.1 * mean].sum() / we.sum()
rec("dead share", m.dead_frac, exp); rec("uniform field dead=0", run(field(1.0)).dead_frac, 0.0, kind="abs")
# G1-4 tip ratio: outer 10 % of span Uz=2, rest 1
rt = TIP - 0.1 * (TIP - HUB)
f = field(lambda R: np.where(R >= rt, 2.0, 1.0)); m = run(f); Re, we = f[4], f[5]
uz = np.where(Re >= rt, 2.0, 1.0); exp = 2.0 / ((uz * we).sum() / we.sum())
rec("tip ratio", m.tip_band_uz_ratio, exp)
# G1-5 push bands: exit p = band-dependent, Uz exit 2, inlet Uz 2, p_in 0; swirl 5 must not count
def bandp(R): return 10.0 * np.clip(((R - HUB) / (TIP - HUB) * N_BANDS).astype(int), 0, N_BANDS - 1)
m = run(field(2.0, 5.0, p_e=bandp, uz_i=2.0))
for i in range(N_BANDS): rec(f"push band {i} (swirl excluded)", m.band_dp0_pa[i], 1.2 * 10.0 * i if i else 0.0, tol=1e-9, kind="abs")
m = run(field(3.0, 0.0, p_e=0.0, uz_i=1.0))
rec("push from dynamic head 0.5*(9-1)*1.2", m.band_dp0_pa[2], 1.2 * 0.5 * (9 - 1))
# G1-6 Proudman: uniform k, omega in the rotor region; one far cell outside must be ignored
pts, u, p, w = field(1.0)[:4]
far = np.array([[0, 0, 5 * TIP]]); pts2 = np.vstack([pts, far]); u2 = np.vstack([u, [[0, 0, 1.0]]])
p2 = np.append(p, 0.0); w2 = np.append(w, 1.0)
k = np.full(len(pts2), 2.0); om = np.full(len(pts2), 1000.0)
m = compute_metrics(FlowSamples(pts=pts2, u=u2, p=p2, w=w2, k=k, omega=om), hub_r=HUB, tip_r=TIP, z_fan=ZF)
from fansim.acoustics import proxies as P
eps = P.CMU * 2.0 * 1000.0; mt = math.sqrt(4.0) / P.C0_AIR
pw = P.ALPHA_PROUDMAN * P.RHO_AIR * eps * mt**5 * w.sum()
rec("Proudman SWL (dB)", m.noise_swl_db, 10 * math.log10(pw / P.W_REF), tol=0.01, kind="abs")
rec("Proudman closed-form 1.2 kg/m3 constants", P.RHO_AIR, 1.2, tol=0.03)
# G2 degenerate cases
def g2(name, fn):
    with warnings.catch_warnings(record=True) as wl:
        warnings.simplefilter("always")
        try:
            m = fn(); vals = [m.backflow_frac, m.swirl_frac, m.dead_frac, m.tip_band_uz_ratio, m.mean_uz_exit] + list(m.band_dp0_pa)
            bad = [v for v in vals if not math.isfinite(v)]
            ok = not bad; print(("PASS " if ok else "FAIL ") + "G2 " + name, "non-finite:", bad, "warnings:", len(wl))
        except FlowReportUnavailable as e:
            ok = True; print("PASS G2 " + name, "explicit error:", e)
    res.append(("G2 " + name, ok, None, None))
g2("zero flow (Uz=0, Uth=0)", lambda: run(field(0.0, 0.0)))
g2("zero weights", lambda: (lambda f: compute_metrics(FlowSamples(pts=f[0], u=f[1], p=f[2], w=np.zeros_like(f[3])), hub_r=HUB, tip_r=TIP, z_fan=ZF))(field(1.0)))
g2("coarse mesh, empty tip band and empty bands (n_r=3)", lambda: run(field(1.0, n_r=3)))
g2("all backflow", lambda: run(field(-1.0)))
g2("no exit cells", lambda: compute_metrics(FlowSamples(pts=np.array([[0.04, 0, 1.0]]), u=np.array([[0, 0, 1.0]]), p=np.zeros(1), w=np.ones(1)), hub_r=HUB, tip_r=TIP, z_fan=ZF))
m = run(field(-1.0)); print("all-backflow: dead", m.dead_frac, "tip", m.tip_band_uz_ratio, "net_reversed", m.net_reversed)
print("SUMMARY", sum(o for _, o, *_ in res), "/", len(res), "pass")

# Documented case (no rule): radial equilibrium. A swirl-only exit (Uth = 4 m/s, no extra work on Uz) with static
# pressure satisfying dp/dr = Uth^2/r (kinematic) and mean static pressure 0. "Push" should be ~0 in every band if swirl were fully excluded.
uth = 4.0
def peq(R): return uth**2 * np.log(R / HUB) - uth**2 * (np.log(np.linspace(HUB, TIP, 1000) / HUB)).mean()
m = run(field(2.0, uth, p_e=peq, uz_i=2.0))
print("RADIAL-EQUILIBRIUM bands Pa:", [round(b, 2) for b in m.band_dp0_pa], "swirl_frac", round(m.swirl_frac, 3))
