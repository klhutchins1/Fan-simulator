"""Measure remaining fuse growth on this box (roadmap 27.1).

Runs a few isolated P builds with the Windows/Linux call hook and writes
logs/fuse_growth.jsonl. One build at a time. Does not enable FANSIM_FUSE_GUARD.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "docs" / "qa" / "fuse_growth" / "hook_win"
OUT = ROOT / "logs" / "fuse_growth.jsonl"
CALLS = ROOT / "logs" / "fuse_growth.calls.jsonl"
os.environ["FANSIM_MEMORY_TIER"] = "8gb"
os.environ["FUSE_CALL_LOG"] = str(CALLS)
os.environ["PYTHONPATH"] = str(HOOK) + os.pathsep + os.environ.get("PYTHONPATH", "")
sys.path.insert(0, str(HOOK))
sys.path.insert(0, str(ROOT))

from fansim.geometry.config import load_blade_params  # noqa: E402
from fansim.geometry.isolated import build_stl_isolated  # noqa: E402
from fansim.optimize.search_space import blade_to_flat  # noqa: E402

SMOOTH = dict(
    n_blades=7, stagger_root=26, stagger_mid=26, stagger_tip=22,
    chord_root=34, chord_mid=44, chord_tip=38, max_camber=0.05,
    sweep_mid=3, sweep_tip=5, lean_mid=14, lean_tip=26,
)


def _jobs():
    stock = blade_to_flat(load_blade_params("config/problems/a12x25_reference.yaml"))
    return [
        ("open_9b", {**SMOOTH, "n_blades": 9}, {}),
        ("ring_9b", {**SMOOTH, "n_blades": 9, "shroud_thick_mm": 1.6, "shroud_height_frac": 0.7}, {}),
        ("ring_11b", {**SMOOTH, "n_blades": 11, "shroud_thick_mm": 1.6, "shroud_height_frac": 0.7}, {}),
        ("stock_v3", stock, {}),
    ]


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    done = {json.loads(l)["id"] for l in OUT.open(encoding="utf-8")} if OUT.exists() else set()
    for name, flat, feat in _jobs():
        if name in done:
            print("skip", name, flush=True)
            continue
        n0 = sum(1 for _ in CALLS.open(encoding="utf-8")) if CALLS.exists() else 0
        t0 = time.monotonic()
        rec: dict = {"id": name, "n_blades": flat.get("n_blades"),
                     "shroud_thick_mm": float(flat.get("shroud_thick_mm") or 0)}
        stl = Path(tempfile.mkdtemp()) / f"{name}.stl"
        try:
            build_stl_isolated(flat, feat, stl, timeout=900.0, preview=False)
            rec["outcome"] = "OK"
        except Exception as exc:  # noqa: BLE001
            rec["outcome"] = "ERR"
            rec["err"] = f"{type(exc).__name__}: {exc}"[:400]
        rec["s"] = round(time.monotonic() - t0, 1)
        rec["events"] = (
            [json.loads(l) for l in list(CALLS.open(encoding="utf-8"))[n0:]]
            if CALLS.exists() else []
        )
        with OUT.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
        print(name, rec["outcome"], rec["s"], flush=True)
        try:
            stl.unlink(missing_ok=True)
        except OSError:
            pass
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
