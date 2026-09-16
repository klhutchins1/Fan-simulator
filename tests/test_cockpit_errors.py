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
    """§15.4 stage-a: every ``except Exception`` in fan_tab must log or surface."""
    import re

    text = Path("fansim/cockpit/fan_tab.py").read_text(encoding="utf-8")
    # Bare ``except Exception:`` / ``except Exception:  # noqa`` followed by only ``pass``.
    bad = re.findall(
        r"except Exception(?: as \w+)?(?:[^\n]*)?:\n[ \t]+pass\b",
        text,
    )
    assert not bad, f"silent except/pass still present ({len(bad)}): {bad[:3]}"
    assert "from fansim.cockpit.errors import log_caught" in text
