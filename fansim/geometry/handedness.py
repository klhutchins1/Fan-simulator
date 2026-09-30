"""CW ⇄ CCW handedness mirror (roadmap §19.4).

The builder produces one designed chirality (omega=+1 as-built, pumps −Z). A motor that
only turns the other way, a CROR rear rotor, or a push-pull pair needs the *mirror*
recipe — negate stagger / lean / circumferential offsets — **and** the opposite spin.
Mirroring geometry alone with the same spin is a backwards fan.

This module does **not** add a "run this design in reverse" performance mode.
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, replace
from pathlib import Path

from fansim.geometry.blade import BladeParams

# Axial CFD places the mesh with ``orientation="flipped"``; spin = −omega_sign so the
# flipped copy still runs the designed rotation (see fansim.cfd.orientation).
DEFAULT_CFD_ORIENTATION = "flipped"


def mirror_blade_params(params: BladeParams) -> BladeParams:
    """Return a deep-copied opposite-hand ``BladeParams`` (stagger / lean / skew negated).

    Camber and thickness stay put: after the stagger sign flip the builder already swaps
    which tangential side leads (see ``_section_loop``), so the pressure face tracks the
    new leading edge. Circumferential planform (lean, skew, sickle ``le_skew``) and uneven
    blade angles are mirrored so sickle / spacing chirality flips with the blade.
    """
    out = deepcopy(params)
    out.stations = [
        replace(
            s,
            stagger_deg=-float(s.stagger_deg),
            lean_deg=-float(s.lean_deg),
            skew=-float(s.skew),
            le_skew=-float(s.le_skew),
        )
        for s in out.stations
    ]
    if out.blade_angles_deg is not None:
        out.blade_angles_deg = [-float(a) for a in out.blade_angles_deg]
    return out


def cfd_spin_for_omega(
    omega_sign: int,
    *,
    orientation: str = DEFAULT_CFD_ORIENTATION,
) -> int:
    """MRF ``spin`` that runs ``omega_sign`` under the given CFD orientation."""
    s = 1 if int(omega_sign) >= 0 else -1
    if orientation == "flipped":
        return -s
    if orientation == "as_built":
        return s
    raise ValueError(f"orientation must be 'flipped' or 'as_built', got {orientation!r}")


@dataclass(frozen=True)
class HandednessVariant:
    """One exportable chirality: params + the spin that must travel with it."""

    label: str  # "as_designed" | "mirrored"
    params: BladeParams
    omega_sign: int
    cfd_orientation: str
    cfd_spin: int
    note: str

    def meta_dict(self) -> dict:
        return {
            "handedness": self.label,
            "omega_sign_designed": int(self.omega_sign),
            "cfd_orientation": self.cfd_orientation,
            "cfd_spin": int(self.cfd_spin),
            "note": self.note,
        }


def handedness_variants(
    params: BladeParams,
    *,
    designed_omega: int = +1,
    orientation: str = DEFAULT_CFD_ORIENTATION,
) -> tuple[HandednessVariant, HandednessVariant]:
    """As-designed + mirrored pair. ``designed_omega`` is the builder chirality (+1 Stock)."""
    o = int(designed_omega)
    if o == 0:
        raise ValueError("designed_omega must be ±1")
    o = 1 if o > 0 else -1
    as_des = HandednessVariant(
        label="as_designed",
        params=deepcopy(params),
        omega_sign=o,
        cfd_orientation=orientation,
        cfd_spin=cfd_spin_for_omega(o, orientation=orientation),
        note="Builder chirality; use cfd_spin with cfd_orientation (do not flip alone).",
    )
    mir = HandednessVariant(
        label="mirrored",
        params=mirror_blade_params(params),
        omega_sign=-o,
        cfd_orientation=orientation,
        cfd_spin=cfd_spin_for_omega(-o, orientation=orientation),
        note=(
            "Opposite-hand geometry; spin is flipped with the mirror "
            "(§19.4 — mirrored blade + same spin = backwards fan)."
        ),
    )
    return as_des, mir


def write_handedness_meta(variant: HandednessVariant, path: str | Path) -> Path:
    """Write ``*.handedness.json`` beside an STL so print/CFD keep geometry+spin paired."""
    path = Path(path)
    path.write_text(json.dumps(variant.meta_dict(), indent=2) + "\n", encoding="utf-8")
    return path
