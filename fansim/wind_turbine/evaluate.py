"""BEM-lite / actuator-disk screen for the wind-turbine scaffold.

Not field-validated. Stamps an honesty note so callers cannot mistake this for RANS.
"""

from __future__ import annotations

import math
from pathlib import Path

from fansim.wind_turbine.params import WindTurbineParams

from fansim.physics.air import RHO_ISA as RHO_AIR  # ISA — props/turbines (fans use AMCA 1.2)
BETZ_LIMIT = 16.0 / 27.0
WIND_TURBINE_HONESTY = (
    "scaffold: BEM-lite Cp screen; no aeroelastic / no RANS domain yet"
)


def evaluate_wind_turbine(
    params: WindTurbineParams,
    workdir: str | Path | None = None,  # noqa: ARG001 — archetype API parity
    **_kwargs,
) -> dict:
    """Return ``Cp`` and ``power_w`` from a crude TSR/pitch-shaped actuator-disk model."""
    tip_r = float(params.diameter_m) / 2.0
    area = math.pi * tip_r * tip_r
    # Peak near λ≈7; pitch sweet spot ~4° — shapes only, not a polar.
    lam = float(params.tip_speed_ratio)
    tsr_shape = math.exp(-0.5 * ((lam - 7.0) / 3.0) ** 2)
    pitch_shape = math.exp(-0.5 * ((float(params.pitch_deg) - 4.0) / 8.0) ** 2)
    # Stay well under Betz; n_blades weakly helps then saturates.
    blade_k = min(1.0, 0.55 + 0.12 * float(params.n_blades))
    cp = float(BETZ_LIMIT * 0.72 * tsr_shape * pitch_shape * blade_k)
    cp = max(0.0, min(cp, 0.45))
    v = float(params.freestream_ms)
    power_w = cp * 0.5 * RHO_AIR * area * (v ** 3)
    omega = (lam * v) / tip_r if tip_r > 0 else 0.0
    rpm = omega * 60.0 / (2.0 * math.pi) if omega else 0.0
    return {
        "feasible": True,
        "Cp": cp,
        "power_w": power_w,
        "raw": {
            "archetype": "wind_turbine",
            "honesty": WIND_TURBINE_HONESTY,
            "tip_speed_ratio": lam,
            "freestream_ms": v,
            "rpm": rpm,
            "area_m2": area,
            "rho": RHO_AIR,
            "betz_limit": BETZ_LIMIT,
        },
    }
