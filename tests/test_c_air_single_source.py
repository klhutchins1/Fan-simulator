"""Issue #113: C_AIR must be single-sourced from fansim.physics.air.C0_AIR."""

from __future__ import annotations

import ast
from pathlib import Path

from fansim.physics import air
from fansim.prop_spec import C_AIR as PROP_SPEC_C_AIR
from fansim.propeller.pythrust_export import C_AIR as PYTHRUST_C_AIR

ROOT = Path(__file__).resolve().parents[1]


def test_c_air_imported_from_physics_air():
    assert PROP_SPEC_C_AIR == air.C0_AIR
    assert PYTHRUST_C_AIR == air.C0_AIR


def test_no_duplicate_c_air_numeric_literals():
    """No module in fansim/ or scripts/ may redefine C_AIR as a numeric literal."""
    offenders: list[str] = []
    for top in ("fansim", "scripts"):
        for path in sorted((ROOT / top).rglob("*.py")):
            rel = path.relative_to(ROOT).as_posix()
            if rel == "fansim/physics/air.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in tree.body:
                if (
                    isinstance(node, ast.Assign)
                    and isinstance(node.value, ast.Constant)
                    and isinstance(node.value.value, (int, float))
                ):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == "C_AIR":
                            offenders.append(f"{rel}:{node.lineno}")
                elif (
                    isinstance(node, ast.AnnAssign)
                    and isinstance(node.target, ast.Name)
                    and node.target.id == "C_AIR"
                    and isinstance(node.value, ast.Constant)
                    and isinstance(node.value.value, (int, float))
                ):
                    offenders.append(f"{rel}:{node.lineno}")
    assert not offenders, f"Duplicate C_AIR literal(s) found: {offenders}"
