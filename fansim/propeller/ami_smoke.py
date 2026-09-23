"""obj_2 compressible AMI smoke helpers (roadmap §4.3)."""
from __future__ import annotations

import math

MRF_REF_THRUST_G = 938.0
BAND_FRAC = 0.25
FLOOR_G = 10.0
N_REVS = 2
DELTA_T = 4e-5
G_PER_NEWTON = 1000.0 / 9.80665


def rev_period_s(rpm: float) -> float:
    return 60.0 / float(rpm)


def end_time_s(rpm: float, n_revs: int = N_REVS) -> float:
    return float(n_revs) * rev_period_s(rpm)


def band_limits() -> tuple[float, float]:
    return (
        MRF_REF_THRUST_G * (1.0 - BAND_FRAC),
        MRF_REF_THRUST_G * (1.0 + BAND_FRAC),
    )


def window_thrust_g(
    rows: list[list[float]],
    *,
    end_time: float,
    rpm: float,
) -> tuple[float | None, int]:
    t0 = float(end_time) - rev_period_s(rpm)
    window = [r for r in rows if len(r) > 3 and float(r[0]) >= t0]
    if not window:
        return None, 0
    grams = [abs(float(r[3])) / 9.80665 * 1000.0 for r in window]
    return sum(grams) / len(grams), len(grams)


def assess_band(mean_thrust_g: float | None) -> dict:
    lo, hi = band_limits()
    finite = mean_thrust_g is not None and math.isfinite(float(mean_thrust_g))
    mean = float(mean_thrust_g) if finite else None
    passed = bool(finite and mean is not None and lo <= mean <= hi and abs(mean) >= FLOOR_G)
    return {
        "mean_thrust_g": mean,
        "band_pass": passed,
        "band_lo_g": lo,
        "band_hi_g": hi,
        "mrf_ref_thrust_g": MRF_REF_THRUST_G,
        "floor_g": FLOOR_G,
    }


def ami_exit_code(summary: dict) -> int:
    mean = summary.get("mean_thrust_g")
    if mean is None:
        return 1
    try:
        value = float(mean)
    except (TypeError, ValueError):
        return 1
    if not math.isfinite(value):
        return 1
    return 0 if summary.get("band_pass") else 2
