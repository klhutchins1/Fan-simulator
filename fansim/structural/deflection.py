"""Analytic tip deflection vs leftover tip gap (cheap FSI gate, roadmap §7.6).

Treat the blade as a uniform rectangular cantilever (tip-station chord × thickness,
span = tip − hub). A hose static pressure ``load_pa`` loads the planform as a
uniform line load ``q = ΔP · chord``. Tip deflection:

    δ = q L⁴ / (8 E I),   I = c t³ / 12

Root bending stress under the same load (roadmap §19.17):

    M = q L² / 2,   σ = M (t/2) / I

Reject when δ ≥ leftover tip gap (rub / catastrophic leakage risk). Not FEA,
not coupled OpenFOAM FSI — same order-of-magnitude class as the flutter gate.

Euler-Bernoulli is out of regime for wide plates (span/chord ≲
:data:`BEAM_ASPECT_MIN`); reports stamp ``beam_regime_ok`` but do **not** fail the
gate on aspect alone (§19.18). Absolute trust still needs shell FEA / tap test.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from fansim.geometry.blade import BladeParams
from fansim.manufacturability.materials import MATERIALS
from fansim.structural.stress import FDM_E_K, LAYER_ADHESION_K

MM_TO_M = 1.0e-3
# Classical slender-beam floor; Audit #5 Stock tip aspect ≈ 1.0 (wide plate).
BEAM_ASPECT_MIN = 1.5


@dataclass
class DeflectionReport:
    ok: bool
    tip_deflection_mm: float
    tip_gap_mm: float
    gap_frac: float
    load_pa: float
    reason: str = ""
    e_fdm_knockdown: float = 1.0
    beam_aspect: float = float("inf")
    beam_regime_ok: bool = True

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
    if not params.stations:
        raise ValueError("BladeParams.stations must not be empty")
    return max(params.stations, key=lambda s: float(s.r_frac))


def _validate_radii(params: BladeParams) -> tuple[float, float]:
    hub = float(params.hub_radius)
    tip = float(params.tip_radius)
    if not (math.isfinite(hub) and math.isfinite(tip)):
        raise ValueError(
            f"hub_radius and tip_radius must be finite, got {params.hub_radius!r}, {params.tip_radius!r}"
        )
    if hub < 0.0 or tip < hub:
        raise ValueError(f"require 0 <= hub_radius <= tip_radius, got hub={hub}, tip={tip}")
    return hub, tip


def beam_aspect_ratio(params: BladeParams, *, station: str = "tip") -> float:
    """Span / chord at tip or mid station. Values ≲ :data:`BEAM_ASPECT_MIN` are plate-like."""
    if station not in ("tip", "mid"):
        raise ValueError(f"station must be 'tip' or 'mid', got {station!r}")
    if not params.stations:
        raise ValueError("BladeParams.stations must not be empty")
    hub, tip = _validate_radii(params)
    span_mm = max(tip - hub, 1.0)
    if station == "mid":
        st = min(params.stations, key=lambda s: abs(float(s.r_frac) - 0.5))
    else:
        st = _tip_station(params)
    chord_raw = float(st.chord)
    if not math.isfinite(chord_raw):
        raise ValueError(f"station chord must be finite, got {st.chord!r}")
    chord = max(chord_raw, 1e-3)
    return span_mm / chord


def beam_regime_ok(params: BladeParams, *, station: str = "tip") -> bool:
    """True when Euler-Bernoulli is a plausible model for this planform."""
    return beam_aspect_ratio(params, station=station) >= BEAM_ASPECT_MIN


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
    hub, tip = _validate_radii(params)
    span_m = max(tip - hub, 1.0) * MM_TO_M
    st = _tip_station(params)
    chord_raw = float(st.chord)
    thick_raw = float(st.thickness)
    if not (math.isfinite(chord_raw) and math.isfinite(thick_raw)):
        raise ValueError(
            f"station chord and thickness must be finite, got chord={st.chord!r}, thickness={st.thickness!r}"
        )
    chord_m = max(chord_raw, 1e-3) * MM_TO_M
    thick_m = max(thick_raw, 1e-4) * chord_m
    e = mat.youngs_modulus_gpa * 1e9 * _fdm_e_factor(material)
    return span_m, chord_m, thick_m, e


def tip_deflection_mm(
    params: BladeParams,
    material: str = "PETG",
    load_pa: float = 1.0,
) -> float:
    """Cantilever tip deflection (mm) under uniform pressure ``load_pa``."""
    load = float(load_pa)
    if not math.isfinite(load):
        raise ValueError(f"load_pa must be finite, got {load_pa!r}")
    span_m, chord_m, thick_m, e = _beam_section(params, material)
    inertia = chord_m * thick_m ** 3 / 12.0
    q = max(load, 0.0) * chord_m  # N/m along span
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
    force = float(force_n)
    if not math.isfinite(force):
        raise ValueError(f"force_n must be finite, got {force_n!r}")
    span_m, chord_m, thick_m, e = _beam_section(params, material)
    inertia = chord_m * thick_m ** 3 / 12.0
    if e <= 0.0 or inertia <= 0.0:
        return float("inf")
    delta_m = abs(force) * span_m ** 3 / (3.0 * e * inertia)
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
    load = float(load_pa)
    if not math.isfinite(load):
        raise ValueError(f"load_pa must be finite, got {load_pa!r}")
    k = LAYER_ADHESION_K if adhesion_k is None else float(adhesion_k)
    if not (math.isfinite(k) and k > 0.0):
        raise ValueError(f"adhesion_k must be finite and > 0, got {k!r}")
    min_sf = float(min_safety_factor)
    if not (math.isfinite(min_sf) and min_sf > 0.0):
        raise ValueError(f"min_safety_factor must be finite and > 0, got {min_safety_factor!r}")
    span_m, chord_m, thick_m, _e = _beam_section(params, material)
    inertia = chord_m * thick_m ** 3 / 12.0
    q = max(load, 0.0) * chord_m
    moment = q * span_m ** 2 / 2.0
    sigma_pa = (moment * (thick_m / 2.0) / inertia) if inertia > 0.0 else float("inf")
    sigma_mpa = float(sigma_pa / 1e6)
    in_plane = float(mat.yield_strength_mpa)
    allow = float(in_plane * k)
    sf = float(allow / sigma_mpa) if sigma_mpa > 1e-9 else float("inf")
    ok = sf >= min_sf
    reason = ""
    if not ok:
        reason = (
            f"root bending SF {sf:.1f} < {min_safety_factor} ({material}, "
            f"{load:g} Pa hose"
        )
        if k < 1.0:
            reason += ", layer-adhesion"
        reason += ")"
    return RootBendingReport(
        ok, sigma_mpa, allow, sf, material, load, reason, k,
    )


def deflection_report(
    params: BladeParams,
    tip_gap_mm: float,
    *,
    material: str = "PETG",
    load_pa: float = 1.0,
) -> DeflectionReport:
    """Gate: tip deflection must stay strictly below leftover tip gap."""
    gap_raw = float(tip_gap_mm)
    if not (math.isfinite(gap_raw) and gap_raw >= 0.0):
        raise ValueError(f"tip_gap_mm must be finite and >= 0, got {tip_gap_mm!r}")
    delta = tip_deflection_mm(params, material=material, load_pa=load_pa)
    gap = max(gap_raw, 0.0)
    frac = delta / gap if gap > 1e-9 else float("inf")
    ok = delta < gap
    e_k = _fdm_e_factor(material)
    aspect = beam_aspect_ratio(params, station="tip")
    regime = aspect >= BEAM_ASPECT_MIN
    reason = ""
    if not ok:
        reason = (
            f"FSI tip rub risk ({material}): tip deflection {delta:.3f} mm "
            f">= leftover tip gap {gap:.3f} mm under {float(load_pa):g} Pa hose. "
            f"Fix: raise tip Thickness, shorten Tip radius, stiffer material, "
            f"or ease the hose Pa."
        )
    elif not regime:
        reason = (
            f"WARN beam regime: tip span/chord={aspect:.2f} < {BEAM_ASPECT_MIN} "
            f"(wide plate; Euler-Bernoulli is order-of-magnitude only — §19.18)"
        )
    return DeflectionReport(
        ok, delta, gap, frac, float(load_pa), reason, e_k, aspect, regime,
    )
