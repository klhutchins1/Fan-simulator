"""CROR Design flat ↔ CrorParams (roadmap §14.5)."""

from __future__ import annotations

from fansim.cror.geometry import CrorParams
from fansim.geometry.blade import BladeParams, RadialStation, apply_tip_shape


def _stations(
    *,
    chord_root: float,
    chord_mid: float,
    chord_tip: float,
    stagger: float,
    thickness_root: float,
    thickness_mid: float,
    thickness_tip: float,
    camber_root: float,
    camber_mid: float,
    camber_tip: float,
    sweep_mid: float = 0.0,
    sweep_tip: float = 0.0,
    lean_tip: float = 0.0,
    le_skew_mid: float = 0.0,
    le_skew_tip: float = 0.0,
) -> list[RadialStation]:
    s = float(stagger)
    return [
        RadialStation(
            0.0, chord_root, s, thickness_root, camber_root, 0.4, 0.0, 0.0, 0.0),
        RadialStation(
            0.5, chord_mid, s * 0.9, thickness_mid, camber_mid, 0.4,
            sweep_mid, 0.0, 0.0, le_skew=le_skew_mid),
        RadialStation(
            1.0, chord_tip, s * 0.8, thickness_tip, camber_tip, 0.4,
            sweep_tip, 0.0, lean_tip, le_skew=le_skew_tip),
    ]


def _g(flat: dict, *keys: str, default: float) -> float:
    for k in keys:
        if k in flat and flat[k] is not None:
            return float(flat[k])
    return float(default)


def _blade(
    flat: dict,
    *,
    prefix: str,
    n_blades: int,
    sign: float,
    hub_radius: float,
    tip_radius: float,
) -> BladeParams:
    p = prefix
    # Legacy Optuna: single chord_mm / stagger_deg for both rotors.
    legacy_chord = flat.get("chord_mm")
    legacy_stag = flat.get("stagger_deg")
    cr = _g(flat, f"{p}chord_root", "chord_root",
            default=float(legacy_chord) if legacy_chord is not None else 14.0)
    cm = _g(flat, f"{p}chord_mid", "chord_mid", default=cr)
    ct = _g(flat, f"{p}chord_tip", "chord_tip",
            default=(float(legacy_chord) * 0.75 if legacy_chord is not None else cr * 0.75))
    stag_abs = _g(
        flat, f"{p}stagger", "stagger",
        default=abs(float(legacy_stag)) if legacy_stag is not None else 40.0)
    stag = abs(stag_abs) * (1.0 if sign > 0 else -1.0)
    bp = BladeParams(
        n_blades=int(n_blades),
        hub_radius=hub_radius,
        tip_radius=tip_radius,
        stations=_stations(
            chord_root=cr, chord_mid=cm, chord_tip=ct, stagger=stag,
            thickness_root=_g(flat, f"{p}thickness_root", default=0.10),
            thickness_mid=_g(flat, f"{p}thickness_mid", default=0.08),
            thickness_tip=_g(flat, f"{p}thickness_tip", default=0.06),
            camber_root=_g(flat, f"{p}camber_root", default=0.04),
            camber_mid=_g(flat, f"{p}camber_mid", default=0.04),
            camber_tip=_g(flat, f"{p}camber_tip", default=0.04),
            sweep_mid=_g(flat, f"{p}sweep_mid", default=0.0),
            sweep_tip=_g(flat, f"{p}sweep_tip", default=0.0),
            lean_tip=_g(flat, f"{p}lean_tip", default=0.0),
            le_skew_mid=_g(flat, f"{p}le_skew_mid", default=0.0),
            le_skew_tip=_g(flat, f"{p}le_skew_tip", default=0.0),
        ),
        cylindrical_tip=bool(flat.get(f"{p}cylindrical_tip", True)),
        chord_basis=str(flat.get(f"{p}chord_basis") or flat.get("chord_basis") or "measured"),
    )
    tip_round = _g(flat, f"{p}tip_round", default=0.0)
    if tip_round > 0.0:
        apply_tip_shape(
            bp, tip_round=tip_round,
            start_frac=_g(flat, f"{p}tip_round_start", default=0.80))
    return bp


def cror_params_from_flat(
    flat: dict | None = None,
    *,
    tip_radius: float = 55.0,
    hub_radius: float = 18.0,
) -> CrorParams:
    """Rebuild CrorParams from Design / Optuna flat (legacy keys supported)."""
    flat = dict(flat or {})
    # Compact Optimize space stores mid only — expand to root/tip when missing.
    for pref in ("f_", "r_"):
        if f"{pref}thickness_mid" in flat and f"{pref}thickness_root" not in flat:
            mid = float(flat[f"{pref}thickness_mid"])
            flat[f"{pref}thickness_root"] = mid + 0.02
            flat[f"{pref}thickness_tip"] = max(0.04, mid - 0.02)
        if f"{pref}camber_mid" in flat and f"{pref}camber_root" not in flat:
            c = float(flat[f"{pref}camber_mid"])
            flat[f"{pref}camber_root"] = c
            flat[f"{pref}camber_tip"] = c
    hub = float(flat.get("hub_radius", hub_radius))
    tip = float(flat.get("tip_radius", tip_radius))
    gap = float(flat.get("axial_gap_mm", 8.0))
    n_f = int(flat.get("n_front", flat.get("f_n_blades", 7)))
    n_r = int(flat.get("n_rear", flat.get("r_n_blades", 9)))
    front = _blade(flat, prefix="f_", n_blades=n_f, sign=+1.0,
                   hub_radius=hub, tip_radius=tip)
    rear = _blade(flat, prefix="r_", n_blades=n_r, sign=-1.0,
                  hub_radius=hub, tip_radius=tip)
    return CrorParams(front=front, rear=rear, axial_gap_mm=gap)


def cror_flat_from_params(params: CrorParams) -> dict:
    """Flatten for Design / Optimize persistence (prefixed f_/r_)."""

    def pack(blade: BladeParams, prefix: str) -> dict:
        st = sorted(blade.stations, key=lambda s: s.r_frac)
        root = st[0]
        mid = min(st, key=lambda s: abs(s.r_frac - 0.5))
        tip = st[-1]
        return {
            f"{prefix}chord_root": float(root.chord),
            f"{prefix}chord_mid": float(mid.chord),
            f"{prefix}chord_tip": float(tip.chord),
            f"{prefix}stagger": abs(float(root.stagger_deg)),
            f"{prefix}thickness_root": float(root.thickness),
            f"{prefix}thickness_mid": float(mid.thickness),
            f"{prefix}thickness_tip": float(tip.thickness),
            f"{prefix}camber_root": float(root.max_camber),
            f"{prefix}camber_mid": float(mid.max_camber),
            f"{prefix}camber_tip": float(tip.max_camber),
            f"{prefix}sweep_mid": float(mid.sweep),
            f"{prefix}sweep_tip": float(tip.sweep),
            f"{prefix}lean_tip": float(tip.lean_deg),
            f"{prefix}le_skew_mid": float(getattr(mid, "le_skew", 0.0) or 0.0),
            f"{prefix}le_skew_tip": float(getattr(tip, "le_skew", 0.0) or 0.0),
            f"{prefix}cylindrical_tip": bool(getattr(blade, "cylindrical_tip", True)),
            f"{prefix}chord_basis": str(getattr(blade, "chord_basis", "measured") or "measured"),
            f"{prefix}tip_round": 0.0,
            f"{prefix}tip_round_start": 0.80,
        }

    out = {
        "axial_gap_mm": float(params.axial_gap_mm),
        "hub_radius": float(params.front.hub_radius),
        "tip_radius": float(params.front.tip_radius),
        "n_front": int(params.front.n_blades),
        "n_rear": int(params.rear.n_blades),
        "f_n_blades": int(params.front.n_blades),
        "r_n_blades": int(params.rear.n_blades),
    }
    out.update(pack(params.front, "f_"))
    out.update(pack(params.rear, "r_"))
    return out
