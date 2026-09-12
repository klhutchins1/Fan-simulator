"""Analytic tip deflection vs leftover tip gap (cheap FSI gate, roadmap §7.6).

Treat the blade as a uniform rectangular cantilever (tip-station chord × thickness,
span = tip − hub). A hose static pressure ``load_pa`` loads the planform as a
uniform line load ``q = ΔP · chord``. Tip deflection:

    δ = q L⁴ / (8 E I),   I = c t³ / 12

Reject when δ ≥ leftover tip gap (rub / catastrophic leakage risk). Not FEA,
not coupled OpenFOAM FSI — same order-of-magnitude class as the flutter gate.
"""

from __future__ import annotations

from dataclasses import dataclass

from fansim.geometry.blade import BladeParams
from fansim.manufacturability.materials import MATERIALS
from fansim.structural.stress import FDM_E_K

MM_TO_M = 1.0e-3


@dataclass
class DeflectionReport:
    ok: bool
    tip_deflection_mm: float
    tip_gap_mm: float
    gap_frac: float
    load_pa: float
    reason: str = ""
    e_fdm_knockdown: float = 1.0


def _tip_station(params: BladeParams):
    return max(params.stations, key=lambda s: float(s.r_frac))


def _fdm_e_factor(material: str) -> float:
    """In-plane E is optimistic for FDM interlayer flapping; knock down non-resin prints."""
    mat = MATERIALS[material]
    # Resin / metals stay full E; FDM filaments in MATERIALS use adhesion on yield → same class.
    name = str(material).upper()
    if name in ("RESIN", "ABS_RESIN", "SLA") or "RESIN" in name:
        return 1.0
    return float(FDM_E_K)


def tip_deflection_mm(
    params: BladeParams,
    material: str = "PETG",
    load_pa: float = 1.0,
) -> float:
    """Cantilever tip deflection (mm) under uniform pressure ``load_pa``."""
    mat = MATERIALS[material]
    span_m = max(params.tip_radius - params.hub_radius, 1.0) * MM_TO_M
    st = _tip_station(params)
    chord_m = max(float(st.chord), 1e-3) * MM_TO_M
    thick_m = max(float(st.thickness), 1e-4) * chord_m
    inertia = chord_m * thick_m ** 3 / 12.0
    e_k = _fdm_e_factor(material)
    e = mat.youngs_modulus_gpa * 1e9 * e_k
    q = max(float(load_pa), 0.0) * chord_m  # N/m along span
    if e <= 0.0 or inertia <= 0.0:
        return float("inf")
    delta_m = q * span_m ** 4 / (8.0 * e * inertia)
    return float(delta_m / MM_TO_M)


def deflection_report(
    params: BladeParams,
    tip_gap_mm: float,
    *,
    material: str = "PETG",
    load_pa: float = 1.0,
) -> DeflectionReport:
    """Gate: tip deflection must stay strictly below leftover tip gap."""
    delta = tip_deflection_mm(params, material=material, load_pa=load_pa)
    gap = max(float(tip_gap_mm), 0.0)
    frac = delta / gap if gap > 1e-9 else float("inf")
    ok = delta < gap
    e_k = _fdm_e_factor(material)
    reason = ""
    if not ok:
        reason = (
            f"FSI tip rub risk ({material}): tip deflection {delta:.3f} mm "
            f">= leftover tip gap {gap:.3f} mm under {float(load_pa):g} Pa hose. "
            f"Fix: raise tip Thickness, shorten Tip radius, stiffer material, "
            f"or ease the hose Pa."
        )
    return DeflectionReport(ok, delta, gap, frac, float(load_pa), reason, e_k)
