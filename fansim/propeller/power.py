from __future__ import annotations
import math
from typing import Any

RHO_AIR = 1.225


class PropulsionExtraMissing(RuntimeError):
    """Raised when a catalog/PyThrust feature is requested without the extra installed."""


def hover_power_budget(
    *,
    all_up_weight_n: float,
    n_rotors: int,
    tip_radius_m: float,
    figure_of_merit: float,
    eta_elec: float = 0.70,
    battery_wh: float | None = None,
    usable_frac: float = 0.80,
    rho: float = RHO_AIR,
    shaft_power_w: float | None = None,
) -> dict[str, Any]:
    if int(n_rotors) < 1:
        raise ValueError("n_rotors must be >= 1")
    if float(tip_radius_m) <= 0.0:
        raise ValueError("tip_radius_m must be > 0")
    if float(eta_elec) <= 0.0 or float(eta_elec) > 1.0:
        raise ValueError("eta_elec must be in (0, 1]")
    T = float(all_up_weight_n) / float(n_rotors)
    A = math.pi * float(tip_radius_m) ** 2
    P_i = (T ** 1.5) / math.sqrt(2.0 * float(rho) * A) if T > 0.0 else 0.0
    if shaft_power_w is None:
        fm = min(1.0, max(0.05, float(figure_of_merit)))
        P_shaft = P_i / fm if fm > 0.0 else 0.0
        power_model = "momentum_fm"
    else:
        P_shaft = float(shaft_power_w)
        power_model = "bemt_shaft"
    P_elec_total = (P_shaft * float(n_rotors)) / float(eta_elec) if eta_elec > 0.0 else 0.0
    minutes = None
    if battery_wh is not None and P_elec_total > 0.0:
        minutes = 60.0 * float(battery_wh) * float(usable_frac) / P_elec_total
    return {
        "power_model": power_model,
        "thrust_per_rotor_n": T,
        "disk_area_m2": A,
        "ideal_power_w": P_i,
        "shaft_power_w": P_shaft,
        "elec_power_w_total": P_elec_total,
        "eta_elec": float(eta_elec),
        "usable_frac": float(usable_frac),
        "battery_wh": None if battery_wh is None else float(battery_wh),
        "hover_minutes": minutes,
        "n_rotors": int(n_rotors),
        "tip_radius_m": float(tip_radius_m),
        "figure_of_merit_used": (
            min(1.0, max(0.05, float(figure_of_merit))) if shaft_power_w is None else float(figure_of_merit)
        ),
        "rho": float(rho),
    }
