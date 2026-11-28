"""2D airfoil section generators.

Sections are returned as a closed, ordered loop of (x_chord, y_thickness) points in
normalized chord coordinates (x in [0, 1], chord length = 1). The loop starts at the
trailing edge, runs along the upper surface to the leading edge, and back along the lower
surface to the trailing edge (standard airfoil ordering), and is explicitly closed.

For cambered NACA sections, loop[:,0] is the *cambered surface* X. LE/TE thickness scales
and chordwise weights must use the generator chord parameter instead — request it via
``return_chord_param=True``.
"""

from __future__ import annotations

import math

import numpy as np

SECTION_NACA = "naca"
SECTION_PLATE = "plate"
SECTION_FAMILIES = (SECTION_NACA, SECTION_PLATE)


def naca4(
    max_camber: float,
    camber_pos: float,
    thickness: float,
    n_points: int = 60,
    *,
    return_chord_param: bool = False,
) -> np.ndarray | tuple[np.ndarray, np.ndarray]:
    """Generate a NACA 4-digit airfoil as a closed loop of 2D points.

    Args:
        max_camber: Maximum camber as a fraction of chord (the ``m`` in NACA MPXX, e.g.
            0.02 for 2%). Use 0.0 for a symmetric section.
        camber_pos: Chordwise position of max camber as a fraction of chord (``p``, e.g.
            0.4). Ignored when ``max_camber`` is 0.
        thickness: Maximum thickness as a fraction of chord (``t``, e.g. 0.10 for 10%).
        n_points: Number of points per surface (upper/lower). More points = smoother.
        return_chord_param: When True, also return generator chord parameter ``x`` in [0, 1]
            aligned with each loop vertex (not the cambered surface X).

    Returns:
        Array of shape (N, 2) of (x, y) points, closed loop, chord = 1.
        Or ``(loop, x_param)`` when ``return_chord_param`` is True.
    """
    m, p, t = float(max_camber), float(camber_pos), float(thickness)
    if not (math.isfinite(m) and math.isfinite(p) and math.isfinite(t)):
        raise ValueError(
            f"naca4 parameters must be finite: max_camber={m!r}, camber_pos={p!r}, thickness={t!r}"
        )
    if t < 0.0:
        raise ValueError(f"naca4 thickness must be >= 0, got {t!r}")
    n_pts = int(n_points)
    if n_pts < 2:
        raise ValueError(f"naca4 n_points must be >= 2, got {n_points!r}")

    # Cosine spacing clusters points near the leading and trailing edges.
    beta = np.linspace(0.0, np.pi, n_pts)
    x = 0.5 * (1.0 - np.cos(beta))

    # Thickness distribution (Abbott & von Doenhoff 1959 §6.2; modified -0.1036 closes TE).
    yt = 5.0 * t * (
        0.2969 * np.sqrt(x)
        - 0.1260 * x
        - 0.3516 * x**2
        + 0.2843 * x**3
        - 0.1036 * x**4
    )

    yc, theta = _naca_camber_line(x, m, p)

    xu = x - yt * np.sin(theta)
    yu = yc + yt * np.cos(theta)
    xl = x + yt * np.sin(theta)
    yl = yc - yt * np.cos(theta)

    # Upper surface trailing->leading, then lower surface leading->trailing.
    upper = np.column_stack([xu[::-1], yu[::-1]])
    lower = np.column_stack([xl[1:], yl[1:]])
    loop = np.vstack([upper, lower])
    x_param = np.concatenate([x[::-1], x[1:]])

    # Ensure explicit closure.
    if not np.allclose(loop[0], loop[-1]):
        loop = np.vstack([loop, loop[0]])
        x_param = np.concatenate([x_param, [float(x_param[0])]])
    if return_chord_param:
        return loop, x_param
    return loop


def _naca_camber_line(
    x: np.ndarray, max_camber: float, camber_pos: float,
) -> tuple[np.ndarray, np.ndarray]:
    """NACA 4-digit meanline ``yc`` and slope angle ``theta`` at chord stations ``x``.

    Supports signed ``max_camber`` (#117): negative values reflect the meanline across ``y = 0``
    (``yc(-m) == -yc(+m)``, ``theta(-m) == -theta(+m)``) instead of silently collapsing to 0.
    """
    m, p = float(max_camber), float(camber_pos)
    if abs(m) <= 1e-12 or not (0.0 < p < 1.0):
        z = np.zeros_like(x, dtype=float)
        return z, z
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
    return yc, np.arctan(dyc)


def rounded_plate(
    thickness: float,
    n_points: int = 60,
    *,
    max_camber: float = 0.0,
    camber_pos: float = 0.4,
    te_radius_frac: float = 1.0,
    le_radius_frac: float = 1.0,
    te_face: float = 1.0,
    le_face: float = 1.0,
    return_chord_param: bool = False,
) -> np.ndarray | tuple[np.ndarray, np.ndarray]:
    """Constant-thickness plate: tunable LE/TE roundness, optional camber (slight face curve).

    ``te_face`` / ``le_face`` are the fraction of the wall still left at the
    trailing-edge tip and the leading-edge tip (1 = full wall, 0 = that edge
    meets the chord). Each taper runs from that edge to mid-chord. Roundness
    still only shapes the chordwise nose; it does not close the wall.

    ``{le,te}_radius_frac`` scales the *chordwise* semi-axis of an ellipse that always
    meets the flat faces at ±``t/2`` (1 = circular bullnose, ~0 = sharp knife). A circle
    of radius ``< t/2`` would leave a shoulder step at the face/nose join — that ridge is
    the false “LE bead” along the blade. Camber uses the NACA 4-digit meanline so the
    blade face bows chordwise; wrap/lean still handle spanwise planform.
    """
    t_raw = float(thickness)
    if not math.isfinite(t_raw) or t_raw <= 0.0:
        raise ValueError(f"rounded_plate thickness must be a positive finite number, got {thickness!r}")
    if int(n_points) < 2:
        raise ValueError(f"rounded_plate n_points must be >= 2, got {n_points!r}")
    for name, val in (
        ("max_camber", max_camber),
        ("camber_pos", camber_pos),
        ("te_radius_frac", te_radius_frac),
        ("le_radius_frac", le_radius_frac),
        ("te_face", te_face),
        ("le_face", le_face),
    ):
        if not math.isfinite(float(val)):
            raise ValueError(f"rounded_plate {name} must be finite, got {val!r}")
    t = max(t_raw, 1e-6)
    half_t = 0.5 * t
    le_frac = float(np.clip(le_radius_frac, 0.0, 1.0))
    te_frac = float(np.clip(te_radius_frac, 0.0, 1.0))
    # Keep a tiny chordwise axis so the loft wire stays manifold when "sharp".
    _min_a = min(0.02 * half_t, 0.004)
    a_le = min(max(le_frac * half_t, _min_a), 0.49)
    a_te = min(max(te_frac * half_t, _min_a), 0.49)

    n_arc = max(int(n_points) // 2, 8)
    n_flat = max(int(n_points) // 2, 4)

    # Ellipse LE/TE: center (a_le,0) / (1-a_te,0); y always spans ±half_t so faces meet flush.
    # Upper TE→LE: TE tip → TE arc → flat → LE arc → LE tip, using identical arc steps on both
    # ends and mirroring upper → lower so upper/lower coordinates are bit-exact symmetric (#118).
    th_te_u = np.linspace(0.0, 0.5 * np.pi, n_arc, endpoint=False)
    te_u = np.column_stack([
        (1.0 - a_te) + a_te * np.cos(th_te_u),
        half_t * np.sin(th_te_u),
    ])

    x_flat_u = np.linspace(1.0 - a_te, a_le, n_flat, endpoint=False)
    flat_u = np.column_stack([x_flat_u, np.full_like(x_flat_u, half_t)])

    th_le_u = np.linspace(0.5 * np.pi, np.pi, n_arc + 1, endpoint=True)
    le_u = np.column_stack([
        a_le + a_le * np.cos(th_le_u),
        half_t * np.sin(th_le_u),
    ])
    upper = np.vstack([te_u, flat_u, le_u])

    # Lower LE→TE: exact mirror of upper (skip LE tip duplicate; ends at TE tip == upper[0]).
    lower = upper[-2::-1].copy()
    lower[:, 1] = -lower[:, 1]

    loop = np.vstack([upper, lower])
    if not np.allclose(loop[0], loop[-1]):
        loop = np.vstack([loop, loop[0]])

    # Chord parameter before camber (surface X ≈ chord param on the flat plate).
    x_param = np.asarray(loop[:, 0], dtype=float)
    te = float(np.clip(te_face, 0.0, 1.0))
    le = float(np.clip(le_face, 0.0, 1.0))
    if te < 1.0 - 1e-12 or le < 1.0 - 1e-12:
        # Full wall at mid-chord. Each end closes in a straight line to its face fraction.
        scale = np.ones_like(x_param)
        if te < 1.0 - 1e-12:
            aft = x_param >= 0.5
            scale[aft] = te + (1.0 - te) * ((1.0 - x_param[aft]) / 0.5)
        if le < 1.0 - 1e-12:
            fore = x_param <= 0.5
            scale[fore] = le + (1.0 - le) * (x_param[fore] / 0.5)
        loop = loop.copy()
        loop[:, 1] = loop[:, 1] * scale

    m = float(max_camber)
    if abs(m) > 1e-12:
        yc, theta = _naca_camber_line(x_param, m, float(camber_pos))
        y_local = loop[:, 1]
        loop = np.column_stack([
            x_param - y_local * np.sin(theta),
            yc + y_local * np.cos(theta),
        ])

    if return_chord_param:
        return loop, x_param
    return loop


def section_loop_2d(
    family: str,
    *,
    max_camber: float,
    camber_pos: float,
    thickness: float,
    n_points: int = 60,
    te_radius_frac: float = 1.0,
    le_radius_frac: float = 1.0,
    te_face: float = 1.0,
    le_face: float = 1.0,
    return_chord_param: bool = False,
) -> np.ndarray | tuple[np.ndarray, np.ndarray]:
    """Dispatch to NACA or rounded-plate generator."""
    fam = SECTION_NACA if not family else str(family).lower().strip()
    if fam not in SECTION_FAMILIES:
        raise ValueError(
            f"unknown airfoil section family {family!r}; expected one of {SECTION_FAMILIES}"
        )
    if fam == SECTION_PLATE:
        return rounded_plate(
            thickness,
            n_points,
            max_camber=max_camber,
            camber_pos=camber_pos,
            te_radius_frac=te_radius_frac,
            le_radius_frac=le_radius_frac,
            te_face=te_face,
            le_face=le_face,
            return_chord_param=return_chord_param,
        )
    return naca4(
        max_camber, camber_pos, thickness, n_points, return_chord_param=return_chord_param,
    )
