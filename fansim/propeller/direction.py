"""Prop rotation/orientation from the mesh-only proof (Audit #1), never from the thrust sign.

The open-air prop domain has freestream toward +Z. The prop's designed rotation must push air +Z,
so the CFD copy is oriented so that the proof's delivery is +Z, and spin is the designed rotation
in that frame. A CW/CCW filename label fixes only chirality (CCW = -1, the real-fan hand) and is
used as a cross-check.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import trimesh

from fansim.audit.direction import prove_direction


@dataclass(frozen=True)
class PropDirection:
    orientation: str
    spin: int
    source: str
    chirality: int | None
    note: str


def chirality_hint_from_name(name: str) -> int | None:
    upper = Path(name).stem.upper().replace("-", "_").replace(" ", "_")
    if re.search(r"(^|_)CCW(_|$)", upper):
        return -1
    if re.search(r"(^|_)CW(_|$)", upper):
        return 1
    return None


def prop_direction(stl_mm: Path, *, name_hint: str | None = None) -> PropDirection:
    proof = prove_direction(trimesh.load(str(stl_mm), force="mesh"))
    if proof.verdict != "CONCLUSIVE":
        raise ValueError(f"prop direction INCONCLUSIVE for {stl_mm}: {proof.note} — pass an explicit "
                         f"spin/orientation (direction='manual') after checking the part")
    hint = chirality_hint_from_name(name_hint) if name_hint else None
    if hint is not None and hint != proof.chirality:
        raise ValueError(f"{name_hint}: label implies chirality {hint:+d} but the geometry has "
                         f"{proof.chirality:+d} — mislabelled file or mirrored mesh")
    if proof.pump_sign == 1:
        orientation, spin = "as_built", int(proof.omega_sign)
    else:
        orientation, spin = "flipped", -int(proof.omega_sign)
    return PropDirection(orientation, spin, "geometry", proof.chirality, proof.note)
