"""Prop Design tooltip copy (roadmap §14.1)."""

from __future__ import annotations

from fansim.cockpit.blade_copy import BLADE_DESC, desc_for

PROP_DESC = {
    "p_n_blades": "Blade count (2–4). More blades → more static thrust, usually less efficiency.",
    "p_pitch": "Geometric pitch (inches). Sets the whole twist law β(r)=atan(P/(2πr)).",
    "p_chord_root": "Root chord as a fraction of tip radius.",
    "p_chord_mid": "Mid chord as a fraction of tip radius.",
    "p_chord_tip": "Tip chord as a fraction of tip radius (narrow tips cut drag).",
    "p_camber": "Legacy single camber — prefer Camber root/mid/tip.",
    "p_thick_mode": "Uniform wall = same mm; Tapered = independent t/c per station.",
}

# Prefixed blade-shape help from the shared vocabulary.
for _bare, _text in BLADE_DESC.items():
    PROP_DESC[f"p_{_bare}"] = _text


def prop_help(model: str) -> str:
    return PROP_DESC.get(model) or desc_for(model, prefix="p_")
