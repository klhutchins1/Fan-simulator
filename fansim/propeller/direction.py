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
    """Derive CFD orientation + spin for a prop from the mesh-only proof, never from thrust sign.

    Identity: ``prop_direction(...).spin == prove_direction(...).chirality`` always, for both
    branches below (``as_built``: spin = omega_sign = chirality / pump_sign = chirality * 1;
    ``flipped``: spin = -omega_sign = -(chirality / pump_sign) = -(chirality / -1) = chirality,
    since chirality = omega_sign * pump_sign algebraically). This is documented behaviour, not a
    coincidence -- it is asserted as a regression in tests/audit/test_prop_thrust_sign.py.

    This identity is also why the thrust-sign check in :func:`fansim.propeller.calibrate.
    normalize_metrics_sign` CANNOT by itself catch a leading-edge-reversed prop: MRF spin is set
    from chirality, and chirality is invariant to a mirror of chord/normal handedness that a
    thickness/midline-fit problem in ``prove_direction`` would otherwise let through -- the prop
    would then spin trailing-edge-first while the resulting Fz still comes out with the "right"
    sign for that (wrong) spin. The section-quality guard in ``fansim.audit.direction`` (thickness
    ratio, midline-fit residual, minimum distinct radii) exists precisely to keep bad sections out
    of the vote before this function is ever called; it is not something the sign check downstream
    can substitute for.
    """
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


# In-house prop/impeller geometry (fansim.propeller.geometry.build_prop / fansim.geometry.
# build_impeller) is built with a FIXED handedness, the same one geometry.stock_handedness pins
# for the ducted fan: omega +1 (CCW from +Z), pumping -Z, as built. That is a property of the
# builders themselves, not something that needs to be read back off the mesh every time -- and
# many legitimate in-house designs (thin, stubby, low-camber optimizer trials from
# fansim.propeller.optimize.random_prop_flat / suggest_prop) fail the mesh-only proof's
# section-quality guard (low camber, poor midline fit) despite being unambiguously built with
# this handedness. So builder geometry uses BUILDER_DIRECTION directly instead of requiring
# prove_direction to be CONCLUSIVE; see resolve_prop_direction for the cross-check that still
# runs against it.
BUILDER_DIRECTION = PropDirection(
    "flipped", -1, "builder", -1,
    "fansim prop/impeller builders (build_prop / build_impeller): omega +1 pumps -Z as built "
    "(geometry.stock_handedness)",
)


def resolve_prop_direction(
    stl_mm: Path, *, external: bool, name_hint: str | None = None,
) -> tuple[PropDirection, dict | None]:
    """Resolve CFD orientation/spin for a just-written prop STL, builder or external.

    External STLs (``external=True`` -- a drone/scanned/otherwise not-ours part) always go
    through :func:`prop_direction`'s mesh-only proof, which raises on an INCONCLUSIVE read or a
    label/chirality mismatch: there is no other source of truth for a part we didn't build.

    In-house geometry (``external=False``, written by ``build_prop``/``build_impeller``) uses
    :data:`BUILDER_DIRECTION` directly -- the builders' handedness is fixed and pinned by
    ``geometry.stock_handedness`` (see also ``tests/audit/test_stock_handedness.py``), so an
    INCONCLUSIVE proof (common for optimizer-search-space designs with low camber or otherwise
    hard-to-read sections) is expected and is not an error. ``prove_direction`` is still run as a
    cross-check: it raises ONLY if it manages a CONCLUSIVE reading that DISAGREES with
    ``BUILDER_DIRECTION``'s (omega=+1, pump=-1) -- catching a genuinely mirrored/misbuilt design --
    while an INCONCLUSIVE cross-check is recorded (not raised) in the returned dict, which the
    caller stores as ``direction_crosscheck``.
    """
    if external:
        return prop_direction(stl_mm, name_hint=name_hint), None
    proof = prove_direction(trimesh.load(str(stl_mm), force="mesh"))
    crosscheck = {
        "verdict": proof.verdict,
        "note": proof.note,
        "omega_sign": proof.omega_sign,
        "pump_sign": proof.pump_sign,
        "chirality": proof.chirality,
    }
    if proof.verdict == "CONCLUSIVE" and (proof.omega_sign, proof.pump_sign) != (1, -1):
        raise ValueError(
            f"builder geometry direction cross-check disagrees with {stl_mm}: proof reads "
            f"(omega={proof.omega_sign:+d}, pump={proof.pump_sign:+d}) but "
            f"{BUILDER_DIRECTION.note} — {proof.note}"
        )
    return BUILDER_DIRECTION, crosscheck
