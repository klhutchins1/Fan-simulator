"""Rotor mass balance — the constraint that makes UNEVEN blade spacing usable.

Uneven circumferential spacing spreads the blade-pass tone (Cattanei 2007, docs/bibliography.md
sec.2) but, with identical blades, only stays balanced if the blade position vectors sum to zero:

    static unbalance  U_vec = sum_k  m_k * r_k * (cos th_k, sin th_k)

Equal spacing gives U_vec = 0 automatically; an arbitrary uneven pattern generally does not. This
module measures the residual, sizes the counterweight to null it, and — crucially — GENERATES uneven
patterns that are balanced by construction, so the search can spread the tone without introducing a
once-per-rev imbalance. Static (single-plane) balance dominates for the thin A12x25 impeller; a
couple-unbalance check is provided for axially-distributed mass.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

TWO_PI = 2.0 * math.pi


@dataclass
class Unbalance:
    magnitude: float   # |U| in kg*m (or dimensionless if m=r=1); 0 = balanced
    angle_rad: float   # direction of the residual (heavy spot)
    normalized: float  # |U| / sum(m_k r_k): 0 = perfect, 1 = all mass aligned

    @property
    def balanced(self) -> bool:
        return self.normalized <= 1e-6


def equal_spacing(n_blades: int) -> np.ndarray:
    """Angular positions [rad] for n equally spaced blades (perfectly balanced)."""
    if n_blades < 2:
        raise ValueError("need >= 2 blades")
    return np.arange(n_blades, dtype=float) * (TWO_PI / n_blades)


def _as_angles(angles) -> np.ndarray:
    ang = np.asarray(angles, dtype=float)
    if ang.ndim != 1 or len(ang) == 0:
        raise ValueError("angles must be a non-empty 1-D sequence")
    if not np.all(np.isfinite(ang)):
        raise ValueError("angles must be finite")
    return ang


def _mr(n: int, masses, radii) -> np.ndarray:
    m = np.ones(n, dtype=float) if masses is None else np.asarray(masses, dtype=float)
    r = np.ones(n, dtype=float) if radii is None else np.asarray(radii, dtype=float)
    if m.ndim != 1 or r.ndim != 1 or len(m) != n or len(r) != n:
        raise ValueError("masses/radii must match number of blades")
    if not (np.all(np.isfinite(m)) and np.all(np.isfinite(r))):
        raise ValueError("masses/radii must be finite")
    if np.any(m < 0.0) or np.any(r < 0.0):
        raise ValueError("masses/radii must be >= 0")
    return m * r


def static_unbalance(angles, masses=None, radii=None) -> Unbalance:
    """Residual first-moment (static) unbalance of blades at ``angles`` [rad].

    ``masses``/``radii`` default to identical unit blades. Returns magnitude (kg*m), heavy-spot
    angle, and the value normalized by total m*r (so tolerance is scale-free).
    """
    ang = _as_angles(angles)
    mr = _mr(len(ang), masses, radii)
    ux = float(np.sum(mr * np.cos(ang)))
    uy = float(np.sum(mr * np.sin(ang)))
    mag = math.hypot(ux, uy)
    total = float(np.sum(np.abs(mr))) or 1.0
    return Unbalance(magnitude=mag, angle_rad=math.atan2(uy, ux), normalized=mag / total)


def is_balanced(angles, masses=None, radii=None, tol: float = 1e-6) -> bool:
    """True if the normalized static unbalance is within ``tol``."""
    return static_unbalance(angles, masses, radii).normalized <= tol


def required_counterweight(angles, masses=None, radii=None) -> tuple[float, float]:
    """Counterweight needed to null the residual: returns (m*r [kg*m], angle [rad]).

    Add mass so that m_c*r_c equals the returned magnitude at the returned angle (opposite the heavy
    spot). Used when a desired uneven pattern can't be made self-balancing.
    """
    u = static_unbalance(angles, masses, radii)
    return u.magnitude, (u.angle_rad + math.pi) % TWO_PI


def residual_force(unbalance_mr: float, omega_rad_s: float) -> float:
    """Rotating centrifugal force [N] from a residual unbalance U=m*r [kg*m]: F = U * omega^2."""
    u = float(unbalance_mr)
    w = float(omega_rad_s)
    if not (math.isfinite(u) and u >= 0.0):
        raise ValueError(f"unbalance_mr must be finite and >= 0, got {unbalance_mr!r}")
    if not math.isfinite(w):
        raise ValueError(f"omega_rad_s must be finite, got {omega_rad_s!r}")
    return float(u * w**2)


def _min_circular_gap(angles: np.ndarray) -> float:
    """Minimum angular separation [rad] between adjacent blades on the circle [0, 2*pi)."""
    s = np.sort(np.asarray(angles, dtype=float) % TWO_PI)
    gaps = np.diff(np.concatenate([s, [s[0] + TWO_PI]]))
    return float(np.min(gaps))


def couple_unbalance(
    angles,
    z_positions,
    masses=None,
    radii=None,
    *,
    z_ref: float | str = 0.0,
) -> float:
    """Couple (dynamic) unbalance magnitude for blades at axial positions ``z_positions``.

    ``|sum_k m_k r_k (z_k - z_0) e^{i th_k}|`` -- nonzero couple tilts the axis even when static
    balance holds. When static unbalance is zero, the result is independent of ``z_0``. When static
    unbalance is nonzero, couple unbalance depends on the axial reference plane (ISO 21940-11):
    pass ``z_ref="cg"`` for the mass-weighted axial centre of gravity, or a float plane position
    (default ``0.0``).
    """
    ang = _as_angles(angles)
    z = np.asarray(z_positions, dtype=float)
    if z.ndim != 1 or len(z) != len(ang):
        raise ValueError("z_positions must match number of blades")
    if not np.all(np.isfinite(z)):
        raise ValueError("z_positions must be finite")
    mr = _mr(len(ang), masses, radii)
    if isinstance(z_ref, str):
        if z_ref != "cg":
            raise ValueError(f"z_ref must be a finite float or 'cg', got {z_ref!r}")
        if masses is None:
            z0 = float(np.mean(z))
        else:
            m = np.asarray(masses, dtype=float)
            m_sum = float(np.sum(m))
            z0 = float(np.sum(m * z) / m_sum) if m_sum > 0.0 else float(np.mean(z))
    else:
        z0 = float(z_ref)
        if not math.isfinite(z0):
            raise ValueError(f"z_ref must be finite, got {z_ref!r}")
    dz = z - z0
    cx = float(np.sum(mr * dz * np.cos(ang)))
    cy = float(np.sum(mr * dz * np.sin(ang)))
    return math.hypot(cx, cy)


def balanced_uneven_spacing(
    n_blades: int,
    spread: float = 0.3,
    rng=None,
    masses=None,
    radii=None,
    *,
    min_gap_frac: float = 0.25,
) -> np.ndarray:
    """Generate an UNEVEN but statically balanced set of blade angles [rad].

    ``spread`` >= 0 scales how far blades wander from equal spacing (0 = equal, tone concentrated;
    larger = more tonal spreading). Even blade counts use diametrically-opposite pairing (balanced by
    construction); odd counts perturb equal spacing then project the residual to zero via a few
    minimal-norm Newton steps. Guarantees ``is_balanced(result)`` for the given masses/radii and
    minimum adjacent angular separation ``>= min_gap_frac * (2*pi / n_blades)`` so blades cannot
    cross or collide at high ``spread``. With masses/radii the angles are returned in BLADE ORDER
    (angle k belongs to masses[k]), otherwise sorted.
    """
    if n_blades < 2:
        raise ValueError("need >= 2 blades")
    spread_f = float(spread)
    if not (math.isfinite(spread_f) and spread_f >= 0.0):
        raise ValueError(f"spread must be finite and >= 0, got {spread!r}")
    gap_frac = float(min_gap_frac)
    if not (math.isfinite(gap_frac) and 0.0 <= gap_frac < 1.0):
        raise ValueError(f"min_gap_frac must be in [0, 1), got {min_gap_frac!r}")
    rng = np.random.default_rng() if rng is None else rng
    step = TWO_PI / n_blades
    min_gap = gap_frac * step
    max_attempts = 64

    if n_blades % 2 == 0 and masses is None and radii is None:
        # pair method: N/2 base angles in [0, pi); blade at base and base+pi -> each pair self-cancels
        half = n_blades // 2
        base0 = np.arange(half) * step
        scale = spread_f
        for attempt in range(max_attempts):
            base = base0 + scale * 0.5 * step * rng.standard_normal(half)
            cand = np.sort(np.concatenate([base, base + math.pi]) % TWO_PI)
            if _min_circular_gap(cand) >= min_gap - 1e-12:
                return cand
            if attempt >= 4:
                scale *= 0.8
        return equal_spacing(n_blades)

    # general case: perturb equal spacing, then null U by minimal-norm angle corrections
    mr = _mr(n_blades, masses, radii)
    total_mr = float(np.sum(np.abs(mr)))
    if total_mr > 0.0 and float(np.max(mr)) > (total_mr - float(np.max(mr))) + 1e-12:
        raise ValueError(
            "cannot statically balance blades by angle adjustment alone: "
            "one blade's m*r exceeds the sum of all others"
        )
    denom = total_mr or 1.0
    scale = spread_f
    last_residual = float("inf")
    for attempt in range(max_attempts):
        ang = equal_spacing(n_blades) + scale * 0.5 * step * rng.standard_normal(n_blades)
        for _ in range(50):
            ux = float(np.sum(mr * np.cos(ang)))
            uy = float(np.sum(mr * np.sin(ang)))
            if math.hypot(ux, uy) / denom < 1e-9:
                break
            # dU/dth_k = mr_k * (-sin, cos); solve J dth = -U with minimal norm (pseudoinverse)
            J = np.vstack([-mr * np.sin(ang), mr * np.cos(ang)])   # 2 x N
            dth = J.T @ np.linalg.solve(J @ J.T + 1e-12 * np.eye(2), -np.array([ux, uy]))
            ang = ang + dth
        ang = ang % TWO_PI
        ux = float(np.sum(mr * np.cos(ang)))
        uy = float(np.sum(mr * np.sin(ang)))
        last_residual = math.hypot(ux, uy) / denom
        if last_residual <= 1e-6 and _min_circular_gap(ang) >= min_gap - 1e-12:
            # Sorting reorders blades; with per-blade masses/radii that would break the
            # mass<->angle pairing the balance was solved for (Audit #5), so keep blade order.
            return np.sort(ang) if (masses is None and radii is None) else ang
        if attempt >= 4:
            scale *= 0.8

    if masses is None and radii is None:
        return equal_spacing(n_blades)
    raise ValueError(
        f"balanced_uneven_spacing did not converge to a non-overlapping statically balanced "
        f"pattern (normalized residual {last_residual:.3e}, min_gap_frac={gap_frac})"
    )
