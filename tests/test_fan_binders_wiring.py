"""Static wiring check for the Fan-tab binder split (§13.9).

When ``setup_fan_tab`` was split into per-domain binders, cross-domain closures started
routing through the shared ``FanSession`` bag (``session.active_spec(...)`` etc.). A typo
like ``session.actve_spec`` is an ordinary attribute access, so neither ``ast.parse`` nor
ruff F821 catches it, and it only blows up when that callback runs at cockpit runtime.

This test closes that gap statically: every ``session.<name>`` that is *read* anywhere in
the cockpit package must be *provided* somewhere -- either a ``FanSession`` field/annotation
or a ``session.<name> = ...`` assignment in some binder. It is a no-op until the binders
exist, then becomes the F821-equivalent for session routing.
"""

from __future__ import annotations

import ast
from pathlib import Path

COCKPIT = Path(__file__).resolve().parents[1] / "fansim" / "cockpit"


def _session_writes_and_reads(tree: ast.AST):
    writes: set[str] = set()
    reads: set[str] = set()
    write_targets: set[int] = set()

    for node in ast.walk(tree):
        # session.<name> = ...  (assignment target)
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if (
                    isinstance(tgt, ast.Attribute)
                    and isinstance(tgt.value, ast.Name)
                    and tgt.value.id == "session"
                ):
                    writes.add(tgt.attr)
                    write_targets.add(id(tgt))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "session"
            and id(node) not in write_targets
        ):
            reads.add(node.attr)
    return writes, reads


def _fan_session_provides() -> set[str]:
    """Attributes FanSession supplies: __init__ self.x = ... plus class annotations."""
    src = (COCKPIT / "fan_session.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    provided: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if (
                    isinstance(tgt, ast.Attribute)
                    and isinstance(tgt.value, ast.Name)
                    and tgt.value.id == "self"
                ):
                    provided.add(tgt.attr)
        elif isinstance(node, ast.AnnAssign):
            tgt = node.target
            if isinstance(tgt, ast.Name):
                provided.add(tgt.id)  # class-level annotation
            elif (
                isinstance(tgt, ast.Attribute)
                and isinstance(tgt.value, ast.Name)
                and tgt.value.id == "self"
            ):
                provided.add(tgt.attr)  # self.x: T = ...
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            provided.add(node.name)  # methods like expose_to_ctx
    return provided


def test_every_session_attr_read_is_provided():
    provided = _fan_session_provides()
    all_reads: dict[str, str] = {}
    for path in COCKPIT.glob("fan_*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        writes, reads = _session_writes_and_reads(tree)
        provided |= writes
        for name in reads:
            all_reads.setdefault(name, path.name)

    missing = {name: mod for name, mod in all_reads.items() if name not in provided}
    assert not missing, (
        "session attributes read but never provided (typo or missing binder wiring): "
        + ", ".join(f"{n} (in {m})" for n, m in sorted(missing.items()))
    )
