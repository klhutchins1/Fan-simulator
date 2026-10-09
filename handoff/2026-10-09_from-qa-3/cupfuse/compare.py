"""Evaluate strategy STLs vs baseline B against the pre-registered rule
(docs/qa/notes/cup-fuse-memory-criteria.md, sha256 f8fcc8bb…). Usage: python compare.py <root> S1 S2 ...
Writes <root>/verdicts.json."""
import json, sys
from pathlib import Path
import numpy as np
import trimesh

root = Path(sys.argv[1]); N = 200_000
B = trimesh.load(root / "B/print.stl", force="mesh")
bd = json.loads((root / "B/driver.json").read_text())
pb, _ = trimesh.sample.sample_surface(B, N, seed=1)


def near(m, pts):
    return np.concatenate([m.nearest.on_surface(pts[i:i + 25000])[1] for i in range(0, len(pts), 25000)])


out = {"B": {"peak_mb": bd["peak_tree_mb"], "wall_s": bd["wall_s"], "volume": B.volume,
             "euler": int(B.euler_number), "watertight": bool(B.is_watertight)}}
for s in sys.argv[2:]:
    d = root / s
    dj = json.loads((d / "driver.json").read_text())
    r = {"peak_mb": dj["peak_tree_mb"], "wall_s": dj["wall_s"], "rc": dj["rc"], "killed": dj.get("killed")}
    if (d / "stages.json").is_file() and (d / "print.stl").is_file():
        sj = json.loads((d / "stages.json").read_text())
        m = trimesh.load(d / "print.stl", force="mesh")
        pm, _ = trimesh.sample.sample_surface(m, N, seed=2)
        h = float(max(near(m, pb).max(), near(B, pm).max()))
        r.update(volume=m.volume, vol_rel=abs(m.volume - B.volume) / B.volume,
                 watertight=bool(m.is_watertight), bodies=len(m.split(only_watertight=False)),
                 euler=int(m.euler_number), hausdorff_mm=h, gauge=sj["gauge"],
                 fuse_hwm_mb=next((x["hwm_mb"] for x in sj["stages"] if x["stage"] == "fuse"), None))
        g = sj["gauge"]
        crit = {"peak<=4000": r["peak_mb"] <= 4000, "vol<=0.1%": r["vol_rel"] <= 1e-3,
                "watertight_1body_euler": r["watertight"] and r["bodies"] == 1 and r["euler"] == out["B"]["euler"],
                "hausdorff<=0.05": h <= 0.05, "gauge": g["watertight"] and g["frame_ok"] and g["mount_ok"],
                "time<=1.5xB": r["wall_s"] <= 1.5 * bd["wall_s"]}
        r["criteria"] = crit; r["PASS"] = all(crit.values())
    else:
        r["PASS"] = False
    out[s] = r
    print(s, json.dumps(r, default=float))
(root / "verdicts.json").write_text(json.dumps(out, indent=1, default=float))
