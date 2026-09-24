"""Helpers for prop CFD refine → airflow case selection."""

from __future__ import annotations

from pathlib import Path


def first_prop_cfd_workdir(rows: list[dict] | None) -> str | None:
    """First non-skipped refine row with a workdir, or None."""
    for row in rows or ():
        if row.get("skipped"):
            continue
        workdir = row.get("workdir")
        if workdir:
            return str(workdir)
    return None


def prop_cfd_workdir_from_study(study_dir: str | Path | None) -> str | None:
    """First solved ``cfd_*`` under ``study/cfd_refine``, or None."""
    if not study_dir:
        return None
    refine = Path(study_dir) / "cfd_refine"
    if not refine.is_dir():
        return None
    candidates = sorted(p for p in refine.glob("cfd_*") if p.is_dir())
    for path in candidates:
        if (path / "constant" / "polyMesh").is_dir() or (path / "0").is_dir():
            return str(path)
    return str(candidates[0]) if candidates else None
