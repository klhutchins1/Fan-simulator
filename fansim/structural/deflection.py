"""Analytic tip deflection vs leftover tip gap (cheap FSI gate, roadmap §7.6).

Treat the blade as an Euler-Bernoulli cantilever with section-family shape factors
``(K_A, K_I)`` matching ``fansim.geometry.airfoil`` (#123):
  - ``plate`` (rounded constant-thickness plate): ``K_A = 1.0``, ``K_I = 1.0`` (``I = c t³ / 12``)
  - ``naca`` (closed-TE symmetric NACA 4-digit, Abbott & von Doenhoff 1959 §6.2):
    ``K_A ≈ 0.6809``, ``K_I ≈ 0.4706`` (``I ≈ 0.03922 c t³``)

A hose static pressure ``load_pa`` loads the planform as ``q(s) = ΔP · c(s)`` (conservative
solidity-free proxy; flapwise ``δ`` is compared directly to radial ``tip_gap_mm``). Tip
deflection uses the tip-station section:

    δ = q L⁴ / (8 E I),   I = K_I c t³ / 12

Root bending stress (roadmap §19.17, #123) integrates the tapered cantilever moment along
the span and evaluates section modulus at the **root** station:

    M_root = ΔP ∫_0^L c(s) s ds,   σ_root = M_root (t_root / 2) / I_root

Reject when δ ≥ leftover tip gap (rub / catastrophic leakage risk). Not FEA,
not coupled OpenFOAM FSI — same order-of-magnitude class as the flutter gate.

Euler-Bernoulli is out of regime for wide plates (span/chord ≲
:data:`BEAM_ASPECT_MIN`); reports stamp ``beam_regime_ok`` but do **not** fail the
gate on aspect alone (§19.18). Absolute trust still needs shell FEA / tap test.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import pairwise

from fansim.geometry.airfoil import SECTION_FAMILIES, SECTION_NACA, SECTION_PLATE
from fansim.geometry.blade import BladeParams
from fansim.manufacturability.materials import MATERIALS
from fansim.structural.stress import (
    _GL3_W,
    _GL3_X,
    FDM_E_K,
    MM_TO_M,
    _adhesion_factor,
    _interp_clamped,
    _is_isotropic_material,
    _station_profile,
    _unit_breakpoints,
)

# Classical slender-beam floor; Audit #5 Stock tip aspect ≈ 1.0 (wide plate).
BEAM_ASPECT_MIN = 1.5

# Exact analytic section shape factors relative to a solid c × t rectangle for the closed-TE
# symmetric NACA 4-digit thickness equation in fansim/geometry/airfoil.py (-0.1036 TE coeff):
#   K_A = ∫_0^1 (2 y_t(x) / t) dx,   K_I = ∫_0^1 (2 y_t(x) / t)^3 dx  (I = K_I * c t^3 / 12).
NACA_AREA_K = 0.6808833333
NACA_INERTIA_K = 0.4706266577
PLATE_AREA_K = 1.0
PLATE_INERTIA_K = 1.0


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


def _root_station(params: BladeParams):
    if not params.stations:
        raise ValueError("BladeParams.stations must not be empty")
    return min(params.stations, key=lambda s: float(s.r_frac))


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


def _section_shape_factors(params: BladeParams) -> tuple[float, float]:
    """Return ``(K_A, K_I)`` section shape factors for ``params.section_family``."""
    raw = getattr(params, "section_family", SECTION_NACA)
    fam = SECTION_NACA if not raw else str(raw).lower().strip()
    if fam not in SECTION_FAMILIES:
        raise ValueError(
            f"unknown airfoil section family {raw!r}; expected one of {SECTION_FAMILIES}"
        )
    if fam == SECTION_PLATE:
        return PLATE_AREA_K, PLATE_INERTIA_K
    return NACA_AREA_K, NACA_INERTIA_K


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
    if _is_isotropic_material(material):
        return 1.0
    if material not in MATERIALS:
        raise KeyError(material)
    return float(FDM_E_K)


def _station_section(params: BladeParams, station, material: str) -> tuple[float, float, float, float]:
    """Return ``(span_m, chord_m, thick_m, E_Pa)`` for a chosen station."""
    mat = MATERIALS[material]
    hub, tip = _validate_radii(params)
    span_m = max(tip - hub, 1.0) * MM_TO_M
    chord_raw = float(station.chord)
    thick_raw = float(station.thickness)
    if not (math.isfinite(chord_raw) and math.isfinite(thick_raw)):
        raise ValueError(
            f"station chord and thickness must be finite, got chord={station.chord!r}, thickness={station.thickness!r}"
        )
    chord_m = max(chord_raw, 1e-3) * MM_TO_M
    thick_m = max(thick_raw, 1e-4) * chord_m
    e = mat.youngs_modulus_gpa * 1e9 * _fdm_e_factor(material)
    return span_m, chord_m, thick_m, e


def _beam_section(params: BladeParams, material: str) -> tuple[float, float, float, float]:
    """Return ``(span_m, chord_m, thick_m, E_Pa)`` for the tip-station cantilever."""
    return _station_section(params, _tip_station(params), material)


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
    _, k_i = _section_shape_factors(params)
    inertia = k_i * chord_m * thick_m ** 3 / 12.0
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
    _, k_i = _section_shape_factors(params)
    inertia = k_i * chord_m * thick_m ** 3 / 12.0
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
    """Root bending stress under uniform hose pressure ``load_pa`` (#123).

    Integrates the tapered root moment ``M = ΔP ∫_0^L c(s) s ds`` across ``params.stations``
    and evaluates ``σ = M (t_root / 2) / I_root`` at ``_root_station(params)`` with
    ``I_root = K_I c_root t_root³ / 12``. Allowable is in-plane yield times layer-adhesion
    knockdown (``1.0`` for isotropic ``RESIN``, ``0.60`` for FDM).
    """
    mat = MATERIALS[material]
    load = float(load_pa)
    if not math.isfinite(load):
        raise ValueError(f"load_pa must be finite, got {load_pa!r}")
    k = _adhesion_factor(material) if adhesion_k is None else float(adhesion_k)
    if not (math.isfinite(k) and k > 0.0):
        raise ValueError(f"adhesion_k must be finite and > 0, got {k!r}")
    min_sf = float(min_safety_factor)
    if not (math.isfinite(min_sf) and min_sf > 0.0):
        raise ValueError(f"min_safety_factor must be finite and > 0, got {min_safety_factor!r}")

    span_m, chord_root_m, thick_root_m, _e = _station_section(params, _root_station(params), material)
    _, k_i = _section_shape_factors(params)
    inertia = k_i * chord_root_m * thick_root_m ** 3 / 12.0

    # Tapered root moment M = ΔP * L^2 * ∫_0^1 c(u) * u du (exact for piecewise-linear chord).
    us, cs, _taus = _station_profile(params)
    load_pos = max(load, 0.0)
    moment_int = 0.0
    cuts = _unit_breakpoints(us)
    for a, b in pairwise(cuts):
        mid = 0.5 * (a + b)
        half = 0.5 * (b - a)
        for xq, wq in zip(_GL3_X, _GL3_W, strict=True):
            u = mid + half * xq
            c = _interp_clamped(u, us, cs)
            moment_int += wq * half * c * u
    moment = load_pos * (span_m ** 2) * moment_int

    sigma_pa = (moment * (thick_root_m / 2.0) / inertia) if inertia > 0.0 else float("inf")
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
