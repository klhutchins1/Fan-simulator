"""Status: only changed / affected / new units need re-audit."""

from __future__ import annotations

from pathlib import Path

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
