"""Score a CROR (dual-MRF) stack in the axial through-flow duct (roadmap §4.2 stage 1)."""

from __future__ import annotations

import time
import json
from dataclasses import replace
from pathlib import Path

from fansim.cfd.domain import MM_TO_M, OPTIMIZER_TIP_GAP_MM, TestRig
from fansim.cfd.frame import export_frame_stl
from fansim.cfd.metrics import parse_fan_metrics
from fansim.cfd.openfoam_case import (
    OPTIMIZER_SURF_MAX_FLOOR,
    MeshResolution,
    build_case,
    run_mesh,
    run_solve,
)
from fansim.cfd.orientation import DIRECTION_META_FILE, orient_impeller_for_cfd
from fansim.cfd.runner import OpenFOAMRunner
from fansim.geometry.blade import min_blade_wall_mm
from fansim.cror.geometry import CrorParams, cror_axial_layout_mm, export_cror_stl
from fansim.fan_spec import A12X25, FanSpec, check_build, estimate_weight_g, over_spec_flags
from fansim.geometry import watertight_report
from fansim.optimize.motor_curve import motor_curve_stamps, motor_operating_rpm
from fansim.optimize.objectives import INFEASIBLE_NOISE, ObjectiveResult, SCREENING_GRID_STAMP, _infeasible
from fansim.optimize.print_penalty import apply_print_penalty
from fansim.optimize.system_curve import (
    SystemCurveError,
    derated_probe_pa,
    score_operating_point,
)


def remaining_cror_tip_gap_mm(params: CrorParams, casing_id_mm: float) -> float:
    tip = float(params.front.tip_radius)
    return float(casing_id_mm) / 2.0 - tip


def dual_mrf_dict(params: CrorParams, omega_front: float) -> dict:
    """As-built (unflipped) dual-MRF zone dict (rear Ω opposite front).

    Not for CFD: solving the as-built stack at spin -1 turns both rotors backwards (Audit #7).
    CFD uses ``prepare_cror_cfd`` / ``cfd_dual_mrf_dict`` on the flipped copy.
    """
    lay = cror_axial_layout_mm(params)
    return {
        "front_z_min": lay["front_z_min_mm"] * MM_TO_M,
        "front_z_max": lay["front_z_max_mm"] * MM_TO_M,
        "rear_z_min": lay["rear_z_min_mm"] * MM_TO_M,
        "rear_z_max": lay["rear_z_max_mm"] * MM_TO_M,
        "omega_front": float(omega_front),
        "omega_rear": -float(omega_front),
    }


def cfd_dual_mrf_dict(params: CrorParams, omega_signed: float) -> dict:
    """Dual-MRF zones for the CFD-oriented (flipped) CROR (Audit #7).

    ``build_cror`` is built as-built like every in-house rotor: front (z~0) designed omega_z=+1,
    rear (z>0) omega_z=-1 (its exact mirror), both pumping -Z. The duct flows +Z, so the CFD copy
    is rotated 180 deg about X (``fansim.cfd.orientation``): z -> -z, omega -> -omega. The former
    rear rotor is then UPSTREAM (low z) and turns +omega, the former front rotor is downstream and
    turns ``omega_signed`` (= rig.spin * |omega| = the designed -1 for spin -1). Zones are named by
    PHYSICAL position: ``front_*`` = upstream. ``omega_signed`` is the DOWNSTREAM rotor's.
    """
    lay = cror_axial_layout_mm(params)
    return {
        "front_z_min": -lay["rear_z_max_mm"] * MM_TO_M,
        "front_z_max": -lay["rear_z_min_mm"] * MM_TO_M,
        "rear_z_min": -lay["front_z_max_mm"] * MM_TO_M,
        "rear_z_max": -lay["front_z_min_mm"] * MM_TO_M,
        "omega_front": -float(omega_signed),
        "omega_rear": float(omega_signed),
    }


def fit_cror_inner_zone_edges(stl_mm: str | Path, dual_mrf: dict, hub_radius_mm: float, *,
                              margin_mm: float = 0.25) -> dict:
    """Grow the INNER (gap-side) zone edges to cover each rotor's real blade extent.

    The analytic band (``cror_axial_layout_mm``) uses the tip section's half depth; the actual
    blade (root sections, camber, thickness) pokes ~0.15 mm past it into the inter-rotor gap,
    which would be solved as stationary wall. Blades are split between the two zones at the
    gap mid-plane.
    """
    import numpy as np
    import trimesh

    mesh = trimesh.load(str(stl_mm), force="mesh")
    v = np.asarray(mesh.vertices, dtype=float)
    z = v[np.hypot(v[:, 0], v[:, 1]) > float(hub_radius_mm) + 0.5, 2] * MM_TO_M
    z_split = 0.5 * (float(dual_mrf["front_z_max"]) + float(dual_mrf["rear_z_min"]))
    m = margin_mm * MM_TO_M
    up_hi = max(float(dual_mrf["front_z_max"]), float(z[z < z_split].max()) + m)
    dn_lo = min(float(dual_mrf["rear_z_min"]), float(z[z >= z_split].min()) - m)
    if up_hi >= dn_lo:
        raise ValueError("CROR MRF zones would overlap after covering the blades")
    return {**dual_mrf, "front_z_max": up_hi, "rear_z_min": dn_lo}


def check_cror_blades_in_zones(stl_mm: str | Path, dual_mrf: dict, hub_radius_mm: float, *,
                               tol_m: float = 1e-6) -> None:
    """Refuse a case where blade material (r > hub) falls outside both MRF zones.

    ``check_placement`` only tests the overall envelope, so a blade poking into the inter-rotor
    gap would be solved as a stationary wall. Hub vertices in the gap are fine (not blades).
    """
    import numpy as np
    import trimesh

    mesh = trimesh.load(str(stl_mm), force="mesh")
    v = np.asarray(mesh.vertices, dtype=float)
    blade = v[np.hypot(v[:, 0], v[:, 1]) > float(hub_radius_mm) + 0.5]
    z = blade[:, 2] * MM_TO_M
    inside = np.zeros(len(z), dtype=bool)
    for lo, hi in (("front_z_min", "front_z_max"), ("rear_z_min", "rear_z_max")):
        inside |= (z >= float(dual_mrf[lo]) - tol_m) & (z <= float(dual_mrf[hi]) + tol_m)
    if not inside.all():
        bad = z[~inside]
        raise ValueError(
            f"{int((~inside).sum())} blade vertices lie outside both MRF zones "
            f"(z {bad.min() * 1e3:.2f}..{bad.max() * 1e3:.2f} mm)")


def prepare_cror_cfd(params: CrorParams, stl_mm: str | Path, rig: TestRig,
                     workdir: str | Path) -> tuple[Path, TestRig, dict]:
    """Orient the CROR for CFD, build its dual-MRF zones, fit rig+zones to the STL.

    Returns ``(oriented_stl, fitted_rig, dual_mrf)``; use these for everything downstream.
    Writes ``workdir/direction_meta.json`` (merged into ``case_meta.json`` by ``build_case``).
    """
    workdir = Path(workdir)
    dst = workdir / "impeller_cfd.stl"
    orient_impeller_for_cfd(Path(stl_mm), dst, "flipped")
    dmrf = cfd_dual_mrf_dict(params, rig.omega_signed)
    rig, dmrf = fit_cror_to_stl(rig, dmrf, dst)
    dmrf = fit_cror_inner_zone_edges(dst, dmrf, float(params.front.hub_radius))
    check_cror_blades_in_zones(dst, dmrf, float(params.front.hub_radius))
    (workdir / DIRECTION_META_FILE).write_text(json.dumps({
        "direction_source": "builder", "orientation": "flipped",
        "spin": int(rig.spin), "proof_verdict": "per-rotor (tests/audit)"}, indent=2),
        encoding="utf-8")
    return dst, rig, dmrf


def rig_for_cror(
    params: CrorParams,
    *,
    tip_gap_mm: float,
    casing_id_mm: float | None = None,
    rpm: float | None = None,
    inlet_diameters: float = 2.0,
    outlet_diameters: float = 4.0,
    mrf_margin_mm: float = 2.0,
) -> TestRig:
    lay = cror_axial_layout_mm(params)
    tip_mm = float(params.front.tip_radius)
    if casing_id_mm is not None:
        duct_r = float(casing_id_mm) * MM_TO_M / 2.0
        tip_gap_m = duct_r - tip_mm * MM_TO_M
    else:
        tip_gap_m = tip_gap_mm * MM_TO_M
        duct_r = tip_mm * MM_TO_M + tip_gap_m
    z_lo = lay["hub_z0_mm"] * MM_TO_M
    z_hi = lay["hub_z1_mm"] * MM_TO_M
    diameter = 2.0 * duct_r
    rpm = float(rpm if rpm is not None else params.front.rpm)
    return TestRig(
        duct_radius=duct_r,
        tip_gap=tip_gap_m,
        inlet_length=inlet_diameters * diameter,
        outlet_length=outlet_diameters * diameter,
        impeller_z_min=z_lo,
        impeller_z_max=z_hi,
        mrf_z_min=z_lo - mrf_margin_mm * MM_TO_M,
        mrf_z_max=z_hi + mrf_margin_mm * MM_TO_M,
        rpm=rpm,
        # Audit #7: CFD copy is flipped 180 deg about X (prepare_cror_cfd) at spin -1, like the
        # axial rotor; zone omegas come from cfd_dual_mrf_dict. Per-rotor direction (front +1,
        # rear -1 as built, both pumping -Z) is pinned by tests/audit/test_cror_mixed_setup_audit.py.
        inlet_velocity=2.0,
        spin=-1,
    )


def fit_cror_to_stl(
    rig: TestRig, dual_mrf: dict, stl_mm: str | Path, *, margin_mm: float = 2.0,
) -> tuple[TestRig, dict]:
    """Fit the CROR rig + dual-MRF zone to the real exported STL bounds.

    Same pattern as ``fansim.cfd.orientation.fit_rig_to_stl``: ``rig_for_cror``/
    ``dual_mrf_dict`` size the front/rear MRF bands from the analytic blade-station layout,
    but the hub cylinder (``cror_axial_layout_mm``'s 1 mm end margin) can poke slightly past
    those bands, leaving hub past the MRF zone. Extend the outer front/rear edges (never the
    inner gap) to cover the actual mesh, with an extra ``margin_mm`` clearance.
    """
    import trimesh

    mesh = trimesh.load(str(stl_mm), force="mesh")
    z0 = float(mesh.bounds[0, 2]) * MM_TO_M
    z1 = float(mesh.bounds[1, 2]) * MM_TO_M
    lo = min(float(dual_mrf["front_z_min"]), z0 - margin_mm * MM_TO_M)
    hi = max(float(dual_mrf["rear_z_max"]), z1 + margin_mm * MM_TO_M)
    fitted_rig = replace(rig, impeller_z_min=z0, impeller_z_max=z1, mrf_z_min=lo, mrf_z_max=hi)
    fitted_dmrf = {**dual_mrf, "front_z_min": lo, "rear_z_max": hi}
    return fitted_rig, fitted_dmrf


def evaluate_cror(
    params: CrorParams,
    workdir: str | Path,
    *,
    spec: FanSpec = A12X25,
    load_pa: float = 8.0,
    iters: int = 800,
    procs: int = 8,
    base_cell: float = 0.005,
    tip_gap_mm: float | None = None,
    circular_duct: bool = True,
    material: str = "PLA",
    apply_print_pen: bool = True,
) -> ObjectiveResult:
    """Steady dual-MRF free+load evaluate for a CROR stack."""
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    if tip_gap_mm is None:
        tip_gap_mm = OPTIMIZER_TIP_GAP_MM
    floor = float(tip_gap_mm)
    casing_id = float(spec.tip_dia_mm[1])
    remaining = remaining_cror_tip_gap_mm(params, casing_id)
    gap_raw: dict = {
        "tip_gap_mm": remaining,
        "casing_id_mm": casing_id,
        "tip_gap_floor_mm": floor,
        "archetype": "cror",
        "rotation": "dual_MRF",
        "stator": "frame",
        "duct": "ring" if circular_duct else "square",
        **SCREENING_GRID_STAMP,
    }
    if remaining < floor:
        return _infeasible(
            f"{spec.name}: tip gap {remaining:.2f} mm < min {floor:.2f} mm "
            f"to {casing_id:.0f} mm frame",
            t0, raw=gap_raw)

    try:
        stl = export_cror_stl(params, workdir / "impeller.stl")
    except Exception as exc:  # noqa: BLE001
        return _infeasible(f"geometry failed: {type(exc).__name__}: {exc}", t0, raw=gap_raw)
    rep = watertight_report(stl)
    if not rep.ok:
        return _infeasible(f"not watertight ({rep.n_bodies} bodies)", t0, raw=gap_raw)
    (xmin, ymin, zmin), (xmax, ymax, zmax) = rep.bounds_mm
    dia = 2.0 * max(abs(xmin), abs(xmax), abs(ymin), abs(ymax))
    depth = zmax - zmin
    hub_dia = 2.0 * float(params.front.hub_radius)
    try:
        import trimesh
        weight_g = estimate_weight_g(abs(float(trimesh.load(str(stl)).volume)), material)
    except Exception:  # noqa: BLE001
        weight_g = None
    ok, reason = check_build(spec, dia, hub_dia, depth, weight_g)
    if not ok:
        return _infeasible(reason, t0, raw=gap_raw)

    rig0 = rig_for_cror(
        params,
        tip_gap_mm=remaining,
        casing_id_mm=casing_id,
        rpm=spec.rpm,
    )
    stl, rig0, dmrf = prepare_cror_cfd(params, stl, rig0, workdir)
    gap_raw["dual_mrf"] = {k: round(float(v), 6) for k, v in dmrf.items()}

    frame_path = workdir / "frame.stl"
    try:
        export_frame_stl(params.front, rig0, frame_path)
    except Exception as exc:  # noqa: BLE001
        return _infeasible(f"frame failed: {type(exc).__name__}: {exc}", t0, raw=gap_raw)

    # Same validated domain + mesh rule as the axial optimizer (CFD v5, Audit #2): the sealed
    # 25 mm frame ring (circular_duct) instead of the v4 full-length tube (~0.7 m of pipe
    # friction, -34 % on the A12x25), and surface refinement sized to the thinnest blade wall
    # (a thin plate meshed at ~1 cell loses ~30 % of its loading).
    casing_path = None
    duct = "ring" if circular_duct else "square"
    mesh0 = MeshResolution.for_blade(
        base_cell, min(min_blade_wall_mm(params.front), min_blade_wall_mm(params.rear)), min_surf_max=OPTIMIZER_SURF_MAX_FLOOR)

    runner = OpenFOAMRunner(workdir)
    try:
        build_case(
            workdir, stl, rig0, mesh=mesh0,
            n_iters=iters, n_subdomains=procs, back_pressure_pa=0.0,
            frame_stl_mm=frame_path, casing_stl_mm=casing_path, duct=duct, dual_mrf=dmrf)
        run_mesh(runner)
    except Exception as exc:  # noqa: BLE001
        return _infeasible(f"mesh failed: {type(exc).__name__}: {exc}", t0, raw=gap_raw)

    def solve_at(back_pa: float):
        build_case(
            workdir, stl, rig0, mesh=mesh0,
            n_iters=iters, n_subdomains=procs, back_pressure_pa=back_pa,
            frame_stl_mm=frame_path, casing_stl_mm=casing_path, duct=duct, dual_mrf=dmrf)
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
    gap_raw.update({
        "free": m_free.to_dict(),
        "load": m_load.to_dict(),
        "converged": bool(m_free.converged and m_load.converged),
        "actual_rpm": actual_rpm,
        "derate": derate,
        "cfm_probe": cfm_probe,
        "p_probe_pa": p_probe_pa,
        "p_free_pa": p_free_pa,
    })
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
    conv_note = ""
    if derate < 0.995:
        conv_note = f"motor-limited: {actual_rpm:.0f} RPM ({derate * 100:.0f}% of {spec.rpm:.0f})"
    if not (m_free.converged and m_load.converged):
        conv_note += ("  " if conv_note else "") + (
            f"UNCONVERGED (free mean shift {m_free.flow_drift_pct:.1f}%, "
            f"osc {m_free.oscillation_pct:.1f}%; load mean shift {m_load.flow_drift_pct:.1f}%, "
            f"osc {m_load.oscillation_pct:.1f}%)")

    cfm_free, cfm_load, efficiency, print_stamps = apply_print_penalty(
        cfm_free, cfm_load, efficiency, enabled=apply_print_pen)

    return ObjectiveResult(
        feasible=True,
        cfm_free=cfm_free,
        cfm_load=cfm_load,
        efficiency=efficiency,
        noise_swl=INFEASIBLE_NOISE,
        actual_rpm=actual_rpm,
        over_spec=over,
        reason=conv_note,
        raw={**gap_raw, **motor_curve_stamps(spec), **print_stamps},
        runtime_s=round(time.time() - t0, 1),
    )
