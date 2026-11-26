"""R3.8 validation page (`docs/VALIDATION.md`) and R2.1 prop C_P limit contract tests."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from fansim.validation import scoreboard as sb

ROOT = Path(__file__).resolve().parents[1]
VALIDATION_DOC = ROOT / "docs" / "VALIDATION.md"


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert VALIDATION_DOC.is_file(), "docs/VALIDATION.md is missing (R3.8)"
    return VALIDATION_DOC.read_text(encoding="utf-8")


def test_validation_doc_markdown_links_and_paths_resolve(doc_text: str):
    """Every markdown link and cited repo file path in docs/VALIDATION.md must exist."""
    md_links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", doc_text)
    assert len(md_links) >= 15, "docs/VALIDATION.md should link every surface to its audits"

    missing: list[str] = []
    for raw in md_links:
        target = raw.split("#", 1)[0].strip()
        if not target or target.startswith(("http://", "https://", "mailto:")):
            continue
        resolved = (VALIDATION_DOC.parent / target).resolve()
        if not resolved.exists():
            missing.append(f"markdown link {raw!r} -> {resolved}")

    # Also verify backticked repo-relative paths (`docs/...`, `validation/...`, `tests/...`, `fansim/...`).
    path_refs = re.findall(
        r"`((?:docs|validation|tests|fansim|scripts|config)/[A-Za-z0-9_./-]+\.(?:md|py|json|yaml|csv))`",
        doc_text,
    )
    for rel in path_refs:
        if not (ROOT / rel).is_file():
            missing.append(f"code-span path `{rel}`")

    assert not missing, "Broken references in docs/VALIDATION.md:\n" + "\n".join(missing)


def test_validation_doc_matches_generated_scoreboard(doc_text: str):
    """Every published-data number quoted in docs/VALIDATION.md must match RV-2 scoreboard."""
    rows = {r["id"]: r for r in sb.evaluate(sb.load_claims())}

    # Links to the machine-checked scoreboard and physics snapshot.
    assert "validation/scoreboard.md" in doc_text
    assert "tests/data/physics_snapshot.json" in doc_text

    # A12x25 CFD v5
    assert "59.8" in doc_text and "60.1" in doc_text
    assert f"{rows['a12x25.free_air']['error_pct']:+.1f} %".replace("-", "−") in doc_text or (
        f"{rows['a12x25.free_air']['error_pct']:+.1f} %" in doc_text
    )
    assert "28.0 Pa" in doc_text and "FAIL" in doc_text

    # FAN-01 (NOT JUDGED until RV-2 re-run lands)
    e7 = f"{rows['fan01.q_7pa']['error_pct']:+.1f} %"
    e64 = f"{rows['fan01.q_64pa']['error_pct']:+.1f} %"
    assert e7 in doc_text, f"FAN-01 7 Pa error {e7} missing from docs/VALIDATION.md"
    assert e64 in doc_text, f"FAN-01 64 Pa error {e64} missing from docs/VALIDATION.md"
    assert "NOT JUDGED" in doc_text

    # lt120 (R1.1b TRENDS)
    assert "+8.1 %" in doc_text and "6.85 Pa" in doc_text
    assert "+25.8 %" in doc_text and "13.71 Pa" in doc_text
    assert "TRENDS" in doc_text

    # Prop BEMT vs UIUC (live from scoreboard)
    for cid in (
        "bemt.apce_9x6.static_ct",
        "bemt.apce_9x6.static_cp",
        "bemt.apcsf_9x4.7.static_ct",
        "bemt.apcsf_9x4.7.static_cp",
    ):
        err = f"{rows[cid]['error_pct']:+.1f} %"
        assert err in doc_text or err.replace("-", "−") in doc_text, f"{cid} error {err} missing"

    sf_rms = f"{rows['bemt.apcsf_9x4.7.ct_j_rms']['ours']:.4f}"
    e_rms = f"{rows['bemt.apce_9x6.ct_j_rms']['ours']:.4f}"
    assert sf_rms in doc_text, f"APC SF C_T(J) RMS {sf_rms} missing"
    assert e_rms in doc_text, f"APC E C_T(J) RMS {e_rms} missing"
    assert "0.015" in doc_text


def test_validation_doc_applies_r21_mismatches_qa64_and_r27_labels(doc_text: str):
    """M1–M9, QA-64 wording, and the four frozen experimental surfaces must all hold."""
    # M1 & M3 & M5: Stock v3 55.7 vs 58.3 in cylinder-sections diagnostic rig; no wrapped-sections link.
    assert "55.7" in doc_text and "58.3" in doc_text
    assert "cylinder-sections diagnostic rig" in doc_text.lower()
    assert "2026-10-12-cylinder-sections.md" in doc_text
    assert "wrapped-sections" not in doc_text

    # M4: Assess screening mesh GCI ≈ 21 % (no stale ~3–5 %).
    assert "21 %" in doc_text
    assert "~3–5 %" not in doc_text and "~3–5%" not in doc_text

    # QA-64: never claim "within 8 %" across the three fans; lt120 is at its lowest measured load.
    assert "within 8 %" not in doc_text.lower()
    assert "within 10 %" in doc_text.lower()
    assert "lowest measured load" in doc_text.lower()

    # M7 & R2.7: all four frozen surfaces carry the standard experimental label.
    exp = "Experimental: not validated against published data"
    for heading in ("Propeller CFD", "Mixed-flow", "Volute", "CROR"):
        idx = doc_text.index(heading)
        section = doc_text[idx : idx + 900]
        assert exp in section, f"{heading} section missing standard experimental label"


def test_readme_and_cockpit_point_to_validation_doc():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "docs/VALIDATION.md" in readme
    assert "docs/validation/scoreboard.md" in readme
    assert "Stock recipe v3" in readme or "55.7 vs 58.3 CFM" in readme
    assert "Parametric Stock recipe v2:" not in readme

    home = (ROOT / "fansim" / "cockpit" / "home_tab.py").read_text(encoding="utf-8")
    assert "docs/VALIDATION.md" in home

    fan_ui = (ROOT / "fansim" / "cockpit" / "fan_tab_ui.py").read_text(encoding="utf-8")
    assert "docs/VALIDATION.md" in fan_ui
    assert "matches three published fans near free air" not in fan_ui


def test_r21_prop_bemt_honesty_labels_cp_limit():
    from fansim.propeller.honesty import PROP_BEMT_HONESTY

    low = PROP_BEMT_HONESTY.lower()
    assert "c_p" in low or "power" in low
    assert "21" in PROP_BEMT_HONESTY


def test_validation_doc_ships_in_release_export(tmp_path):
    from scripts import export_release as er

    excludes = er.read_excludes(ROOT / "RELEASE_EXCLUDE")
    out = tmp_path / "release"
    er.export(
        out,
        files=["docs/VALIDATION.md", "docs/validation/scoreboard.md"],
        excludes=excludes,
        root=ROOT,
    )
    assert (out / "docs" / "VALIDATION.md").is_file()
    assert (out / "docs" / "validation" / "scoreboard.md").is_file()
