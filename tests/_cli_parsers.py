"""Load script ``build_parser`` helpers without grepping source text."""

from __future__ import annotations

import importlib.util
from functools import lru_cache
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=8)
def load_build_parser(script: str):
    path = _ROOT / "scripts" / script
    name = f"_fansim_cli_{path.stem}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.build_parser
