"""Standalone entry for surrogate-guided search (roadmap §20.5).

Thin wrapper around ``run_optimization.py --surrogate-guided`` so campaigns can
run without the full CFD study path. Docker is only required with ``--verify-cfd``.

Usage (PowerShell)::

    uv run python scripts/run_surrogate_search.py --out runs/surr --doe 24 --top-k 4
    uv run python scripts/run_surrogate_search.py --out runs/surr --verify-cfd
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))


def main() -> int:
    argv = list(sys.argv[1:])
    if "--surrogate-guided" not in argv:
        argv = ["--surrogate-guided", *argv]
    sys.argv = [sys.argv[0], *argv]

    opt_path = Path(__file__).resolve().parent / "run_optimization.py"
    spec = importlib.util.spec_from_file_location("run_optimization", opt_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return int(mod.main())


if __name__ == "__main__":
    raise SystemExit(main())
