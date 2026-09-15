# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Launch the Fan-simulator design cockpit.

Usage:
    uv run --extra viz --extra optim python scripts/cockpit.py --run runs/opt_run1 [--port 8080]

Binds 127.0.0.1 by default (local UI). Pass --host 0.0.0.0 only if you intend LAN access.

Add --reload for DEV MODE: the server runs as a child process and AUTO-RESTARTS whenever any
fansim/ or validation/ source file changes, so you never have to restart by hand to pick up code
edits. The browser reconnects on its own after each restart (a brief blip). Without --reload the
server runs once (production) — restart manually to load new code.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

WATCH_DIRS = ("fansim", "validation")   # source trees whose edits should trigger a restart


def _snapshot() -> dict[str, float]:
    """Map every watched .py file -> its mtime (for change detection)."""
    snap: dict[str, float] = {}
    for d in WATCH_DIRS:
        for p in (ROOT / d).rglob("*.py"):
            try:
                snap[str(p)] = p.stat().st_mtime
            except OSError:
                pass
    return snap


def _run_with_reload(args) -> int:
    """Supervise a child server, restarting it when watched source changes (pure-Python, no deps)."""
    child = [sys.executable, str(Path(__file__).resolve()),
             "--run", args.run, "--port", str(args.port),
             "--host", args.host]
    if args.study_name:
        child += ["--study-name", args.study_name]

    # Unique tag for THIS supervisor's CFD containers so a restart reaps only its own child's
    # containers (never another optimization/cockpit on the same machine). Inherited by the child
    # cockpit and every eval-worker/docker it spawns (fansim.cfd.runner._label_args reads it).
    session = f"cockpit-{os.getpid()}"

    def _spawn():
        return subprocess.Popen(child, env={**os.environ, "FANSIM_CFD_SESSION": session})

    def _reap_containers():
        """docker kill any CFD containers this supervisor's children left running. Containers outlive
        a killed worker (the Docker daemon owns them), so this is what actually stops orphaned CFD."""
        try:
            out = subprocess.run(
                ["docker", "ps", "-q", "--filter", f"label=fansim_cfd_session={session}"],
                capture_output=True, text=True, timeout=20)
            ids = out.stdout.split()
            if ids:
                subprocess.run(["docker", "kill", *ids], capture_output=True, text=True, timeout=30)
                print(f"[reload] reaped {len(ids)} orphaned CFD container(s)", flush=True)
        except Exception as exc:  # noqa: BLE001 - cleanup is best-effort
            print(f"[reload] container reap skipped: {exc}", flush=True)

    def _stop(proc):
        """Kill the child cockpit AND its whole subprocess tree (eval/build workers + docker clients),
        then reap the CFD containers those workers left running. The old version only terminated the
        child, orphaning in-flight CFD -> the workers + containers saturated the machine, compounding
        across every restart."""
        if sys.platform == "win32":
            # /T kills the entire process tree (workers + docker CLI children); /F forces it.
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                           capture_output=True, text=True)
        else:
            proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        _reap_containers()

    print(f"[reload] DEV MODE — watching {', '.join(WATCH_DIRS)}/ ; the server auto-restarts on edits. "
          "Ctrl+C to stop.", flush=True)
    proc = _spawn()
    last = _snapshot()
    try:
        while True:
            time.sleep(1.0)
            if proc.poll() is not None:                 # child exited on its own — relaunch
                print("[reload] server exited; relaunching…", flush=True)
                _reap_containers()                       # a crashed child can leave CFD running too
                proc, last = _spawn(), _snapshot()
                continue
            cur = _snapshot()
            if cur != last:
                changed = [p for p, m in cur.items() if last.get(p) != m] + \
                          [p for p in last if p not in cur]
                rel = ", ".join(Path(c).relative_to(ROOT).as_posix() for c in changed[:3])
                print(f"[reload] change ({rel}{'…' if len(changed) > 3 else ''}) — restarting server",
                      flush=True)
                _stop(proc)
                time.sleep(0.4)                          # let the OS release the port
                proc, last = _spawn(), _snapshot()
    except KeyboardInterrupt:
        print("\n[reload] stopping.", flush=True)
        _stop(proc)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="fansim design cockpit")
    ap.add_argument("--run", default="runs/opt_run1", help="optimization run directory")
    ap.add_argument("--study-name", default=None)
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument(
        "--host",
        default="127.0.0.1",
        help="bind address (default 127.0.0.1; use 0.0.0.0 only if you intend LAN access)",
    )
    ap.add_argument("--reload", action="store_true",
                    help="dev mode: auto-restart the server when fansim/ or validation/ source changes")
    args = ap.parse_args()

    if args.reload:
        return _run_with_reload(args)

    from fansim.cockpit.app import build_server
    server = build_server(args.run, args.study_name)
    server.start(port=args.port, host=args.host, open_browser=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
