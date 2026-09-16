"""Lightweight FDM printability gate for candidate blades.

Fast, analytic checks used to reject un-buildable designs during optimization (full slicer
analysis is reserved for finalists). The binding rule is minimum wall thickness, applied
RADIUS-AWARE: the blade BODY needs a real 2-perimeter wall, but the TIP EDGE is allowed to taper
down to a single extrusion width — real fan/prop blades have thin tips, and a rounded/tapered tip
is a designed thin edge, not a structural wall. Only below ONE nozzle width is it truly unprintable
(no path for plastic).
"""

from __future__ import annotations

from dataclasses import dataclass

from fansim.geometry.blade import BladeParams

DEFAULT_NOZZLE_MM = 0.4
MIN_WALL_PERIMETERS = 2   # blade BODY: 2 perimeters -> ~0.8 mm minimum printable wall
TIP_WALL_PERIMETERS = 1   # blade TIP EDGE: a single extrusion width (~0.4 mm) is the real floor
TIP_ZONE_FRAC = 0.85      # stations beyond this span fraction are the "tip edge" (allowed thinner)


@dataclass
class PrintabilityReport:
    printable: bool
    min_section_thickness_mm: float
    min_wall_mm: float
    reason: str = ""


def _section_thickness_mm(s) -> float:
    """Max thickness (mm) of one airfoil station = thickness fraction * chord."""
    return s.thickness * s.chord


def min_section_thickness_mm(params: BladeParams, body_only: bool = False) -> float:
    """Smallest station max-thickness (mm). With ``body_only``, ignore the tapered tip edge (stations
    beyond TIP_ZONE_FRAC) so a designed thin/rounded tip doesn't read as a thin blade BODY."""
    stations = params.stations
    if body_only:
        body = [s for s in stations if s.r_frac <= TIP_ZONE_FRAC]
        stations = body or stations           # keep at least one station if everything is "tip"
    return min(_section_thickness_mm(s) for s in stations)


def check_printability(
    params: BladeParams, nozzle_mm: float = DEFAULT_NOZZLE_MM
) -> PrintabilityReport:
    """Gate a blade on wall thickness: the BODY must meet a 2-perimeter wall; the TIP EDGE only a
    single extrusion width. Reports the tighter-binding failure. ``min_section_thickness_mm`` on the
    report is the overall thinnest section (for the difficulty score / info)."""
    from fansim.geometry.blade import SHROUD_MIN_WALL_MM

    body_wall = MIN_WALL_PERIMETERS * nozzle_mm    # ~0.8 mm
    tip_wall = TIP_WALL_PERIMETERS * nozzle_mm     # ~0.4 mm — a printable thin edge
    overall = min_section_thickness_mm(params)
    body_t = min_section_thickness_mm(params, body_only=True)
    tip_t = min((_section_thickness_mm(s) for s in params.stations if s.r_frac > TIP_ZONE_FRAC),
                default=body_t)

    shroud_t = float(getattr(params, "shroud_thick_mm", 0.0) or 0.0)
    if 0.0 < shroud_t < SHROUD_MIN_WALL_MM:
        return PrintabilityReport(
            False, overall, SHROUD_MIN_WALL_MM,
            f"shroud wall {shroud_t:.2f} mm < min printable wall {SHROUD_MIN_WALL_MM:.2f} mm")

    if body_t < body_wall:                          # thin over the blade BODY -> genuinely un-buildable
        return PrintabilityReport(False, overall, body_wall,
                                  f"blade body thinnest {body_t:.2f} mm < min wall {body_wall:.2f} mm")
    if tip_t < tip_wall:                            # tip below a single extrusion width -> no plastic path
        return PrintabilityReport(False, overall, tip_wall,
                                  f"tip edge {tip_t:.2f} mm < one extrusion width {tip_wall:.2f} mm "
                                  f"(round the tip less, or thicken the tip)")
    return PrintabilityReport(True, overall, body_wall)


# --- spliced preview_unprintable_note (recovery) ---
def preview_unprintable_note(reason: str) -> str:
    """Cockpit preview caption when the shape draws but would fail Assess/Export."""
    if "shroud" in reason.lower():
        return (f"⚠ Not printable as-is: {reason}. Preview shown anyway — raise Shroud "
                f"thickness to at least 0.8 mm (1.6 mm is four walls); it'll be gated at "
                f"Assess/Export.")
    return (f"⚠ Not printable as-is: {reason}. Preview shown anyway — thicken the "
            f"tip (Airfoil → Thickness tip) or lower Tip round; it'll be gated at Assess/Export.")
