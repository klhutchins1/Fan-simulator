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
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


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
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == name:
            return node
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == name for t in node.targets
        ):
            return node
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name:
            return node
    return None


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
    node = _resolve_node(target, root)
    return ast.unparse(_strip_docstrings(node))


def fingerprint_target(target: str, root: Path = ROOT) -> str:
    return hashlib.sha256(normalized_source(target, root).encode()).hexdigest()[:16]


def lib_versions(libs: tuple[str, ...]) -> dict[str, str]:
    out: dict[str, str] = {}
    for lib in libs:
        if lib == "openfoam":
            out[lib] = ast.literal_eval(_resolve_node("fansim.cfd.runner:DEFAULT_IMAGE").value)
        else:
            try:
                out[lib] = importlib.metadata.version(lib)
            except importlib.metadata.PackageNotFoundError:
                out[lib] = "missing"
    return out


def fingerprint_unit(unit, root: Path = ROOT) -> str:
    parts = [f"{t}={fingerprint_target(t, root)}" for t in sorted(unit.targets)]
    parts += [f"lib:{k}={v}" for k, v in sorted(lib_versions(unit.libs).items())]
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()[:16]
