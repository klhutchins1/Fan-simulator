"""Run the pre-registered flow-report checks on saved cases (no CFD; reconstructs if needed)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fansim.cfd.flow_report_case import load_or_compute_metrics  # noqa: E402
from fansim.cfd.flow_verdicts import judge, overall_line  # noqa: E402

import os  # noqa: E402

# runs/ is gitignored and lives in the main checkout; a worktree can point at it with FANSIM_RUNS.
RUNS = Path(os.environ.get("FANSIM_RUNS", ROOT / "runs")) / "screen_rank_audit"
REF = RUNS / "stock_hubclip" / "full"
CASES = {"stock_self": REF, "stock_prev": RUNS / "stock" / "full",
         "9610": RUNS / "r3_9610" / "full", "t9005": RUNS / "t9005" / "full",
         "9604": RUNS / "r3_9604" / "full"}


def main() -> int:
    ref = load_or_compute_metrics(REF)
    print(f"F0 reference mean exit Uz = {ref.mean_uz_exit:+.3f} m/s ({'PASS' if ref.mean_uz_exit > 0 else 'FAIL'})")
    out = {"reference": ref.to_dict()}
    for name, case in CASES.items():
        m = load_or_compute_metrics(case)
        rows = judge(m, ref)
        out[name] = {"metrics": m.to_dict(),
                     "rows": [{"key": r.key, "status": r.status, "text": r.text, "bands": r.bands}
                              for r in rows],
                     "overall": overall_line(rows, compared=True)}
        print(f"{name:11s} " + " ".join(f"{r.key}={r.status}" for r in rows) + " | " + out[name]["overall"])
    (RUNS / "flow_report_checks.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
