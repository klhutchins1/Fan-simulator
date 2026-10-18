"""QA r14 Task A1 (PREREG_R14 586bbe9): r9 Task E item selection reused verbatim, hook_c11, master 9562574 (run clone /workspace/fansim/qa/run_r14).
Original r9 docstring follows.
12 shrouded stress designs (S7 rows, seed 9012: 3 ring-height bins [0.3,0.55),[0.55,0.8),[0.8,1.0] x 4,
spread over n_blades), each also built as an unshrouded TWIN (same flat, shroud_thick_mm=0), plus 4
unshrouded controls (random S1-S6, seed 9012). Serial P builds, 8gb tier, round-8 hook_c (RSS/HWM at the
check_fuse_memory call and VmHWM at worker exit). Gate: MemAvailable >= 1.1*expected+0.5 GB (expected 3 GB
shrouded, 2.5 otherwise), waited <= 600 s monotonic. Usage: python run_e.py <out.jsonl>"""
import gzip, json, os, random, sys, time
from pathlib import Path
os.environ["FANSIM_MEMORY_TIER"] = "8gb"; os.environ.pop("FANSIM_FUSE_GUARD", None)
R7 = "/workspace/fansim/repo-r7/handoff/2026-10-11_from-qa-7/stress"
D = [json.loads(l) for l in gzip.open(f"{R7}/inputs.jsonl.gz")]; D = [d for d in D if not d.get("sample_error")]
rng = random.Random(9012)
shr = [d for d in D if float(d["flat"].get("shroud_thick_mm") or 0) > 0]
items = []
for lo, hi in ((0.3, 0.55), (0.55, 0.8), (0.8, 1.01)):
    pool = sorted([d for d in shr if lo <= float(d["flat"]["shroud_height_frac"]) < hi], key=lambda d: (d["flat"]["n_blades"], d["id"]))
    q = [pool[int(round(i * (len(pool) - 1) / 3))] for i in range(4)] if len(pool) >= 4 else pool
    for d in q:
        items.append({"id": d["id"], "kind": "shrouded", "flat": d["flat"], "features": d.get("features") or {}})
        items.append({"id": d["id"] + "_twin", "kind": "twin", "flat": dict(d["flat"], shroud_thick_mm=0.0), "features": d.get("features") or {}})
ctl = rng.sample([d for d in D if not float(d["flat"].get("shroud_thick_mm") or 0) and d["stratum"] in ("S1", "S2", "S3", "S4", "S5", "S6")], 4)
items += [{"id": d["id"], "kind": "control", "flat": d["flat"], "features": d.get("features") or {}} for d in ctl]
OUT = Path(sys.argv[1]); LOG = OUT.with_suffix(".calls.jsonl")
os.environ["FUSE_CALL_LOG"] = str(LOG)
os.environ["PYTHONPATH"] = "/workspace/fansim/repo-r13/handoff/2026-10-13_to-qa-11/hook_c11" + os.pathsep + os.environ.get("PYTHONPATH", "")
from fansim.geometry.isolated import build_stl_isolated
import fansim; assert fansim.__file__.startswith("/workspace/fansim/qa/run_r14"), fansim.__file__
def avail():
    for l in open("/proc/meminfo"):
        if l.startswith("MemAvailable"): return int(l.split()[1]) / 1048576
done = {json.loads(l)["id"] for l in open(OUT)} if OUT.exists() else set()
for it in items:
    if it["id"] in done: continue
    need = 1.1 * (3.0 if it["kind"] == "shrouded" else 2.5) + 0.5; t0 = time.monotonic()
    while avail() < need and time.monotonic() - t0 < 600: time.sleep(10)
    rec = {"id": it["id"], "kind": it["kind"], "shroud_height_frac": it["flat"].get("shroud_height_frac"),
           "shroud_thick_mm": it["flat"].get("shroud_thick_mm"), "n_blades": it["flat"]["n_blades"],
           "need_gb": round(need, 2), "avail_start_gb": round(avail(), 2), "gate_wait_s": round(time.monotonic() - t0, 1)}
    if avail() < need: rec["gate_unmet_built_anyway"] = True
    n0 = sum(1 for _ in open(LOG)) if LOG.exists() else 0
    t1 = time.monotonic()
    try:
        build_stl_isolated(it["flat"], it["features"], f"/tmp/qa14a_{it['id']}.stl", timeout=900.0, preview=False); rec["outcome"] = "OK"
        import trimesh; m = trimesh.load(f"/tmp/qa14a_{it['id']}.stl", force="mesh"); rec["out_faces"] = len(m.faces)
    except Exception as e:
        rec["outcome"] = "ERR"; rec["err"] = f"{type(e).__name__}: {e}"[:300]
    rec["mono_s"] = round(time.monotonic() - t1, 1)
    rec["events"] = [json.loads(l) for l in list(open(LOG))[n0:]] if LOG.exists() else []
    try: os.remove(f"/tmp/qa14a_{it['id']}.stl")
    except OSError: pass
    with open(OUT, "a") as f: f.write(json.dumps(rec) + "\n")
    print(it["id"], rec["outcome"], rec.get("mono_s"), flush=True)
print("DONE", flush=True)
