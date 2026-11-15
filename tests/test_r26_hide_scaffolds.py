"""R2.6: centrifugal-only and wind-turbine flows have no cockpit or quickstart entry.

Mixed-flow and Volute stay. The wind_turbine package may stay in the repo. This file
only reads source; it does not import fansim (no CAD kernel).
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COCKPIT = ROOT / "fansim" / "cockpit"
README = ROOT / "README.md"

# A control, tab, menu item, or link that starts the parked flow.
_ENTRY = re.compile(
    r"\b(centrifugal|wind[\s_-]*turbine)\b",
    re.IGNORECASE,
)

_SHIPPING_TABS = {"fan", "mixed", "volute", "propeller", "cror"}
_DOC_PARENTS = (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def _docstring_nodes(tree: ast.AST) -> set[ast.AST]:
    found: set[ast.AST] = set()
    for node in ast.walk(tree):
        if not isinstance(node, _DOC_PARENTS) or not getattr(node, "body", None):
            continue
        first = node.body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
            and ast.get_docstring(node) is not None
        ):
            found.add(first.value)
    return found


def _user_strings(path: Path) -> list[str]:
    """Widget text, menu titles, and other string constants. Skip docstrings."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    docs = _docstring_nodes(tree)
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node not in docs:
            out.append(node.value)
    return out


def _call_name(func: ast.AST) -> str:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _layout_tabs(path: Path) -> list[tuple[str, str]]:
    """Top-level ``VTab(label, value=...)`` pairs in the cockpit layout."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    tabs: list[tuple[str, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or _call_name(node.func) != "VTab":
            continue
        if not node.args or not isinstance(node.args[0], ast.Constant):
            continue
        label = node.args[0].value
        if not isinstance(label, str):
            continue
        value = None
        for kw in node.keywords:
            if kw.arg == "value" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                value = kw.value.value
        if value is not None:
            tabs.append((label, value))
    return tabs


def _quickstart(readme: str) -> str:
    lines = readme.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip() == "## Quickstart":
            start = i + 1
            break
    if start is None:
        raise AssertionError("README has no ## Quickstart section")
    end = len(lines)
    for j in range(start, len(lines)):
        if lines[j].startswith("## "):
            end = j
            break
    return "\n".join(lines[start:end])


def _hits(text: str) -> list[str]:
    return [m.group(0) for m in _ENTRY.finditer(text)]


def test_centrifugal_and_wind_turbine_absent_from_cockpit_and_quickstart():
    """No cockpit control, tab, or menu, and no README quickstart link, starts either parked flow."""
    layout = COCKPIT / "app.py"
    tabs = _layout_tabs(layout)
    assert tabs, "cockpit layout has no VTab entries"
    values = {value for _label, value in tabs}
    assert values == _SHIPPING_TABS
    assert "mixed" in values and "volute" in values

    parked: list[str] = []
    for label, value in tabs:
        for hit in _hits(f"{label} {value}"):
            parked.append(f"{layout.name} tab {label!r}/{value!r} ({hit})")

    for path in sorted(COCKPIT.glob("*.py")):
        for text in _user_strings(path):
            for hit in _hits(text):
                parked.append(f"{path.name}: {text!r} ({hit})")

    quick = _quickstart(README.read_text(encoding="utf-8"))
    assert "scripts/cockpit.py" in quick
    for hit in _hits(quick):
        parked.append(f"README Quickstart ({hit})")
    for href in re.findall(r"\[[^\]]*\]\(([^)]+)\)", quick):
        for hit in _hits(href):
            parked.append(f"README Quickstart link {href!r} ({hit})")

    assert not parked, "parked flow is reachable:\n" + "\n".join(parked)
