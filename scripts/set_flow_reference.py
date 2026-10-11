"""Point the flow report at a saved Stock Assess case.

    .venv/Scripts/python.exe scripts/set_flow_reference.py runs/screen_rank_audit/stock_hubclip/full
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fansim.cfd.flow_report_case import load_or_compute_metrics  # noqa: E402
from fansim.cockpit.flow_reference import REFERENCE_FILE, set_reference  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    case = Path(argv[0])
    m = load_or_compute_metrics(case)  # fails loudly if the case has no usable fields
    set_reference(case)
    print(f"reference -> {case.resolve()} ({REFERENCE_FILE})")
    print(m.to_dict())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
