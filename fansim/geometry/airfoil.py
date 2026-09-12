"""2D airfoil section generators.

Sections are returned as a closed, ordered loop of (x_chord, y_thickness) points in
normalized chord coordinates (x in [0, 1], chord length = 1). The loop starts at the
trailing edge, runs along the upper surface to the leading edge, and back along the lower
surface to the trailing edge (standard airfoil ordering), and is explicitly closed.
"""

from __future__ import annotations

import numpy as np

SECTION_NACA = "naca"
SECTION_PLATE = "plate"
SECTION_FAMILIES = (SECTION_NACA, SECTION_PLATE)


def naca4(
    max_camber: float,
    camber_pos: float,
    thickness: float,
    n_points: int = 60,
) -> np.ndarray:
    """Generate a NACA 4-digit airfoil as a closed loop of 2D points.

    Args:
        max_camber: Maximum camber as a fraction of chord (the ``m`` in NACA MPXX, e.g.
            0.02 for 2%). Use 0.0 for a symmetric section.
        camber_pos: Chordwise position of max camber as a fraction of chord (``p``, e.g.
            0.4). Ignored when ``max_camber`` is 0.
        thickness: Maximum thickness as a fraction of chord (``t``, e.g. 0.10 for 10%).
        n_points: Number of points per surface (upper/lower). More points = smoother.

    Returns:
        Array of shape (2 * n_points, 2) of (x, y) points, closed loop, chord = 1.
    """
    m, p, t = float(max_camber), float(camber_pos), float(thickness)

    # Cosine spacing clusters points near the leading and trailing edges.
    beta = np.linspace(0.0, np.pi, n_points)
    x = 0.5 * (1.0 - np.cos(beta))

    # Thickness distribution (last coefficient closes the trailing edge: -0.1036).
    yt = 5.0 * t * (
        0.2969 * np.sqrt(x)
        - 0.1260 * x
        - 0.3516 * x**2
        + 0.2843 * x**3
        - 0.1036 * x**4
    )

    if m > 0.0 and 0.0 < p < 1.0:
        yc = np.where(
            x < p,
            (m / p**2) * (2 * p * x - x**2),
            (m / (1 - p) ** 2) * ((1 - 2 * p) + 2 * p * x - x**2),
        )
        dyc = np.where(
            x < p,
            (2 * m / p**2) * (p - x),
            (2 * m / (1 - p) ** 2) * (p - x),
        )
        theta = np.arctan(dyc)
    else:
        yc = np.zeros_like(x)
        theta = np.zeros_like(x)

    xu = x - yt * np.sin(theta)
    yu = yc + yt * np.cos(theta)
    xl = x + yt * np.sin(theta)
    yl = yc - yt * np.cos(theta)

    # Upper surface trailing->leading, then lower surface leading->trailing.
    upper = np.column_stack([xu[::-1], yu[::-1]])
    lower = np.column_stack([xl[1:], yl[1:]])
    loop = np.vstack([upper, lower])

    # Ensure explicit closure.
    if not np.allclose(loop[0], loop[-1]):
        loop = np.vstack([loop, loop[0]])
    return loop


def rounded_plate(thickness: float, n_points: int = 60) -> np.ndarray:
    """Constant-thickness stadium section: flat faces + semicircle LE and TE (bullnose).

    Radius of each end = ``thickness / 2`` (full round). Chord normalized to 1. Same loop
    ordering as ``naca4`` (start at TE, upper to LE, lower back to TE). Symmetric — no camber.
    """
    t = max(float(thickness), 1e-6)
    R = min(0.5 * t, 0.49)

    n_arc = max(int(n_points) // 2, 8)
    n_flat = max(int(n_points) // 2, 4)

    # Upper TE→LE: TE tip → TE quarter-circle → flat → LE quarter-circle → LE tip
    th_te_u = np.linspace(0.0, 0.5 * np.pi, n_arc, endpoint=False)
    te_u = np.column_stack([(1.0 - R) + R * np.cos(th_te_u), R * np.sin(th_te_u)])

    x_flat_u = np.linspace(1.0 - R, R, n_flat, endpoint=False)
    flat_u = np.column_stack([x_flat_u, np.full_like(x_flat_u, R)])

    th_le_u = np.linspace(0.5 * np.pi, np.pi, n_arc, endpoint=True)
    le_u = np.column_stack([R + R * np.cos(th_le_u), R * np.sin(th_le_u)])
    upper = np.vstack([te_u, flat_u, le_u])

    # Lower LE→TE (skip LE tip duplicate)
    th_le_l = np.linspace(np.pi, 1.5 * np.pi, n_arc, endpoint=False)[1:]
    le_l = np.column_stack([R + R * np.cos(th_le_l), R * np.sin(th_le_l)])

    x_flat_l = np.linspace(R, 1.0 - R, n_flat, endpoint=False)
    flat_l = np.column_stack([x_flat_l, np.full_like(x_flat_l, -R)])

    th_te_l = np.linspace(-0.5 * np.pi, 0.0, n_arc, endpoint=True)
    te_l = np.column_stack([(1.0 - R) + R * np.cos(th_te_l), R * np.sin(th_te_l)])
    lower = np.vstack([le_l, flat_l, te_l])

    loop = np.vstack([upper, lower])
    if not np.allclose(loop[0], loop[-1]):
        loop = np.vstack([loop, loop[0]])
    return loop


def section_loop_2d(
    family: str,
    *,
    max_camber: float,
    camber_pos: float,
    thickness: float,
    n_points: int = 60,
) -> np.ndarray:
    """Dispatch to NACA or rounded-plate generator."""
    fam = str(family or SECTION_NACA).lower().strip()
    if fam == SECTION_PLATE:
        return rounded_plate(thickness, n_points)
    return naca4(max_camber, camber_pos, thickness, n_points)
