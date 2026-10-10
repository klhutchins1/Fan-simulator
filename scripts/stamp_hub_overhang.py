"""Stamp each saved fan design with how far its built blade reached below the hub face.

One-off migration for the hub-face clip (2026-10-09): scores computed before the rule describe
blades that may have hung below the hub's motor face. The cockpit flags those "needs re-run (blade
below hub)". Its quick section-point estimate misses the loft's realised chords on 'measured'
designs (t9015: 0.0 estimated vs 0.98 mm built), so this builds the real blade solid once per
design and writes ``extra.hub_overhang_mm`` (exact). Skips designs already stamped or re-scored
under the rule (``extra.hub_clip``).

    uv run python scripts/stamp_hub_overhang.py
"""

from __future__ import annotations

import copy
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    from fansim.geometry.blade import _hub_axial_range, build_blade_solid
    from fansim.optimize.search_space import blade_from_flat

    for jf in sorted((ROOT / "runs").glob("*/cockpit_assess/design_*/design.json")):
        d = json.loads(jf.read_text(encoding="utf-8"))
        extra = d.setdefault("extra", {})
        if extra.get("hub_clip") or extra.get("hub_overhang_mm") is not None:
            continue
        try:
            p = blade_from_flat(d.get("params") or {})
        except Exception as exc:  # noqa: BLE001 — not an axial flat dict
            print(f"skip {jf.parent.name}: {exc}", flush=True)
            continue
        raw = copy.copy(p)
        raw.clip_below_hub = False
        over = max(0.0, _hub_axial_range(p)[0] - float(build_blade_solid(raw).BoundingBox().zmin))
        extra["hub_overhang_mm"] = round(over, 3)
        jf.write_text(json.dumps(d, indent=2), encoding="utf-8")
        print(f"{jf.parents[2].name}/{jf.parent.name}: {over:.2f} mm", flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
