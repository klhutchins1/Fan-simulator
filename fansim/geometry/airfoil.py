# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""2D airfoil section generators.

Sections are returned as a closed, ordered loop of (x_chord, y_thickness) points in
normalized chord coordinates (x in [0, 1], chord length = 1). The loop starts at the
trailing edge, runs along the upper surface to the leading edge, and back along the lower
surface to the trailing edge (standard airfoil ordering), and is explicitly closed.
"""

from __future__ import annotations

import numpy as np


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
