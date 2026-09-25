"""Status: only changed / affected / new units need re-audit."""

from __future__ import annotations

import importlib.util
from io import StringIO
from pathlib import Path
from unittest import mock

from fansim.audit.registry import Registry, Unit
from fansim.audit.status import State, classify, find_unregistered, load_ledger, record_pass


def _u(uid, deps=(), targets=("m",)):
    return Unit(uid, tuple(targets), "c", {"kind": "derivation"}, {}, (), tuple(deps), ())


REG = Registry(units={"a": _u("a"), "b": _u("b", ["a"]), "c": _u("c", ["b"]), "d": _u("d")},
               exempt=())


def _ledger(**fps):
    return {"units": {k: {"fingerprint": v, "verdict": "PASS"} for k, v in fps.items()}}


def test_all_proven():
    fps = {"a": "1", "b": "2", "c": "3", "d": "4"}
    st = classify(REG, _ledger(**fps), fps)
    assert set(st.values()) == {State.PROVEN}


def test_change_propagates_transitively_but_not_sideways():
    led = _ledger(a="1", b="2", c="3", d="4")
    st = classify(REG, led, {"a": "X", "b": "2", "c": "3", "d": "4"})
    assert st == {"a": State.CHANGED, "b": State.AFFECTED, "c": State.AFFECTED, "d": State.PROVEN}


def test_never_passed_is_new_and_blocks_dependents():
    led = _ledger(b="2", c="3", d="4")
    st = classify(REG, led, {"a": "1", "b": "2", "c": "3", "d": "4"})
    assert st["a"] is State.NEW and st["b"] is State.AFFECTED and st["c"] is State.AFFECTED


def test_record_pass_round_trip(tmp_path):
    p = tmp_path / "ledger.json"
    record_pass("a", "abc", "docs/validation/audits/x.md", "2026-09-24", path=p)
    led = load_ledger(p)
    assert led["units"]["a"] == {"fingerprint": "abc", "verdict": "PASS", "date": "2026-09-24",
                                 "report": "docs/validation/audits/x.md"}


def test_find_unregistered(tmp_path: Path):
    pkg = tmp_path / "phys"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "m1.py").write_text("def covered():\n    pass\n\ndef loose():\n    pass\n\n"
                               "def _private():\n    pass\n\nclass K:\n    pass\n", encoding="utf-8")
    (pkg / "m2.py").write_text("def whole():\n    pass\n", encoding="utf-8")
    (pkg / "m3.py").write_text("def skipme():\n    pass\n", encoding="utf-8")
    reg = Registry(units={"x": _u("x", targets=("phys.m1:covered", "phys.m2"))},
                   exempt=("phys.m3:*",))
    assert find_unregistered(reg, ("phys",), tmp_path) == ["phys.m1:K", "phys.m1:loose"]


def test_cli_missing_path():
    """Test that CLI properly reports MISSING units when targets cannot be resolved."""
    import json
    # Load audit_status.py as a module
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "audit_status.py"
    spec = importlib.util.spec_from_file_location("audit_status_test", script_path)
    audit_status = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit_status)

    # Create a registry with one real unit and one with missing target
    real_unit = _u("real", targets=("fansim.audit.status",))
    missing_unit = _u("missing", targets=("fansim.does_not_exist",))
    test_registry = Registry(
        units={"real": real_unit, "missing": missing_unit},
        exempt=()
    )

    # Patch the imported functions in the audit_status module
    with mock.patch.object(audit_status, "load_registry", return_value=test_registry):
        with mock.patch.object(audit_status, "load_ledger", return_value={"units": {}}):
            with mock.patch.object(audit_status, "find_unregistered", return_value=[]):
                # Test main([])
                output = StringIO()
                with mock.patch("sys.stdout", output):
                    ret = audit_status.main([])
                stdout = output.getvalue()
                assert ret == 1, f"Expected return code 1, got {ret}"
                assert "MISSING" in stdout, f"Expected 'MISSING' in stdout: {stdout}"
                assert "missing" in stdout, f"Expected unit id 'missing' in stdout: {stdout}"
                assert "NEW=1" in stdout, f"Expected 'NEW=1' in stdout: {stdout}"
                assert "MISSING=1" in stdout, f"Expected 'MISSING=1' in stdout: {stdout}"

                # Test main(["--json"])
                output = StringIO()
                with mock.patch("sys.stdout", output):
                    ret = audit_status.main(["--json"])
                stdout = output.getvalue()
                assert ret == 1, f"Expected return code 1 for --json, got {ret}"
                data = json.loads(stdout)
                assert "missing" in data, f"Expected 'missing' key in JSON: {data}"
                assert "missing" in data["missing"], f"Expected 'missing' unit id in 'missing' dict: {data}"
                assert "missing" not in data["units"], f"'missing' unit should not be in 'units': {data}"
