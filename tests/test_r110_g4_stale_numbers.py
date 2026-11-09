"""R1.10 G4 / QA-58: drop stale ~2× / ~0.6× / ~3–5 % claims."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_figures_static_ceiling_is_about_10_percent():
    src = (ROOT / "fansim" / "cockpit" / "figures.py").read_text(encoding="utf-8")
    assert "~2×" not in src and "~2x" not in src.lower()
    assert "CFD's static-pressure ceiling is a little below the datasheet's (about 10 %)" in src


def test_assess_alert_says_two_solves():
    src = (ROOT / "fansim" / "cockpit" / "fan_tab_ui.py").read_text(encoding="utf-8")
    assert "Assess runs two CFD solves (free air and a loaded point), about 20–40 min" in src
    assert "Assess runs one CFD solve" not in src


def test_bem_copy_is_ranking_only_not_0_6x():
    src = (ROOT / "fansim" / "cockpit" / "fan_copy.py").read_text(encoding="utf-8")
    assert "under-ranks CFD (~0.6×)" not in src
    assert "ranking only; coarse; can't separate close designs" in src.lower()


def test_design_rules_drop_stale_blade_and_gci():
    src = (ROOT / "docs" / "design-rules.md").read_text(encoding="utf-8")
    assert "more blades raise airflow" not in src.lower()
    assert "~3–5%" not in src and "~3–5 %" not in src
    assert "screening mesh, GCI ≈ 21 %" in src
    assert "±1 % run to run on Stock" in src
    assert "Noise dB(A) (min)" not in src
    assert "Noise estimate (min)" in src


def test_extract_design_rules_does_not_label_lbm_as_dba():
    src = (ROOT / "scripts" / "extract_design_rules.py").read_text(encoding="utf-8")
    assert '"Noise dB(A) (min)"' not in src
    assert '"Noise estimate (min)"' in src


def test_adversarial_review_gci_is_21_percent():
    src = (ROOT / "docs" / "adversarial-review.md").read_text(encoding="utf-8")
    assert "~3–5%" not in src and "~3–5 %" not in src
    assert "GCI ≈ 21 %" in src or "GCI_fine ≈ 21 %" in src or "screening mesh, GCI ≈ 21 %" in src


def test_a12x25_reference_names_close_ref_and_open_gaps():
    src = (ROOT / "docs" / "a12x25-reference.md").read_text(encoding="utf-8")
    assert "validated on a close-reference STL of the A12x25: 59.8 vs 60.1 CFM" in src
    assert "every gap below has since been closed" not in src
    assert "near-stall" in src
    assert "Stock recipe" in src or "recipe gap" in src


def test_readme_known_limits_is_a_list():
    src = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "The one real gap" not in src
    assert "nothing printed or measured yet" in src.lower() or "printed and measured" in src
    assert "propeller CFD is not a performance predictor" in src
    assert "volute" in src.lower() and "unconverged" in src
    assert "mixed-flow" in src.lower()
    assert "noise" in src.lower()
    assert "5 %" in src and "Stock" in src
