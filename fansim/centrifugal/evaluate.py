"""Score a mixed-flow impeller in the axial through-flow MRF duct (roadmap §4.1)."""

from __future__ import annotations

import time
from pathlib import Path

from fansim.centrifugal.bem import mixed_bem_screen_cfm
from fansim.centrifugal.geometry import (
    MixedFlowParams,
    _loft_tip_radius_mm,
    export_mixed_flow_stl,
)
from fansim.cfd.casing import export_casing_stl
from fansim.cfd.domain import MM_TO_M, OPTIMIZER_TIP_GAP_MM, TestRig
from fansim.cfd.duct_area import require_circular_inlet_area
from fansim.cfd.frame import export_frame_stl
from fansim.cfd.metrics import parse_fan_metrics
from fansim.cfd.openfoam_case import MeshResolution, build_case, run_mesh, run_solve
from fansim.cfd.runner import OpenFOAMRunner
from fansim.fan_spec import A12X25, FanSpec, check_build, estimate_weight_g, over_spec_flags
from fansim.geometry import watertight_report
from fansim.geometry.blade import BladeParams
from fansim.optimize.motor_curve import motor_curve_stamps, motor_operating_rpm
from fansim.optimize.objectives import INFEASIBLE_NOISE, ObjectiveResult, SCREENING_GRID_STAMP, _infeasible
from fansim.optimize.print_penalty import apply_print_penalty
from fansim.optimize.system_curve import (
    REF_CFM,
    SystemCurveError,
    derated_probe_pa,
    refine_operating_metrics,
    score_operating_point,
)


def remaining_mixed_tip_gap_mm(params: MixedFlowParams, casing_id_mm: float) -> float:
    """Radial leftover between loft tip radius and circular casing ID."""
    return float(casing_id_mm) / 2.0 - _loft_tip_radius_mm(params)


def rig_for_mixed_flow(
    params: MixedFlowParams,
    *,
    tip_gap_mm: float,
    casing_id_mm: float,
    rpm: float,
    inlet_diameters: float = 2.0,
    outlet_diameters: float = 4.0,
    mrf_margin_mm: float = 2.0,
    inlet_velocity: float = 2.0,
) -> TestRig:
    """Axial MRF duct sized to a mixed-flow impeller (SI meters)."""
    duct_r = float(casing_id_mm) * MM_TO_M / 2.0
    tip_gap_m = tip_gap_mm * MM_TO_M
    half = 0.5 * params.z_span_mm * MM_TO_M
    z_lo, z_hi = -half, half
    diameter = 2.0 * duct_r
    return TestRig(
        duct_radius=duct_r,
        tip_gap=tip_gap_m,
        inlet_length=inlet_diameters * diameter,
        outlet_length=outlet_diameters * diameter,
        impeller_z_min=z_lo,
        impeller_z_max=z_hi,
        mrf_z_min=z_lo - mrf_margin_mm * MM_TO_M,
        mrf_z_max=z_hi + mrf_margin_mm * MM_TO_M,
        rpm=float(rpm),
        inlet_velocity=inlet_velocity,
    )


def _frame_blade_proxy(params: MixedFlowParams, rpm: float) -> BladeParams:
    """Minimal BladeParams so the four-bar frame export can use hub_radius."""
    return BladeParams(
        n_blades=params.n_blades,
        hub_radius=params.r_back_mm,
        tip_radius=params.r_tip_mm,
        rpm=rpm,
    )


def evaluate_mixed_flow(
    params: MixedFlowParams,
    workdir: str | Path,
    *,
    procs: int = 8,
    base_cell: float = 0.005,
    iters: int = 1000,
    load_pa: float = 1.0,
    material: str = "PETG",
    tip_gap_mm: float | None = None,
    refine_op: bool = False,
    print_penalty: bool = True,
    circular_duct: bool = True,
    bem_prescreen_cfm: float = 0.0,
    wall_ks_mm: float | None = None,
    spec: FanSpec = A12X25,
) -> ObjectiveResult:
    """Export mixed-flow STL and score free + load CFD in the axial A12x25 duct."""
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    if tip_gap_mm is None:
        tip_gap_mm = OPTIMIZER_TIP_GAP_MM
    floor = float(tip_gap_mm)
    casing_id = float(spec.tip_dia_mm[1])
    remaining = remaining_mixed_tip_gap_mm(params, casing_id)
    gap_raw = {
        "tip_gap_mm": remaining,
        "casing_id_mm": casing_id,
        "tip_gap_floor_mm": floor,
        "archetype": "centrifugal",
        "topology": "mixed_flow",
        "stator": "frame",
        "duct": "circular" if circular_duct else "square",
        "inlet": "plain" if circular_duct else "none",
        **SCREENING_GRID_STAMP,
    }
    if remaining < floor:
        return _infeasible(
            f"{spec.name}: tip gap {remaining:.2f} mm < min {floor:.2f} mm "
            f"to {casing_id:.0f} mm frame",
            t0, raw=gap_raw)

    if bem_prescreen_cfm > 0.0:
        gap_raw["bem_adapter"] = "axial"
        try:
            from fansim.optimize.system_curve import SystemCurveError
            bem_free, bem_op = mixed_bem_screen_cfm(
                params, spec.rpm, load_pa, remaining)
            gap_raw["bem_cfm_free"] = bem_free
            gap_raw["bem_cfm_load"] = bem_op
            if bem_op < bem_prescreen_cfm:
                return _infeasible(
                    f"bem-prescreen: {bem_op:.0f} CFM op < {bem_prescreen_cfm:.0f} "
                    "system-curve floor (skipped CFD)",
                    t0, raw=gap_raw)
        except SystemCurveError as exc:
            return _infeasible(f"bem-prescreen: {exc} (skipped CFD)", t0, raw=gap_raw)
        except Exception as exc:  # noqa: BLE001 - stamp; do not fall through to CFD (§9.6)
            gap_raw["bem_prescreen_error"] = f"{type(exc).__name__}: {exc}"
            return _infeasible(
                f"bem-prescreen failed: {type(exc).__name__}: {exc} (skipped CFD)",
                t0, raw=gap_raw)

    try:
        stl = export_mixed_flow_stl(params, workdir / "impeller.stl")
    except Exception as exc:  # noqa: BLE001
        return _infeasible(f"geometry failed: {type(exc).__name__}: {exc}", t0, raw=gap_raw)
    rep = watertight_report(stl)
    if not rep.ok:
        return _infeasible(f"not watertight ({rep.n_bodies} bodies)", t0, raw=gap_raw)
    (xmin, ymin, zmin), (xmax, ymax, zmax) = rep.bounds_mm
    dia = 2.0 * max(abs(xmin), abs(xmax), abs(ymin), abs(ymax))
    depth = zmax - zmin
    hub_dia = 2.0 * params.r_back_mm
    try:
        import trimesh
        weight_g = estimate_weight_g(abs(float(trimesh.load(str(stl)).volume)), material)
    except Exception:  # noqa: BLE001
        weight_g = None
    ok, reason = check_build(spec, dia, hub_dia, depth, weight_g)
    if not ok:
        return _infeasible(reason, t0, raw=gap_raw)

    rig0 = rig_for_mixed_flow(
        params,
        tip_gap_mm=remaining,
        casing_id_mm=casing_id,
        rpm=spec.rpm,
        inlet_diameters=2.0,
        outlet_diameters=4.0,
    )
    bp = _frame_blade_proxy(params, spec.rpm)
    frame_path = workdir / "frame.stl"
    try:
        export_frame_stl(bp, rig0, frame_path)
    except Exception as exc:  # noqa: BLE001
        return _infeasible(f"frame failed: {type(exc).__name__}: {exc}", t0, raw=gap_raw)

    casing_path = None
    if circular_duct:
        casing_path = workdir / "casing.stl"
        try:
            export_casing_stl(rig0, casing_path, stepped=False)
        except Exception as exc:  # noqa: BLE001
            return _infeasible(f"casing failed: {type(exc).__name__}: {exc}", t0, raw=gap_raw)

    runner = OpenFOAMRunner(workdir)
    try:
        build_case(workdir, stl, rig0, mesh=MeshResolution(base_cell=base_cell),
                   n_iters=iters, n_subdomains=procs, back_pressure_pa=0.0,
                   frame_stl_mm=frame_path, casing_stl_mm=casing_path,
                   wall_ks_mm=wall_ks_mm)
        run_mesh(runner)
        if circular_duct:
            gap_raw["inlet_area_m2"] = require_circular_inlet_area(
                workdir, rig0.duct_radius)
    except Exception as exc:  # noqa: BLE001
        return _infeasible(f"mesh failed: {type(exc).__name__}: {exc}", t0, raw=gap_raw)

    def solve_at(back_pa: float):
        build_case(workdir, stl, rig0, mesh=MeshResolution(base_cell=base_cell),
                   n_iters=iters, n_subdomains=procs, back_pressure_pa=back_pa,
                   frame_stl_mm=frame_path, casing_stl_mm=casing_path,
                   wall_ks_mm=wall_ks_mm)
        run_solve(runner, n_procs=procs)
        return parse_fan_metrics(workdir, omega_rad_s=rig0.omega_rad_s)

    try:
        m_free = solve_at(0.0)
        m_load = solve_at(load_pa)
    except Exception as exc:  # noqa: BLE001
        return _infeasible(f"solve failed: {type(exc).__name__}: {exc}", t0, raw=gap_raw)

    torque_rated = max(m_free.torque_nm, m_load.torque_nm, 0.0)
    actual_rpm = motor_operating_rpm(torque_rated, spec)
    derate = min(1.0, actual_rpm / spec.rpm) if spec.rpm else 1.0
    cfm_free = m_free.cfm * derate
    cfm_load = max(m_load.cfm, 0.0) * derate
    over = over_spec_flags(spec, dia, depth, weight_g)
    cfm_probe = cfm_load
    p_probe_pa = derated_probe_pa(load_pa, derate)
    p_free_pa = max(0.0, float(m_free.static_pressure_rise_pa)) * (derate * derate)
    try:
        op = score_operating_point(
            q_free_cfm=cfm_free,
            q_probe_cfm=cfm_probe,
            p_probe_pa=p_probe_pa,
            eta_free=m_free.efficiency,
            eta_load=m_load.efficiency,
            load_pa=load_pa,
            p_free_pa=p_free_pa,
        )
    except SystemCurveError as exc:
        return _infeasible(f"system-curve: {exc}", t0, raw=gap_raw)
    cfm_load = op.q_op_cfm
    efficiency = max(op.eta * 100.0, 0.0)
    if refine_op:
        refined = refine_operating_metrics(op, derate, load_pa, m_load, solve_at)
        cfm_load = refined.q_op_cfm
        efficiency = max(refined.eta * 100.0, 0.0)
        gap_raw["cfm_op_alg"] = refined.cfm_op_alg
        gap_raw["op_cfd"] = refined.op_cfd

    conv_note = ""
    if derate < 0.995:
        conv_note = f"motor-limited: {actual_rpm:.0f} RPM ({derate * 100:.0f}% of {spec.rpm:.0f})"
    if not (m_free.converged and m_load.converged):
        conv_note += ("  " if conv_note else "") + (
            f"UNCONVERGED (free drift {m_free.flow_drift_pct:.1f}%, "
            f"load drift {m_load.flow_drift_pct:.1f}%)")

    cfm_free, cfm_load, efficiency, print_stamps = apply_print_penalty(
        cfm_free, cfm_load, efficiency, enabled=print_penalty)

    return ObjectiveResult(
        feasible=True,
        cfm_free=cfm_free,
        cfm_load=cfm_load,
        efficiency=efficiency,
        noise_swl=INFEASIBLE_NOISE,
        actual_rpm=actual_rpm,
        over_spec=over,
        reason=conv_note,
        raw={**gap_raw, "free": m_free.to_dict(), "load": m_load.to_dict(),
             "converged": bool(m_free.converged and m_load.converged),
             "actual_rpm": actual_rpm, "derate": derate,
             "k": op.k, "dp_op_pa": op.p_op_pa, "q_ref_cfm": REF_CFM,
             "cfm_probe": cfm_probe, "p_probe_pa": p_probe_pa,
             **motor_curve_stamps(spec), **print_stamps},
        runtime_s=round(time.time() - t0, 1),
    )
