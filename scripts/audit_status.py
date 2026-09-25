"""Show which audited physics units need re-auditing.

Usage:
    uv run python scripts/audit_status.py                 # table of registered units
    uv run python scripts/audit_status.py --unregistered  # also list physics code with no unit
    uv run python scripts/audit_status.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fansim.audit.fingerprint import FingerprintError, fingerprint_unit  # noqa: E402
from fansim.audit.registry import load_registry  # noqa: E402
from fansim.audit.status import State, classify, find_unregistered, load_ledger  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Physics audit status")
    ap.add_argument("--unregistered", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    reg = load_registry()
    fps = {}
    missing = {}
    for uid, u in reg.units.items():
        try:
            fps[uid] = fingerprint_unit(u)
        except FingerprintError as e:
            fps[uid] = ""
            missing[uid] = str(e)
    states = classify(reg, load_ledger(), fps)
    loose = find_unregistered(reg)
    if args.json:
        output = {"units": {k: v.value for k, v in states.items() if k not in missing}, "unregistered": loose}
        if missing:
            output["missing"] = missing
        print(json.dumps(output, indent=2))
        return 1 if missing else 0
    for uid in sorted(states):
        if uid in missing:
            print(f"{'MISSING':<9} {uid}  ({missing[uid]})")
        else:
            print(f"{states[uid].value:<9} {uid}")
    counts = {s.value: sum(1 for uid, v in states.items() if v is s and uid not in missing) for s in State}
    count_items = [(k, counts[k]) for k in ["PROVEN", "CHANGED", "AFFECTED", "NEW"]]
    if missing:
        count_items.append(("MISSING", len(missing)))
    print("\n" + "  ".join(f"{k}={v}" for k, v in count_items) + f"  UNREGISTERED={len(loose)}")
    if args.unregistered:
        print("\nUnregistered physics code:")
        for name in loose:
            print(f"  {name}")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
