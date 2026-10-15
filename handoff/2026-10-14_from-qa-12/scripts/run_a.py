"""QA r12 Task A (PREREG_R12 42004b3): QA-34 strip check. Resumable, serial. Usage: python run_a.py <out.jsonl>"""
import gzip, json, os, random, shutil, sys, time
from pathlib import Path
os.environ["FANSIM_MEMORY_TIER"] = "8gb"; os.environ.pop("FANSIM_FUSE_GUARD", None)
HERE = Path(__file__).resolve().parent
os.environ["PYTHONPATH"] = str(HERE / "hook_b") + os.pathsep + os.environ.get("PYTHONPATH", "")
R7 = "/workspace/fansim/repo-r7/handoff/2026-10-11_from-qa-7/stress/inputs.jsonl.gz"
R10 = "/workspace/fansim/repo-r10/handoff/2026-10-13_from-qa-10/data/b_sample.jsonl"
ctl = next(json.loads(l) for l in open(R10) if json.loads(l)["id"] == "S5_0184")
D = [json.loads(l) for l in gzip.open(R7)]; D = [d for d in D if not d.get("sample_error")]
pool = [d for d in D if d["stratum"] == "S5" and not float(d["flat"].get("shroud_thick_mm") or 0)
        and any(float(v or 0) for v in (d.get("features") or {}).values()) and d["id"] not in ("S5_0184", "S5_0228", "S5_0112")]
new = random.Random(11013).sample(pool, 2)
items = [("control", ctl)] + [("new", d) for d in new]
from fansim.geometry.isolated import build_stl_isolated
import fansim, trimesh; assert fansim.__file__.startswith("/workspace/fansim/qa/run_r12"), fansim.__file__
OUT = Path(sys.argv[1]); KEEP = OUT.parent / "a_kept"
done = {json.loads(l)["id"] for l in open(OUT)} if OUT.exists() else set()
print("pool", len(pool), "new", [d["id"] for d in new], flush=True)
for kind, d in items:
    if d["id"] in done: continue
    flat = dict(d["flat"], section_wrap="cylinder"); stl = Path(f"/tmp/qa12a_{d['id']}.stl"); stl.unlink(missing_ok=True)
    q = Path(f"/tmp/qa12a_{d['id']}.fuse"); q.unlink(missing_ok=True); os.environ["QA_FUSE_LOG"] = str(q)
    rec = {"id": d["id"], "kind": kind, "n_blades": flat["n_blades"], "features": {k: v for k, v in (d.get("features") or {}).items() if float(v or 0)}}
    t = time.monotonic()
    try:
        build_stl_isolated(flat, d.get("features") or {}, stl, timeout=900.0, preview=False); rec["outcome"] = "OK"
    except Exception as e:
        msg = f"{type(e).__name__}: {e}"; rec["err"] = msg[-600:]; rec["outcome"] = "REFUSED_HANG" if "hang" in msg else "ERR"
    rec["mono_s"] = round(time.monotonic() - t, 1)
    rec["fuse_calls"] = [json.loads(x) for x in q.read_text().splitlines()] if q.exists() else []
    rec["brep_solids"] = rec["fuse_calls"][-1]["solids"] if rec["fuse_calls"] else None
    if rec["outcome"] == "OK":
        m = trimesh.load(stl, force="mesh"); a = m.area_faces
        rec.update(faces=len(m.faces), watertight=bool(m.is_watertight), bodies=len(m.split(only_watertight=False)),
                   degenerate=int((a < 1e-9).sum()), volume=float(m.volume))
        rec["pass"] = rec["watertight"] and rec["bodies"] == 1 and rec["degenerate"] == 0 and (kind != "control" or rec["brep_solids"] == 1)
        if not rec["pass"]:
            KEEP.mkdir(exist_ok=True)
            with open(stl, "rb") as fi, gzip.open(KEEP / f"{d['id']}.stl.gz", "wb") as fo: shutil.copyfileobj(fi, fo)
    stl.unlink(missing_ok=True)
    with open(OUT, "a") as f: f.write(json.dumps(rec) + "\n")
    print(d["id"], rec["outcome"], rec.get("pass"), rec["mono_s"], flush=True)
    if kind == "control" and rec.get("pass") is False:
        print("F0 FAIL: stop A", flush=True); break
print("DONE", flush=True)
