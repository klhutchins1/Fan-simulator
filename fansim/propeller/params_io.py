"""Prop Design flat ↔ BladeParams (roadmap §14.1).

Chord values in flats are fractions of tip radius (legacy Optimize / cockpit). Pitch still
drives geometric twist; Design knobs layer planform, thickness, camber, and 3-D shape on top.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from fansim.geometry.blade import BladeParams, apply_tip_shape
from fansim.prop_spec import PropSpec
from fansim.propeller.geometry import prop_blade_params

# Keys persisted on Optimize / Analyze rows (plus n_blades / pitch_in).
PROP_DESIGN_KEYS = (
    "chord_root", "chord_mid", "chord_tip",
    "thickness_root", "thickness_mid", "thickness_tip",
    "camber_root", "camber_mid", "camber_tip",
    "camber_pos",
    "sweep_mid", "sweep_tip",
    "lean_mid", "lean_tip",
    "le_sweep_mid", "le_sweep_tip",
    "le_skew_mid", "le_skew_tip",
    "tip_round", "tip_round_start",
    "cylindrical_tip",
    "thick_mode", "thick_mm",
)

_DEFAULTS = {
    "chord_root": 0.20, "chord_mid": 0.26, "chord_tip": 0.10,
    "thickness_root": 0.09, "thickness_mid": 0.06, "thickness_tip": 0.04,
    "camber_root": 0.04, "camber_mid": 0.04, "camber_tip": 0.04,
    "camber_pos": 0.4,
    "sweep_mid": 0.0, "sweep_tip": 3.0,
    "lean_mid": 0.0, "lean_tip": 0.0,
    "le_sweep_mid": 0.0, "le_sweep_tip": 0.0,
    "le_skew_mid": 0.0, "le_skew_tip": 0.0,
    "tip_round": 0.0, "tip_round_start": 0.80,
    "cylindrical_tip": True,
    "thick_mode": "tapered", "thick_mm": 1.5,
}


def prop_design_defaults() -> dict[str, Any]:
    return dict(_DEFAULTS)


def _f(flat: dict, key: str) -> float:
    if key in flat and flat[key] is not None:
        return float(flat[key])
    return float(_DEFAULTS[key])


def prop_params_from_flat(spec: PropSpec, flat: dict | None = None) -> BladeParams:
    """Rebuild prop BladeParams from an Optuna / cockpit flat (missing keys → defaults).

    Backward compatible: legacy ``camber`` fills all three camber stations when
    ``camber_root/mid/tip`` are absent.
    """
    flat = flat or {}
    cam_legacy = flat.get("camber")
    cam_r = float(flat["camber_root"]) if "camber_root" in flat else (
        float(cam_legacy) if cam_legacy is not None else _DEFAULTS["camber_root"])
    cam_m = float(flat["camber_mid"]) if "camber_mid" in flat else (
        float(cam_legacy) if cam_legacy is not None else _DEFAULTS["camber_mid"])
    cam_t = float(flat["camber_tip"]) if "camber_tip" in flat else (
        float(cam_legacy) if cam_legacy is not None else _DEFAULTS["camber_tip"])

    thick = (
        _f(flat, "thickness_root"),
        _f(flat, "thickness_mid"),
        _f(flat, "thickness_tip"),
    )
    mode = str(flat.get("thick_mode") or _DEFAULTS["thick_mode"]).lower()
    bp = prop_blade_params(
        spec,
        chord_frac=(_f(flat, "chord_root"), _f(flat, "chord_mid"), _f(flat, "chord_tip")),
        thickness=thick,
        camber=(cam_r, cam_m, cam_t),
        camber_pos=_f(flat, "camber_pos"),
        sweep_mid=_f(flat, "sweep_mid"),
        sweep_tip=_f(flat, "sweep_tip"),
        lean_mid=_f(flat, "lean_mid"),
        lean_tip=_f(flat, "lean_tip"),
        le_sweep_mid=_f(flat, "le_sweep_mid"),
        le_sweep_tip=_f(flat, "le_sweep_tip"),
        le_skew_mid=_f(flat, "le_skew_mid"),
        le_skew_tip=_f(flat, "le_skew_tip"),
        cylindrical_tip=bool(flat.get("cylindrical_tip", _DEFAULTS["cylindrical_tip"])),
    )
    if mode == "uniform":
        thick_mm = _f(flat, "thick_mm")
        for st in bp.stations:
            c = max(float(st.chord), 1e-3)
            st.thickness = float(thick_mm) / c
    tip_round = _f(flat, "tip_round")
    if tip_round > 0.0:
        apply_tip_shape(bp, tip_round=tip_round, start_frac=_f(flat, "tip_round_start"))
    return bp


def prop_flat_from_params(params: BladeParams, *, pitch_in: float) -> dict[str, Any]:
    """Flatten a prop BladeParams (+ pitch) into a Design / Optimize row dict."""
    st = sorted(params.stations, key=lambda s: s.r_frac)
    root, mid, tip = st[0], min(st, key=lambda s: abs(s.r_frac - 0.5)), st[-1]
    R = float(params.tip_radius)
    cr = float(root.chord) / R
    cm = float(mid.chord) / R
    ct = float(tip.chord) / R
    th_r, th_m, th_t = float(root.thickness), float(mid.thickness), float(tip.thickness)
    ar, am, at = th_r * float(root.chord), th_m * float(mid.chord), th_t * float(tip.chord)
    thick_mode = (
        "uniform" if abs(ar - am) < 0.12 and abs(am - at) < 0.12 else "tapered"
    )
    return {
        "n_blades": int(params.n_blades),
        "pitch_in": float(pitch_in),
        "chord_root": cr, "chord_mid": cm, "chord_tip": ct,
        "thickness_root": th_r, "thickness_mid": th_m, "thickness_tip": th_t,
        "camber_root": float(root.max_camber),
        "camber_mid": float(mid.max_camber),
        "camber_tip": float(tip.max_camber),
        "camber": float(mid.max_camber),  # legacy alias
        "camber_pos": float(mid.camber_pos),
        "sweep_mid": float(mid.sweep), "sweep_tip": float(tip.sweep),
        "lean_mid": float(mid.lean_deg), "lean_tip": float(tip.lean_deg),
        "le_sweep_mid": float(mid.le_sweep), "le_sweep_tip": float(tip.le_sweep),
        "le_skew_mid": float(getattr(mid, "le_skew", 0.0) or 0.0),
        "le_skew_tip": float(getattr(tip, "le_skew", 0.0) or 0.0),
        "tip_round": 0.0, "tip_round_start": 0.80,
        "cylindrical_tip": bool(getattr(params, "cylindrical_tip", True)),
        "thick_mode": thick_mode,
        "thick_mm": round((ar + am + at) / 3.0, 2),
    }


def spec_with_flat(spec: PropSpec, flat: dict) -> PropSpec:
    """Apply n_blades + pitch_in from flat onto a PropSpec envelope."""
    return dataclasses.replace(
        spec,
        n_blades=int(flat.get("n_blades", spec.n_blades)),
        pitch_in=float(flat.get("pitch_in", spec.pitch_in)),
    )
