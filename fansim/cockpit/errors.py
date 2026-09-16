"""Cockpit error reporting — never swallow an action failure silently (§15.4)."""

from __future__ import annotations

import logging
from typing import Any


def log_caught(
    log: logging.Logger,
    where: str,
    exc: BaseException,
    *,
    level: int = logging.WARNING,
) -> str:
    """Log a caught exception; return a short user-facing message fragment."""
    summary = f"{type(exc).__name__}: {exc}"
    log.log(level, "%s: %s", where, summary, exc_info=level >= logging.ERROR)
    return summary


def set_state_error(
    state: Any,
    msg_attr: str,
    where: str,
    exc: BaseException,
    *,
    log: logging.Logger,
    prefix: str = "⚠",
) -> str:
    """Log + write ``state.<msg_attr>`` with a visible error line."""
    summary = log_caught(log, where, exc, level=logging.ERROR)
    text = f"{prefix} {where}: {summary}"
    setattr(state, msg_attr, text)
    return text
