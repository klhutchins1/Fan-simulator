"""Run the night job queue (AGENTS.md rule 2). Launched by the Scheduled Task `fansim-night-queue` at 00:30.

Jobs live in ``night/queue.json`` (tracked, so any agent can add one):

    {"jobs": [{"id": "suite-too-close-r03", "branch": "too-close-r03",
               "cmd": ["python", "scripts/pytest_chunks.py", "--chunks", "3", "--chunk", "0", "--", "-q"],
               "max_hours": 2, "status": "queued"}]}

- `status` "queued" runs **once**: a job whose id and spec already ran (``runs/night/done.json``) is skipped on later
  nights. Set `status` to "rerun" to run it again, or change its spec. Anything else is skipped.
- With `branch`, the job runs in a fresh worktree of that branch (``runs/night/wt-<id>``), so the main checkout
  (which other agents may be using) is never switched.
- `cmd[0] == "python"` means this venv's python.
- The runner never starts a job at or after 15:30 or when the next job's `max_hours` would reach 16:00. The 4–9 PM
  peak-demand window is never touched.
- The Scheduled Task runs this file from its own worktree of master (``T:/Projects/fansim-night``) with
  ``--self-update``: it first moves that worktree to the latest local ``master``, then re-runs itself. A job
  therefore runs only once it is committed to master's ``night/queue.json``.
- Jobs get ``PYTHONPATH=<their checkout>``, because the venv's editable install points at the main checkout.
- Results always go to the **main** checkout (``<main>/runs/night``), not the night worktree:
  ``runs/night/<date>/<id>.log`` and ``runs/night/<date>/results.json``. The queue file itself is not
  edited by the runner; a human or agent marks jobs done.

    python scripts/night_queue.py            # run now (what the Scheduled Task does)
    python scripts/night_queue.py --dry-run  # show what would run
"""
from __future__ import annotations

import argparse
import hashlib
import os
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "night" / "queue.json"


def results_root() -> Path:
    """``runs/night`` in the main worktree (the first entry of ``git worktree list``), wherever this runs from."""
    try:
        out = subprocess.run(["git", "worktree", "list", "--porcelain"], cwd=ROOT, capture_output=True,
                             text=True, check=True).stdout
        main = Path(out.splitlines()[0].split(" ", 1)[1].strip())
    except (OSError, subprocess.CalledProcessError, IndexError):
        main = ROOT
    return main / "runs" / "night"


OUT = results_root()
LAST_START = dt.time(15, 30)
PEAK_START = dt.time(16, 0)


def may_start(now: dt.datetime, max_hours: float) -> bool:
    """False at/after 15:30, or if the job could run into the 16:00 peak window."""
    if now.time() >= LAST_START and now.time() < dt.time(21, 0):
        return False
    if dt.time(21, 0) <= now.time():
        end_ok_until = dt.datetime.combine(now.date() + dt.timedelta(days=1), PEAK_START)
    else:
        end_ok_until = dt.datetime.combine(now.date(), PEAK_START)
    return now + dt.timedelta(hours=float(max_hours)) <= end_ok_until


def _spec_hash(job: dict) -> str:
    spec = {k: job.get(k) for k in ("cmd", "branch", "max_hours")}
    return hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()[:16]


def should_run(job: dict, done: dict) -> bool:
    status = job.get("status")
    if status == "rerun":
        return True
    if status != "queued":
        return False
    return done.get(job["id"], {}).get("spec") != _spec_hash(job)


def mark_ran(done: dict, job: dict, result: str, date: str) -> None:
    done[job["id"]] = {"spec": _spec_hash(job), "date": date, "result": result}


def resolve_cmd(cmd: list[str]) -> list[str]:
    return [sys.executable if (i == 0 and c == "python") else c for i, c in enumerate(cmd)]


def _worktree(branch: str, job_id: str) -> Path:
    wt = OUT / f"wt-{job_id}"
    if wt.exists():
        subprocess.run(["git", "worktree", "remove", "--force", str(wt)], cwd=ROOT, check=False)
    subprocess.run(["git", "worktree", "add", "--detach", str(wt), branch], cwd=ROOT, check=True)
    return wt


def run(dry_run: bool = False, now_fn=dt.datetime.now) -> list[dict]:
    jobs = json.loads(QUEUE.read_text(encoding="utf-8")).get("jobs", [])
    day = OUT / now_fn().strftime("%Y-%m-%d")
    done_path = OUT / "done.json"
    try:
        done = json.loads(done_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        done = {}
    results: list[dict] = []
    for job in jobs:
        if not should_run(job, done):
            continue
        now = now_fn()
        rec = {"id": job["id"], "start": now.isoformat(timespec="seconds")}
        if not may_start(now, job.get("max_hours", 1)):
            rec["result"] = "not started: inside or would reach the 4-9 PM peak window"
            results.append(rec)
            continue
        if dry_run:
            rec["result"] = "dry run"
            results.append(rec)
            continue
        day.mkdir(parents=True, exist_ok=True)
        cwd = _worktree(job["branch"], job["id"]) if job.get("branch") else ROOT
        log = day / f"{job['id']}.log"
        with log.open("w", encoding="utf-8") as fh:
            try:
                env = {**os.environ, "PYTHONPATH": str(cwd), "PYTHONUNBUFFERED": "1"}
                rc = subprocess.run(resolve_cmd(job["cmd"]), cwd=cwd, stdout=fh, stderr=subprocess.STDOUT, env=env,
                                    timeout=float(job.get("max_hours", 1)) * 3600).returncode
                rec["result"] = f"exit {rc}"
            except subprocess.TimeoutExpired:
                rec["result"] = "timeout"
        rec["end"] = now_fn().isoformat(timespec="seconds")
        rec["log"] = str(log)
        results.append(rec)
        mark_ran(done, job, rec["result"], day.name)
        done_path.write_text(json.dumps(done, indent=1), encoding="utf-8")
        (day / "results.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    if not dry_run and results:
        day.mkdir(parents=True, exist_ok=True)
        (day / "results.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    return results


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--self-update", action="store_true",
                    help="move this worktree to the latest local master, then re-run without this flag")
    args = ap.parse_args(argv)
    if args.self_update:
        subprocess.run(["git", "checkout", "-q", "--detach", "master"], cwd=ROOT, check=True)
        rest = ["--dry-run"] if args.dry_run else []
        return subprocess.run([sys.executable, str(Path(__file__).resolve()), *rest], cwd=ROOT).returncode
    for r in run(dry_run=args.dry_run):
        print(json.dumps(r), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
