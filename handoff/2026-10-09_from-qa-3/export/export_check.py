"""QA r4 request 6, step 2: trimesh checks E1-E12 (criteria: docs/qa/notes/export-correctness-criteria.md).
Usage: python export_check.py <outdir> <stem>   -> <outdir>/checks.json"""
import json, math, sys
from pathlib import Path
import numpy as np
import trimesh

d, stem = Path(sys.argv[1]), sys.argv[2]
from fansim.fan_spec import get_fan_spec
spec = get_fan_spec("a12x25"); mm = spec.motor_mount
NS = 100_000


def radial_profile(m, z, nang=720):
    ang = np.linspace(0, 2 * np.pi, nang, endpoint=False)
    dirs = np.c_[np.cos(ang), np.sin(ang), np.zeros(nang)]
    org = np.tile([0.0, 0.0, z], (nang, 1))
    loc, idx, _ = m.ray.intersects_location(org, dirs, multiple_hits=True)
    r = np.full(nang, np.inf)
    for p, i in zip(loc, idx):
        rr = math.hypot(p[0], p[1])
        if rr > 1e-6 and rr < r[i]:
            r[i] = rr
    return r


def basic(m):
    lo, hi = m.bounds
    rxy = np.hypot(m.vertices[:, 0], m.vertices[:, 1])
    return {"faces": int(len(m.faces)), "watertight": bool(m.is_watertight),
            "winding_consistent": bool(m.is_winding_consistent), "is_volume": bool(m.is_volume),
            "bodies": int(len(m.split(only_watertight=False))), "euler": int(m.euler_number),
            "volume_mm3": float(m.volume), "tip_dia_mm": float(2 * rxy.max()),
            "depth_mm": float(hi[2] - lo[2]), "zmin": float(lo[2]), "zmax": float(hi[2])}


def cup(m, b):
    zs = np.arange(b["zmin"] + 0.025, b["zmax"], 0.05)
    rows = []
    for z in zs:
        r = radial_profile(m, z, 360)
        fin = r[np.isfinite(r)]
        rows.append((z, float(np.median(fin)) if len(fin) > 300 else float("nan")))
    rcav = mm.cavity_dia_mm / 2
    incup = [abs(med - rcav) < 0.6 for _, med in rows]
    # contiguous run touching an end face
    side = "zmin" if incup[0] else ("zmax" if incup[-1] else None)
    if side is None:
        return {"cup_found": False}
    seq = incup if side == "zmin" else incup[::-1]
    n = next((i for i, v in enumerate(seq) if not v), len(seq))
    depth = n * 0.05
    zmid = (b["zmin"] + depth / 2) if side == "zmin" else (b["zmax"] - depth / 2)
    r = radial_profile(m, zmid, 1440)
    base = float(np.percentile(r[np.isfinite(r)], 90))
    pad = r < base - mm.grip_protrude_mm / 2
    runs = int(np.sum(pad & ~np.roll(pad, 1)))
    return {"cup_found": True, "open_side": side, "cup_dia_mm": 2 * base, "cup_depth_mm": depth,
            "grip_count": runs, "grip_protrude_mm": float(base - np.min(r)), "z_mid": float(zmid)}


def blades(m, b, R):
    rr = 0.8 * R
    ang = np.linspace(0, 2 * np.pi, 1440, endpoint=False)
    best, centers = 0, {}
    for f in np.linspace(0.1, 0.9, 9):
        z = b["zmin"] + f * b["depth_mm"]
        pts = np.c_[rr * np.cos(ang), rr * np.sin(ang), np.full(len(ang), z)]
        ins = m.contains(pts)
        starts = np.where(ins & ~np.roll(ins, 1))[0]
        best = max(best, len(starts))
        if len(starts):  # centre of the run nearest angle 0 (for chirality)
            runs = []
            for s in starts:
                e = s
                while ins[(e + 1) % len(ang)]:
                    e += 1
                runs.append((s + e) / 2 * 360 / len(ang))
            c = min(runs, key=lambda a: min(a, 360 - a))
            centers[round(f, 1)] = c if c < 180 else c - 360
    ks = sorted(centers)
    hand = float(np.sign(centers[ks[-1]] - centers[ks[0]])) if len(ks) >= 2 else 0.0
    return {"blade_count_0p8R": best, "lean_centers_deg": centers, "handedness_sign": hand}


def hausdorff(a, b, n=NS):
    pa, _ = trimesh.sample.sample_surface(a, n, seed=1)
    pb, _ = trimesh.sample.sample_surface(b, n, seed=2)
    da = np.concatenate([b.nearest.on_surface(pa[i:i + 20000])[1] for i in range(0, n, 20000)])
    db = np.concatenate([a.nearest.on_surface(pb[i:i + 20000])[1] for i in range(0, n, 20000)])
    return float(max(da.max(), db.max())), float(np.percentile(np.r_[da, db], 99))


res = {}
meshes = {}
for tag, name in (("main", f"{stem}.stl"), ("as_designed", f"{stem}_as_designed.stl"),
                  ("mirrored", f"{stem}_mirrored.stl")):
    p = d / name
    if not p.is_file():
        res[tag] = {"missing": True}; continue
    m = trimesh.load(p, force="mesh"); meshes[tag] = m
    b = basic(m)
    b.update(cup(m, b)); b.update(blades(m, b, b["tip_dia_mm"] / 2))
    res[tag] = b
if "main" in meshes and "mirrored" in meshes:
    a, mi = meshes["main"], meshes["mirrored"]
    out = {}
    for ax in (0, 1):
        r = mi.copy(); M = np.eye(4); M[ax, ax] = -1; r.apply_transform(M)
        out[f"reflect_{'xy'[ax]}"] = hausdorff(a, r)
    res["mirror"] = {"hausdorff_max_p99_mm": out,
                     "vol_rel_diff": abs(a.volume - mi.volume) / a.volume}
if "main" in meshes and "as_designed" in meshes:
    res["main_vs_as_designed_hausdorff"] = hausdorff(meshes["main"], meshes["as_designed"], 20000)
res["sidecars"] = sorted(p.name for p in d.iterdir() if p.name.startswith(stem) and not p.suffix == ".stl")
(d / "checks.json").write_text(json.dumps(res, indent=1, default=float))
print(json.dumps(res, default=float)[:3000])
