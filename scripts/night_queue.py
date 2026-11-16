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
  ``--self-update``: it first fetches and moves that worktree to ``origin/master`` (or to local ``master`` if that
  has unpushed commits or the fetch fails), then re-runs itself. A job therefore runs once it is on master's
  ``night/queue.json`` and pushed.
- Jobs get ``PYTHONPATH=<their checkout>``, because the venv's editable install points at the main checkout.
- Results always go to the **main** checkout (``<main>/runs/night``), not the night worktree:
  ``runs/night/<date>/<id>.log`` and ``runs/night/<date>/results.json``.
- Every run appends to ``runs/night/<date>/runner.log`` (which master it followed and why, which jobs, the morning
  check's exit); that file exists even on a night with no jobs. Read it first if a queued job did not run.
- After the last job the runner calls ``scripts/morning_check.py --apply``: it marks jobs done/failed on master,
  merges a green branch whose job has ``"merge_on_green": true`` (only when that is safe; see that file), and
  writes ``runs/night/STATUS.md``.

    python scripts/night_queue.py            # run now (what the Scheduled Task does)
    python scripts/night_queue.py --dry-run  # show what would run
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
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


def choose_update_target(root: Path = ROOT) -> tuple[str, str]:
    """(ref to run from, why). ``origin/master`` only if a fetch works and it contains local master.

    A failed fetch falls back to local ``master`` and says so: a runner that quietly runs a week-old master
    never sees the jobs pushed since (2026-11-15).
    """
    try:
        fetch = subprocess.run(["git", "fetch", "-q", "origin", "master"], cwd=root, capture_output=True,
                               text=True, timeout=120, check=False)
        if fetch.returncode != 0:
            return "master", f"FETCH FAILED: {(fetch.stderr or fetch.stdout).strip()[:200] or fetch.returncode}"
        sha = {ref: subprocess.run(["git", "rev-parse", ref], cwd=root, capture_output=True, text=True,
                                   check=False).stdout.strip() for ref in ("master", "origin/master")}
        if sha["master"] == sha["origin/master"]:
            return "master", "local master is up to date with origin/master"
        ahead = subprocess.run(["git", "merge-base", "--is-ancestor", "master", "origin/master"], cwd=root,
                               capture_output=True, timeout=60, check=False).returncode == 0
    except (OSError, subprocess.TimeoutExpired) as exc:
        return "master", f"FETCH FAILED: {type(exc).__name__}: {exc}"[:240]
    if ahead:
        return "origin/master", "origin/master is ahead of local master"
    return "master", "local master has unpushed commits (it is not behind origin/master)"


def update_target(root: Path = ROOT) -> str:
    return choose_update_target(root)[0]


def log_runner(day: Path, msg: str, now: dt.datetime | None = None) -> None:
    """Append a line to ``<day>/runner.log``: what the runner did, even on a night with no jobs."""
    now = now or dt.datetime.now()  # noqa: DTZ005
    day.mkdir(parents=True, exist_ok=True)
    with (day / "runner.log").open("a", encoding="utf-8") as fh:
        fh.write(f"{now:%Y-%m-%d %H:%M} {msg}\n")


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
        if job.get("branch"):
            rec["sha"] = subprocess.run(["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True,
                                        text=True).stdout.strip()
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
    day = OUT / dt.datetime.now().strftime("%Y-%m-%d")  # noqa: DTZ005
    if args.self_update:
        target, why = choose_update_target()
        if not args.dry_run:
            log_runner(day, f"update to {target}: {why}")
        subprocess.run(["git", "checkout", "-q", "--detach", target], cwd=ROOT, check=True)
        rest = ["--dry-run"] if args.dry_run else []
        return subprocess.run([sys.executable, str(Path(__file__).resolve()), *rest], cwd=ROOT).returncode
    results = run(dry_run=args.dry_run)
    for r in results:
        print(json.dumps(r), flush=True)
    if not args.dry_run:
        head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True,
                              check=False).stdout.strip()
        ids = ", ".join(r["id"] for r in results) or "none queued"
        log_runner(day, f"running from {head}; {len(results)} job(s): {ids}")
    if results and not args.dry_run:
        # Close the jobs and merge what is safely green; a failure here must never fail the night run.
        mc = subprocess.run([sys.executable, str(Path(__file__).with_name("morning_check.py")), "--apply"],
                            cwd=ROOT, capture_output=True, text=True, check=False)
        (day / "morning_check.log").write_text((mc.stdout or "") + (mc.stderr or ""), encoding="utf-8")
        tail = f": {mc.stderr.strip()[-200:]}" if mc.returncode else ""
        log_runner(day, f"morning_check exit {mc.returncode}{tail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
