"""Desktop-scale HAWT params for the registry scaffold (not a field turbine)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WindTurbineParams:
    """Scaffold wind-turbine design vector.

    Lengths in SI meters for aero formulas; geometry converts to mm for the loft.
    """

    diameter_m: float = 0.20
    hub_radius_m: float = 0.025
    n_blades: int = 3
    tip_speed_ratio: float = 7.0
    pitch_deg: float = 4.0  # tip pitch vs rotation plane (scaffold knob)
    freestream_ms: float = 8.0
    chord_tip_frac: float = 0.10  # tip chord / R

    def __post_init__(self) -> None:
        if self.diameter_m <= 0:
            raise ValueError(f"diameter_m must be > 0, got {self.diameter_m}")
        if self.hub_radius_m <= 0 or self.hub_radius_m >= self.diameter_m / 2:
            raise ValueError(
                f"hub_radius_m {self.hub_radius_m} must be in (0, tip_radius)"
            )
        if self.n_blades < 2:
            raise ValueError(f"n_blades must be >= 2, got {self.n_blades}")
        if self.tip_speed_ratio <= 0:
            raise ValueError(f"tip_speed_ratio must be > 0, got {self.tip_speed_ratio}")
        if self.freestream_ms <= 0:
            raise ValueError(f"freestream_ms must be > 0, got {self.freestream_ms}")
