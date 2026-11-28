"""Analytic centrifugal-stress gate for a spinning printed blade.

A first-order estimate of the tensile stress at the blade root from centrifugal loading,
used to reject designs that would over-stress the filament (full FEA is for finalists).

Model: integrate centrifugal tension over the radially tapered blade planform from
``r_hub`` to ``r_tip`` with cross-sectional area ``A(r) = K_A * c(r) * t(r)`` (where ``K_A``
is uniform along the span and cancels identically in ``A(r) / A(r_hub)``):

    sigma_root = (rho * omega^2 / A(r_hub)) * integral_{r_hub}^{r_tip} A(r) * r dr

For a prismatic blade (constant ``c`` and ``t``), this reduces identically to the uniform-bar
closed form ``rho * omega^2 * (r_tip^2 - r_hub^2) / 2``. On outward-flaring blades (e.g.
Stock v3 where ``A_tip / A_root ≈ 1.80``), it captures the ~1.48x higher root stress that
a uniform-bar approximation misses (#123). Shroud-ring hoop-coupled loading and hub-fillet
stress concentration ``K_t`` remain outside this first-order screening gate.

FDM parts are weaker between layers (~50-70% of in-plane yield); isotropic SLA/DLP resin
keeps full yield (``adhesion_k = 1.0``) by default (roadmap §1.3, #123).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import pairwise

from fansim.geometry.blade import BladeParams
from fansim.manufacturability.materials import MATERIALS

MM_TO_M = 1.0e-3
LAYER_ADHESION_K = 0.60   # allowable / in-plane yield (FDM inter-layer)
# Flexural modulus knockdown for FDM interlayer bending (δ / f1). Not the same as yield
# adhesion 0.60 — mid of typical 0.5–0.8 published FDM E anisotropy bands.
FDM_E_K = 0.70

# 3-point Gauss-Legendre nodes/weights on [-1, 1] (exact for polynomials up to degree 5).
_GL3_X = (-math.sqrt(3.0 / 5.0), 0.0, math.sqrt(3.0 / 5.0))
_GL3_W = (5.0 / 9.0, 8.0 / 9.0, 5.0 / 9.0)


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


def _is_isotropic_material(material: str) -> bool:
    """True for isotropic SLA/DLP resins (no FDM interlayer knockdown)."""
    name = str(material).upper()
    return name in ("RESIN", "ABS_RESIN", "SLA") or "RESIN" in name


def _adhesion_factor(material: str) -> float:
    """Default yield knockdown: 1.0 for isotropic resin, ``LAYER_ADHESION_K`` for FDM."""
    if _is_isotropic_material(material):
        return 1.0
    if material not in MATERIALS:
        raise KeyError(material)
    return float(LAYER_ADHESION_K)


def _station_profile(params: BladeParams) -> tuple[list[float], list[float], list[float]]:
    """Return sorted ``(r_frac, chord_m, thickness_frac)`` lists, validating all stations."""
    if not params.stations:
        raise ValueError("BladeParams.stations must not be empty")
    rows: list[tuple[float, float, float]] = []
    for st in params.stations:
        u = float(st.r_frac)
        c_raw = float(st.chord)
        tau_raw = float(st.thickness)
        if not (math.isfinite(u) and math.isfinite(c_raw) and math.isfinite(tau_raw)):
            raise ValueError(
                f"station r_frac, chord, and thickness must be finite, got "
                f"r_frac={st.r_frac!r}, chord={st.chord!r}, thickness={st.thickness!r}"
            )
        rows.append((u, max(c_raw, 1e-3) * MM_TO_M, max(tau_raw, 1e-4)))
    rows.sort(key=lambda r: r[0])
    return [r[0] for r in rows], [r[1] for r in rows], [r[2] for r in rows]


def _interp_clamped(u: float, xs: list[float], ys: list[float]) -> float:
    """Piecewise-linear interpolation on sorted ``xs``, clamped flat at endpoints."""
    if u <= xs[0]:
        return ys[0]
    if u >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        x0, x1 = xs[i], xs[i + 1]
        if u <= x1:
            dx = x1 - x0
            if dx <= 0.0:
                return ys[i + 1]
            t = (u - x0) / dx
            return ys[i] + t * (ys[i + 1] - ys[i])
    return ys[-1]


def _unit_breakpoints(us: list[float]) -> list[float]:
    """Breakpoints covering ``[0, 1]`` from sorted station ``r_frac`` values."""
    cuts = [0.0]
    for u in us:
        if 0.0 < u < 1.0 and u - cuts[-1] > 1e-12:
            cuts.append(u)
    if 1.0 - cuts[-1] > 1e-12:
        cuts.append(1.0)
    return cuts


def centrifugal_root_stress(
    params: BladeParams,
    material: str = "PETG",
    min_safety_factor: float = 3.0,
    adhesion_k: float | None = None,
) -> CentrifugalReport:
    mat = MATERIALS[material]
    k = _adhesion_factor(material) if adhesion_k is None else float(adhesion_k)
    rpm = float(params.rpm)
    tip_radius = float(params.tip_radius)
    hub_radius = float(params.hub_radius)
    min_sf = float(min_safety_factor)
    if not (math.isfinite(rpm) and rpm >= 0.0):
        raise ValueError(f"rpm must be finite and >= 0, got {params.rpm!r}")
    if not (math.isfinite(hub_radius) and math.isfinite(tip_radius)):
        raise ValueError(
            f"hub_radius and tip_radius must be finite, got {params.hub_radius!r}, {params.tip_radius!r}"
        )
    if hub_radius < 0.0 or tip_radius < hub_radius:
        raise ValueError(
            f"require 0 <= hub_radius <= tip_radius, got hub={hub_radius}, tip={tip_radius}"
        )
    if not (math.isfinite(k) and k > 0.0):
        raise ValueError(f"adhesion_k must be finite and > 0, got {k!r}")
    if not (math.isfinite(min_sf) and min_sf > 0.0):
        raise ValueError(f"min_safety_factor must be finite and > 0, got {min_safety_factor!r}")

    us, cs, taus = _station_profile(params)
    omega = rpm * 2.0 * math.pi / 60.0
    r_tip = tip_radius * MM_TO_M
    r_hub = hub_radius * MM_TO_M
    span_m = r_tip - r_hub

    if span_m <= 0.0:
        sigma_pa = 0.0
    else:
        c_root = _interp_clamped(0.0, us, cs)
        tau_root = _interp_clamped(0.0, us, taus)
        area_root = c_root * (tau_root * c_root)
        # Piecewise 3-point Gauss-Legendre integrates degree-4 A(r)*r = tau(r)*c(r)^2*r exactly.
        integral = 0.0
        cuts = _unit_breakpoints(us)
        for a, b in pairwise(cuts):
            mid = 0.5 * (a + b)
            half = 0.5 * (b - a)
            for xq, wq in zip(_GL3_X, _GL3_W, strict=True):
                u = mid + half * xq
                r = r_hub + u * span_m
                c = _interp_clamped(u, us, cs)
                tau = _interp_clamped(u, us, taus)
                area = c * (tau * c)
                integral += wq * half * span_m * area * r
        sigma_pa = mat.density_kg_m3 * (omega ** 2) * integral / area_root

    sigma_mpa = float(sigma_pa / 1e6)
    in_plane = float(mat.yield_strength_mpa)
    allow = float(in_plane * k)
    sf = float(allow / sigma_mpa) if sigma_mpa > 1e-9 else float("inf")
    ok = sf >= min_sf
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
