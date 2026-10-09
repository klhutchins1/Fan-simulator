"""Launch cupfuse_job.py for one strategy and sample the process tree's RSS every 0.25 s.
Usage: python cupfuse_driver.py <strategy> <outroot> [timeout_s]. Writes <outroot>/<strategy>/{rss.tsv,driver.json}.
S5 runs the job via fansim.isolated_job-style child (python -c spawning a 2nd process) so the counted
peak is the worker's; S7 sets MALLOC_ARENA_MAX=2."""
import json, os, subprocess, sys, time
from pathlib import Path

st, root = sys.argv[1], Path(sys.argv[2])
timeout = float(sys.argv[3]) if len(sys.argv) > 3 else 1800
out = root / st
out.mkdir(parents=True, exist_ok=True)
here = Path(__file__).resolve().parent
py = sys.executable
env = dict(os.environ)
if st in ("S7", "X1"):  # X1 = S3 + MALLOC_ARENA_MAX=2 (exploratory, NOT pre-registered)
    env["MALLOC_ARENA_MAX"] = "2"
job = [py, str(here / "cupfuse_job.py"), "B" if st in ("S5", "S7") else ("S3" if st == "X1" else st), str(out)]
if st == "S5":  # parent that never imports OCP; the worker is a separate process (as in the cockpit)
    job = [py, "-c", "import subprocess,sys; sys.exit(subprocess.call(sys.argv[1:]))", *job]


def rss(p):
    try:
        with open(f"/proc/{p}/status") as f:
            for ln in f:
                if ln.startswith("VmRSS:"):
                    return int(ln.split()[1]) // 1024
    except OSError:
        pass
    return 0


def tree(rootpid):
    kids = {}
    for d in os.listdir("/proc"):
        if d.isdigit():
            try:
                with open(f"/proc/{d}/stat") as f:
                    pp = int(f.read().rsplit(")", 1)[1].split()[1])
                kids.setdefault(pp, []).append(int(d))
            except (OSError, ValueError, IndexError):
                pass
    s, todo = [], [rootpid]
    while todo:
        p = todo.pop(); s.append(p); todo += kids.get(p, [])
    return s


t0 = time.time()
proc = subprocess.Popen(job, env=env, cwd=os.getcwd(), stdout=open(out / "job.log", "w"),
                        stderr=subprocess.STDOUT)
peak, ptime, minavail, killed = 0, 0.0, 10**9, None
with open(out / "rss.tsv", "w") as f:
    while proc.poll() is None:
        tm = sum(rss(p) for p in tree(proc.pid))
        with open("/proc/meminfo") as m:
            av = next(int(ln.split()[1]) // 1024 for ln in m if ln.startswith("MemAvailable"))
        minavail = min(minavail, av)
        if tm > peak:
            peak, ptime = tm, time.time() - t0
        f.write(f"{time.time()-t0:.2f}\t{tm}\t{av}\n")
        if time.time() - t0 > timeout or av < 250:  # timeout or OOM guard (box has no swap)
            proc.kill(); killed = 'timeout' if av >= 250 else 'memguard'; break
        time.sleep(0.25)
res = {"strategy": st, "rc": proc.returncode, "wall_s": round(time.time() - t0, 1),
       "peak_tree_mb": peak, "peak_at_s": round(ptime, 1), "min_memavailable_mb": minavail, "killed": killed}
(out / "driver.json").write_text(json.dumps(res))
print(json.dumps(res))
