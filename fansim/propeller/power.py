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


_pythrust_ok: bool | None = None


def pythrust_available() -> bool:
    global _pythrust_ok
    if _pythrust_ok is not None:
        return _pythrust_ok
    try:
        import pythrust  # noqa: F401
        _pythrust_ok = True
    except ImportError:
        _pythrust_ok = False
    return _pythrust_ok


def _require_pythrust() -> None:
    if not pythrust_available():
        raise PropulsionExtraMissing(
            "Catalog propulsion requires optional extra: "
            "uv sync --extra propulsion  (setuav-pythrust==0.2.3)"
        )


def _load_apc_db() -> Any:
    from pathlib import Path

    from pythrust import dataset_dir
    from pythrust.propellers.database import PropellerDatabase

    db = PropellerDatabase()
    db.load(Path(dataset_dir()) / "propellers" / "apc_202602")
    return db


def list_catalog_props(*, manufacturer: str = "APC") -> list[dict[str, Any]]:
    _require_pythrust()
    db = _load_apc_db()
    rows: list[dict[str, Any]] = []
    for pid in db.list_propellers():
        meta = db.get(pid).metadata
        if manufacturer and manufacturer.upper() not in (meta.manufacturer or "").upper():
            if manufacturer.upper() != "APC":
                continue
        rows.append(
            {
                "prop_id": meta.id,
                "manufacturer": meta.manufacturer,
                "diameter_in": meta.diameter_in,
                "pitch_in": meta.pitch_in,
                "blade_count": meta.blade_count,
            }
        )
    return rows


def find_catalog_prop(diameter_in: float, pitch_in: float, *, blade_count: int = 2) -> dict[str, Any]:
    _require_pythrust()
    db = _load_apc_db()
    entry = db.find_by_size(float(diameter_in), float(pitch_in), blade_count=int(blade_count))
    meta = entry.metadata
    return {
        "prop_id": meta.id,
        "manufacturer": meta.manufacturer,
        "diameter_in": meta.diameter_in,
        "pitch_in": meta.pitch_in,
        "blade_count": meta.blade_count,
    }


def solve_catalog_operating_point(
    *,
    motor: dict[str, Any],
    battery_voltage_v: float,
    prop_id: str | None = None,
    diameter_in: float | None = None,
    pitch_in: float | None = None,
    blade_count: int = 2,
    throttle: float = 0.7,
    airspeed_mps: float = 0.0,
    rho: float = RHO_AIR,
    system_resistance_ohm: float = 0.02,
) -> dict[str, Any]:
    _require_pythrust()
    import pythrust
    from pythrust.propulsion.models.battery import FixedVoltageBattery
    from pythrust.propulsion.models.motor import MotorSpec
    from pythrust.propulsion.models.propeller import PropellerSpec
    from pythrust.propulsion.models.system import SystemSpec
    from pythrust.propulsion.solver import PropulsionSolver

    db = _load_apc_db()
    if prop_id:
        entry = db.get(prop_id)
    else:
        if diameter_in is None or pitch_in is None:
            raise ValueError("provide prop_id or diameter_in+pitch_in")
        entry = db.find_by_size(float(diameter_in), float(pitch_in), blade_count=int(blade_count))
    meta = entry.metadata
    prop = PropellerSpec(diameter_m=float(meta.diameter_in) * 0.0254)
    m = MotorSpec(
        kv_rpm_per_v=float(motor["kv_rpm_per_v"]),
        resistance_ohm=float(motor["resistance_ohm"]),
        no_load_current_a=float(motor["no_load_current_a"]),
        current_max_a=float(motor["current_max_a"]),
    )
    batt = FixedVoltageBattery(voltage_v=float(battery_voltage_v))
    sys = SystemSpec(resistance_ohm=float(system_resistance_ohm))
    pt = PropulsionSolver().solve_operating_point(
        motor=m,
        battery=batt,
        system=sys,
        propeller=prop,
        prop_entry=entry,
        rho=float(rho),
        airspeed_mps=float(airspeed_mps),
        throttle=float(throttle),
    )
    return {
        "rpm": float(pt.rpm),
        "thrust_n": float(pt.thrust_n),
        "thrust_g": float(pt.thrust_n) / 9.80665 * 1000.0,
        "torque_nm": float(pt.torque_nm),
        "shaft_power_w": float(pt.shaft_power_w),
        "motor_power_w": float(pt.motor_power_w),
        "battery_power_w": float(pt.battery_power_w),
        "motor_current_a": float(pt.motor_current_a),
        "battery_current_a": float(pt.battery_current_a),
        "motor_efficiency": float(pt.motor_efficiency),
        "is_feasible": bool(pt.is_feasible),
        "infeasible_reason": pt.infeasible_reason,
        "source": "pythrust",
        "pythrust_version": getattr(pythrust, "__version__", "0.2.3"),
        "prop_id": meta.id,
        "throttle": float(throttle),
        "airspeed_mps": float(airspeed_mps),
    }
