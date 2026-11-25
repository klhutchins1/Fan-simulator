"""RV-1 physics snapshot: CI fails when a number the physics computes moves.

Rules are pre-registered in docs/validation/audits/2026-11-24-physics-snapshot-prereg.md.
Regenerate (only with an audit file that explains the change):
    python scripts/physics_snapshot.py --write --reason docs/validation/audits/<file>.md
"""

from __future__ import annotations

from pathlib import Path

import pytest

from fansim.validation import physics_snapshot as ps

ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------- the compare rules (pre-registered)

def _snap(kind, values):
    return {"cases": {"c": {"kind": kind, "values": values}}}


def test_closed_form_tolerance_is_1e9_relative_with_floor_1():
    base = _snap("closed", {"x": 1000.0, "y": 0.001})
    assert ps.compare(base, _snap("closed", {"x": 1000.0 + 0.9e-6, "y": 0.001 + 0.9e-9})) == []
    bad = ps.compare(base, _snap("closed", {"x": 1000.0 + 1.1e-6, "y": 0.001}))
    assert len(bad) == 1 and "c.x" in bad[0]
    assert ps.compare(base, _snap("closed", {"x": 1000.0, "y": 0.001 + 1.1e-9})) != []


def test_iterative_series_scale_is_the_largest_value_in_the_series():
    # near-zero dp at free delivery must not be judged by relative error
    base = _snap("iter", {"dp": [40.0, 20.0, 0.0001]})
    assert ps.compare(base, _snap("iter", {"dp": [40.0, 20.0, 0.0001 + 39e-6]})) == []
    assert ps.compare(base, _snap("iter", {"dp": [40.0, 20.0, 0.0001 + 41e-6]})) != []


def test_iterative_scalar_tolerance_is_1e6_relative_with_floor_1():
    base = _snap("iter", {"free": 60.4})
    assert ps.compare(base, _snap("iter", {"free": 60.4 + 60.4e-6 * 0.9})) == []
    assert ps.compare(base, _snap("iter", {"free": 60.4 + 60.4e-6 * 1.1})) != []


def test_bools_strings_and_shapes_match_exactly():
    base = _snap("iter", {"ok": True, "status": "crossed", "s": [1.0, 2.0]})
    assert ps.compare(base, _snap("iter", {"ok": False, "status": "crossed", "s": [1.0, 2.0]})) != []
    assert ps.compare(base, _snap("iter", {"ok": True, "status": "no_rise", "s": [1.0, 2.0]})) != []
    assert ps.compare(base, _snap("iter", {"ok": True, "status": "crossed", "s": [1.0]})) != []
    assert ps.compare(base, _snap("iter", {"ok": True, "status": "crossed", "s": [1.0, 2.0], "new": 1.0})) != []
    assert ps.compare(base, {"cases": {}}) != []


def test_nan_and_inf_compare_by_identity():
    base = _snap("closed", {"sf": float("inf"), "eta": None})
    assert ps.compare(base, _snap("closed", {"sf": float("inf"), "eta": None})) == []
    assert ps.compare(base, _snap("closed", {"sf": 3.0, "eta": None})) != []
    assert ps.compare(base, _snap("closed", {"sf": float("inf"), "eta": 0.5})) != []


def test_every_case_has_a_known_kind():
    for cid, case in ps.compute()["cases"].items():
        assert case["kind"] in ("closed", "iter"), cid


# ---------------------------------------------------------------- the pin

@pytest.fixture(scope="module")
def committed():
    assert ps.SNAPSHOT_PATH.is_file(), f"missing {ps.SNAPSHOT_PATH}; run scripts/physics_snapshot.py --write"
    return ps.load()


def test_snapshot_reason_is_a_committed_audit_file(committed):
    reason = committed["reason"]
    assert reason.startswith("docs/validation/audits/") and reason.endswith(".md")
    assert (ROOT / reason).is_file(), f"snapshot reason {reason} does not exist"


def test_physics_matches_the_committed_snapshot(committed):
    diffs = ps.compare(committed, ps.compute())
    assert not diffs, (
        "physics output moved (RV-1). If this is intended, write an audit file and run\n"
        "  python scripts/physics_snapshot.py --write --reason docs/validation/audits/<file>.md\n"
        + "\n".join(diffs[:40])
    )
