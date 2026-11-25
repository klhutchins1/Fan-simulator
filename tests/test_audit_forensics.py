"""RV-4: audit_forensics names fingerprint parts and first commits that touch them."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_forensics():
    path = ROOT / "scripts" / "audit_forensics.py"
    spec = importlib.util.spec_from_file_location("audit_forensics", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[spec.name] = mod  # dataclass needs the module registered
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def forensics():
    return _load_forensics()


def test_target_to_path_maps_module_and_attr(forensics):
    p = forensics.target_to_path("fansim.fan_bem:pq_curve")
    assert p is not None
    assert p.name == "fan_bem.py"
    assert p.is_file()


def test_part_inventory_has_targets_unit_and_checks(forensics):
    inv = forensics.part_inventory("physics.air_properties")
    assert any(k.startswith("target:") for k in inv)
    assert "unit" in inv
    # hashes are non-empty hex-ish strings
    for name, (h, paths) in inv.items():
        assert isinstance(h, str) and len(h) >= 4, name
        assert isinstance(paths, tuple)


def test_first_commit_touching_empty_paths(forensics):
    assert forensics.first_commit_touching((), since_commit="HEAD") == (None, None)


def test_cli_lists_parts_for_known_unit(forensics, capsys):
    rc = forensics.main(["physics.air_properties"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "unit physics.air_properties" in out
    assert "target:" in out or "unit:" in out or "unit " in out
