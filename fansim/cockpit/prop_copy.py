"""Prop Design tooltip copy (roadmap §14.1)."""

from __future__ import annotations

from fansim.cockpit.blade_copy import BLADE_DESC, BLADE_DESC_SIMPLE, desc_for

PROP_DESC = {
    "p_n_blades": "Blade count (2–4). More blades → more static thrust, usually less efficiency.",
    "p_pitch": "Geometric pitch (inches per revolution). Higher = steeper blade angle and faster airspeed, more power draw.",
    "p_chord_root": "Root chord as a fraction of tip radius (×R).",
    "p_chord_mid": "Mid-span chord as a fraction of tip radius (×R).",
    "p_chord_tip": "Tip chord as a fraction of tip radius (×R; narrow tips cut drag).",
    "p_camber": "Legacy single camber — prefer Camber root/mid/tip.",
    "p_thick_mode": "Uniform wall = same mm everywhere; Tapered = independent t/c per station.",
}

PROP_DESC_SIMPLE = {
    "p_n_blades": "How many blades (2–4). More blades give more punch/thrust, usually at lower efficiency.",
    "p_pitch": "Propeller pitch in inches (ideal forward travel per turn). Higher pitch = steeper blade angle and higher top speed, using more power.",
    "p_chord_root": "Blade width near the hub (as a fraction of blade radius).",
    "p_chord_mid": "Blade width in the middle (as a fraction of blade radius).",
    "p_chord_tip": "Blade width at the tip (as a fraction of blade radius; narrower tips reduce drag).",
    "p_thick_mode": "Same plastic wall thickness (mm) everywhere, or tapered thinner toward the tip.",
}

# Prefixed blade-shape help from the shared vocabulary.
for _bare, _text in BLADE_DESC.items():
    PROP_DESC[f"p_{_bare}"] = _text
for _bare, _text in BLADE_DESC_SIMPLE.items():
    PROP_DESC_SIMPLE[f"p_{_bare}"] = _text


def prop_help(model: str) -> str:
    return PROP_DESC.get(model) or desc_for(model, prefix="p_")
