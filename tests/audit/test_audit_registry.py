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
