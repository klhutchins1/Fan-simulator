"""Analytic centrifugal-stress gate for a spinning printed blade.

A first-order estimate of the tensile stress at the blade root from centrifugal loading,
used to reject designs that would over-stress the filament (full FEA is for finalists).

Model: treat the blade as a radial bar of roughly uniform cross-section spinning at omega.
The centrifugal tensile stress at the root is

    sigma_root = rho * omega^2 * (r_tip^2 - r_hub^2) / 2

which is independent of cross-section for a uniform bar. For a 120 mm fan at ~2000 RPM this
is tiny (well under any filament's yield), so this gate rarely binds -- but it protects
against pathological high-RPM / large-radius designs the search might propose.

FDM parts are weaker between layers (~50-70% of in-plane yield). The gate scores safety
factor against that knockdown by default (roadmap §1.3).
"""

from __future__ import annotations

from dataclasses import dataclass

from fansim.geometry.blade import BladeParams
from fansim.manufacturability.materials import MATERIALS

MM_TO_M = 1.0e-3
LAYER_ADHESION_K = 0.60   # allowable / in-plane yield (FDM inter-layer)
# Flexural modulus knockdown for FDM interlayer bending (δ / f1). Not the same as yield
# adhesion 0.60 — mid of typical 0.5–0.8 published FDM E anisotropy bands.
FDM_E_K = 0.70


@dataclass
class CentrifugalReport:
    ok: bool
    sigma_root_mpa: float
    yield_mpa: float              # allowable after adhesion knockdown
    safety_factor: float
    material: str
    reason: str = ""
    in_plane_yield_mpa: float = 0.0
    adhesion_k: float = 1.0


def centrifugal_root_stress(
    params: BladeParams,
    material: str = "PETG",
    min_safety_factor: float = 3.0,
    adhesion_k: float | None = None,
) -> CentrifugalReport:
    mat = MATERIALS[material]
    k = LAYER_ADHESION_K if adhesion_k is None else float(adhesion_k)
    omega = params.rpm * 2.0 * 3.141592653589793 / 60.0
    r_tip = params.tip_radius * MM_TO_M
    r_hub = params.hub_radius * MM_TO_M
    sigma_pa = 0.5 * mat.density_kg_m3 * omega**2 * (r_tip**2 - r_hub**2)
    sigma_mpa = sigma_pa / 1e6
    in_plane = float(mat.yield_strength_mpa)
    allow = in_plane * k
    sf = allow / sigma_mpa if sigma_mpa > 1e-9 else float("inf")
    ok = sf >= min_safety_factor
    reason = ""
    if not ok:
        reason = f"safety factor {sf:.1f} < {min_safety_factor} ({material}"
        if k < 1.0:
            reason += ", layer-adhesion"
        reason += ")"
    return CentrifugalReport(
        ok, sigma_mpa, allow, sf, material, reason,
        in_plane_yield_mpa=in_plane, adhesion_k=k,
    )
