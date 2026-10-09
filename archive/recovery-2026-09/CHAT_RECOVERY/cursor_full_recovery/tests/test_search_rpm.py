"""--search-rpm wiring smoke (no Docker)."""

from __future__ import annotations

from pathlib import Path

import pytest

from fansim.optimize.pwm_table import (
    make_pwm_table,
    pwm_caption,
    resolve_pwm_table,
    suggest_rpm,
)


class _Trial:
    def suggest_float(self, name, lo, hi):
        assert name == "rpm"
        return 0.5 * (lo + hi)


def test_suggest_rpm_midband():
    assert suggest_rpm(_Trial()) == pytest.approx(1225.0)


def test_suggest_rpm_custom_band():
    tab = make_pwm_table(600.0, 1600.0)
    assert suggest_rpm(_Trial(), tab) == pytest.approx(1100.0)


def test_resolve_pwm_table_defaults_and_override():
    assert resolve_pwm_table().rpm_min == 450.0
    tab = resolve_pwm_table(500.0, 1800.0)
    assert tab.rpm_min == 500.0
    assert tab.rpm_max == 1800.0
    with pytest.raises(ValueError):
        make_pwm_table(2000.0, 450.0)


def test_pwm_caption_mentions_band():
    text = pwm_caption()
    assert "450" in text and "2000" in text
    assert "Kv" in text


def test_cli_declares_search_rpm_and_bounds():
    text = Path("scripts/run_optimization.py").read_text(encoding="utf-8")
    assert "--search-rpm" in text
    assert "--rpm-min" in text
    assert "--rpm-max" in text
