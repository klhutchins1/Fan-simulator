# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
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
        return self.normalized < 1e-6


def equal_spacing(n_blades: int) -> np.ndarray:
    """Angular positions [rad] for n equally spaced blades (perfectly balanced)."""
    if n_blades < 2:
        raise ValueError("need >= 2 blades")
    return np.arange(n_blades, dtype=float) * (TWO_PI / n_blades)


def _mr(n, masses, radii):
    m = np.ones(n) if masses is None else np.asarray(masses, float)
    r = np.ones(n) if radii is None else np.asarray(radii, float)
    if len(m) != n or len(r) != n:
        raise ValueError("masses/radii must match number of blades")
    return m * r


def static_unbalance(angles, masses=None, radii=None) -> Unbalance:
    """Residual first-moment (static) unbalance of blades at ``angles`` [rad].

    ``masses``/``radii`` default to identical unit blades. Returns magnitude (kg*m), heavy-spot
    angle, and the value normalized by total m*r (so tolerance is scale-free).
    """
    angles = np.asarray(angles, float)
    mr = _mr(len(angles), masses, radii)
    ux = float(np.sum(mr * np.cos(angles)))
    uy = float(np.sum(mr * np.sin(angles)))
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
    return unbalance_mr * omega_rad_s**2


def couple_unbalance(angles, z_positions, masses=None, radii=None) -> float:
    """Couple (dynamic) unbalance magnitude for blades at axial positions ``z_positions``.

    |sum_k m_k r_k z_k e^{i th_k}| -- nonzero couple tilts the axis even when static balance holds.
    Negligible for a thin single-plane rotor; report it for axially-staggered designs.
    """
    angles = np.asarray(angles, float)
    z = np.asarray(z_positions, float)
    mr = _mr(len(angles), masses, radii)
    cx = float(np.sum(mr * z * np.cos(angles)))
    cy = float(np.sum(mr * z * np.sin(angles)))
    return math.hypot(cx, cy)


def balanced_uneven_spacing(n_blades: int, spread: float = 0.3, rng=None,
                            masses=None, radii=None) -> np.ndarray:
    """Generate an UNEVEN but statically balanced set of blade angles [rad].

    ``spread`` in [0,1) scales how far blades wander from equal spacing (0 = equal, tone concentrated;
    larger = more tonal spreading). Even blade counts use diametrically-opposite pairing (balanced by
    construction); odd counts perturb equal spacing then project the residual to zero via a few
    minimal-norm Newton steps. Guarantees is_balanced(result) for the given masses/radii.
    """
    if n_blades < 2:
        raise ValueError("need >= 2 blades")
    rng = np.random.default_rng() if rng is None else rng
    step = TWO_PI / n_blades

    if n_blades % 2 == 0 and masses is None and radii is None:
        # pair method: N/2 base angles in [0, pi); blade at base and base+pi -> each pair self-cancels
        half = n_blades // 2
        base = np.arange(half) * (TWO_PI / n_blades)
        base = base + spread * 0.5 * step * rng.standard_normal(half)
        return np.sort(np.concatenate([base, base + math.pi]) % TWO_PI)

    # general case: perturb equal spacing, then null U by minimal-norm angle corrections
    ang = equal_spacing(n_blades) + spread * 0.5 * step * rng.standard_normal(n_blades)
    mr = _mr(n_blades, masses, radii)
    for _ in range(50):
        ux = np.sum(mr * np.cos(ang)); uy = np.sum(mr * np.sin(ang))
        if math.hypot(ux, uy) / (np.sum(np.abs(mr)) or 1.0) < 1e-9:
            break
        # dU/dth_k = mr_k * (-sin, cos); solve J dth = -U with minimal norm (pseudoinverse)
        J = np.vstack([-mr * np.sin(ang), mr * np.cos(ang)])   # 2 x N
        dth = J.T @ np.linalg.solve(J @ J.T + 1e-12 * np.eye(2), -np.array([ux, uy]))
        ang = ang + dth
    return np.sort(ang % TWO_PI)
