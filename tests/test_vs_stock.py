"""R1.10 G1 / QA-56: Assess compares with scored Stock, never the datasheet."""

from __future__ import annotations

from pathlib import Path

from fansim.cockpit.vs_stock import vs_stock_same_test_line
from fansim.optimize.design import Design
from fansim.optimize.search_space import stock_blade_flat

ROOT = Path(__file__).resolve().parents[1]


def _extra(**kw) -> dict:
    out = {
        "preset": "case",
        "load_pa": 8.0,
        "refine_op": False,
        "material": "PETG",
        "fan_model": "a12x25",
        "cfd_version": 6,
    }
    out.update(kw)
    return out


def _design(params, cfm, extra, trial=1, **kw) -> Design:
    return Design(
        trial=trial,
        params=dict(params),
        objectives={"cfm_free": float(cfm), "cfm_load": 30.0, "efficiency": 20.0},
        feasible=True,
        is_pareto=False,
        stl_path=None,
        extra=dict(extra),
        **kw,
    )


def test_stock_vs_itself_is_zero_not_minus_seventeen():
    """G1: assessing Stock against itself is 0 %, never −17 % vs the datasheet."""
    stock = stock_blade_flat("a12x25")
    extra = _extra()
    d = _design(stock, 49.6, extra)
    line = vs_stock_same_test_line(49.6, extra, [d])
    assert "vs Stock (same test): +0 % free air" in line
    assert "-17" not in line
    assert "60" not in line
    assert "datasheet" not in line.lower()


def test_no_scored_stock_omits_the_line():
    extra = _extra()
    other = _design({"n_blades": 9, "chord_tip": 40.0, "stagger_mid": 20.0}, 55.0, extra)
    assert vs_stock_same_test_line(55.0, extra, [other]) == ""


def test_datasheet_reference_is_not_a_scored_stock():
    stock_params = stock_blade_flat("a12x25")
    ref = _design(stock_params, 60.1, _extra(is_reference=True, source="reference"), trial=0)
    other = _design({"n_blades": 9, "chord_tip": 40.0}, 50.0, _extra(), trial=2)
    assert vs_stock_same_test_line(50.0, other.extra, [ref, other]) == ""


def test_other_design_vs_scored_stock_same_test():
    extra = _extra()
    stock = _design(stock_blade_flat("a12x25"), 50.0, extra, trial=1)
    other = _design({"n_blades": 9, "chord_tip": 40.0}, 55.0, extra, trial=2)
    line = vs_stock_same_test_line(55.0, extra, [stock, other])
    assert line == "vs Stock (same test): +10 % free air"


def test_different_hose_omits_the_line():
    stock = _design(stock_blade_flat("a12x25"), 50.0, _extra(preset="case", load_pa=8.0), trial=1)
    other = _design({"n_blades": 9}, 55.0, _extra(preset="heatsink", load_pa=20.0), trial=2)
    assert vs_stock_same_test_line(55.0, other.extra, [stock, other]) == ""


def test_assess_source_does_not_compare_to_datasheet():
    src = (ROOT / "fansim" / "cockpit" / "fan_assess.py").read_text(encoding="utf-8")
    assert "vs stock free" not in src
    assert "vs_stock_same_test_line" in src
    assert "spec.ref_cfm" not in src
