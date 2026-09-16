"""Cockpit error reporting helpers (§15.4)."""

from __future__ import annotations

import logging
from pathlib import Path

from fansim.cockpit.errors import log_caught, set_state_error


def test_log_caught_returns_summary(caplog):
    log = logging.getLogger("fansim.cockpit.errors_test")
    with caplog.at_level(logging.WARNING, logger=log.name):
        summary = log_caught(log, "Preview", ValueError("boom"))
    assert "ValueError: boom" in summary
    assert any("Preview" in r.message for r in caplog.records)


def test_set_state_error_writes_msg_attr(caplog):
    class _S:
        preview_msg = ""

    state = _S()
    log = logging.getLogger("fansim.cockpit.errors_test2")
    with caplog.at_level(logging.ERROR, logger=log.name):
        set_state_error(state, "preview_msg", "Assess", RuntimeError("no docker"), log=log)
    assert "Assess" in state.preview_msg
    assert "RuntimeError" in state.preview_msg


def test_fan_tab_has_no_bare_silent_pass():
    """§15.4 stage-a: every ``except Exception`` in the Fan tab must log or surface.

    The Fan tab is the coordinator (fan_tab.py) plus the per-domain binders (§13.9); the
    exception handling lives in the binders now, so the guarantee is checked across all of them.
    """
    import re

    root = Path("fansim/cockpit")
    modules = [
        "fan_tab.py", "fan_core.py", "fan_models.py", "fan_editor.py", "fan_viz.py",
        "fan_export.py", "fan_library.py", "fan_assess.py", "fan_optimize.py", "fan_trials.py",
    ]
    combined = ""
    for name in modules:
        text = (root / name).read_text(encoding="utf-8")
        combined += text
        # Bare ``except Exception:`` / ``except Exception:  # noqa`` followed by only ``pass``.
        bad = re.findall(
            r"except Exception(?: as \w+)?(?:[^\n]*)?:\n[ \t]+pass\b",
            text,
        )
        assert not bad, f"silent except/pass still present in {name} ({len(bad)}): {bad[:3]}"
    # The logging helper is still wired into the Fan tab (not stripped by the split).
    assert "from fansim.cockpit.errors import log_caught" in combined
