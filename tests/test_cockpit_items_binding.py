"""Guard against the trame ``items=[literal]`` crash (cockpit blank-widget bug).

trame's ``AbstractElement.attrs`` treats *any* list/tuple attribute value as a
``(state_var, default)`` binding. So a VSelect written ``items=[{"title": ...}, ...]`` makes
trame use the first dict as the state-variable *name* and call ``.startswith`` on it — raising
``'dict' object has no attribute 'startswith'`` and rendering the widget as ``<VSelect html-error/>``.
Item lists must be bound through a state variable instead: ``items=("some_state_var",)``.

This scans the cockpit tab modules' AST for the exact anti-pattern so it cannot creep back in.
"""

from __future__ import annotations

import ast
from pathlib import Path

_COCKPIT = Path(__file__).resolve().parents[1] / "fansim" / "cockpit"

# trame keyword args that are list-valued props and must be bound via a state var, never a literal.
_LIST_BOUND_KWARGS = {"items", "ticks"}


def _literal_list_bindings(path: Path) -> list[str]:
    """Return 'file:line kwarg' for any call passing a list/dict *literal* to a list-bound kwarg."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for kw in node.keywords:
            if kw.arg in _LIST_BOUND_KWARGS and isinstance(kw.value, (ast.List, ast.Dict)):
                hits.append(f"{path.name}:{kw.value.lineno} items={kw.arg}=<literal>")
    return hits


def test_no_literal_list_items_in_cockpit_widgets():
    offenders: list[str] = []
    for py in sorted(_COCKPIT.glob("*.py")):
        offenders.extend(_literal_list_bindings(py))
    assert not offenders, (
        "trame reads a list/dict literal passed to items=/ticks= as a state binding and crashes "
        "('dict' object has no attribute 'startswith'). Bind via a state var, e.g. "
        "items=('my_items_state',). Offenders:\n  " + "\n  ".join(offenders)
    )
