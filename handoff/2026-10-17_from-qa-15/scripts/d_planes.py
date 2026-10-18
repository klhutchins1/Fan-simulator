"""QA r15 Task D (PREREG_R15 336211b): re-check of the 27.3e plane fix. Synthetic only, no CFD.
Usage: PYTHONPATH=/workspace/fansim/qa/run_r14 python d_planes.py out.json"""
import json, math, sys, tempfile
from pathlib import Path
import numpy as np, trimesh
import fansim; assert "run_r14" in fansim.__file__, fansim.__file__
from fansim.cfd.flow_report import slab_centres, slab_half_width, compute_metrics, FlowSamples, PLANE_Z_FRAC
from fansim.cfd.flow_report_case import blade_z_extent
from fansim.physics.air import RHO_AMCA
OUT = {}

# ---------- D1: hand derivation (expected values from the audit text, written here first) ----------
def mine(tip, le, te):
    h = max(0.04 * tip, 0.002)
    return le - 0.1 * tip - h, te + 0.1 * tip + h, h
d1 = []
for tip, le, te in [(0.0545, -0.0164, 0.0042), (0.0545, -0.0079, 0.0082), (0.030, -0.0164, 0.0042)]:
    zi, ze, h = mine(tip, le, te)
    ci, ce = slab_centres(tip_r=tip, z_fan=0.0, blade_z=(le, te))
    hc = slab_half_width(tip)
    gap_in = le - (ci + hc); gap_ex = (ce - hc) - te
    d1.append(dict(tip=tip, le=le, te=te, mine=(zi, ze, h), code=(ci, ce, hc),
                   err=max(abs(zi - ci), abs(ze - ce), abs(h - hc)), gap_in=gap_in, gap_ex=gap_ex,
                   ok=max(abs(zi - ci), abs(ze - ce), abs(h - hc)) <= 1e-12 and gap_in >= 0.1 * tip - 1e-12
                   and gap_ex >= 0.1 * tip - 1e-12))
leg = slab_centres(tip_r=0.0545, z_fan=0.003, blade_z=None)
leg_ok = abs(leg[0] - (0.003 - PLANE_Z_FRAC * 0.0545)) < 1e-15 and abs(leg[1] - (0.003 + 0.18 * 0.0545)) < 1e-15 \
    and PLANE_Z_FRAC == 0.18
OUT["D1"] = dict(rows=d1, legacy=leg, legacy_ok=leg_ok, PASS=all(r["ok"] for r in d1) and leg_ok)

# ---------- D2: mm->m and hub exclusion on a synthetic STL ----------
def ring(r0, r1, z0, z1, n=96):
    a = trimesh.creation.annulus(r_min=r0, r_max=r1, height=z1 - z0, sections=n) if r0 > 0 else \
        trimesh.creation.cylinder(radius=r1, height=z1 - z0, sections=n)
    a.apply_translation([0, 0, 0.5 * (z0 + z1)]); return a
hub = ring(0, 21.5, -9.0, 7.0)
fillet = ring(21.5, 22.0, -9.5, 7.5)
blade = trimesh.creation.box(extents=[54.5 - 22.6, 2.0, 8.2 + 7.9]); blade.apply_translation([0.5 * (22.6 + 54.5), 0, 0.5 * (8.2 - 7.9)])
d = Path(tempfile.mkdtemp(prefix="qa15d2_"))
trimesh.util.concatenate([hub, fillet, blade]).export(str(d / "impeller_cfd.stl"))
res = {hr: blade_z_extent(d, hub_r=hr) for hr in (0.0215, 0.018625, 0.0)}
ok2 = res[0.0215] is not None and abs(res[0.0215][0] + 0.0079) <= 1e-6 and abs(res[0.0215][1] - 0.0082) <= 1e-6
OUT["D2"] = dict(results={str(k): v for k, v in res.items()}, PASS=bool(ok2))

# ---------- D3: synthetic swirling field ----------
HUB, TIP, LE, TE, UZ, OM, PB = 0.0215, 0.0545, -0.0164, 0.0042, 3.0, 209.44, 6.667
nr, nt, nz = 60, 48, 480
r_e = np.linspace(0, 0.06, nr + 1); rc = 0.5 * (r_e[1:] + r_e[:-1]); dr = np.diff(r_e)
t_c = (np.arange(nt) + 0.5) * 2 * math.pi / nt
z_e = np.linspace(-0.06, 0.06, nz + 1); zc = 0.5 * (z_e[1:] + z_e[:-1]); dz = np.diff(z_e)
R, T, Z = np.meshgrid(rc, t_c, zc, indexing="ij")
W = np.meshgrid(rc * dr, np.full(nt, 2 * math.pi / nt), dz, indexing="ij")
W = W[0] * W[1] * W[2]
ann = (rc >= HUB) & (rc <= TIP)
def field(S, garbage):
    g = np.clip((Z - LE) / (TE - LE), 0, 1)
    uth = S * 0.3 * OM * R * g
    p = np.where(Z < LE, -0.5 * UZ ** 2, -0.5 * UZ ** 2 + OM * R * uth - 0.5 * uth ** 2)
    # downstream: P_b + tilt(r); tilt = int uth^2/r dr minus its area-weighted mean over the annulus
    uth_d = S * 0.3 * OM * rc
    integrand = uth_d ** 2 / np.maximum(rc, 1e-12)
    tilt = np.concatenate([[0], np.cumsum(integrand[:-1] * dr[:-1])]) if False else np.cumsum(integrand * dr)
    wa = rc * dr * ann
    tilt = tilt - np.sum(tilt * wa) / np.sum(wa)
    p = np.where(Z > TE, PB + tilt[:, None, None], p)
    ux = -uth * np.sin(T); uy = uth * np.cos(T); uz = np.full_like(R, UZ)
    if garbage:
        bad = (R < HUB) | (R > TIP)
        p = np.where(bad, 1e3, p); ux = np.where(bad, 50.0, ux); uy = np.where(bad, -50.0, uy); uz = np.where(bad, -7.0, uz)
    else:  # physically: no flow inside the hub
        hubm = R < HUB
        ux = np.where(hubm, 0, ux); uy = np.where(hubm, 0, uy); uz = np.where(hubm, 0, uz)
    pts = np.c_[(R * np.cos(T)).ravel(), (R * np.sin(T)).ravel(), Z.ravel()]
    return FlowSamples(pts=pts, u=np.c_[ux.ravel(), uy.ravel(), uz.ravel()], p=p.ravel(), w=W.ravel())
rows = []
for S in (0.0, 0.5, 1.0, 1.5):
    row = {"S": S}
    for tag, bz in (("v4", (LE, TE)), ("legacy", None)):
        m = compute_metrics(field(S, False), hub_r=HUB, tip_r=TIP, z_fan=0.0, blade_z=bz)
        mg = compute_metrics(field(S, True), hub_r=HUB, tip_r=TIP, z_fan=0.0, blade_z=bz)
        a, b = m.to_dict(), mg.to_dict(); a.pop("missing"); b.pop("missing")
        diff = max(abs((x if x is not None else 0) - (y if y is not None else 0)) for k in a
                   for x, y in ([(a[k], b[k])] if not isinstance(a[k], list) else zip(a[k], b[k])) if not isinstance(x, bool))
        row[tag] = dict(mean_dp0=m.mean_dp0_pa, swirl=m.swirl_frac, bands=m.band_dp0_pa, garbage_maxdiff=diff,
                        missing=m.missing)
    rows.append(row)
exp = RHO_AMCA * (PB + 0.5 * UZ ** 2)
v4 = [r["v4"]["mean_dp0"] for r in rows]; lg = [r["legacy"]["mean_dp0"] for r in rows]
D3a = all(abs(x - exp) <= 1e-9 * abs(exp) for x in v4)
D3b = all(b > a for a, b in zip(lg, lg[1:])) and abs(lg[-1] - lg[0]) > 0.10 * abs(lg[0])
D3c = all(all(rows[i + 1][t]["swirl"] > rows[i][t]["swirl"] for i in range(3)) for t in ("v4", "legacy"))
D3d = all(r[t]["garbage_maxdiff"] <= 1e-9 for r in rows for t in ("v4", "legacy"))
OUT["D3"] = dict(expected_v4=exp, rows=rows, v4_mean=v4, legacy_mean=lg, D3a=D3a, D3b=D3b, D3c=D3c, D3d=D3d,
                 slabs_v4=slab_centres(tip_r=TIP, z_fan=0, blade_z=(LE, TE)), slabs_legacy=slab_centres(tip_r=TIP, z_fan=0, blade_z=None),
                 h=slab_half_width(TIP))
Path(sys.argv[1]).write_text(json.dumps(OUT, indent=1, default=float))
print("D1", OUT["D1"]["PASS"], "D2", OUT["D2"]["PASS"], OUT["D2"]["results"])
print("D3a", D3a, v4, "exp", exp); print("D3b", D3b, lg); print("D3c", D3c, [r["v4"]["swirl"] for r in rows]); print("D3d", D3d)
