"""R4.3 v0.1.0 release notes contract tests (links, scoreboard sync, honesty invariants)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from fansim.validation import scoreboard as sb

ROOT = Path(__file__).resolve().parents[1]
NOTES_PATH = ROOT / "docs" / "release" / "RELEASE_NOTES_v0.1.0.md"


@pytest.fixture(scope="module")
def notes_text() -> str:
    assert NOTES_PATH.is_file(), "docs/release/RELEASE_NOTES_v0.1.0.md is missing (R4.3)"
    return NOTES_PATH.read_text(encoding="utf-8")


def test_release_notes_links_resolve(notes_text: str):
    md_links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", notes_text)
    assert len(md_links) >= 6, "Release notes should link README, VALIDATION, scoreboard, LICENSE, THIRD_PARTY"

    missing: list[str] = []
    for raw in md_links:
        target = raw.split("#", 1)[0].strip()
        if not target or target.startswith(("http://", "https://", "mailto:")):
            continue
        resolved = (NOTES_PATH.parent / target).resolve()
        if not resolved.exists():
            missing.append(f"markdown link {raw!r} -> {resolved}")

    assert not missing, "Broken links in RELEASE_NOTES_v0.1.0.md:\n" + "\n".join(missing)


def test_release_notes_numbers_match_scoreboard(notes_text: str):
    rows = {r["id"]: r for r in sb.evaluate(sb.load_claims())}

    assert "VALIDATION.md" in notes_text
    assert "scoreboard.md" in notes_text

    # A12x25
    assert "59.8" in notes_text and "60.1" in notes_text
    assert "−0.5 %" in notes_text or "-0.5 %" in notes_text
    assert "28.0 Pa" in notes_text and "FAIL" in notes_text

    # lt120
    assert "6.85 Pa" in notes_text and "+8.1 %" in notes_text
    assert "13.71 Pa" in notes_text and "+25.8 %" in notes_text
    assert "TRENDS" in notes_text

    # FAN-01
    e7 = f"{rows['fan01.q_7pa']['error_pct']:+.1f} %"
    e64 = f"{rows['fan01.q_64pa']['error_pct']:+.1f} %"
    assert e7 in notes_text and e64 in notes_text
    assert "NOT JUDGED" in notes_text

    # Prop BEMT
    for cid in (
        "bemt.apce_9x6.static_ct",
        "bemt.apce_9x6.static_cp",
        "bemt.apcsf_9x4.7.static_ct",
        "bemt.apcsf_9x4.7.static_cp",
    ):
        err = f"{rows[cid]['error_pct']:+.1f} %"
        assert err in notes_text or err.replace("-", "−") in notes_text, f"{cid} {err} missing"

    sf_rms = f"{rows['bemt.apcsf_9x4.7.ct_j_rms']['ours']:.4f}"
    assert sf_rms in notes_text and "0.015" in notes_text


def test_release_notes_honesty_and_no_overstated_claims(notes_text: str):
    low = notes_text.lower()

    # Forbidden overstated / stale claims
    for banned in ("within 8 %", "~2×", "~2x", "~0.6×", "~0.6x", "~3–5 %", "~3–5%", "honest mrf", "honest cfd"):
        assert banned not in low, f"Overstated/stale phrase {banned!r} found in release notes"

    # Required honesty statements
    assert "55.7" in notes_text and "58.3" in notes_text
    assert "cylinder-sections diagnostic rig" in low
    assert "21 %" in notes_text
    assert "resonance check, not flutter" in low
    assert "not validated" in low
    assert "0.95" in notes_text or "5 %" in notes_text

    # All four frozen experimental surfaces explicitly listed with the standard label
    assert "Experimental: not validated against published data" in notes_text
    for surface in ("Propeller CFD", "Mixed-flow", "Volute", "CROR"):
        assert surface in notes_text, f"{surface} missing from release notes"

    # Licensing & install basics
    assert "MIT" in notes_text
    assert "THIRD_PARTY.md" in notes_text
    assert "3.12" in notes_text
    assert "opencfd/openfoam-default:2406" in notes_text


def test_release_notes_audit_unit_count_matches_registry(notes_text: str):
    from fansim.audit.registry import load_registry

    n_units = len(load_registry().units)
    assert f"{n_units}-unit physics audit ledger" in notes_text


def test_readme_commands_reference_live_scripts_and_github_url():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "<the GitHub URL>" not in readme
    assert "https://github.com/klhutchins1/Fan-simulator" in readme
    for script in re.findall(r"scripts/([A-Za-z0-9_]+\.py)", readme):
        assert (ROOT / "scripts" / script).is_file(), f"README references missing scripts/{script}"


def test_release_notes_ships_in_release_export(tmp_path):
    from scripts import export_release as er

    excludes = er.read_excludes(ROOT / "RELEASE_EXCLUDE")
    out = tmp_path / "release"
    er.export(
        out,
        files=["docs/release/RELEASE_NOTES_v0.1.0.md"],
        excludes=excludes,
        root=ROOT,
    )
    assert (out / "docs" / "release" / "RELEASE_NOTES_v0.1.0.md").is_file()
