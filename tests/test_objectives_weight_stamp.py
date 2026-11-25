"""O6 / #52: trimesh volume failure stamps weight_error; gate still runs with weight_g=None."""

from __future__ import annotations

from pathlib import Path

import pytest

from fansim.optimize import objectives as obj


def test_printed_weight_g_stamps_error_when_trimesh_fails(tmp_path, monkeypatch):
    stl = tmp_path / "x.stl"
    stl.write_text("solid x\nendsolid x\n", encoding="utf-8")

    class Boom:
        @staticmethod
        def load(_path):
            raise RuntimeError("no volume")

    monkeypatch.setitem(__import__("sys").modules, "trimesh", Boom)
    weight, err = obj.printed_weight_g(stl, "PLA+")
    assert weight is None
    assert err is not None
    assert "RuntimeError" in err
    assert "no volume" in err


def test_printed_weight_g_returns_grams_when_trimesh_works(tmp_path, monkeypatch):
    stl = tmp_path / "x.stl"
    stl.write_text("solid x\nendsolid x\n", encoding="utf-8")

    class Mesh:
        volume = 1000.0  # mm³

    class Ok:
        @staticmethod
        def load(_path):
            return Mesh()

    monkeypatch.setitem(__import__("sys").modules, "trimesh", Ok)
    weight, err = obj.printed_weight_g(stl, "PLA+")
    assert err is None
    from fansim.fan_spec import estimate_weight_g

    assert weight == pytest.approx(estimate_weight_g(1000.0, "PLA+"))


def test_evaluate_candidate_source_stamps_weight_error():
    src = Path(obj.__file__).read_text(encoding="utf-8")
    assert 'gap_raw["weight_error"]' in src or "gap_raw['weight_error']" in src
    assert "printed_weight_g" in src
