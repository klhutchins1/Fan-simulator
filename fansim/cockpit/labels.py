"""English names for optimizer run folders. Folder ids on disk stay unchanged."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

_DEFAULT = Path(__file__).resolve().parents[2] / "config" / "run_labels.yaml"


@lru_cache(maxsize=4)
def _load(path: str) -> dict[str, str]:
    p = Path(path)
    if not p.exists():
        return {}
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return {str(k): str(v) for k, v in data.items()}


def run_label(run_id: str, labels_path: Path | None = None) -> str:
    """Return the human label for a run folder, or the folder name if unknown."""
    if not run_id:
        return ""
    path = str(labels_path or _DEFAULT)
    named = _load(path).get(run_id)
    if named:
        return named
    from fansim.optimize.cli_argv import run_label as stamped_label  # cockpit_opt_<stamp> → date

    return stamped_label(run_id)
