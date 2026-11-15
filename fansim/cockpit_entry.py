"""Console script for the design cockpit.

``fansim-cockpit`` wraps ``scripts/cockpit.py``. A wheel has no ``scripts/``
tree, so the build copies that file to ``fansim/_bundled_cockpit.py``.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def cockpit_script() -> Path:
    """Return ``scripts/cockpit.py`` in a checkout, else the wheel copy."""
    repo_script = Path(__file__).resolve().parents[1] / "scripts" / "cockpit.py"
    if repo_script.is_file():
        return repo_script
    bundled = Path(__file__).resolve().parent / "_bundled_cockpit.py"
    if bundled.is_file():
        return bundled
    raise FileNotFoundError("scripts/cockpit.py is not available")


def main() -> None:
    script = cockpit_script()
    spec = importlib.util.spec_from_file_location("fansim_cockpit_script", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    raise SystemExit(module.main())


if __name__ == "__main__":
    sys.argv[0] = "fansim-cockpit"
    main()
