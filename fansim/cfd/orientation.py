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


def prepare_axial_cfd(stl_mm: Path, rig: TestRig, workdir: Path, *,
                      orientation: str = AXIAL_CFD_ORIENTATION,
                      mrf_margin_mm: float = 2.0) -> tuple[Path, TestRig]:
    """Orient the rotor for CFD and fit the rig to it. Use the returned STL and rig for everything
    downstream (frame, stator, casing export, and ``build_case``)."""
    dst = Path(workdir) / "impeller_cfd.stl"
    orient_impeller_for_cfd(Path(stl_mm), dst, orientation)
    return dst, fit_rig_to_stl(rig, dst, mrf_margin_mm=mrf_margin_mm)
