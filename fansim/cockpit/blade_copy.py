"""Shared BladeParams Design tooltip copy (roadmap §14.2).

Keys are unprefixed (``thickness_root``, ``le_skew_tip``, …). Cockpit tabs prefix them
(``p_``, ``cror_f_``, …) when looking up help text.
"""

from __future__ import annotations

BLADE_DESC = {
    "thickness_root": "Wall t/c at the hub (fraction of chord). Through-blade thickness, not planform width.",
    "thickness_mid": "Wall t/c at mid-span.",
    "thickness_tip": "Wall t/c at the tip — thin tips cut drag but print weaker.",
    "camber_root": "Section curvature at the hub.",
    "camber_mid": "Section curvature at mid-span (primary lift lever).",
    "camber_tip": "Section curvature at the tip.",
    "camber_pos": "Where max camber sits along the chord (0.2 near LE → 0.6 aft).",
    "sweep_mid": "Axial rake of the whole mid section (mm, + toward outlet / +Z).",
    "sweep_tip": "Axial rake of the whole tip section (mm).",
    "lean_mid": "Circumferential wrap at mid-span (deg). Light on props.",
    "lean_tip": "Circumferential wrap at the tip (deg).",
    "le_sweep_mid": "Rakes only the leading edge at mid-span (mm).",
    "le_sweep_tip": "Rakes only the leading edge at the tip (mm).",
    "le_skew_mid": "Sickle / LE skew at mid-span (mm) — scimitar planform; TE stays put.",
    "le_skew_tip": "Sickle / LE skew at the tip (mm). Typical drone tips 4–12 mm.",
    "tip_round": "Rounds the blade tip (0 = square, 1 = fully rounded).",
    "tip_round_start": "Where tip rounding begins (fraction of span).",
    "cylindrical_tip": "Cut tip to a cylinder at tip radius so OD is constant.",
    "thick_mode": "Uniform wall = same mm through the blade; Tapered = independent t/c.",
    "thick_mm": "Uniform wall thickness through the blade (mm) when thick_mode is uniform.",
}


def desc_for(prefixed_key: str, *, prefix: str) -> str:
    """Look up help for ``p_thickness_root`` given prefix ``p_``."""
    if prefixed_key.startswith(prefix):
        bare = prefixed_key[len(prefix):]
        return BLADE_DESC.get(bare, "")
    return BLADE_DESC.get(prefixed_key, "")
