"""CFD orientation of the axial rotor (Audit #1, docs/validation/audits/2026-09-25-audit-01-flow-direction.md).

The A12x25 rotors are designed to turn ω_z = +1 (CCW seen from +Z) and pump −Z *as built*. The ducted
CFD flows +Z (inlet −Z → outlet +Z) with ``spin = −1``. Rotating the rotor 180° about X maps body
ω → −ω and delivery −Z → +Z, so the flipped rotor at ``spin = −1`` IS the designed rotation pumping
down the duct. Only the CFD copy is oriented. The printed/exported STL is unchanged.

The rig's impeller and MRF z-range are fitted to the oriented STL's real bounds. The recipe-based
estimate in ``rig_for_impeller`` under-sizes them (±3 mm vs the Stock STL's −8.1…+8.4 mm), which
left blade ends outside the MRF zone.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import trimesh

from fansim.cfd.domain import MM_TO_M, TestRig
from fansim.geometry.rotate import flip_about_x  # noqa: F401  (re-export; one implementation)

AXIAL_CFD_ORIENTATION = "flipped"
ORIENTATIONS = ("as_built", "flipped")


def orient_impeller_for_cfd(src_stl_mm: Path, dst_stl_mm: Path,
                            orientation: str = AXIAL_CFD_ORIENTATION) -> tuple[float, float]:
    if orientation not in ORIENTATIONS:
        raise ValueError(f"orientation must be one of {ORIENTATIONS}, got {orientation!r}")
    mesh = trimesh.load(str(src_stl_mm), force="mesh")
    out = flip_about_x(mesh) if orientation == "flipped" else mesh
    Path(dst_stl_mm).parent.mkdir(parents=True, exist_ok=True)
    out.export(str(dst_stl_mm))
    return float(out.bounds[0, 2]), float(out.bounds[1, 2])


def orientation_from_proof(proof) -> tuple[str, int]:
    """Map a geometric :class:`~fansim.audit.direction.DirectionProof` to a CFD orientation.

    ``proof`` must be CONCLUSIVE (raises ``ValueError`` otherwise -- guessing which way an
    inconclusive rotor turns is worse than stopping, same policy as ``prove_direction`` itself).

    The rule (roadmap Sec.19.2): the rotor is designed to pump toward ``pump_sign``. The CFD duct
    always flows +Z (inlet -Z -> outlet +Z), so a rotor whose designed pump is +Z is used
    ``"as_built"`` at ``spin = omega_sign`` (it already pumps the right way); a rotor whose
    designed pump is -Z must be ``"flipped"`` 180 deg about X (which negates the body ``omega``)
    at ``spin = -omega_sign`` so the flipped copy's spin still pumps the designed rotation down
    the +Z duct. See ``fansim.audit.direction.prove_direction`` for ``pump_sign``/``omega_sign``.
    """
    if proof.verdict != "CONCLUSIVE":
        raise ValueError(
            f"direction proof is not CONCLUSIVE (verdict={proof.verdict!r}): {proof.note}")
    if proof.pump_sign == 1:
        return "as_built", int(proof.omega_sign)
    if proof.pump_sign == -1:
        return "flipped", -int(proof.omega_sign)
    raise ValueError(f"unexpected pump_sign {proof.pump_sign!r} on a CONCLUSIVE proof")


def fit_rig_to_stl(rig: TestRig, stl_mm: Path, *, mrf_margin_mm: float = 2.0) -> TestRig:
    mesh = trimesh.load(str(stl_mm), force="mesh")
    z0, z1 = float(mesh.bounds[0, 2]), float(mesh.bounds[1, 2])
    return replace(
        rig,
        impeller_z_min=z0 * MM_TO_M,
        impeller_z_max=z1 * MM_TO_M,
        mrf_z_min=(z0 - mrf_margin_mm) * MM_TO_M,
        mrf_z_max=(z1 + mrf_margin_mm) * MM_TO_M,
    )


# In-house axial geometry (fansim.geometry.build_impeller) is built with ONE fixed handedness (omega
# +1 as built, pumping -Z; pinned by tests/audit/test_search_space_handedness.py), so builder
# rotors use it directly instead of requiring the mesh-only proof to be CONCLUSIVE (thin/low-camber
# optimizer trials are INCONCLUSIVE). The proof still runs as a cross-check. Mirrors
# fansim.propeller.direction.BUILDER_DIRECTION.
AXIAL_BUILDER_DIRECTION = (AXIAL_CFD_ORIENTATION, -1)
DIRECTION_SOURCES = ("builder", "external")
DIRECTION_META_FILE = "direction_meta.json"


def check_rotor_direction(stl_mm: Path | str, expected_omega_sign: int) -> None:
    """Cross-check helper: raise if the mesh-only proof is CONCLUSIVE and disagrees.

    ``expected_omega_sign`` is the body-frame omega sign the rotor is meant to turn (as built).
    INCONCLUSIVE proofs pass silently (nothing to contradict). Used where a rotor's spin is chosen
    by convention rather than derived (CROR/mixed), so a mirrored part cannot slip through.
    """
    from fansim.audit.direction import prove_direction

    proof = prove_direction(trimesh.load(str(stl_mm), force="mesh"))
    if proof.verdict == "CONCLUSIVE" and int(proof.omega_sign) != int(expected_omega_sign):
        raise ValueError(
            f"rotor direction cross-check disagrees for {stl_mm}: geometry reads "
            f"omega={proof.omega_sign:+d} but {int(expected_omega_sign):+d} was expected -- {proof.note}")


DESIGN_CAMBER_TRUST = 0.02  # |design camber| from which the measured split must match its sign


def builder_direction_refusal(proof, design_camber: float | None) -> str | None:
    """Why a builder rotor's geometry contradicts the builder, or None (audit 2026-10-10, attempt 2).

    * A CONCLUSIVE proof whose chirality is not the real fan's is a mirrored part: always refused.
    * The camber-derived (omega, pump) split is judged only against a design that really is cambered
      (|camber| >= DESIGN_CAMBER_TRUST): a cylinder cut through a flat but strongly leaned blade reads
      lean curvature as camber (9605/9606/9620/9630), so on flat designs the split is not evidence.
    * ``design_camber`` None (caller has no params): chirality only.
    """
    from fansim.audit.direction import REAL_FAN_CHIRALITY

    if getattr(proof, "verdict", None) != "CONCLUSIVE":
        return None
    if proof.chirality != REAL_FAN_CHIRALITY:
        return (f"mirrored part: geometry chirality {proof.chirality:+d}, a builder rotor has "
                f"{REAL_FAN_CHIRALITY:+d} -- {proof.note}")
    if design_camber is None or abs(float(design_camber)) < DESIGN_CAMBER_TRUST:
        return None
    expected = (1, -1) if float(design_camber) > 0 else (-1, 1)
    if (proof.omega_sign, proof.pump_sign) != expected:
        return (f"geometry reads (omega={proof.omega_sign:+d}, pump={proof.pump_sign:+d}) but the design "
                f"camber {float(design_camber):+.3f} implies (omega={expected[0]:+d}, "
                f"pump={expected[1]:+d}) -- {proof.note}")
    return None


def _resolve_direction(stl_mm: Path, source: str,
                       design_camber: float | None = None) -> tuple[str, int, str]:
    """Return (orientation, spin, proof_verdict) for ``source`` in {"builder", "external"}."""
    from fansim.audit.direction import prove_direction

    if source not in DIRECTION_SOURCES:
        raise ValueError(f"source must be one of {DIRECTION_SOURCES}, got {source!r}")
    proof = prove_direction(trimesh.load(str(stl_mm), force="mesh"))
    if source == "external":
        if proof.verdict != "CONCLUSIVE":
            raise ValueError(
                f"external rotor direction is not provable from geometry for {stl_mm} "
                f"(verdict={proof.verdict!r}: {proof.note}); pass orientation= and spin= explicitly")
        orientation, spin = orientation_from_proof(proof)
        return orientation, spin, proof.verdict
    orientation, spin = AXIAL_BUILDER_DIRECTION
    why = builder_direction_refusal(proof, design_camber)
    if why:
        raise ValueError(f"builder rotor direction cross-check refuses {stl_mm}: {why}")
    return orientation, spin, proof.verdict


def prepare_axial_cfd(stl_mm: Path, rig: TestRig, workdir: Path, *,
                      source: str = "builder",
                      orientation: str | None = None,
                      spin: int | None = None,
                      mrf_margin_mm: float = 2.0,
                      design_camber: float | None = None) -> tuple[Path, TestRig]:
    """Orient the rotor for CFD, set the spin, and fit the rig. Use the returned STL and rig for
    everything downstream (frame, stator, casing export, and ``build_case``).

    Direction resolution (roadmap Sec.19.2):

    * ``orientation`` and ``spin`` both given: explicit override, used as-is, no proof.
    * only ``orientation`` given (legacy): that orientation, spin left as the rig's.
    * ``source="builder"``: :data:`AXIAL_BUILDER_DIRECTION`; the proof is a cross-check that raises
      only if CONCLUSIVE and disagreeing.
    * ``source="external"``: the proof must be CONCLUSIVE; ``orientation_from_proof`` decides.

    The decision is written to ``workdir/direction_meta.json``; ``build_case`` merges it into
    ``constant/case_meta.json`` when the impeller STL sits in that directory.
    """
    workdir = Path(workdir)
    if orientation is not None and spin is not None:
        direction_source, verdict = "explicit", None
    elif orientation is not None:
        direction_source, verdict, spin = "explicit", None, int(rig.spin)
    else:
        orientation, spin, verdict = _resolve_direction(Path(stl_mm), source, design_camber)
        direction_source = source
    if int(spin) not in (-1, 1):
        raise ValueError(f"spin must be +1 or -1, got {spin!r}")
    dst = workdir / "impeller_cfd.stl"
    orient_impeller_for_cfd(Path(stl_mm), dst, orientation)
    fitted = replace(fit_rig_to_stl(rig, dst, mrf_margin_mm=mrf_margin_mm), spin=int(spin))
    (workdir / DIRECTION_META_FILE).write_text(json.dumps({
        "direction_source": direction_source, "orientation": orientation,
        "spin": int(spin), "proof_verdict": verdict,
        "design_camber": design_camber}, indent=2), encoding="utf-8")
    return dst, fitted
