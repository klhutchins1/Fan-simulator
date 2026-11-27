"""25.10 cheap BEM near-stall flag. Thresholds frozen in docs/qa/notes/near-stall-flag-prereg.md."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from fansim.geometry.config import load_blade_params
from fansim.optimize.near_stall import (
    DF_LIMIT,
    STALL_MARGIN_DEG,
    near_stall_caption,
    near_stall_report,
)


def _stock():
    return load_blade_params("config/problems/a12x25_reference.yaml")


def test_thresholds_match_the_prereg():
    assert STALL_MARGIN_DEG == 0.0
    assert DF_LIMIT == pytest.approx(0.60)


def test_stock_on_the_case_hose_is_not_flagged():
    r = near_stall_report(_stock(), rpm=2000.0, load_pa=8.0)
    assert r.flagged is False
    assert near_stall_caption(r) == ""


def test_stock_past_shutoff_is_flagged():
    r = near_stall_report(_stock(), rpm=2000.0, load_pa=40.0)
    assert r.flagged is True
    assert r.rule in ("incidence", "no_intersect", "lieblein")
    assert "near stall" in near_stall_caption(r)


R3 = Path("handoff/2026-10-09_from-qa-2/screen_r3/designs")


@pytest.mark.skipif(not R3.is_dir(), reason="handoff/ omitted from public export")
@pytest.mark.parametrize(
    "stem, expect",
    [
        ("10_S01136", True),   # 9610 — Q3 blind spot
        ("04_S03681", False),  # 9604
        ("08_S01417", False),  # 9608
    ],
)
def test_q3_holdout_9610_vs_healthy_neighbours(stem, expect):
    r = near_stall_report(load_blade_params(R3 / f"{stem}.blade.yaml"), rpm=2000.0, load_pa=8.0)
    assert r.flagged is expect


@pytest.mark.skipif(not R3.is_dir(), reason="handoff/ omitted from public export")
def test_holdout_9613_also_flags_on_incidence():
    """Prereg hoped 9613 would stay quiet. BEM incidence is past stall; recorded MIXED."""
    r = near_stall_report(load_blade_params(R3 / "13_S02977.blade.yaml"), rpm=2000.0, load_pa=8.0)
    assert r.flagged is True
    assert r.rule == "incidence"


def test_t9005_on_the_case_hose_is_not_flagged():
    import csv
    import json

    from fansim.optimize.search_space import blade_from_flat

    path = Path("handoff/2026-10-09_to-qa-2/cfd_designs.csv")
    if not path.is_file():
        pytest.skip("t9005 flat not in tree")
    flat = None
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["design_id"] == "t9005":
                flat = json.loads(row["flat"])
                break
    if flat is None:
        pytest.skip("t9005 row missing")
    r = near_stall_report(blade_from_flat(flat), rpm=2000.0, load_pa=8.0)
    assert r.flagged is False


def test_paddle_on_the_case_hose_is_flagged():
    p = copy.deepcopy(_stock())
    for s in p.stations:
        s.stagger_deg = 89.0
    r = near_stall_report(p, rpm=2000.0, load_pa=8.0)
    assert r.flagged is True
