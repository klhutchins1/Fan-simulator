# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Analytic centrifugal-stress gate for a spinning printed blade.

A first-order estimate of the tensile stress at the blade root from centrifugal loading,
used to reject designs that would over-stress the filament (full FEA is for finalists).

Model: treat the blade as a radial bar of roughly uniform cross-section spinning at omega.
The centrifugal tensile stress at the root is

    sigma_root = rho * omega^2 * (r_tip^2 - r_hub^2) / 2

which is independent of cross-section for a uniform bar. For a 120 mm fan at ~2000 RPM this
is tiny (well under any filament's yield), so this gate rarely binds -- but it protects
against pathological high-RPM / large-radius designs the search might propose.
"""

from __future__ import annotations

from dataclasses import dataclass

from fansim.geometry.blade import BladeParams
from fansim.manufacturability.materials import MATERIALS

MM_TO_M = 1.0e-3


@dataclass
class CentrifugalReport:
    ok: bool
    sigma_root_mpa: float
    yield_mpa: float
    safety_factor: float
    material: str
    reason: str = ""


def centrifugal_root_stress(
    params: BladeParams, material: str = "PETG", min_safety_factor: float = 3.0
) -> CentrifugalReport:
    mat = MATERIALS[material]
    omega = params.rpm * 2.0 * 3.141592653589793 / 60.0
    r_tip = params.tip_radius * MM_TO_M
    r_hub = params.hub_radius * MM_TO_M
    sigma_pa = 0.5 * mat.density_kg_m3 * omega**2 * (r_tip**2 - r_hub**2)
    sigma_mpa = sigma_pa / 1e6
    sf = mat.yield_strength_mpa / sigma_mpa if sigma_mpa > 1e-9 else float("inf")
    ok = sf >= min_safety_factor
    reason = "" if ok else f"safety factor {sf:.1f} < {min_safety_factor} ({material})"
    return CentrifugalReport(ok, sigma_mpa, mat.yield_strength_mpa, sf, material, reason)
