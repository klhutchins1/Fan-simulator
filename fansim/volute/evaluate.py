"""Score a radial / volute blower in the stage-1 radial-discharge MRF domain."""

from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path

from fansim.cfd.metrics import parse_fan_metrics
from fansim.cfd.openfoam_case import MeshResolution, run_mesh, run_solve
from fansim.cfd.runner import OpenFOAMRunner
from fansim.fan_spec import A12X25, FanSpec
from fansim.geometry import watertight_report
from fansim.optimize.motor_curve import motor_curve_stamps, motor_operating_rpm
from fansim.optimize.objectives import INFEASIBLE_NOISE, ObjectiveResult, SCREENING_GRID_STAMP, _infeasible
from fansim.optimize.print_penalty import apply_print_penalty
from fansim.optimize.system_curve import (
    REF_CFM,
    SystemCurveError,
    derated_probe_pa,
    score_operating_point,
)
from fansim.volute.case import build_volute_case
from fansim.volute.domain import DEFAULT_VOLUTE_RPM, domain_for_volute
from fansim.volute.geometry import VOLUTE_HONESTY, VoluteParams, export_volute_stls


def evaluate_volute(
    params: VoluteParams,
    workdir: str | Path,
    *,
    procs: int = 8,
    base_cell: float = 0.006,
    iters: int = 800,
    load_pa: float = 50.0,
    rpm: float = DEFAULT_VOLUTE_RPM,
    spec: FanSpec = A12X25,
    wall_ks_mm: float | None = None,
    mesh_only: bool = False,
    print_penalty: bool = True,
) -> ObjectiveResult:
    """Export impeller+casing, write the volute MRF case, mesh, and free+load solve.

    Stage 2: sealed casing fill removes exterior hex bypass; tongue is still a
    discrete cutwater on a segmented spiral. Failures return ``feasible=False``
    with a clear reason (geometry / mesh / solve) instead of crashing the caller.

    Motor derate matches axial/mixed/CROR: CFD torque at ``rpm`` intersects the
    FanSpec motor curve (rated at this CFD rpm), then CFM ∝ RPM and probe
    pressure ∝ RPM².
    """
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    run_rpm = float(rpm)
    # Center the motor curve on this CFD rpm (same electrical budget as ``spec``).
    run_spec = replace(spec, rpm=run_rpm)
    raw: dict = {
        "archetype": "volute",
        "topology": "volute_radial",
        "domain": "radial_mrf_sealed_enclosure",
        "honesty": VOLUTE_HONESTY,
        "rpm": run_rpm,
        "cfd_rpm": run_rpm,
        "load_pa": float(load_pa),
        "spec_name": spec.name,
        # GCI honesty (§11.1 / §10.8). No circular inlet-area check: sealed scroll, not tube-in-hex.
        **SCREENING_GRID_STAMP,
    }

    try:
        domain = domain_for_volute(params, rpm=run_rpm)
    except Exception as exc:  # noqa: BLE001
        return _infeasible(f"domain failed: {type(exc).__name__}: {exc}", t0, raw=raw)
    raw["outlet_area_m2"] = domain.outlet_area_m2
    raw["mrf_radius_m"] = domain.mrf_radius

    try:
        imp_stl, cas_stl = export_volute_stls(params, workdir)
    except Exception as exc:  # noqa: BLE001
        return _infeasible(
            f"geometry failed: {type(exc).__name__}: {exc}", t0, raw=raw)

    rep = watertight_report(imp_stl)
    if not rep.ok:
        return _infeasible(
            f"impeller not watertight ({rep.n_bodies} bodies)", t0, raw=raw)

    try:
        build_volute_case(
            workdir, imp_stl, cas_stl, domain,
            mesh=MeshResolution(base_cell=base_cell),
            n_iters=iters, n_subdomains=procs,
            back_pressure_pa=0.0, wall_ks_mm=wall_ks_mm,
        )
    except Exception as exc:  # noqa: BLE001
        return _infeasible(
            f"case writer failed: {type(exc).__name__}: {exc}", t0, raw=raw)
    raw["case_written"] = True

    runner = OpenFOAMRunner(workdir)
    try:
        run_mesh(runner)
    except Exception as exc:  # noqa: BLE001
        return _infeasible(
            f"mesh failed: {type(exc).__name__}: {exc}", t0, raw=raw)
    raw["meshed"] = True

    if mesh_only:
        return ObjectiveResult(
            feasible=False,
            reason="mesh_only: case written and meshed; solve skipped",
            raw={**raw, "mesh_only": True},
            runtime_s=round(time.time() - t0, 1),
        )

    def solve_at(back_pa: float):
        build_volute_case(
            workdir, imp_stl, cas_stl, domain,
            mesh=MeshResolution(base_cell=base_cell),
            n_iters=iters, n_subdomains=procs,
            back_pressure_pa=back_pa, wall_ks_mm=wall_ks_mm,
        )
        run_solve(runner, n_procs=procs)
        return parse_fan_metrics(workdir, omega_rad_s=domain.omega_rad_s)

    try:
        m_free = solve_at(0.0)
        m_load = solve_at(float(load_pa))
    except Exception as exc:  # noqa: BLE001
        return _infeasible(
            f"solve failed: {type(exc).__name__}: {exc}", t0, raw=raw)

    torque_rated = max(m_free.torque_nm, m_load.torque_nm, 0.0)
    actual_rpm = motor_operating_rpm(torque_rated, run_spec)
    derate = min(1.0, actual_rpm / run_spec.rpm) if run_spec.rpm else 1.0
    cfm_free = float(m_free.cfm) * derate
    cfm_probe = max(float(m_load.cfm), 0.0) * derate
    p_probe_pa = derated_probe_pa(load_pa, derate)
    p_free_pa = max(0.0, float(m_free.static_pressure_rise_pa)) * (derate * derate)
    raw.update({
        "free": m_free.to_dict(),
        "load": m_load.to_dict(),
        "converged": bool(m_free.converged and m_load.converged),
        "actual_rpm": actual_rpm,
        "derate": derate,
        "cfm_probe": cfm_probe,
        "p_probe_pa": p_probe_pa,
        "p_free_pa": p_free_pa,
        **motor_curve_stamps(run_spec),
    })
    try:
        op = score_operating_point(
            q_free_cfm=cfm_free,
            q_probe_cfm=cfm_probe,
            p_probe_pa=p_probe_pa,
            eta_free=m_free.efficiency,
            eta_load=m_load.efficiency,
            load_pa=float(load_pa),
            p_free_pa=p_free_pa,
        )
    except SystemCurveError as exc:
        return _infeasible(f"system-curve: {exc}", t0, raw=raw)

    conv_note = ""
    if derate < 0.995:
        conv_note = (
            f"motor-limited: {actual_rpm:.0f} RPM "
            f"({derate * 100:.0f}% of {run_rpm:.0f})")
    if not (m_free.converged and m_load.converged):
        conv_note += ("  " if conv_note else "") + (
            f"UNCONVERGED (free mean shift {m_free.flow_drift_pct:.1f}%, "
            f"osc {m_free.oscillation_pct:.1f}%; load mean shift {m_load.flow_drift_pct:.1f}%, "
            f"osc {m_load.oscillation_pct:.1f}%)")

    cfm_load = op.q_op_cfm
    efficiency = max(op.eta * 100.0, 0.0)
    # Radial blades: no axial tip station; base sim→print knockdown (§7.6).
    cfm_free, cfm_load, efficiency, print_stamps = apply_print_penalty(
        cfm_free, cfm_load, efficiency, enabled=print_penalty)

    return ObjectiveResult(
        feasible=True,
        cfm_free=cfm_free,
        cfm_load=cfm_load,
        efficiency=efficiency,
        noise_swl=INFEASIBLE_NOISE,
        actual_rpm=actual_rpm,
        reason=conv_note,
        raw={
            **raw,
            "k": op.k,
            "dp_op_pa": op.p_op_pa,
            "q_ref_cfm": REF_CFM,
            "free": m_free.to_dict(),
            "load": m_load.to_dict(),
            "converged": bool(m_free.converged and m_load.converged),
            "actual_rpm": actual_rpm,
            "derate": derate,
            **motor_curve_stamps(run_spec),
            **print_stamps,
        },
        runtime_s=round(time.time() - t0, 1),
    )
