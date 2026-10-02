"""Long-run chain (2026-10-02): volute fine mesh, prop mesh ladder, prop entrainment boundaries.

Run all stages, or only those whose name contains a given word:
  uv run python scripts/overnight_wrapup.py entrainment

Each stage pilots first and logs its estimate, then runs in full. Results:
  docs/validation/audits/direction_cfd_volute_fine.json
  docs/validation/audits/prop_cfd_apcsf_9x4.7_L5.json
Run detached so tool time limits cannot kill it:
  uv run python scripts/overnight_wrapup.py > runs/overnight_wrapup.log 2>&1
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = [sys.executable]

STAGES = [
    ("volute fine mesh (base 4 mm)", "scripts/audit_archetype_direction_cfd.py",
     ["--machine", "volute", "--base-cell", "0.004", "--tag", "fine",
      "--out", "runs/audit_archetype_direction_fine"],
     "runs/audit_archetype_direction_fine/volute/pilot.json"),
    ("prop APC 9x4.7 surface level 5, designed only", "scripts/audit_prop_cfd.py",
     ["--surf-level", "5", "--designed-only", "--tag", "L5", "--out", "runs/audit_prop_cfd_L5"],
     "runs/audit_prop_cfd_L5/pilot/pilot.json"),
    ("prop APC 9x4.7 entrainment boundaries (level 4), designed only", "scripts/audit_prop_cfd.py",
     ["--bc", "entrain", "--designed-only", "--tag", "entrain", "--out", "runs/audit_prop_cfd_entrain"],
     "runs/audit_prop_cfd_entrain/pilot/pilot.json"),
]


def log(msg: str) -> None:
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def run(script: str, args: list[str]) -> int:
    return subprocess.call(PY + [str(ROOT / script)] + args, cwd=ROOT)


def main(argv: list[str] | None = None) -> int:
    """Run every stage, or only those whose name contains one of the given words."""
    words = [w.lower() for w in (sys.argv[1:] if argv is None else argv)]
    stages = [st for st in STAGES if not words or any(w in st[0].lower() for w in words)]
    worst = 0
    for name, script, args, pilot_json in stages:
        log(f"=== {name}: pilot")
        rc = run(script, args + ["--pilot"])
        try:
            est = json.loads((ROOT / pilot_json).read_text(encoding="utf-8"))
            log(f"pilot estimate: {est.get('estimated_full_run_eta')} "
                f"({est.get('cells')} cells, {est.get('sec_per_iter'):.2f} s/iter)")
        except (OSError, ValueError, TypeError) as exc:
            log(f"pilot estimate unavailable ({exc}); pilot rc={rc}")
        log(f"=== {name}: full run")
        t0 = time.time()
        rc = run(script, args)
        log(f"=== {name}: done rc={rc} in {(time.time() - t0) / 60:.0f} min")
        worst = max(worst, rc)
    log("ALL STAGES DONE")
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
