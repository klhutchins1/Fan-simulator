from __future__ import annotations
import math
from typing import Any

from fansim.physics.air import RHO_ISA as RHO_AIR


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


_QUORUM_MOTOR: dict[str, float] = {
    "kv_rpm_per_v": 1900.0,
    "resistance_ohm": 0.05,
    "no_load_current_a": 1.0,
    "current_max_a": 40.0,
}
_QUORUM_BATTERY_V = 22.2
_QUORUM_THROTTLE = 0.7
_Q4_POWER_BAND = 0.15
_Q5_FM_LO = 0.50
_Q5_FM_HI = 0.85
_Q3_FIELD_TOL = 1e-9


def _apc_static_coefficients(entry: Any, rpm_static: float) -> tuple[float, float, float]:
    rpm_keys = list(entry.data_by_rpm.keys())
    if not rpm_keys:
        raise ValueError("APC entry has no RPM tables")
    rpm_key = min(rpm_keys, key=lambda k: abs(float(k) - float(rpm_static)))
    points = entry.data_by_rpm[rpm_key]
    static = next((p for p in points if float(getattr(p, "j", 1.0)) == 0.0), None)
    if static is None:
        static = min(points, key=lambda p: float(getattr(p, "j", 0.0)))
    return float(rpm_key), float(static.ct), float(static.cp)


def _pythrust_native_operating_point(
    *,
    prop_id: str,
    motor: dict[str, Any],
    battery_voltage_v: float,
    throttle: float,
    airspeed_mps: float = 0.0,
    rho: float = RHO_AIR,
    system_resistance_ohm: float = 0.02,
) -> dict[str, float]:
    from pythrust.propulsion.models.battery import FixedVoltageBattery
    from pythrust.propulsion.models.motor import MotorSpec
    from pythrust.propulsion.models.propeller import PropellerSpec
    from pythrust.propulsion.models.system import SystemSpec
    from pythrust.propulsion.solver import PropulsionSolver

    db = _load_apc_db()
    entry = db.get(prop_id)
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
        "shaft_power_w": float(pt.shaft_power_w),
        "motor_current_a": float(pt.motor_current_a),
    }


def _fields_close(a: float, b: float, *, rel: float = _Q3_FIELD_TOL, abs_tol: float = _Q3_FIELD_TOL) -> bool:
    return math.isclose(float(a), float(b), rel_tol=rel, abs_tol=abs_tol)


def run_propulsion_quorum(*, prop_id: str = "APC_5x4.5E", rpm_static: float = 10000.0) -> dict[str, Any]:
    _require_pythrust()
    checks: list[dict[str, Any]] = []

    adapter = solve_catalog_operating_point(
        motor=_QUORUM_MOTOR,
        battery_voltage_v=_QUORUM_BATTERY_V,
        prop_id=prop_id,
        throttle=_QUORUM_THROTTLE,
        airspeed_mps=0.0,
    )
    native = _pythrust_native_operating_point(
        prop_id=prop_id,
        motor=_QUORUM_MOTOR,
        battery_voltage_v=_QUORUM_BATTERY_V,
        throttle=_QUORUM_THROTTLE,
    )
    q3_fields = ("rpm", "thrust_n", "shaft_power_w", "motor_current_a")
    q3_mismatches = [
        f"{name}: adapter={adapter[name]!r} native={native[name]!r}"
        for name in q3_fields
        if not _fields_close(adapter[name], native[name])
    ]
    checks.append(
        {
            "id": "Q3",
            "pass": not q3_mismatches,
            "detail": "PyThrust adapter matches native solver"
            if not q3_mismatches
            else "; ".join(q3_mismatches),
        }
    )

    db = _load_apc_db()
    entry = db.get(prop_id)
    dia_m = float(entry.metadata.diameter_in) * 0.0254
    rpm_used, ct, cp = _apc_static_coefficients(entry, rpm_static)
    n = rpm_used / 60.0
    rho = RHO_AIR
    thrust_n = ct * rho * (n**2) * (dia_m**4)
    shaft_power_w = cp * rho * (n**3) * (dia_m**5)
    disk_area_m2 = math.pi * (dia_m / 2.0) ** 2
    ideal_power_w = (thrust_n**1.5) / math.sqrt(2.0 * rho * disk_area_m2)
    figure_of_merit = ideal_power_w / shaft_power_w if shaft_power_w > 0.0 else 0.0
    momentum_shaft_w = ideal_power_w / figure_of_merit if figure_of_merit > 0.0 else 0.0
    identity_ok = _fields_close(shaft_power_w, momentum_shaft_w)
    budget = hover_power_budget(
        all_up_weight_n=thrust_n,
        n_rotors=1,
        tip_radius_m=dia_m / 2.0,
        figure_of_merit=figure_of_merit,
    )
    budget_shaft_w = float(budget["shaft_power_w"])
    rel_err = abs(budget_shaft_w - shaft_power_w) / shaft_power_w if shaft_power_w > 0.0 else float("inf")
    band_ok = rel_err <= _Q4_POWER_BAND
    q4_pass = identity_ok and band_ok
    checks.append(
        {
            "id": "Q4",
            "pass": q4_pass,
            "detail": (
                f"rpm={rpm_used} static ct={ct} cp={cp}; "
                f"P_catalog={shaft_power_w:.4f}W P_hover_budget={budget_shaft_w:.4f}W "
                f"rel_err={rel_err:.4f} FM={figure_of_merit:.4f}"
            ),
            "rpm_used": rpm_used,
            "shaft_power_w": shaft_power_w,
            "hover_budget_shaft_w": budget_shaft_w,
            "relative_error": rel_err,
            "figure_of_merit": figure_of_merit,
        }
    )

    fm_ok = _Q5_FM_LO <= figure_of_merit <= _Q5_FM_HI
    checks.append(
        {
            "id": "Q5",
            "pass": fm_ok,
            "detail": (
                f"catalog static FoM={figure_of_merit:.4f} "
                f"expected [{_Q5_FM_LO}, {_Q5_FM_HI}] at rpm={rpm_used}"
            ),
            "figure_of_merit": figure_of_merit,
            "rpm_used": rpm_used,
        }
    )

    all_pass = all(c["pass"] for c in checks)
    return {"checks": checks, "all_pass": all_pass, "prop_id": prop_id, "rpm_static": float(rpm_static)}
