"""BEMT vs PropSpec datasheet thrust/power (affinity-scaled). No Docker."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from fansim.prop_spec import get_prop_spec, prop_spec_names  # noqa: E402
from fansim.propeller.calibrate import bemt_datasheet_report  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare BEMT static thrust to PropSpec datasheet")
    ap.add_argument("--spec", default="fpv_5inch")
    ap.add_argument("--rpm", type=float, default=None, help="default: spec.ref_rpm")
    ap.add_argument("--all", action="store_true", help="run every registered prop spec")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    keys = prop_spec_names() if args.all else [args.spec]
    rows = []
    for key in keys:
        spec = get_prop_spec(key)
        rep = bemt_datasheet_report(spec, rpm=args.rpm)
        rep["spec"] = key
        rows.append(rep)
        d = rep["datasheet"]
        ratio = d.get("thrust_ratio")
        print(
            f"{key}: BEMT {rep['thrust_g']:.0f} g @ {rep['rpm']:.0f} RPM | "
            f"ref_scaled {d.get('thrust_ref_scaled_g')} g | "
            f"ratio {ratio if ratio is None else round(ratio, 3)} | "
            f"within_2x={d.get('within_2x')}"
        )

    payload = {"rows": rows}
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    else:
        print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
