"""Load/save BladeParams from YAML so designs are configurable and reproducible."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import yaml

from fansim.geometry.blade import BladeParams, RadialStation
from fansim.geometry.features import Features


def blade_params_from_dict(data: dict) -> BladeParams:
    """Build BladeParams from a plain dict (e.g. parsed YAML)."""
    data = dict(data)
    stations = data.pop("stations", None)
    features = data.pop("features", None)
    params = BladeParams(**data)
    if stations is not None:
        params.stations = [RadialStation(**s) for s in stations]
    if features is not None:
        params.features = Features(**features)
    return params


def load_blade_params(path: str | Path) -> BladeParams:
    """Load a BladeParams definition from a YAML file."""
    with open(path) as fh:
        data = yaml.safe_load(fh) or {}
    return blade_params_from_dict(data)


def save_blade_params(params: BladeParams, path: str | Path) -> Path:
    """Serialize BladeParams to YAML (round-trips through load_blade_params)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as fh:
        yaml.safe_dump(asdict(params), fh, sort_keys=False)
    return path
