"""Analytic tip deflection vs leftover tip gap (cheap FSI gate, roadmap §7.6).

Treat the blade as a uniform rectangular cantilever (tip-station chord × thickness,
span = tip − hub). A hose static pressure ``load_pa`` loads the planform as a
uniform line load ``q = ΔP · chord``. Tip deflection:

    δ = q L⁴ / (8 E I),   I = c t³ / 12

Root bending stress under the same load (roadmap §19.17):

    M = q L² / 2,   σ = M (t/2) / I

Reject when δ ≥ leftover tip gap (rub / catastrophic leakage risk). Not FEA,
not coupled OpenFOAM FSI — same order-of-magnitude class as the flutter gate.
"""

from __future__ import annotations

from dataclasses import dataclass

from fansim.geometry.blade import BladeParams
from fansim.manufacturability.materials import MATERIALS
from fansim.structural.stress import FDM_E_K, LAYER_ADHESION_K

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


@dataclass
class RootBendingReport:
    ok: bool
    sigma_root_mpa: float
    yield_mpa: float
    safety_factor: float
    material: str
    load_pa: float
    reason: str = ""
    adhesion_k: float = 1.0


def _tip_station(params: BladeParams):
    return max(params.stations, key=lambda s: float(s.r_frac))


def _fdm_e_factor(material: str) -> float:
    """In-plane E is optimistic for FDM interlayer flapping; knock down non-resin prints."""
    name = str(material).upper()
    # Resin / SLA stay full E (isotropic). Key may be RESIN or any MATERIALS alias with RESIN.
    if name in ("RESIN", "ABS_RESIN", "SLA") or "RESIN" in name:
        return 1.0
    if material not in MATERIALS:
        raise KeyError(material)
    return float(FDM_E_K)


def _beam_section(params: BladeParams, material: str) -> tuple[float, float, float, float]:
    """Return (span_m, chord_m, thick_m, E_Pa) for the tip-station rectangular cantilever."""
    mat = MATERIALS[material]
    span_m = max(params.tip_radius - params.hub_radius, 1.0) * MM_TO_M
    st = _tip_station(params)
    chord_m = max(float(st.chord), 1e-3) * MM_TO_M
    thick_m = max(float(st.thickness), 1e-4) * chord_m
    e = mat.youngs_modulus_gpa * 1e9 * _fdm_e_factor(material)
    return span_m, chord_m, thick_m, e


def tip_deflection_mm(
    params: BladeParams,
    material: str = "PETG",
    load_pa: float = 1.0,
) -> float:
    """Cantilever tip deflection (mm) under uniform pressure ``load_pa``."""
    span_m, chord_m, thick_m, e = _beam_section(params, material)
    inertia = chord_m * thick_m ** 3 / 12.0
    q = max(float(load_pa), 0.0) * chord_m  # N/m along span
    if e <= 0.0 or inertia <= 0.0:
        return float("inf")
    delta_m = q * span_m ** 4 / (8.0 * e * inertia)
    return float(delta_m / MM_TO_M)


def tip_deflection_point_load_mm(
    params: BladeParams,
    force_n: float,
    material: str = "PETG",
) -> float:
    """Cantilever tip deflection (mm) under a tip point load ``force_n`` (N): δ = P L³ / (3 E I)."""
    span_m, chord_m, thick_m, e = _beam_section(params, material)
    inertia = chord_m * thick_m ** 3 / 12.0
    if e <= 0.0 or inertia <= 0.0:
        return float("inf")
    delta_m = abs(float(force_n)) * span_m ** 3 / (3.0 * e * inertia)
    return float(delta_m / MM_TO_M)


def root_bending_stress(
    params: BladeParams,
    material: str = "PETG",
    load_pa: float = 1.0,
    min_safety_factor: float = 3.0,
    adhesion_k: float | None = None,
) -> RootBendingReport:
    """Root bending stress under the same uniform hose load as :func:`tip_deflection_mm`.

    ``M = q L² / 2``, ``σ = M (t/2) / I`` with ``I = c t³ / 12``. Allowable is in-plane yield
    times layer-adhesion knockdown (same as centrifugal).
    """
    mat = MATERIALS[material]
    k = LAYER_ADHESION_K if adhesion_k is None else float(adhesion_k)
    span_m, chord_m, thick_m, _e = _beam_section(params, material)
    inertia = chord_m * thick_m ** 3 / 12.0
    q = max(float(load_pa), 0.0) * chord_m
    moment = q * span_m ** 2 / 2.0
    sigma_pa = (moment * (thick_m / 2.0) / inertia) if inertia > 0.0 else float("inf")
    sigma_mpa = sigma_pa / 1e6
    in_plane = float(mat.yield_strength_mpa)
    allow = in_plane * k
    sf = allow / sigma_mpa if sigma_mpa > 1e-9 else float("inf")
    ok = sf >= min_safety_factor
    reason = ""
    if not ok:
        reason = (
            f"root bending SF {sf:.1f} < {min_safety_factor} ({material}, "
            f"{float(load_pa):g} Pa hose"
        )
        if k < 1.0:
            reason += ", layer-adhesion"
        reason += ")"
    return RootBendingReport(
        ok, float(sigma_mpa), allow, float(sf), material, float(load_pa), reason, k,
    )


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
