"""Persist OpenFOAM field snapshots for a future FNO (roadmap §7.4).

Stage 1 does **not** train an operator. It copies the latest time-directory field
files (``U``, ``p``, …) plus a JSON manifest so later work has on-disk tensors /
raw OF ASCII to ingest.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path


DEFAULT_FIELDS = ("U", "p")


def _latest_time_dir(case_dir: Path) -> Path | None:
    best: tuple[float, Path] | None = None
    for p in case_dir.iterdir():
        if not p.is_dir():
            continue
        try:
            t = float(p.name)
        except ValueError:
            continue
        if t <= 0.0:
            continue
        if best is None or t > best[0]:
            best = (t, p)
    return None if best is None else best[1]


def ingest_case_fields(
    case_dir: str | Path,
    dest: str | Path,
    *,
    fields: tuple[str, ...] = DEFAULT_FIELDS,
    label: str | None = None,
) -> dict:
    """Copy latest non-zero time fields into ``dest`` and write ``manifest.json``."""
    case_dir = Path(case_dir)
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    time_dir = _latest_time_dir(case_dir)
    if time_dir is None:
        # Fall back to 0/ (mesh-only / dry cases).
        time_dir = case_dir / "0"
    if not time_dir.is_dir():
        raise FileNotFoundError(f"no OpenFOAM time directory under {case_dir}")

    copied: list[str] = []
    missing: list[str] = []
    for name in fields:
        src = time_dir / name
        if src.is_file():
            shutil.copy2(src, dest / name)
            copied.append(name)
        else:
            missing.append(name)

    manifest = {
        "label": label or dest.name,
        "case_dir": str(case_dir.resolve()),
        "time_dir": str(time_dir.resolve()),
        "time": time_dir.name,
        "fields_copied": copied,
        "fields_missing": missing,
        "format": "openfoam_ascii",
        "fno_ready": False,  # true only after a numeric tensor pack exists
        "note": "Raw OF field ASCII for future FNO ingest; not a trained operator.",
    }
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def list_snapshots(root: str | Path) -> list[dict]:
    root = Path(root)
    if not root.is_dir():
        return []
    rows = []
    for child in sorted(root.iterdir()):
        man = child / "manifest.json"
        if man.is_file():
            rows.append(json.loads(man.read_text(encoding="utf-8")))
    return rows


def snapshots_available(root: str | Path) -> bool:
    return bool(list_snapshots(root))
