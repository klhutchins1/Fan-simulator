"""QA r8 Task C runner (prereg 6b0aedf): serial P builds on the 8gb tier with the fuse-call hook.
Resumable: designs already in OUT are skipped. All limits use time.monotonic()."""
import gzip, json, os, sys, time
from pathlib import Path
os.environ["FANSIM_MEMORY_TIER"] = "8gb"
R7 = "/workspace/fansim/repo-r7/handoff/2026-10-11_from-qa-7/stress"
IDS = "S1_0018 S7_0015 S2_0014 S7_0017 S8_0002 S2_0016 S6_0018 S1_0020 S7_0013 S6_0015 CTL_0001 S6_0019 S1_0016 S6_0017 S6_0016 S5_0016 S5_0017 S5_0007 S5_0014 S5_0019 S5_0015 S3_0019".split()
OUT = Path(sys.argv[1]); LOG = OUT.with_suffix(".calls.jsonl")
inp = {json.loads(l)["id"]: json.loads(l) for l in gzip.open(f"{R7}/inputs.jsonl.gz")}
r7 = {json.loads(l)["id"]: json.loads(l) for l in gzip.open(f"{R7}/run_r7/designs.jsonl.gz")}
os.environ["FUSE_CALL_LOG"] = str(LOG)
os.environ["PYTHONPATH"] = str(Path(__file__).parent / "hook_c") + os.pathsep + os.environ.get("PYTHONPATH", "")
from fansim.geometry.isolated import build_stl_isolated
def avail():
    for l in open("/proc/meminfo"):
        if l.startswith("MemAvailable"): return int(l.split()[1]) / 1048576
done = {json.loads(l)["id"] for l in open(OUT)} if OUT.exists() else set()
for i in IDS:
    if i in done: continue
    need = 1.1 * r7[i]["builds"]["P"]["peak_mb"] / 1024 + 0.5
    t0 = time.monotonic()
    while avail() < need and time.monotonic() - t0 < 600: time.sleep(10)
    rec = {"id": i, "need_gb": round(need, 2), "avail_start_gb": round(avail(), 2), "gate_wait_s": round(time.monotonic() - t0, 1)}
    if avail() < need:
        rec["outcome"] = "SKIPPED_MEM"
    else:
        n0 = sum(1 for _ in open(LOG)) if LOG.exists() else 0
        t1, w1 = time.monotonic(), time.time()
        try:
            build_stl_isolated(inp[i]["flat"], inp[i].get("features") or {}, f"/tmp/qa8c_{i}.stl", timeout=900.0, preview=False)
            rec["outcome"] = "OK"
        except Exception as e:
            rec["outcome"] = "ERR"; rec["err"] = f"{type(e).__name__}: {e}"[:300]
        rec["mono_s"] = round(time.monotonic() - t1, 1); rec["wall_s"] = round(time.time() - w1, 1)
        rec["events"] = [json.loads(l) for l in list(open(LOG))[n0:]] if LOG.exists() else []
        try: os.remove(f"/tmp/qa8c_{i}.stl")
        except OSError: pass
    with open(OUT, "a") as f: f.write(json.dumps(rec) + "\n")
    print(i, rec["outcome"], rec.get("mono_s"), flush=True)
print("DONE", flush=True)
