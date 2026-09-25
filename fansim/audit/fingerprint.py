"""Logic-only fingerprints of audited code.

Source is parsed to an AST, docstrings are dropped, and ``ast.unparse`` re-emits it. Comments,
docstrings and formatting therefore never change a fingerprint; any change to what the code *does*
does. Modules are read from disk, not imported, so fingerprinting is fast and side-effect free.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import importlib.metadata
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DATA_TARGET_PREFIX = "data:"


class FingerprintError(LookupError):
    """A registry target does not resolve to code."""


def module_path(module: str, root: Path = ROOT) -> Path:
    base = Path(root, *module.split("."))
    for cand in (base.with_suffix(".py"), base / "__init__.py"):
        if cand.is_file():
            return cand
    raise FingerprintError(f"module {module!r} not found under {root}")


def _strip_docstrings(tree: ast.AST) -> ast.AST:
    tree = copy.deepcopy(tree)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(
                getattr(body[0], "value", None), ast.Constant
            ) and isinstance(body[0].value.value, str):
                node.body = body[1:] or [ast.Pass()]
    return tree


def _find(body: list[ast.stmt], name: str) -> ast.stmt | None:
    """Return the LAST top-level definition of ``name`` in ``body`` (Python: last binding wins)."""
    result: ast.stmt | None = None
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == name:
            result = node
        elif isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == name for t in node.targets
        ):
            result = node
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name:
            result = node
    return result


def _module_defs(tree: ast.Module) -> dict[str, ast.stmt]:
    """Map every top-level def/class/Assign/AnnAssign name to its (last-binding) node."""
    defs: dict[str, ast.stmt] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defs[node.name] = node
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    defs[t.id] = node
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            defs[node.target.id] = node
    return defs


def _referenced_names(node: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def _resolve_node(target: str, root: Path = ROOT) -> ast.AST:
    """Resolve a target (module or module:qualifier) to its AST node."""
    module, _, qual = target.partition(":")
    tree = ast.parse(module_path(module, root).read_text(encoding="utf-8"))
    node: ast.AST = tree
    if qual:
        for part in qual.split("."):
            found = _find(getattr(node, "body", []), part)
            if found is None:
                raise FingerprintError(f"{target!r}: {part!r} not found")
            node = found
    return node


def normalized_source(target: str, root: Path = ROOT) -> str:
    """Normalized source of ``target``, plus the transitive closure of same-module top-level
    definitions it references by bare ``ast.Name`` id (sorted by name, deterministic order).
    """
    module, _, qual = target.partition(":")
    tree = ast.parse(module_path(module, root).read_text(encoding="utf-8"))
    if not qual:
        return ast.unparse(_strip_docstrings(tree))
    node: ast.AST = tree
    target_name = None
    for part in qual.split("."):
        found = _find(getattr(node, "body", []), part)
        if found is None:
            raise FingerprintError(f"{target!r}: {part!r} not found")
        node = found
        target_name = part
    defs = _module_defs(tree)
    closure: set[str] = set()
    frontier: list[ast.AST] = [node]
    while frontier:
        n = frontier.pop()
        for name in _referenced_names(n):
            if name in defs and name not in closure and name != target_name:
                closure.add(name)
                frontier.append(defs[name])
    parts = [ast.unparse(_strip_docstrings(node))]
    parts += [ast.unparse(_strip_docstrings(defs[name])) for name in sorted(closure)]
    return "\n".join(parts)


def _data_content(target: str, root: Path = ROOT) -> str:
    """Canonical JSON of a ``data:<repo-relative path>`` target's YAML/JSON content."""
    rel = target[len(DATA_TARGET_PREFIX):]
    path = Path(root, rel)
    if not path.is_file():
        raise FingerprintError(f"data target {target!r}: file not found: {path}")
    text = path.read_text(encoding="utf-8")
    data = json.loads(text) if path.suffix == ".json" else yaml.safe_load(text)
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def fingerprint_target(target: str, root: Path = ROOT) -> str:
    if target.startswith(DATA_TARGET_PREFIX):
        return hashlib.sha256(_data_content(target, root).encode()).hexdigest()[:16]
    return hashlib.sha256(normalized_source(target, root).encode()).hexdigest()[:16]


def lib_versions(libs: tuple[str, ...]) -> dict[str, str]:
    out: dict[str, str] = {}
    for lib in libs:
        if lib == "openfoam":
            try:
                out[lib] = ast.literal_eval(_resolve_node("fansim.cfd.runner:DEFAULT_IMAGE").value)
            except ValueError as e:
                raise FingerprintError(f"cannot evaluate fansim.cfd.runner:DEFAULT_IMAGE: {e}") from e
        else:
            try:
                out[lib] = importlib.metadata.version(lib)
            except importlib.metadata.PackageNotFoundError:
                out[lib] = "missing"
    return out


def _unit_fields_json(unit) -> str:
    return json.dumps(
        {
            "id": unit.id,
            "targets": list(unit.targets),
            "claim": unit.claim,
            "source": unit.source,
            "regime": unit.regime,
            "checks": list(unit.checks),
            "depends_on": list(unit.depends_on),
            "libs": list(unit.libs),
        },
        sort_keys=True,
    )


def _checks_source(check: str, root: Path) -> str:
    tree = ast.parse(Path(root, check).read_text(encoding="utf-8"))
    return ast.unparse(_strip_docstrings(tree))


def fingerprint_unit(unit, root: Path = ROOT) -> str:
    parts = [f"{t}={fingerprint_target(t, root)}" for t in sorted(unit.targets)]
    parts += [f"lib:{k}={v}" for k, v in sorted(lib_versions(unit.libs).items())]
    parts.append(f"unit={_unit_fields_json(unit)}")
    for c in sorted(unit.checks):
        if not c.startswith("ref:"):
            parts.append(f"check:{c}={_checks_source(c, root)}")
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()[:16]
