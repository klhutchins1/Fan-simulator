"""lt120 tip-gap follow-up (2026-10-30 prereg): the CLI can vary the gap, points and meshes; the rotor stays frozen."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "validate_lt120", Path(__file__).resolve().parents[1] / "scripts" / "validate_lt120.py")
v = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(v)


def test_defaults_are_the_frozen_campaign():
    a = v.parse_cli([])
    assert a.tip_gap == pytest.approx(v.TIP_GAP_MM)
    assert v.select_points(a.dp) == list(v.POINTS)
    assert tuple(a.meshes) == tuple(v.MESHES_MM)
    assert v.duct_id_mm(a.tip_gap) == pytest.approx(v.DUCT_ID_MM)   # 121 mm at 0.5 mm


def test_only_the_duct_grows_with_the_gap():
    assert v.duct_id_mm(1.5) == pytest.approx(v.DUCT_ID_MM + 2.0)
    a = v.parse_cli(["--tip-gap", "1.0", "--dp", "6.85", "13.71", "--meshes", "5.8"])
    assert [p["dp_pa"] for p in v.select_points(a.dp)] == [6.85, 13.71]
    assert list(a.meshes) == [5.8]


def test_unknown_point_is_refused():
    with pytest.raises(ValueError):
        v.select_points([9.99])
