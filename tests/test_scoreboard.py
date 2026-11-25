"""RV-2 validation scoreboard: published-data claims are generated and re-judged, not typed.

Regenerate the page after a deliberate change:  python scripts/scoreboard.py --write
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

from fansim.validation import scoreboard as sb

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def rows():
    return sb.evaluate(sb.load_claims())


def test_every_claim_cites_files_that_exist():
    for c in sb.load_claims():
        tol = c.get("tolerance")
        if tol:
            src = tol["source"].split(" ")[0]
            assert (ROOT / src).is_file(), f"{c['id']}: tolerance source {src} missing"
        for side in ("published", "ours"):
            spec = c[side]
            if spec.get("kind") == "data":
                assert (ROOT / spec["file"]).is_file(), f"{c['id']}: {spec['file']} missing"
            if spec.get("kind") == "recorded":
                path, _, line = spec["where"].partition("#L")
                text = (ROOT / path).read_text(encoding="utf-8").splitlines()
                assert spec["where_text"] in text[int(line) - 1], (
                    f"{c['id']}: {spec['where']} does not show {spec['where_text']!r}")


def test_recomputed_verdicts_match_the_recorded_ones(rows):
    """A code or data change that flips a live/data claim fails here."""
    for r in rows:
        if r["kind"] in ("live", "data"):
            assert r["verdict"] == r["recorded_verdict"], (r["id"], r["verdict"], r["error_text"])


def test_rows_without_a_preregistered_tolerance_are_not_judged(rows):
    for r in rows:
        if r["tolerance"] is None:
            assert r["verdict"] == "NOT JUDGED", r["id"]


def test_judge_rules():
    assert sb.judge(66.0, 60.0, {"rel": 0.10}) == "PASS"
    assert sb.judge(66.1, 60.0, {"rel": 0.10}) == "FAIL"
    assert sb.judge(27.9, 22.9, {"abs": 5.0}) == "PASS"
    assert sb.judge(28.0, 22.9, {"abs": 5.0}) == "FAIL"
    assert sb.judge(0.015, None, {"max": 0.015}) == "PASS"
    assert sb.judge(0.0151, None, {"max": 0.015}) == "FAIL"
    assert sb.judge(1.0, 1.0, None) == "NOT JUDGED"


def test_committed_page_is_current(rows):
    page = (ROOT / sb.PAGE_PATH).read_text(encoding="utf-8")
    assert page == sb.render(rows), "docs/validation/scoreboard.md is stale: python scripts/scoreboard.py --write"


def _audit_helpers():
    spec = importlib.util.spec_from_file_location(
        "bemt_audit", ROOT / "tests" / "audit" / "test_prop_bemt_audit.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("prefix", ["apce_9x6", "apcsf_9x4.7"])
def test_uiuc_numbers_equal_the_audit_procedure(prefix):
    """The scoreboard's copy of the Audit #3 procedure must not drift from the audit test."""
    audit = _audit_helpers()
    e_ct, e_cp = audit._static_errors(prefix)
    s = sb.uiuc_static(prefix)
    assert s["ct_ours"] / s["ct_pub"] - 1.0 == pytest.approx(e_ct, abs=1e-12)
    assert s["cp_ours"] / s["cp_pub"] - 1.0 == pytest.approx(e_cp, abs=1e-12)
    worst = max(audit._ct_rms(prefix, f) for f in audit._sweep_files(prefix))
    assert sb.uiuc_ct_rms(prefix) == pytest.approx(worst, abs=1e-12)


def test_readme_fan01_numbers_match_the_scoreboard(rows):
    """README quotes FAN-01; the scoreboard computes it from the committed result file."""
    by_id = {r["id"]: r for r in rows}
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    m = re.search(r"FAN-01[^\n]*?within \*\*\+([0-9.]+)% / \+([0-9.]+)%", readme)
    assert m, "README FAN-01 line not found"
    assert float(m.group(1)) == pytest.approx(by_id["fan01.q_7pa"]["error_pct"], abs=0.05)
    assert float(m.group(2)) == pytest.approx(by_id["fan01.q_64pa"]["error_pct"], abs=0.05)
