"""R1.10 G3 / QA-57 / R2.4: Mixed and Volute copy is not 'honest MRF'."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIXED = ROOT / "fansim" / "cockpit" / "mixed_tab.py"
VOLUTE = ROOT / "fansim" / "cockpit" / "volute_tab.py"
APP = ROOT / "fansim" / "cockpit" / "app.py"
README = ROOT / "README.md"

EXPERIMENTAL = "Experimental: not validated against published data"
ASSESS_MRF = "Assess runs MRF CFD (not validated against published data)"
VOLUTE_RANK = "ranking only, unvalidated (CFD not yet converged)"


def test_mixed_copy_is_experimental_not_honest_mrf():
    mixed = MIXED.read_text(encoding="utf-8")
    app = APP.read_text(encoding="utf-8")
    assert "honest MRF" not in mixed
    assert EXPERIMENTAL in mixed
    assert EXPERIMENTAL in app
    assert ASSESS_MRF in mixed
    assert "Mixed · experimental" in app


def test_volute_copy_is_unvalidated_ranking_not_honest_cfd():
    src = VOLUTE.read_text(encoding="utf-8")
    assert "honest CFD" not in src
    assert "honest radial MRF" not in src
    assert VOLUTE_RANK in src


def test_readme_labels_mixed_experimental():
    text = README.read_text(encoding="utf-8")
    assert EXPERIMENTAL in text
    assert "mixed-flow" in text.lower() or "Mixed-flow" in text


def test_mixed_export_readme_labels_experimental():
    src = MIXED.read_text(encoding="utf-8")
    assert "def mixed_export_readme" in src
    assert "with_suffix(\".md\")" in src or "with_suffix('.md')" in src
    # The sidecar text is the helper's return value; the phrases must appear next to it.
    helper = src[src.index("def mixed_export_readme") : src.index("def mixed_export_readme") + 800]
    assert EXPERIMENTAL in helper
    assert ASSESS_MRF in helper


def test_volute_assess_copy_is_labelled_unvalidated():
    """QA-57 rest: Volute Assess lines and result readout carry the ranking-only label too."""
    src = VOLUTE.read_text(encoding="utf-8")
    assess_lines = [ln for ln in src.splitlines() if "Assess runs radial MRF" in ln or "Assess: free+load CFD" in ln]
    assert assess_lines
    assert "Volute CFD: ranking only, unvalidated (CFD not yet converged)." in src
    i = src.index("Assess runs radial MRF")
    assert VOLUTE_RANK in src[i:i + 200]
