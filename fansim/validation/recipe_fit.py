"""Pure update step for the section-fit of a parametric blade recipe to a reference STL.

One fixed-point iteration per station: measure the built section, compare with the reference target
and move the recipe parameter so the built section approaches the target (damped, clamped).
"""

from __future__ import annotations

DAMPING = 0.7

# (lo, hi) hard bounds per recipe field. Hitting one is reported, never silently accepted.
BOUNDS = {
    "chord": (5.0, 60.0),
    "stagger_deg": (5.0, 80.0),
    "thickness": (0.03, 0.25),
    "max_camber": (0.0, 0.25),
    "camber_pos": (0.2, 0.7),
    "sweep": (-10.0, 10.0),
    "skew": (-15.0, 30.0),
}

# Stop tolerances on the BUILT-vs-reference residuals.
TOL = {"stagger_deg": 1.5, "chord_rel": 0.03, "camber_ratio": 0.005, "thickness_rel": 0.10}

SWEEP_SKEW_TRIGGER_MM = 2.0


def _blend(old: float, target: float, damping: float) -> float:
    return old + damping * (target - old)


def update_station(st: dict, built: dict, ref: dict, damping: float = DAMPING,
                   adjust_sweep: bool = False, adjust_skew: bool = False,
                   d_le_z_mm: float = 0.0, d_skew_mm: float = 0.0,
                   bounds: dict | None = None) -> tuple[dict, list[str]]:
    """Return (new recipe station dict, names of fields that hit a clamp).

    ``st``: recipe fields (chord, stagger_deg, thickness, max_camber, camber_pos, sweep, skew, ...).
    ``built``/``ref``: measure_sections keys (chord_mm, stagger_deg, camber_ratio, camber_pos,
    thickness_ratio). Targets: stagger and camber_pos additive (ref - built), chord / max_camber /
    thickness multiplicative (ref / built); each move is damped toward its target and clamped.
    ``d_le_z_mm`` / ``d_skew_mm`` are (built - ref) LE offsets, applied only when adjusting.
    """
    b = BOUNDS if bounds is None else bounds
    new = dict(st)
    hit: list[str] = []

    def put(name: str, value: float) -> None:
        lo, hi = b[name]
        v = min(max(value, lo), hi)
        if v != value:
            hit.append(name)
        new[name] = float(v)

    put("stagger_deg", _blend(st["stagger_deg"],
                              st["stagger_deg"] + (ref["stagger_deg"] - built["stagger_deg"]),
                              damping))
    put("chord", _blend(st["chord"], st["chord"] * ref["chord_mm"] / built["chord_mm"], damping))
    if built["camber_ratio"] > 1e-4:
        put("max_camber", _blend(st["max_camber"],
                                 st["max_camber"] * ref["camber_ratio"] / built["camber_ratio"],
                                 damping))
    put("camber_pos", _blend(st["camber_pos"],
                             st["camber_pos"] + (ref["camber_pos"] - built["camber_pos"]), damping))
    put("thickness", _blend(st["thickness"],
                            st["thickness"] * ref["thickness_ratio"] / built["thickness_ratio"],
                            damping))
    if adjust_sweep:
        put("sweep", st["sweep"] - damping * d_le_z_mm)
    if adjust_skew:
        put("skew", st["skew"] - damping * d_skew_mm)
    return new, hit


def residuals(built: dict, ref: dict) -> dict:
    return {
        "stagger_deg": built["stagger_deg"] - ref["stagger_deg"],
        "chord_rel": built["chord_mm"] / ref["chord_mm"] - 1.0,
        "camber_ratio": built["camber_ratio"] - ref["camber_ratio"],
        "thickness_rel": built["thickness_ratio"] / ref["thickness_ratio"] - 1.0,
    }


def within_tol(res: dict) -> bool:
    return all(abs(res[k]) <= TOL[k] for k in TOL)
