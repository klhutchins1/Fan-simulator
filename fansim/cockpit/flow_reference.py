"""Which saved Stock CFD case the flow report compares against (gitignored pointer, §24)."""

from __future__ import annotations

import json
from pathlib import Path

from fansim.cockpit.stock_cache import STOCK_CACHE_DIR

REFERENCE_FILE = STOCK_CACHE_DIR / "flow_reference.json"


def set_reference(case_dir) -> None:
    REFERENCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    REFERENCE_FILE.write_text(json.dumps({"case_dir": str(Path(case_dir).resolve())}), encoding="utf-8")


def get_reference() -> Path | None:
    try:
        p = Path(json.loads(REFERENCE_FILE.read_text(encoding="utf-8"))["case_dir"])
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return p if p.is_dir() else None
