"""Fixed geometry vector for the catalog GP (roadmap §7.4)."""

from __future__ import annotations

import numpy as np

from fansim.geometry.blade import BladeParams

FEATURE_KEYS = (
    "n_blades", "hub_radius", "tip_radius",
    "stagger_root", "stagger_mid", "stagger_tip",
    "chord_root", "chord_mid", "chord_tip",
    "sweep_mid", "sweep_tip",
    "lean_mid", "lean_tip", "max_camber",
    "shroud_thick_mm", "shroud_height_frac",
)

_REQUIRED = (
    "n_blades",
    "stagger_root", "stagger_mid", "stagger_tip",
    "chord_root", "chord_mid", "chord_tip",
)


def _optional_defaults() -> dict:
    bp = BladeParams()
    return {
        "hub_radius": float(bp.hub_radius),
        "tip_radius": float(bp.tip_radius),
        "sweep_mid": 0.0, "sweep_tip": 0.0,
        "lean_mid": 0.0, "lean_tip": 0.0,
        "max_camber": 0.0,
        "shroud_thick_mm": 0.0,
        "shroud_height_frac": 1.0,
    }


def _from_blade(bp: BladeParams) -> dict:
    if len(bp.stations) < 3:
        raise ValueError("need 3 stations")
    root, mid, tip = bp.stations[0], bp.stations[1], bp.stations[2]
    return {
        "n_blades": bp.n_blades,
        "hub_radius": bp.hub_radius,
        "tip_radius": bp.tip_radius,
        "stagger_root": root.stagger_deg,
        "stagger_mid": mid.stagger_deg,
        "stagger_tip": tip.stagger_deg,
        "chord_root": root.chord,
        "chord_mid": mid.chord,
        "chord_tip": tip.chord,
        "sweep_mid": mid.sweep,
        "sweep_tip": tip.sweep,
        "lean_mid": mid.lean_deg,
        "lean_tip": tip.lean_deg,
        "max_camber": mid.max_camber,
        "shroud_thick_mm": float(bp.shroud_thick_mm or 0.0),
        "shroud_height_frac": float(bp.shroud_height_frac if bp.shroud_height_frac is not None else 1.0),
    }


def feature_vector(src: BladeParams | dict) -> np.ndarray:
    """16-D geometry vector. Raises ValueError if required keys/stations are missing."""
    if isinstance(src, BladeParams):
        src = _from_blade(src)
    missing = [k for k in _REQUIRED if src.get(k) is None]
    if missing:
        raise ValueError(f"incomplete geometry vector: missing {missing}")
    d = {**_optional_defaults(), **{k: src[k] for k in src if src.get(k) is not None}}
    return np.array([float(d[k]) for k in FEATURE_KEYS], dtype=float)


def would_skip(mu: float, sigma: float, floor: float) -> bool:
    """True when the GP is confident free-delivery CFM is below the floor (kappa=1)."""
    return float(floor) > 0.0 and (float(mu) + float(sigma)) < float(floor)
