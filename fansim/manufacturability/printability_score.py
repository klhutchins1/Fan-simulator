"""Graded printability difficulty — how hard a blade is to FDM-print, and which printer class it
needs. Complements the binary fdm_rules gate (which only checks the min wall) with a 0-100 difficulty
score and a recommended printer class, driven by geometry the optimizer already varies.

HONEST SCOPE: analytic heuristics, not a slicer. The score is a RELATIVE difficulty ranking + a
printer-class steer, under the assumption the part is printed hub-axis vertical (hub face down) —
re-orienting can trade one difficulty (overhang) for another. Thresholds are documented inline.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fansim.geometry.blade import BladeParams, blade_solidity
from fansim.manufacturability.fdm_rules import (
    MIN_WALL_PERIMETERS,
    DEFAULT_NOZZLE_MM,
    min_section_thickness_mm,
)

# Printer classes, easiest -> hardest. The recommendation is the hardest class any factor demands.
CLASS_EASY = "Easy FDM (no supports)"
CLASS_SUPPORTS = "FDM + supports"
CLASS_TRAPPED = "FDM + soluble/breakaway support (trapped regions)"
CLASS_RESIN = "Resin (SLA) — sub-FDM detail"


@dataclass
class DifficultyFactor:
    name: str
    severity: float   # 0 (trivial) .. 1 (dominant difficulty)
    note: str


@dataclass
class PrintabilityGrade:
    difficulty: float                 # 0 (trivial) .. 100 (very hard)
    printer_class: str
    factors: list[DifficultyFactor] = field(default_factory=list)  # worst first
    summary: str = ""


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def grade_printability(params: BladeParams, nozzle_mm: float = DEFAULT_NOZZLE_MM) -> PrintabilityGrade:
    """Graded difficulty + recommended printer class for one impeller design."""
    min_wall = MIN_WALL_PERIMETERS * nozzle_mm          # ~0.8 mm at a 0.4 mm nozzle
    factors: list[DifficultyFactor] = []
    needs_resin = False
    needs_trapped = False

    # 1) Wall thinness — radius-aware. The blade BODY needs a real 2-perimeter wall and drives the
    #    FDM difficulty; a thin TIP EDGE is a designed thin edge (prints as a single wall), so it only
    #    nudges difficulty and does NOT force resin.
    body_t = min_section_thickness_mm(params, body_only=True)
    overall_t = min_section_thickness_mm(params)
    wall_sev = _clamp01((1.5 - body_t) / (1.5 - 0.4))     # 1.5 mm -> 0, 0.4 mm -> 1 (body-driven)
    if body_t < min_wall:
        needs_resin = True
    note = f"body thinnest {body_t:.2f} mm vs {min_wall:.2f} mm min FDM wall"
    if body_t < min_wall:
        note += " — below FDM capability"
    elif overall_t < min_wall:                            # only the tip edge is thin -> printable
        note += f"; tip edge {overall_t:.2f} mm (thin but printable as a single wall)"
        wall_sev = max(wall_sev, 0.25)                    # a thin tip is a little harder, not resin-only
    factors.append(DifficultyFactor("Thin walls", wall_sev, note))

    # 2) Overhang — printed hub-down, a low-stagger blade lies flat and overhangs the bed. Overhang
    #    from vertical ~ 90-stagger; supports are usual once it exceeds ~45 deg (stagger < 45).
    stagger_min = min(s.stagger_deg for s in params.stations)
    overhang_sev = _clamp01((45.0 - stagger_min) / 45.0)   # stagger 45 -> 0, 0 deg -> 1
    factors.append(DifficultyFactor(
        "Overhang", overhang_sev,
        f"flattest blade angle {stagger_min:.0f} deg (hub-down) -> "
        f"~{max(0.0, 90.0 - stagger_min):.0f} deg overhang from vertical"))

    # 3) Tall-thin aspect — a wide, thin section prints as a tall wobbly wall even above the min wall.
    aspects = [s.chord / max(s.thickness * s.chord, 1e-6) for s in params.stations]  # = 1/thickness_frac
    aspect = max(aspects)
    aspect_sev = _clamp01((aspect - 15.0) / 45.0)         # 1/0.067=15 -> 0, 1/0.017=60 -> 1
    factors.append(DifficultyFactor(
        "Tall-thin walls", aspect_sev,
        f"max chord/thickness aspect {aspect:.0f}:1 (thin, wobbly walls)"))

    # 4) Fine surface features — bio-feature length scales below what FDM resolves need resin.
    feat = params.features
    if feat.active:
        span = max(params.tip_radius - params.hub_radius, 1e-6)
        chord_mean = sum(s.chord for s in params.stations) / len(params.stations)
        scales = []
        if feat.tubercle_amp > 0 and feat.tubercle_waves > 0:
            scales.append(span / feat.tubercle_waves)
        if feat.serration_amp > 0 and feat.serration_waves > 0:
            scales.append(span / feat.serration_waves)
        if feat.dimple_amp > 0 and feat.dimple_rows > 0 and feat.dimple_cols > 0:
            scales.append(min(chord_mean / feat.dimple_rows, span / feat.dimple_cols))
        if scales:
            smallest = min(scales)
            feat_sev = _clamp01((4.0 * nozzle_mm - smallest) / (4.0 * nozzle_mm))  # <1.6mm ramps up
            if smallest < 2.0 * nozzle_mm:                 # finer than ~2 nozzle widths -> resin
                needs_resin = True
            factors.append(DifficultyFactor(
                "Fine features", feat_sev,
                f"smallest feature ~{smallest:.2f} mm vs ~{2*nozzle_mm:.1f} mm FDM detail limit"))

    # 5) Overlap / trapped regions — overlap (solidity > 1) is NORMAL for a high-pressure fan and
    #    prints fine with ordinary supports; only EXTREME overlap makes channels supports can't reach.
    sol = blade_solidity(params)
    sol_max = max(sol.values())
    trap_sev = _clamp01((sol_max - 1.2) / 1.0)             # 1.2 -> 0, 2.2 -> 1 (extreme overlap)
    if sol_max > 2.0:
        needs_trapped = True
    factors.append(DifficultyFactor(
        "Overlap / trapped gaps", trap_sev,
        f"max solidity {sol_max:.2f} ({'overlapping blades' if sol_max > 1 else 'open'})"))

    factors.sort(key=lambda f: -f.severity)
    sev = [f.severity for f in factors]
    difficulty = 100.0 * _clamp01(0.55 * max(sev) + 0.45 * (sum(sev) / len(sev)))

    # Printer class = hardest any factor demands (resin > trapped > supports > easy).
    if needs_resin:
        printer_class = CLASS_RESIN
    elif needs_trapped:
        printer_class = CLASS_TRAPPED
    elif overhang_sev > 0.35 or aspect_sev > 0.5 or trap_sev > 0.5 or difficulty >= 35.0:
        printer_class = CLASS_SUPPORTS   # keep the class monotonic with the score (no 'easy' at 40/100)
    else:
        printer_class = CLASS_EASY

    drivers = ", ".join(f.name.lower() for f in factors[:2] if f.severity > 0.2) or "nothing notable"
    summary = f"Difficulty {difficulty:.0f}/100 — {printer_class}. Main drivers: {drivers}."
    return PrintabilityGrade(difficulty, printer_class, factors, summary)
