"""Audit registry: schema validation and the shipped registry loads."""

from __future__ import annotations

from pathlib import Path

import pytest

from fansim.audit.registry import REGISTRY_PATH, RegistryError, load_registry


def _write(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "registry.yaml"
    p.write_text(body, encoding="utf-8")
    return p


GOOD = """
exempt: ["fansim.cfd.glyphs:*"]
units:
  - id: a.base
    targets: ["fansim.cfd.metrics:parse_fan_metrics"]
    claim: "x"
    source: {kind: standard, ref: "unit conversion"}
  - id: a.child
    targets: ["fansim.cfd.metrics"]
    claim: "y"
    source: {kind: derivation, ref: "hand"}
    depends_on: [a.base]
    libs: [numpy]
"""


def test_loads_valid_registry(tmp_path):
    reg = load_registry(_write(tmp_path, GOOD))
    assert set(reg.units) == {"a.base", "a.child"}
    assert reg.units["a.child"].depends_on == ("a.base",)
    assert reg.units["a.child"].libs == ("numpy",)
    assert reg.units["a.base"].checks == ()
    assert reg.exempt == ("fansim.cfd.glyphs:*",)


@pytest.mark.parametrize("body, msg", [
    ("units:\n  - {id: a, claim: c, source: {kind: paper, ref: r}}\n", "targets"),
    ("units:\n  - {id: a, targets: [m], claim: c, source: {kind: vibes, ref: r}}\n", "kind"),
    ("units:\n  - {id: a, targets: [m], claim: c, source: {kind: paper, ref: r}}\n"
     "  - {id: a, targets: [m], claim: c, source: {kind: paper, ref: r}}\n", "duplicate"),
    ("units:\n  - {id: a, targets: [m], claim: c, source: {kind: paper, ref: r}, depends_on: [zz]}\n",
     "unknown"),
    ("units:\n  - {id: a, targets: [m], claim: c, source: {kind: paper, ref: r}, depends_on: [b]}\n"
     "  - {id: b, targets: [m], claim: c, source: {kind: paper, ref: r}, depends_on: [a]}\n", "cycle"),
    ("units:\n  - {id: a, targets: ['bad target!'], claim: c, source: {kind: paper, ref: r}}\n",
     "target"),
])
def test_rejects_invalid(tmp_path, body, msg):
    with pytest.raises(RegistryError, match=msg):
        load_registry(_write(tmp_path, body))


def test_shipped_registry_loads():
    reg = load_registry(REGISTRY_PATH)
    assert "cfd.flow_direction_convention" in reg.units


def test_missing_checks_path_raises(tmp_path):
    body = (
        "units:\n"
        "  - {id: a, targets: [m], claim: c, source: {kind: paper, ref: r}, "
        "checks: [tests/audit/does_not_exist.py]}\n"
    )
    with pytest.raises(RegistryError, match="checks path not found"):
        load_registry(_write(tmp_path, body))


def test_data_target_is_accepted(tmp_path):
    body = (
        "units:\n"
        "  - {id: a, targets: ['data:config/problems/a12x25_reference.yaml'], claim: c, "
        "source: {kind: paper, ref: r}}\n"
    )
    reg = load_registry(_write(tmp_path, body))
    assert reg.units["a"].targets == ("data:config/problems/a12x25_reference.yaml",)


def test_find_unregistered_ignores_data_targets():
    from fansim.audit.registry import Registry, Unit
    from fansim.audit.status import find_unregistered

    unit = Unit(
        id="a", targets=("data:config/problems/a12x25_reference.yaml",), claim="c",
        source={"kind": "paper", "ref": "r"}, regime={}, checks=(), depends_on=(), libs=(),
    )
    reg = Registry(units={"a": unit}, exempt=())
    # Must not raise, and must not claim to cover any real python name.
    names = find_unregistered(reg)
    assert isinstance(names, list)


def test_ref_checks_path_is_not_validated(tmp_path):
    body = (
        "units:\n"
        "  - {id: a, targets: [m], claim: c, source: {kind: paper, ref: r}, "
        "checks: ['ref:a12x25_direction_matrix']}\n"
    )
    reg = load_registry(_write(tmp_path, body))
    assert reg.units["a"].checks == ("ref:a12x25_direction_matrix",)
