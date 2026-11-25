"""Full cockpit Assess of the QA bot's BEM-screen top 5 (runs/bem_screen_top5, trials 9501-9505).

The BEM screen (handoff/2026-10-08_fan-sim-qa, screen/README.md) ranked them only 2-5 % below
Stock under the project objective; this is the CFD check of whether that ranking means anything.
Same settings as every other full Assess (scripts/screen_rank_audit.run_full). Resumable: finished
designs are skipped. Scores are written back into each design.json (previous kept under
``extra.rescored``) so the cockpit shows them.

    uv run python scripts/assess_bem_top5.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

import refresh_stale_designs as rsd
import screen_rank_audit as sra

SRC = ROOT / "runs" / "bem_screen_top5" / "cockpit_assess"
REPORT = sra.OUT / "bem_top5.json"


def main() -> int:
    rows = {}
    for jf in sorted(SRC.glob("design_*/design.json")):
        d = json.loads(jf.read_text(encoding="utf-8"))
        name = f"bem_{d['trial']}"
        r = sra.run_full(name, d["params"])
        extra = d.get("extra") or {}
        prev = (extra.get("rescored") or {}).get("previous", {}).get("objectives")
        r["bem"] = {"rank": extra.get("bem_rank"), "id": extra.get("bem_id"),
                    "objectives": prev or d.get("objectives")}
        res = rsd.finished(sra.OUT / name / "full")
        if extra.get("rescored"):
            r["applied"] = "already applied"
        else:
            r["applied"] = rsd.apply(jf, sra.OUT / name / "full", res) if res else "no result"
        rows[name] = r
        print(json.dumps({name: {k: r.get(k) for k in
                                 ("feasible", "cfm_free", "cfm_load", "efficiency", "wall_s")}}),
              flush=True)
    stock = sra._read(sra.OUT / "stock" / "full" / "result.json")
    REPORT.write_text(json.dumps({"stock_full": stock, "designs": rows}, indent=2),
                      encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
