"""Same-day merge gate: run the fast suite on a branch now, in its own worktree (AGENTS.md rule 4).

    python scripts/gate.py <branch>

- Refuses (exit 3) if the run could reach the 4-9 PM peak window: the same rule as the night queue.
- First runs the same static checks as CI (ruff F811/F821, mypy, ``audit_status.py --strict``). Any red one stops
  the gate before the suite. ``--static-only`` runs just those (light, allowed in the peak window).
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
# Same checks as .github/workflows/ci.yml, plus the physics ledger (RV-0). Run in the branch's worktree.
STATIC = [
    ("ruff", [sys.executable, "-m", "ruff", "check", "fansim", "tests", "scripts", "--select", "F811,F821"]),
    ("mypy", [sys.executable, "-m", "mypy"]),
    ("audit", [sys.executable, "scripts/audit_status.py", "--strict"]),
]


def run_static(wt: Path, env: dict, fh) -> dict[str, bool]:
    """Run every STATIC check in ``wt``; log output to ``fh``; return {name: passed}."""
    out: dict[str, bool] = {}
    for name, cmd in STATIC:
        proc = subprocess.run(cmd, cwd=wt, env=env, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", check=False)
        fh.write(f"--- static {name}: {' '.join(cmd)}\n{proc.stdout}{proc.stderr}")
        out[name] = proc.returncode == 0
        print(f"static {name}: {'ok' if out[name] else 'FAILED'}", flush=True)
        if not out[name]:
            sys.stdout.write((proc.stdout + proc.stderr)[-2000:])
    return out


class _StaticRed(Exception):
    """A static check failed; skip the suite."""


def main(argv: list[str] | None = None, now_fn=dt.datetime.now) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("branch")
    ap.add_argument("--chunks", type=int, default=3)
    ap.add_argument("--max-hours", type=float, default=1.5, help="worst-case run time, for the peak-window check")
    ap.add_argument("--static-only", action="store_true", help="run only the static checks (any time of day)")
    args = ap.parse_args(argv)

    if not args.static_only and not nq.may_start(now_fn(), args.max_hours):
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
    static: dict[str, bool] = {}
    rc = 1
    try:
        with log.open("w", encoding="utf-8") as fh:
            static = run_static(wt, env, fh)
            bad = [name for name, ok in static.items() if not ok]
            if args.static_only:
                if bad:
                    print(f"\nstatic check failed: {', '.join(bad)} ({args.branch} {sha[:7]}). Log: {log}")
                    return 1
                print(f"\nstatic checks green: {args.branch} {sha[:7]}. Run the full gate before merging.")
                return 0
            if bad:
                print(f"\nstatic check failed: {', '.join(bad)}. The suite was not run.")
                raise _StaticRed
            proc = subprocess.Popen(cmd, cwd=wt, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, encoding="utf-8", errors="replace", bufsize=1)
            assert proc.stdout is not None
            for line in proc.stdout:
                sys.stdout.write(line)
                fh.write(line)
                if re.match(r"chunk \d+: ", line):
                    verdicts.append(line.strip())
            rc = proc.wait()
    except _StaticRed:
        rc = 1
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", str(wt)], cwd=ROOT, check=False)

    ok = rc == 0
    result = {"branch": args.branch, "sha": sha, "ok": ok, "exit": rc, "verdicts": verdicts, "static": static,
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
