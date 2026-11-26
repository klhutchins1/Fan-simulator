"""Shared BladeParams Design tooltip copy (roadmap §14.2).

Keys are unprefixed (``thickness_root``, ``le_skew_tip``, …). Cockpit tabs prefix them
(``p_``, ``cror_f_``, …) when looking up help text.
"""

from __future__ import annotations

BLADE_DESC = {
    "thickness_root": "Wall t/c at the hub (fraction of chord). Through-blade thickness, not planform width.",
    "thickness_mid": "Wall t/c at mid-span.",
    "thickness_tip": "Wall t/c at the tip — thin tips cut drag but print weaker.",
    "camber_root": "Section curvature at the hub (fraction of chord).",
    "camber_mid": "Section curvature at mid-span (primary lift lever, fraction of chord).",
    "camber_tip": "Section curvature at the tip (fraction of chord).",
    "camber_pos": "Where max camber sits along the chord (0.2 near LE → 0.6 aft, fraction of chord).",
    "sweep_mid": "Axial rake of the whole mid section (mm, + toward outlet / +Z).",
    "sweep_tip": "Axial rake of the whole tip section (mm, + toward outlet / +Z).",
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

BLADE_DESC_SIMPLE = {
    "thickness_root": "Blade wall thickness near the hub (fraction of blade width).",
    "thickness_mid": "Blade wall thickness in the middle (fraction of blade width).",
    "thickness_tip": "Blade wall thickness at the tip — thinner cuts drag but prints weaker.",
    "camber_root": "How scooped the blade face is near the hub (0 = flat).",
    "camber_mid": "How scooped the blade face is in the middle — main lift/push lever.",
    "camber_tip": "How scooped the blade face is near the tip.",
    "camber_pos": "Where the deepest scoop sits from front edge (0.25) toward back edge (0.55).",
    "sweep_mid": "Shifts the middle of the blade forward or back along the airflow axis (mm).",
    "sweep_tip": "Shifts the blade tip forward or back along the airflow axis (mm).",
    "lean_mid": "Wraps the middle of the blade around the hub (deg).",
    "lean_tip": "Wraps the blade tip around the hub (deg).",
    "le_sweep_mid": "Curves only the front edge at mid-span (mm).",
    "le_sweep_tip": "Curves only the front edge at the tip (mm).",
    "le_skew_mid": "Curves the front edge sideways in the spin plane at mid-span (mm).",
    "le_skew_tip": "Curves the front edge sideways at the tip for a scimitar look (mm).",
    "tip_round": "Rounds off the outer blade tip (0 = square, 1 = fully rounded).",
    "tip_round_start": "Where tip rounding begins along the blade length (fraction of span).",
    "cylindrical_tip": "Trims the outer tip cleanly to a circle so outer diameter stays exact.",
    "thick_mode": "Uniform wall keeps the same mm everywhere; Tapered varies thickness from hub to tip.",
    "thick_mm": "Plastic wall thickness through the blade (mm) when Wall mode is Uniform.",
}

CROR_DESC = {
    "cror_hub_r": "Shared hub outer radius for both counter-rotating rotors (mm).",
    "cror_tip_r": "Outer blade tip radius for both rotors (mm).",
    "cror_gap": "Axial clearance between the front and rear rotor stacks (mm).",
    "cror_f_n": "Blade count on the front rotor.",
    "cror_r_n": "Blade count on the rear rotor (different count reduces tonal overlap).",
    "cror_f_chord_root": "Front rotor blade width (chord) at the hub (mm).",
    "cror_f_chord_mid": "Front rotor blade width (chord) at mid-span (mm).",
    "cror_f_chord_tip": "Front rotor blade width (chord) at the tip (mm).",
    "cror_f_stagger": "Front rotor blade pitch angle (deg).",
    "cror_r_chord_root": "Rear rotor blade width (chord) at the hub (mm).",
    "cror_r_chord_mid": "Rear rotor blade width (chord) at mid-span (mm).",
    "cror_r_chord_tip": "Rear rotor blade width (chord) at the tip (mm).",
    "cror_r_stagger": "Rear rotor blade pitch angle (deg).",
}
for _bare, _text in BLADE_DESC.items():
    CROR_DESC[f"cror_f_{_bare}"] = f"Front rotor — {_text}"
    CROR_DESC[f"cror_r_{_bare}"] = f"Rear rotor — {_text}"


def desc_for(prefixed_key: str, *, prefix: str) -> str:
    """Look up help for ``p_thickness_root`` given prefix ``p_``."""
    if prefixed_key.startswith(prefix):
        bare = prefixed_key[len(prefix):]
        return BLADE_DESC.get(bare, "")
    return BLADE_DESC.get(prefixed_key, "")
