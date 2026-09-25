"""Which audited units need re-auditing: PROVEN / CHANGED / AFFECTED / NEW (+ unregistered code)."""

from __future__ import annotations

import ast
import fnmatch
import json
from enum import Enum
from pathlib import Path

from fansim.audit.fingerprint import ROOT
from fansim.audit.registry import Registry

LEDGER_PATH = ROOT / "docs" / "validation" / "audits" / "ledger.json"
PHYSICS_PACKAGES = (
    "fansim.cfd", "fansim.acoustics", "fansim.propeller", "fansim.cror", "fansim.centrifugal",
    "fansim.volute", "fansim.wind_turbine", "fansim.structural", "fansim.physics", "fansim.fan_bem",
)


class State(str, Enum):
    PROVEN = "PROVEN"
    CHANGED = "CHANGED"
    AFFECTED = "AFFECTED"
    NEW = "NEW"


def load_ledger(path: Path = LEDGER_PATH) -> dict:
    if not Path(path).is_file():
        return {"units": {}}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def record_pass(unit_id: str, fingerprint: str, report: str, date: str,
                path: Path = LEDGER_PATH) -> None:
    if not fingerprint:
        raise ValueError("fingerprint must not be empty")
    led = load_ledger(path)
    led.setdefault("units", {})[unit_id] = {
        "fingerprint": fingerprint, "verdict": "PASS", "date": date, "report": report,
    }
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(led, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def classify(registry: Registry, ledger: dict, fingerprints: dict[str, str]) -> dict[str, State]:
    passed = ledger.get("units", {})
    own: dict[str, State] = {}
    for uid in registry.units:
        rec = passed.get(uid)
        if rec is None or rec.get("verdict") != "PASS":
            own[uid] = State.NEW
        elif rec.get("fingerprint") != fingerprints[uid]:
            own[uid] = State.CHANGED
        else:
            own[uid] = State.PROVEN
    out: dict[str, State] = {}

    def resolve(uid: str) -> State:
        if uid in out:
            return out[uid]
        state = own[uid]
        if state is State.PROVEN and any(
            resolve(d) is not State.PROVEN for d in registry.units[uid].depends_on
        ):
            state = State.AFFECTED
        out[uid] = state
        return state

    for uid in registry.units:
        resolve(uid)
    return out


def _covered(name: str, registry: Registry) -> bool:
    module = name.split(":")[0]
    for u in registry.units.values():
        for t in u.targets:
            if t == name or t == module:
                return True
    return any(fnmatch.fnmatch(name, pat) for pat in registry.exempt)


def find_unregistered(registry: Registry, packages: tuple[str, ...] = PHYSICS_PACKAGES,
                      root: Path = ROOT) -> list[str]:
    names: list[str] = []
    for pkg in packages:
        base = Path(root, *pkg.split("."))
        files = sorted(base.rglob("*.py")) if base.is_dir() else [base.with_suffix(".py")]
        for f in files:
            if not f.is_file():
                continue
            rel = f.relative_to(root).with_suffix("")
            parts = rel.parts[:-1] if rel.name == "__init__" else rel.parts
            module = ".".join(parts)
            tree = ast.parse(f.read_text(encoding="utf-8"))
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) \
                        and not node.name.startswith("_"):
                    name = f"{module}:{node.name}"
                    if not _covered(name, registry):
                        names.append(name)
    return sorted(names)
