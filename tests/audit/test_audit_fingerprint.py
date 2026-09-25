"""Fingerprints change on logic edits only (not comments / docstrings / formatting)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from fansim.audit.fingerprint import (
    FingerprintError,
    fingerprint_target,
    fingerprint_unit,
    lib_versions,
    normalized_source,
)
from fansim.audit.registry import Unit

BASE = '''"""Module doc."""
RHO = 1.2

def f(x):
    """Doc."""
    # comment
    return x * RHO

class C:
    def m(self):
        return 1
'''


def _pkg(tmp_path: Path, body: str) -> Path:
    (tmp_path / "pkgx").mkdir(exist_ok=True)
    (tmp_path / "pkgx" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "pkgx" / "mod.py").write_text(body, encoding="utf-8")
    return tmp_path


def test_comment_docstring_and_format_changes_are_ignored(tmp_path):
    root = _pkg(tmp_path, BASE)
    before = fingerprint_target("pkgx.mod:f", root)
    _pkg(tmp_path, BASE.replace('"""Doc."""', '"""Other doc."""')
         .replace("# comment", "# changed").replace("x * RHO", "x*RHO"))
    assert fingerprint_target("pkgx.mod:f", root) == before


def test_logic_change_is_detected(tmp_path):
    root = _pkg(tmp_path, BASE)
    before = fingerprint_target("pkgx.mod:f", root)
    _pkg(tmp_path, BASE.replace("x * RHO", "-x * RHO"))
    assert fingerprint_target("pkgx.mod:f", root) != before


def test_constant_method_and_module_targets(tmp_path):
    root = _pkg(tmp_path, BASE)
    assert "1.2" in normalized_source("pkgx.mod:RHO", root)
    assert "return 1" in normalized_source("pkgx.mod:C.m", root)
    whole = normalized_source("pkgx.mod", root)
    assert "Module doc" not in whole and "def f" in whole


def test_missing_target_raises(tmp_path):
    root = _pkg(tmp_path, BASE)
    with pytest.raises(FingerprintError):
        fingerprint_target("pkgx.mod:nope", root)
    with pytest.raises(FingerprintError):
        fingerprint_target("pkgx.missing", root)


def test_unit_fingerprint_includes_libs(tmp_path, monkeypatch):
    root = _pkg(tmp_path, BASE)
    u = Unit("u", ("pkgx.mod:f",), "c", {"kind": "derivation"}, {}, (), (), ("numpy",))
    a = fingerprint_unit(u, root)
    import fansim.audit.fingerprint as fp
    monkeypatch.setattr(fp, "lib_versions", lambda libs: {"numpy": "0.0-test"})
    assert fingerprint_unit(u, root) != a


def test_openfoam_lib_version_is_the_image_tag():
    from fansim.cfd.runner import DEFAULT_IMAGE
    assert lib_versions(("openfoam",)) == {"openfoam": DEFAULT_IMAGE}


CLOSURE_BASE = '''
def helper(x):
    return x * 2

def unrelated(y):
    return y + 1

def target(x):
    return helper(x) + CONST

CONST = 3
'''


def test_closure_includes_same_module_referenced_helper(tmp_path):
    root = _pkg(tmp_path, CLOSURE_BASE)
    before = fingerprint_target("pkgx.mod:target", root)
    _pkg(tmp_path, CLOSURE_BASE.replace("return x * 2", "return x * 3"))
    assert fingerprint_target("pkgx.mod:target", root) != before


def test_closure_ignores_unreferenced_sibling(tmp_path):
    root = _pkg(tmp_path, CLOSURE_BASE)
    before = fingerprint_target("pkgx.mod:target", root)
    _pkg(tmp_path, CLOSURE_BASE.replace("return y + 1", "return y + 2"))
    assert fingerprint_target("pkgx.mod:target", root) == before


def test_closure_terminates_on_cycles(tmp_path):
    body = '''
def a(x):
    return b(x)

def b(x):
    return a(x) + 1
'''
    root = _pkg(tmp_path, body)
    # Must not hang / recurse infinitely.
    assert fingerprint_target("pkgx.mod:a", root)


def test_closure_covers_dead_design_guard_via_same_module():
    # optimize.reject_dead_designs targets score_operating_point; intersect_fan_line lives in the
    # same module, so it must be covered by the closure without an explicit registry target.
    src = normalized_source("fansim.optimize.system_curve:score_operating_point")
    assert "intersect_fan_line" in src


def test_find_returns_last_binding(tmp_path):
    body = '''
def dup():
    return 1

def dup():
    return 2
'''
    root = _pkg(tmp_path, body)
    assert "return 2" in normalized_source("pkgx.mod:dup", root)


def test_unit_fingerprint_changes_when_checks_file_changes(tmp_path):
    root = _pkg(tmp_path, BASE)
    check = tmp_path / "check.py"
    check.write_text("def test_x():\n    assert 1 == 1\n", encoding="utf-8")
    u = Unit("u", ("pkgx.mod:f",), "c", {"kind": "derivation"}, {}, ("check.py",), (), ())
    before = fingerprint_unit(u, root)
    check.write_text("def test_x():\n    assert 1 == 2\n", encoding="utf-8")
    assert fingerprint_unit(u, root) != before


def test_unit_fingerprint_changes_when_claim_changes(tmp_path):
    root = _pkg(tmp_path, BASE)
    u1 = Unit("u", ("pkgx.mod:f",), "claim one", {"kind": "derivation"}, {}, (), (), ())
    u2 = Unit("u", ("pkgx.mod:f",), "claim two", {"kind": "derivation"}, {}, (), (), ())
    assert fingerprint_unit(u1, root) != fingerprint_unit(u2, root)


def test_unit_fingerprint_ignores_ref_checks(tmp_path):
    root = _pkg(tmp_path, BASE)
    u = Unit("u", ("pkgx.mod:f",), "c", {"kind": "derivation"}, {}, ("ref:something",), (), ())
    # Must not raise even though "ref:something" resolves to no real file.
    assert fingerprint_unit(u, root)


def test_lib_versions_reraises_value_error_as_fingerprint_error(monkeypatch):
    import ast as _ast

    import fansim.audit.fingerprint as fp

    def boom(target, root=fp.ROOT):
        class Bad:
            value = _ast.parse("foo()", mode="eval").body  # a Call node: not a literal
        return Bad()

    monkeypatch.setattr(fp, "_resolve_node", boom)
    with pytest.raises(FingerprintError):
        lib_versions(("openfoam",))


def test_openfoam_lookup_does_not_import_cfd():
    result = subprocess.run(
        [sys.executable, "-c",
         "import sys; from fansim.audit.fingerprint import lib_versions; "
         "v = lib_versions(('openfoam',)); print(v['openfoam'], 'fansim.cfd' in sys.modules)"],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True
    )
    last_line = result.stdout.strip().split('\n')[-1]
    assert last_line.endswith("False"), f"Expected 'False' at end of: {last_line}"
    assert last_line.split()[0].startswith("opencfd/"), f"Expected tag starting with opencfd/: {last_line}"
