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

from fansim.audit.fingerprint import fingerprint_unit  # noqa: E402
from fansim.audit.registry import load_registry  # noqa: E402
from fansim.audit.status import State, classify, find_unregistered, load_ledger  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Physics audit status")
    ap.add_argument("--unregistered", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    reg = load_registry()
    fps = {uid: fingerprint_unit(u) for uid, u in reg.units.items()}
    states = classify(reg, load_ledger(), fps)
    loose = find_unregistered(reg)
    if args.json:
        print(json.dumps({"units": {k: v.value for k, v in states.items()},
                          "unregistered": loose}, indent=2))
        return 0
    for uid in sorted(states):
        print(f"{states[uid].value:<9} {uid}")
    counts = {s.value: sum(1 for v in states.values() if v is s) for s in State}
    print("\n" + "  ".join(f"{k}={v}" for k, v in counts.items()) + f"  UNREGISTERED={len(loose)}")
    if args.unregistered:
        print("\nUnregistered physics code:")
        for name in loose:
            print(f"  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
