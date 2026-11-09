"""Same-day merge gate: run the fast suite on a branch now, in its own worktree (AGENTS.md rule 4).

    python scripts/gate.py <branch>

- Refuses (exit 3) if the run could reach the 4-9 PM peak window: the same rule as the night queue.
- Runs ``scripts/pytest_chunks.py --chunks 3 --all`` from a fresh worktree of the branch, so the checkout you are
  working in is never switched.
- Writes ``runs/gate/<branch>.json`` (sha, ok, one verdict line per chunk) and ``runs/gate/<branch>-<sha>.log`` in
  the main checkout, and prints the line to paste on the board.
- Exit 0 = green: merge to master with ``--no-ff``. Exit 1 = red: fix it, do not merge.

Use this for ordinary branches. Keep the night queue for CFD and other long jobs.
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location("night_queue", Path(__file__).with_name("night_queue.py"))
nq = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(nq)

OUT = nq.results_root().parent / "gate"
FAST = ["-m", "not docker and not slow", "-q", "--tb=line"]


def main(argv: list[str] | None = None, now_fn=dt.datetime.now) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("branch")
    ap.add_argument("--chunks", type=int, default=3)
    ap.add_argument("--max-hours", type=float, default=1.5, help="worst-case run time, for the peak-window check")
    args = ap.parse_args(argv)

    if not nq.may_start(now_fn(), args.max_hours):
        print(f"gate refused: a {args.max_hours:g} h run could reach the 4-9 PM peak window. "
              "Run it after 9 PM or tomorrow before 2:30 PM.")
        return 3

    sha = subprocess.run(["git", "rev-parse", args.branch], cwd=ROOT, check=True, capture_output=True,
                         text=True).stdout.strip()
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", args.branch)
    OUT.mkdir(parents=True, exist_ok=True)
    wt = OUT / f"wt-{safe}"
    if wt.exists():
        subprocess.run(["git", "worktree", "remove", "--force", str(wt)], cwd=ROOT, check=False)
    subprocess.run(["git", "worktree", "add", "-q", "--detach", str(wt), sha], cwd=ROOT, check=True)

    log = OUT / f"{safe}-{sha[:7]}.log"
    cmd = [sys.executable, "scripts/pytest_chunks.py", "--chunks", str(args.chunks), "--all", "--", *FAST]
    env = {**os.environ, "PYTHONPATH": str(wt), "PYTHONUNBUFFERED": "1"}
    verdicts: list[str] = []
    try:
        with log.open("w", encoding="utf-8") as fh:
            proc = subprocess.Popen(cmd, cwd=wt, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, encoding="utf-8", errors="replace", bufsize=1)
            assert proc.stdout is not None
            for line in proc.stdout:
                sys.stdout.write(line)
                fh.write(line)
                if re.match(r"chunk \d+: ", line):
                    verdicts.append(line.strip())
            rc = proc.wait()
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", str(wt)], cwd=ROOT, check=False)

    ok = rc == 0
    result = {"branch": args.branch, "sha": sha, "ok": ok, "exit": rc, "verdicts": verdicts,
              "date": now_fn().isoformat(timespec="minutes"), "log": str(log)}
    (OUT / f"{safe}.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    counts = "/".join(m.group(1) for v in verdicts if (m := re.search(r"(\d+) passed", v)))
    if ok:
        print(f"\ngate green: {args.branch} {sha[:7]}, {counts} passed ({now_fn():%Y-%m-%d}). Merge with --no-ff.")
    else:
        print(f"\ngate RED: {args.branch} {sha[:7]} (exit {rc}). Do not merge. Log: {log}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
