"""The night queue never starts work that could reach the 4-9 PM peak window (AGENTS.md rule 2)."""
from __future__ import annotations

import datetime as dt
import importlib.util
import sys
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "night_queue", Path(__file__).resolve().parents[1] / "scripts" / "night_queue.py")
nq = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(nq)


def _t(h, m=0):
    return dt.datetime(2026, 10, 18, h, m)


def test_night_start_ok():
    assert nq.may_start(_t(0, 30), 2)
    assert nq.may_start(_t(21, 30), 8)          # ends 05:30 next day


def test_never_into_the_peak_window():
    assert not nq.may_start(_t(15, 30), 0.1)    # last start is before 15:30
    assert not nq.may_start(_t(17, 0), 0.1)     # inside 4-9 PM
    assert not nq.may_start(_t(14, 30), 2)      # would end 16:30
    assert nq.may_start(_t(13, 0), 2)           # ends 15:00
    assert not nq.may_start(_t(21, 0), 20)      # would end 17:00 next day


def test_python_means_this_venv():
    assert nq.resolve_cmd(["python", "-V"])[0] == sys.executable
    assert nq.resolve_cmd(["git", "python"]) == ["git", "python"]
