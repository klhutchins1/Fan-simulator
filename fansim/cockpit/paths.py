"""Project-anchored cockpit folders (not relative to wherever the cockpit was launched)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def exports_dir() -> Path:
    """``<project>/exports``: every tab's STL/STEP exports, also served for browser download.

    Was ``Path("exports")`` per tab, i.e. relative to the launch directory, so a cockpit started
    from elsewhere wrote (and served) a different folder (QA UI-19).
    """
    return ROOT / "exports"
