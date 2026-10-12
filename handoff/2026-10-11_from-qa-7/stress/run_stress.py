"""Resumable stress runner (PREREG §4). Light: never imports fansim.
Usage: python run_stress.py <inputs.jsonl> <outdir> [--pilot] [--counts counts.json] [--r6 r6_designs.jsonl]
Round 7 (PREREG amendment 5): with --r6, order = r6 failures, then designs r6 never reached, then the
other r6 designs. Build subprocesses get the K12 sitecustomize hook via PYTHONPATH (amendment 8).
Appends one line per design to <outdir>/designs.jsonl; rewrites <outdir>/summary.json after each."""
import json, os, statistics, subprocess, sys, time
from collections import Counter, defaultdict
from pathlib import Path

inp, outdir = Path(sys.argv[1]), Path(sys.argv[2]); outdir.mkdir(parents=True, exist_ok=True)
pilot = "--pilot" in sys.argv
counts = json.loads(Path(sys.argv[sys.argv.index("--counts") + 1]).read_text()) if "--counts" in sys.argv else {}
here = Path(__file__).resolve().parent
py = sys.executable
out = outdir / "designs.jsonl"; summ = outdir / "summary.json"
work = Path("/tmp/stress_work"); work.mkdir(exist_ok=True)
os.environ["STRESS_KEEP_DIR"] = str(outdir / "kept_stl")
os.environ["PYTHONPATH"] = str(here / "hook") + (os.pathsep + os.environ["PYTHONPATH"] if os.environ.get("PYTHONPATH") else "")
R6_FAIL = ["S5_0007", "S2_0000", "S8_0002", "S8_0008", "S3_0002", "S4_0005", "S4_0012",
           "CTL_0001", "CTL_0002", "CTL_0003", "CTL_0004"]

D = [json.loads(l) for l in inp.open()]
for d in D:
    s, i = d["stratum"], d["idx"]
    d["kind_C"] = s in ("S8", "CTL") or i % 20 == 0
    d["kind_T"] = s == "CTL" or (s not in ("S8",) and i % 20 == 0)
    d["kind_R"] = d["seq"] % 50 == 0
plan = [d for d in D if (d["pilot"] if pilot else (d["pilot"] or d["idx"] < counts.get(d["stratum"], 10**9)))]
if "--r6" in sys.argv:
    r6 = set()
    for l in Path(sys.argv[sys.argv.index("--r6") + 1]).open():
        try:
            r6.add(json.loads(l)["id"])
        except (ValueError, KeyError):
            pass
    byid = {d["id"]: d for d in plan}
    first = [byid[i] for i in R6_FAIL if i in byid]
    plan = first + [d for d in plan if d["id"] not in r6] + [d for d in plan if d["id"] in r6 and d["id"] not in R6_FAIL]
done = {}
if out.exists():
    for l in out.open():
        try:
            r = json.loads(l); done[r["id"]] = r
        except ValueError:
            pass


def summarize(t_start, n_new):
    rs = list(done.values())
    by = defaultdict(Counter); checks = defaultdict(Counter); kt = defaultdict(list); kp = defaultdict(int)
    for r in rs:
        by[r["stratum"]][r.get("builds", {}).get("P", {}).get("outcome", r.get("job_status", "?"))] += 1
        for k, v in r.get("checks", {}).items():
            checks[k][v] += 1
        for k, b in r.get("builds", {}).items():
            if "s" in b:
                kt[k].append(b["s"]); kp[k] = max(kp[k], b.get("peak_mb", 0))
    first200 = sorted(rs, key=lambda r: r["seq"])[:200]
    k1f = sum(r.get("checks", {}).get("K1") == "FAIL" for r in first200)
    remaining = [d for d in plan if d["id"] not in done]
    per = (time.time() - t_start) / n_new if n_new else None
    import re as _re
    ss = [r for r in rs if r.get("builds")]
    mono = sum(b.get("mono_s", 0) for r in ss for b in r["builds"].values() if isinstance(b, dict))
    wall = sum(b.get("s", 0) for r in ss for b in r["builds"].values() if isinstance(b, dict))
    s = {"updated": time.strftime("%F %T"), "done": len(rs),
         "build_wall_h": round(wall / 3600, 2), "build_mono_h": round(mono / 3600, 2),
         "suspect_suspend_builds": sum(1 for r in ss for b in r["builds"].values() if isinstance(b, dict) and b.get("suspect_suspend")), "planned": len(plan), "remaining": len(remaining),
         "P_outcome_by_stratum": {k: dict(v) for k, v in sorted(by.items())},
         "checks": {k: dict(v) for k, v in sorted(checks.items())},
         "build_s_median": {k: round(statistics.median(v), 1) for k, v in kt.items()},
         "build_s_max": {k: round(max(v), 1) for k, v in kt.items()},
         "build_peak_mb": dict(kp), "job_errors": sum(1 for r in rs if r.get("job_error") or r.get("job_status")),
         "first200_K1_fail": [k1f, len(first200)],
         "sec_per_design_this_session": round(per, 1) if per else None,
         "eta_h": round(per * len(remaining) / 3600, 1) if per else None}
    summ.write_text(json.dumps(s, indent=1))
    return s


t0 = time.time(); n_new = 0
summarize(t0, 0)
for d in plan:
    if d["id"] in done:
        continue
    wd = work / d["id"]; wd.mkdir(exist_ok=True)
    (wd / "design.json").write_text(json.dumps(d))
    res = wd / "result.json"; res.unlink(missing_ok=True)
    ts = time.time()
    try:
        cp = subprocess.run([py, str(here / "design_job.py"), str(wd / "design.json"), str(wd), str(res)],
                            stdout=open(wd / "job.log", "w"), stderr=subprocess.STDOUT, timeout=4 * 3600)
        rc = cp.returncode
    except subprocess.TimeoutExpired:
        rc = "job_timeout"
    r = json.loads(res.read_text()) if res.exists() else {"id": d["id"], "stratum": d["stratum"], "seq": d["seq"], "builds": {}, "checks": {}}
    if rc != 0:
        r["job_status"] = f"job rc={rc}"
        r["job_log_tail"] = (wd / "job.log").read_text(errors="replace")[-1500:] if (wd / "job.log").exists() else ""
    r["job_s"] = round(time.time() - ts, 1)
    r["input"] = {k: d[k] for k in ("flat", "features", "flags", "pilot", "kind_C", "kind_T", "kind_R") if k in d}
    r["input"]["s8_kind"] = d.get("s8_kind")
    with out.open("a") as fh:
        fh.write(json.dumps(r, default=float) + "\n")
    done[d["id"]] = r; n_new += 1
    for f in wd.glob("*.stl"):
        f.unlink()
    s = summarize(t0, n_new)
    if s["first200_K1_fail"][1] >= 200 and s["first200_K1_fail"][0] > 60:
        (outdir / "STOPPED").write_text("stop rule: >30% of the first 200 designs fail K1\n"); break
print(json.dumps(summarize(t0, n_new))[:600])
