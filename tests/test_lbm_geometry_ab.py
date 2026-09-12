"""Tests for LBM geometry A/B helpers (no GPU, no CadQuery build)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fansim.cfd.lbm_geometry_ab import (
    HONESTY,
    blade_params_for_variant,
    compare_shutoff_deltas,
    load_base_params,
    stepped_inlet_row,
    summary_markdown,
)


def test_load_base_params_from_bare_dict(tmp_path: Path):
    p = tmp_path / "base.json"
    p.write_text(json.dumps({"n_blades": 7, "rpm": 2000}), encoding="utf-8")
    flat = load_base_params(p)
    assert flat["n_blades"] == 7
    assert flat["rpm"] == 2000


def test_load_base_params_from_params_wrapper(tmp_path: Path):
    p = tmp_path / "design.json"
    p.write_text(json.dumps({"params": {"n_blades": 5, "rpm": 1500}}), encoding="utf-8")
    assert load_base_params(p)["n_blades"] == 5


def test_load_base_params_from_trial_list(tmp_path: Path):
    p = tmp_path / "study.json"
    p.write_text(
        json.dumps(
            [
                {"trial": 1, "params": {"n_blades": 5, "rpm": 1000}},
                {"trial": 3, "params": {"n_blades": 9, "rpm": 2000}},
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="--trial"):
        load_base_params(p)
    assert load_base_params(p, trial=3)["n_blades"] == 9


def _flat(**extra):
    base = {
        "n_blades": 7,
        "chord_root": 34,
        "chord_mid": 44,
        "chord_tip": 38,
        "stagger_root": 26,
        "stagger_mid": 26,
        "stagger_tip": 22,
        "sweep_mid": 3,
        "sweep_tip": 5,
        "max_camber": 0.05,
    }
    base.update(extra)
    return base


def test_blade_params_for_variant_stamps_sickle_and_notches():
    flat = _flat(sickle_mm=10.0, notched_tips=True, tip_notch_count=3)
    base = blade_params_for_variant(flat, "default")
    assert all(s.le_skew == 0.0 for s in base.stations)
    assert int(base.tip_notch_count) == 0

    sickle = blade_params_for_variant(flat, "sickle")
    tip = max(sickle.stations, key=lambda s: s.r_frac)
    assert tip.le_skew == pytest.approx(10.0)

    notched = blade_params_for_variant(flat, "notched_tips")
    assert notched.tip_notch_count == 3
    assert all(s.le_skew == 0.0 for s in notched.stations)

    with pytest.raises(ValueError, match="unknown"):
        blade_params_for_variant(flat, "bogus")


def test_compare_shutoff_deltas_vs_default():
    results = [
        {
            "variant": "default",
            "shutoff": {"shut_off_pa": 22.4, "residual_cfm": 1.8},
        },
        {
            "variant": "sickle",
            "shutoff": {"shut_off_pa": 21.0, "residual_cfm": 2.1},
        },
        {
            "variant": "notched_tips",
            "shutoff": {"shut_off_pa": 22.9, "residual_cfm": 1.5},
        },
        stepped_inlet_row(casing_plain="a.stl", casing_stepped="b.stl"),
    ]
    deltas = compare_shutoff_deltas(results)
    by = {d["variant"]: d for d in deltas}
    assert by["sickle"]["delta_shut_off_pa"] == pytest.approx(-1.4)
    assert by["sickle"]["delta_residual_cfm"] == pytest.approx(0.3)
    assert by["notched_tips"]["delta_shut_off_pa"] == pytest.approx(0.5)
    assert "stepped_inlet" not in by


def test_compare_shutoff_deltas_empty_without_metrics():
    assert compare_shutoff_deltas([{"variant": "default", "shutoff": None}]) == []
    assert compare_shutoff_deltas([{"variant": "sickle", "shutoff": {"shut_off_pa": 1}}]) == []


def test_stepped_inlet_row_honesty():
    row = stepped_inlet_row(casing_plain="p.stl", casing_stepped="s.stl")
    assert row["variant"] == "stepped_inlet"
    assert row["shutoff"] is None
    assert "casing-only" in row["skipped"]
    assert row["casing_plain_stl"] == "p.stl"
    assert "OpenFOAM" in row["note"]


def test_summary_markdown_includes_honesty_and_deltas():
    payload = {
        "date": "2026-09-08",
        "base_json": "base.json",
        "honesty": HONESTY,
        "results": [
            {"variant": "default", "label": "baseline", "stl": "default.stl", "skipped": "dry-run"},
            stepped_inlet_row(casing_plain="c_plain.stl", casing_stepped="c_step.stl"),
        ],
        "deltas": [
            {
                "variant": "sickle",
                "delta_shut_off_pa": -1.0,
                "shut_off_pa": 21.0,
                "baseline_shut_off_pa": 22.0,
                "delta_residual_cfm": 0.2,
            }
        ],
    }
    md = summary_markdown(payload)
    assert HONESTY in md
    assert "stepped_inlet" in md
    assert "c_plain.stl" in md
    assert "ΔPa=-1.0" in md
