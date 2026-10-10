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


def session_tmp(name: str) -> Path:
    """``<temp>/fansim_<pid>/<name>``: this cockpit's own scratch file.

    The preview STL, its progress and meta sidecars used fixed names in the system temp folder, so
    every cockpit on the machine shared them: a second cockpit overwrote the first's preview, and a
    leftover progress file seeded the next Preview's bar at "stage 4/4" (QA UI-30, UI-4).
    """
    import os
    import tempfile

    d = Path(tempfile.gettempdir()) / f"fansim_{os.getpid()}"
    d.mkdir(parents=True, exist_ok=True)
    return d / name
