"""R0.3 C3: v4 27.3d cases must not flip verdicts across Stock's five meshes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fansim.cfd.flow_report import FlowMetrics
from fansim.cfd.flow_verdicts import judge

ROOT = Path(__file__).resolve().parents[1]
STOCK = ROOT / "runs" / "stock_flow_mesh_repeats"
DESIGNS = ROOT / "runs" / "design_flow_mesh_repeats"
MESHES = ("m1", "m2", "m3", "m4", "m5")
ROWS = ("direction", "push", "spin", "dead")


def _metrics(case: Path) -> FlowMetrics:
    blob = json.loads((case / "flow_report.json").read_text(encoding="utf-8"))
    assert blob.get("version") == 4, case
    return FlowMetrics.from_dict(blob["metrics"])


@pytest.mark.skipif(not (STOCK / "m1" / "flow_report.json").is_file(),
                    reason="Stock mesh-repeat cases are not on this box")
@pytest.mark.xfail(strict=True, reason="C3 FAIL: √2×Stock-2σ still flips; see 2026-10-17-too-close-to-call-prereg.md")
@pytest.mark.parametrize("design_id", ["9604", "9610"])
def test_no_verdict_flips_across_meshes(design_id):
    stocks = [_metrics(STOCK / m) for m in MESHES]
    designs = [_metrics(DESIGNS / design_id / m) for m in MESHES]
    by_row: dict[str, set[str]] = {k: set() for k in ROWS}
    for d, s in zip(designs, stocks):
        for row in judge(d, s):
            if row.key in by_row:
                by_row[row.key].add(row.status)
    flipped = {k: v for k, v in by_row.items() if len(v) > 1}
    assert flipped == {}, f"{design_id} flipped: {flipped}"
