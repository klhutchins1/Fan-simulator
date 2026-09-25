"""Load and validate the audit unit registry (``registry.yaml``).

A *unit* is one audited piece of physics: the code that implements it (``targets``), what it
claims, where the claim comes from, and which checks prove it. See the design spec
``docs/superpowers/specs/2026-09-24-physics-audit-design.md``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from fansim.audit.fingerprint import ROOT as _FINGERPRINT_ROOT

REGISTRY_PATH = Path(__file__).with_name("registry.yaml")
SOURCE_KINDS = frozenset({"paper", "datasheet", "standard", "derivation"})
_TARGET_RE = re.compile(r"^[A-Za-z_][\w.]*(:[A-Za-z_][\w.]*)?$")


class RegistryError(ValueError):
    """The registry file is malformed."""


@dataclass(frozen=True)
class Unit:
    id: str
    targets: tuple[str, ...]
    claim: str
    source: dict
    regime: dict
    checks: tuple[str, ...]
    depends_on: tuple[str, ...]
    libs: tuple[str, ...]


@dataclass(frozen=True)
class Registry:
    units: dict[str, Unit]
    exempt: tuple[str, ...]


def _unit(raw: dict) -> Unit:
    uid = raw.get("id")
    if not uid:
        raise RegistryError(f"unit without id: {raw!r}")
    targets = tuple(raw.get("targets") or ())
    if not targets:
        raise RegistryError(f"{uid}: needs at least one entry in targets")
    for t in targets:
        if not _TARGET_RE.match(str(t)):
            raise RegistryError(f"{uid}: bad target {t!r} (want 'pkg.mod' or 'pkg.mod:Name')")
    source = dict(raw.get("source") or {})
    if source.get("kind") not in SOURCE_KINDS:
        raise RegistryError(f"{uid}: source kind must be one of {sorted(SOURCE_KINDS)}")
    for c in raw.get("checks") or ():
        c = str(c)
        if not c.startswith("ref:") and not (_FINGERPRINT_ROOT / c).is_file():
            raise RegistryError(f"{uid}: checks path not found: {c!r}")
    return Unit(
        id=str(uid),
        targets=tuple(str(t) for t in targets),
        claim=str(raw.get("claim", "")),
        source=source,
        regime=dict(raw.get("regime") or {}),
        checks=tuple(str(c) for c in raw.get("checks") or ()),
        depends_on=tuple(str(d) for d in raw.get("depends_on") or ()),
        libs=tuple(str(x) for x in raw.get("libs") or ()),
    )


def _check_graph(units: dict[str, Unit]) -> None:
    for u in units.values():
        for d in u.depends_on:
            if d not in units:
                raise RegistryError(f"{u.id}: depends_on unknown unit {d!r}")
    state: dict[str, int] = {}  # 1 = visiting, 2 = done

    def visit(uid: str) -> None:
        if state.get(uid) == 1:
            raise RegistryError(f"dependency cycle through {uid!r}")
        if state.get(uid) == 2:
            return
        state[uid] = 1
        for d in units[uid].depends_on:
            visit(d)
        state[uid] = 2

    for uid in units:
        visit(uid)


def load_registry(path: Path = REGISTRY_PATH) -> Registry:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    units: dict[str, Unit] = {}
    for raw in data.get("units") or ():
        u = _unit(raw)
        if u.id in units:
            raise RegistryError(f"duplicate unit id {u.id!r}")
        units[u.id] = u
    _check_graph(units)
    return Registry(units=units, exempt=tuple(str(e) for e in data.get("exempt") or ()))
