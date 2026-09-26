"""Prop forward-flight polar helpers (BEMT + CFD sweeps).

Advance ratio ``J = V∞ / (n D)`` with ``n`` in rev/s. Force/power coefficients use the
usual propeller definitions at air density ``ρ``:

- ``CT = T / (ρ n² D⁴)``
- ``CP = P / (ρ n³ D⁵)``
- ``η = J·CT / (2π·CP)`` when ``CP > 0`` and ``J > 0`` (else ``None``)
"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, Sequence

from fansim.propeller.bemt import RHO_AIR, analyze

if TYPE_CHECKING:
    from fansim.geometry.blade import BladeParams

DEFAULT_V_INF_MS = (0.0, 5.0, 10.0, 15.0, 20.0)
_HOVER_BC_U = 1.0  # solver needs a tiny freestream; report still uses requested V∞=0


@dataclass(frozen=True)
class PolarPoint:
    v_inf: float
    J: float
    rpm: float
    thrust_n: float
    thrust_g: float
    torque_nm: float
    power_w: float
    CT: float
    CP: float
    eta: float | None
    source: str  # "bemt" | "cfd"
    u_bc: float | None = None  # CFD boundary freestream (may differ at hover)


def advance_ratio(v_inf: float, rpm: float, diameter_m: float) -> float:
    n = float(rpm) / 60.0
    d = float(diameter_m)
    if n <= 0.0 or d <= 0.0:
        return 0.0
    return float(v_inf) / (n * d)


def v_inf_from_j(j: float, rpm: float, diameter_m: float) -> float:
    n = float(rpm) / 60.0
    return float(j) * n * float(diameter_m)


def nondim(
    thrust_n: float,
    power_w: float,
    *,
    rpm: float,
    diameter_m: float,
    v_inf: float,
    rho: float = RHO_AIR,
) -> dict[str, float | None]:
    n = float(rpm) / 60.0
    d = float(diameter_m)
    if n <= 0.0 or d <= 0.0 or rho <= 0.0:
        return {"CT": 0.0, "CP": 0.0, "eta": None, "J": 0.0}
    j = advance_ratio(v_inf, rpm, d)
    ct = float(thrust_n) / (rho * n * n * d**4)
    cp = float(power_w) / (rho * n**3 * d**5)
    eta = (j * ct / (2.0 * math.pi * cp)) if (cp > 0.0 and j > 0.0) else None
    return {"CT": ct, "CP": cp, "eta": eta, "J": j}


def resolve_sweep(
    *,
    v_inf: Sequence[float] | None = None,
    j: Sequence[float] | None = None,
    rpm: float,
    diameter_m: float,
    include_hover: bool = True,
    default: Sequence[float] = DEFAULT_V_INF_MS,
) -> list[float]:
    """Merge ``--v-inf`` and ``--j`` into a sorted unique V∞ list [m/s]."""
    vs: list[float] = []
    if v_inf:
        vs.extend(float(v) for v in v_inf)
    if j:
        vs.extend(v_inf_from_j(float(jj), rpm, diameter_m) for jj in j)
    if not vs:
        vs = [float(v) for v in default]
    if include_hover and all(abs(v) > 1e-12 for v in vs):
        vs.append(0.0)
    # unique within 1e-9, sorted
    uniq: list[float] = []
    for v in sorted(vs):
        if not uniq or abs(v - uniq[-1]) > 1e-9:
            uniq.append(v)
    return uniq


def parse_float_list(text: str | None) -> list[float] | None:
    if text is None or str(text).strip() == "":
        return None
    parts = [p.strip() for p in str(text).replace(";", ",").split(",")]
    return [float(p) for p in parts if p]


def _point_from_forces(
    *,
    v_inf: float,
    rpm: float,
    diameter_m: float,
    thrust_n: float,
    torque_nm: float,
    power_w: float,
    source: str,
    u_bc: float | None = None,
) -> PolarPoint:
    nd = nondim(thrust_n, power_w, rpm=rpm, diameter_m=diameter_m, v_inf=v_inf)
    return PolarPoint(
        v_inf=float(v_inf),
        J=float(nd["J"] or 0.0),
        rpm=float(rpm),
        thrust_n=float(thrust_n),
        thrust_g=float(thrust_n) / 9.80665 * 1000.0,
        torque_nm=float(torque_nm),
        power_w=float(power_w),
        CT=float(nd["CT"] or 0.0),
        CP=float(nd["CP"] or 0.0),
        eta=None if nd["eta"] is None else float(nd["eta"]),
        source=source,
        u_bc=u_bc,
    )


def run_bemt_polar(
    params: BladeParams,
    rpm: float,
    v_infs: Iterable[float],
    *,
    diameter_m: float | None = None,
) -> list[PolarPoint]:
    d = float(diameter_m) if diameter_m is not None else float(params.tip_radius) * 2.0 / 1000.0
    points: list[PolarPoint] = []
    for v in v_infs:
        perf = analyze(params, rpm=float(rpm), v_forward=float(v))
        points.append(
            _point_from_forces(
                v_inf=float(v),
                rpm=float(rpm),
                diameter_m=d,
                thrust_n=perf.thrust_n,
                torque_nm=perf.torque_nm,
                power_w=perf.power_w,
                source="bemt",
            )
        )
    return points


def cfd_bc_u(v_inf: float) -> float:
    """Boundary freestream; hover uses ε so rhoSimpleFoam has a direction."""
    v = float(v_inf)
    return v if v >= 0.5 else _HOVER_BC_U


def run_cfd_polar(
    spec,
    workdir: str | Path,
    v_infs: Sequence[float],
    *,
    rpm: float | None = None,
    iters: int = 400,
    procs: int = 8,
    base_cell: float = 0.005,
    spec_key: str | None = None,
    params: BladeParams | None = None,
    bemt_floor_g: float = 0.0,
    direction: str = "auto",
) -> dict:
    """Mesh once, re-solve at each V∞, return meta + ``points`` list of dicts.

    ``direction`` is ``"auto"`` (default) to derive orientation/spin from the mesh-only proof
    (:func:`fansim.propeller.direction.prop_direction`), orienting the CFD copy if needed and
    overriding the spin used for MRF; or ``"manual"`` to keep spin=-1 as-is.
    """
    from fansim.cfd.openfoam_case import MeshResolution
    from fansim.cfd.orientation import orient_impeller_for_cfd
    from fansim.cfd.runner import OpenFOAMRunner
    from fansim.geometry import build_impeller, export_stl, watertight_report
    from fansim.propeller.cfd import (
        build_prop_case,
        parse_prop_metrics,
        prop_open_air,
        purge_prop_time_dirs,
        run_solve_prop,
        set_prop_freestream,
    )
    from fansim.propeller.calibrate import datasheet_compare, normalize_metrics_sign
    from fansim.propeller.direction import prop_direction
    from fansim.propeller.geometry import build_prop, prop_blade_params
    from fansim.propeller.optimize import bemt_thrust_g

    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    case_dir = workdir / "case"
    case_dir.mkdir(parents=True, exist_ok=True)

    rpm_f = float(0.7 * float(spec.rpm_max) if rpm is None else rpm)
    omega_rad_s = rpm_f * 2.0 * math.pi / 60.0
    diameter_m = float(spec.diameter_mm) / 1000.0
    tip_radius_m = diameter_m / 2.0
    spin_i = -1

    blade = params if params is not None else prop_blade_params(spec)
    bemt_g = float(bemt_thrust_g(blade, spec, rpm=rpm_f))
    key = spec_key or getattr(spec, "name", None) or str(spec)
    if float(bemt_floor_g) > 0.0 and bemt_g < float(bemt_floor_g):
        return {
            "skipped": True,
            "reason": f"bemt_thrust_g {bemt_g:.6g} < bemt_floor_g {float(bemt_floor_g):.6g}",
            "bemt_thrust_g": bemt_g,
            "tip_mach": float(spec.tip_mach(rpm_f)),
            "rpm": rpm_f,
            "spin": spin_i,
            "spec": key,
            "points": [],
        }

    stl = workdir / "prop.stl"
    if params is None:
        build_prop(spec, stl)
    else:
        export_stl(build_impeller(blade), stl, tolerance=0.02, angular_tolerance=0.1)

    orientation_used = None
    if direction == "auto":
        d = prop_direction(stl)
        if d.orientation == "flipped":
            orient_impeller_for_cfd(stl, stl, "flipped")
        spin_i = d.spin
        direction_source = d.source
        orientation_used = d.orientation
    else:
        direction_source = "manual"

    # The flip mirrors z, so bounds must be re-measured after orientation.
    rep = watertight_report(stl)
    (_, _, z0), (_, _, z1) = rep.bounds_mm

    v_list = [float(v) for v in v_infs]
    first_bc = cfd_bc_u(v_list[0] if v_list else 0.0)
    dom = prop_open_air(
        tip_radius_m, z0 / 1000.0, z1 / 1000.0, rpm=rpm_f, u_eps=first_bc, spin=spin_i,
    )

    runner = OpenFOAMRunner(case_dir)
    build_prop_case(
        case_dir,
        stl,
        dom,
        mesh=MeshResolution(base_cell=float(base_cell)),
        n_iters=int(iters),
        n_subdomains=int(procs),
    )
    from fansim.cfd.openfoam_case import run_mesh

    run_mesh(runner)

    points: list[PolarPoint] = []
    for v in v_list:
        u_bc = cfd_bc_u(v)
        set_prop_freestream(case_dir, u_bc, tip_radius_m=tip_radius_m)
        purge_prop_time_dirs(case_dir)
        run_solve_prop(runner, n_procs=int(procs))
        m = parse_prop_metrics(case_dir, omega_rad_s=omega_rad_s)
        m = normalize_metrics_sign(m, spin=spin_i)
        points.append(
            _point_from_forces(
                v_inf=v,
                rpm=rpm_f,
                diameter_m=diameter_m,
                thrust_n=m["thrust_n"],
                torque_nm=m["torque_nm"],
                power_w=m["shaft_power_w"],
                source="cfd",
                u_bc=u_bc,
            )
        )

    return {
        "skipped": False,
        "bemt_thrust_g": bemt_g,
        "solver": "rhoSimpleFoam",
        "domain": "open_air",
        "regime": "compressible-MRF",
        "tip_mach": float(spec.tip_mach(rpm_f)),
        "rpm": rpm_f,
        "spin": spin_i,
        "direction_source": direction_source,
        "orientation": orientation_used,
        "spec": key,
        "datasheet": datasheet_compare(
            thrust_g=points[0].thrust_g if points else 0.0,
            power_w=points[0].power_w if points else None,
            rpm=rpm_f,
            spec=spec,
        ),
        "points": [asdict(p) for p in points],
    }


def write_polar_artifacts(
    out_dir: str | Path,
    points: Sequence[PolarPoint] | Sequence[dict],
    *,
    meta: dict | None = None,
) -> tuple[Path, Path]:
    """Write ``polar.csv`` + ``polar.json`` under ``out_dir``."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = [asdict(p) if isinstance(p, PolarPoint) else dict(p) for p in points]
    csv_path = out_dir / "polar.csv"
    json_path = out_dir / "polar.json"
    fieldnames = [
        "v_inf", "J", "rpm", "thrust_n", "thrust_g", "torque_nm", "power_w",
        "CT", "CP", "eta", "source", "u_bc",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)
    payload = {"meta": meta or {}, "points": rows}
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return csv_path, json_path
