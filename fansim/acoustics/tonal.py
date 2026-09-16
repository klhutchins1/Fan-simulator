"""Blade-passing tonal analysis from the spacing pattern alone (compute-free).

For a rotor with (approximately) uniform per-blade loading, the tonal source strength at the m-th
shaft harmonic is the blade-count array factor

    A(m) = | sum_k exp(-i m theta_k) |

with theta_k the blade angles. Equal spacing concentrates all of it into A(m)=N at m = N, 2N, ...
(the blade-pass tone + harmonics) and zero elsewhere -- a single loud tone. Uneven spacing spreads
that energy across many m at LOWER peaks. So the *peak* of A(m) is a free, physics-based proxy for
tonal loudness that we can minimize over balanced spacing patterns without any CFD.

Reference: rotor tonal-noise theory / Cattanei et al. 2007 (docs/bibliography.md sec.2).
"""

from __future__ import annotations

import numpy as np


def blade_passing_modes(angles_rad, m_max: int | None = None):
    """Array-factor amplitude A(m)=|sum_k e^{-i m theta_k}| for m=1..m_max. Returns (m, amplitude)."""
    ang = np.asarray(angles_rad, float)
    n = len(ang)
    m_max = m_max or 4 * n
    m = np.arange(1, m_max + 1)
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
    return peak_tone_amplitude(angles_rad, m_max) / len(angles_rad)


def peak_tone_reduction_db(angles_rad, m_max: int | None = None) -> float:
    """Peak-tone reduction vs equal spacing, in dB: 20*log10(ratio) (<= 0; more negative = quieter)."""
    r = tonal_peak_ratio(angles_rad, m_max)
    return 20.0 * np.log10(r) if r > 0 else float("-inf")
