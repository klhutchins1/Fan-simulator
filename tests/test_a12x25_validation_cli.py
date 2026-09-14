"""CLI wiring for Phase 3 A12x25 validation runner (no Docker)."""

from __future__ import annotations

from pathlib import Path

SCRIPT = Path("scripts/run_a12x25_validation.py")
REPORT = Path("docs/validation/a12x25_pq_report.md")


def test_validation_runner_script_exists():
    assert SCRIPT.is_file()


def test_default_params_is_reference_stock():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "a12x25_reference.yaml" in text
    assert "config/problems/a12x25_reference.yaml" in text


def test_cli_declares_mesh_ladder_and_backs():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "--mesh-ladder" in text
    assert "--ladder-only" in text
    assert "--tip-gap-mm" in text
    assert "--tip-gap-study" in text
    assert "--physics-study" in text
    assert "--physics-only" in text
    assert "--with-frame" in text
    assert "--wall-ks-mm" in text
    assert "--backs" in text
    assert "--base-cell" in text
    assert "★" not in text


def test_pq_report_scaffold_exists():
    assert REPORT.is_file()
    text = REPORT.read_text(encoding="utf-8")
    assert "geometry" in text.lower()
    assert "60.1" in text
