"""Blade-passing tonal analysis from the spacing pattern alone (compute-free).

For a rotor with (approximately) uniform per-blade loading, the tonal source strength at the m-th
shaft harmonic is the unweighted geometric blade-count array factor

    A(m) = | sum_k exp(-i m theta_k) |

with theta_k the blade angles. Equal spacing concentrates all of it into A(m)=N at m = N, 2N, ...
(the blade-pass tone + harmonics) and zero elsewhere -- a single loud tone. Uneven spacing spreads
that energy across many m at LOWER peaks. So the *peak* of A(m) is a free, physics-based proxy for
tonal spreading that we can minimize over balanced spacing patterns without any CFD.

Scope & known limits (#125, Audit #6):
  - **Unweighted geometric array factor only:** applies uniform unit weight across harmonics
    ``m = 1..m_max`` (default ``4 * N``). It omits blade-force harmonic decay ``|F_m|``, Curle
    dipole radiation scaling (``~ m``), and IEC 61672 A-weighting (which attenuates low shaft
    orders ``m = 1, 2`` by 25-40 dB relative to higher sidebands).
  - **Dirichlet ``m_max`` sensitivity:** by Dirichlet's approximation theorem, ``A(m) -> N`` for
    arbitrarily large ``m``, so ``tonal_peak_ratio`` depends on the chosen ``m_max`` cutoff; always
    compare designs at the same ``m_max``. Physically weighted tonal loudness awaits measured rig
    spectra (v0.2).

Reference: rotor tonal-noise theory / Cattanei et al. 2007 (docs/bibliography.md sec.2).
"""

from __future__ import annotations

import numpy as np


def blade_passing_modes(angles_rad, m_max: int | None = None):
    """Array-factor amplitude A(m)=|sum_k e^{-i m theta_k}| for m=1..m_max. Returns (m, amplitude)."""
    ang = np.asarray(angles_rad, float)
    if ang.ndim != 1 or len(ang) == 0:
        raise ValueError("angles_rad must be a non-empty 1-D sequence")
    if not np.all(np.isfinite(ang)):
        raise ValueError("angles_rad must be finite")
    n = len(ang)
    m_hi = 4 * n if m_max is None else int(m_max)
    if m_hi < 1:
        raise ValueError(f"m_max must be >= 1, got {m_max!r}")
    m = np.arange(1, m_hi + 1)
    amp = np.abs(np.exp(-1j * np.outer(m, ang)).sum(axis=1))
    return m, amp


def peak_tone_amplitude(angles_rad, m_max: int | None = None) -> float:
    """Largest tonal amplitude max_m A(m). Equal spacing -> N (all energy at the blade-pass tone)."""
    _, amp = blade_passing_modes(angles_rad, m_max)
    return float(amp.max())


def tonal_peak_ratio(angles_rad, m_max: int | None = None) -> float:
    """Peak tonal amplitude normalized by blade count: 1.0 = fully concentrated (equal spacing),

    < 1.0 = spread (quieter peak tone). The scale-free objective to MINIMIZE when choosing a spacing
    pattern; lower is quieter.
    """
    ang = np.asarray(angles_rad, float)
    return peak_tone_amplitude(ang, m_max) / len(ang)


def peak_tone_reduction_db(angles_rad, m_max: int | None = None) -> float:
    """Peak-tone reduction vs equal spacing, in dB: 20*log10(ratio) (<= 0; more negative = quieter)."""
    r = tonal_peak_ratio(angles_rad, m_max)
    return float(20.0 * np.log10(r)) if r > 0.0 else float("-inf")
