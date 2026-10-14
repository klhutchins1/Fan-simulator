"""QA r10b Task B runner (PREREG_R10 26aa359; from r9 run_a). Resumable; one design (so one build) at a time; never imports fansim.
Usage: python run_a.py <a_sample.jsonl> <outdir>. Appends <outdir>/designs.jsonl; writes <outdir>/summary.json."""
import json, os, subprocess, sys, time
from collections import Counter
from pathlib import Path
inp, outdir = Path(sys.argv[1]), Path(sys.argv[2]); outdir.mkdir(parents=True, exist_ok=True)
here = Path(__file__).resolve().parent; py = sys.executable
out = outdir / "designs.jsonl"; work = Path("/tmp/qa10b_work"); work.mkdir(exist_ok=True)
os.environ["STRESS_KEEP_DIR"] = str(outdir / "kept_stl")
os.environ["PYTHONPATH"] = str(here / "hook_b") + (os.pathsep + os.environ["PYTHONPATH"] if os.environ.get("PYTHONPATH") else "")
plan = [json.loads(l) for l in inp.open()]
done = {}
if out.exists():
    for l in out.open():
        try: r = json.loads(l); done[r["id"]] = r
        except ValueError: pass
m0 = time.monotonic()
def summ():
    rs = list(done.values()); oc = Counter(); k5 = Counter(); k7 = Counter()
    for r in rs:
        for k in ("Pp", "Pc", "C"):
            if k in r["builds"]: oc[f'{k}:{r["builds"][k]["outcome"]}'] += 1
        for k in ("Pp", "Pc"):
            k5[f'{k}:{r["meas"].get(k, {}).get("K5", {}).get("k5")}'] += 1
        if "K7" in r["checks"]: k7[r["checks"]["K7"]] += 1
    s = {"done": len(rs), "planned": len(plan), "session_mono_h": round((time.monotonic() - m0) / 3600, 2),
         "outcomes": dict(oc), "K5": dict(k5), "K7": dict(k7), "job_errors": sum(1 for r in rs if r.get("job_error") or r.get("job_status"))}
    (outdir / "summary.json").write_text(json.dumps(s, indent=1)); return s
for d in plan:
    if d["id"] in done: continue
    wd = work / d["id"]; wd.mkdir(exist_ok=True); (wd / "design.json").write_text(json.dumps(d))
    res = wd / "result.json"; res.unlink(missing_ok=True); ts = time.monotonic()
    try:
        rc = subprocess.run([py, str(here / "job_b.py"), str(wd / "design.json"), str(wd), str(res)],
                            stdout=open(wd / "job.log", "w"), stderr=subprocess.STDOUT, timeout=3 * 3600).returncode
    except subprocess.TimeoutExpired:
        rc = "job_timeout"
    r = json.loads(res.read_text()) if res.exists() else {"id": d["id"], "stratum": d["stratum"], "seq": d["seq"], "builds": {}, "checks": {}, "meas": {}}
    if rc != 0:
        r["job_status"] = f"job rc={rc}"; r["job_log_tail"] = (wd / "job.log").read_text(errors="replace")[-1500:]
    r["job_mono_s"] = round(time.monotonic() - ts, 1); r["group"] = d["group"]; r["kind_C"] = d["kind_C"]
    r["input"] = {k: d[k] for k in ("flat", "features") if k in d}
    with out.open("a") as fh: fh.write(json.dumps(r, default=float) + "\n")
    done[d["id"]] = r
    for f in wd.glob("*.stl"): f.unlink()
    summ()
print("DONE", json.dumps(summ()), flush=True)
