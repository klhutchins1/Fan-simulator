"""Evaluate one blade design into multi-objective performance numbers.

Objectives (all maximized):
  * cfm_free   -- airflow at free delivery (back-pressure 0): raw flow capability
  * cfm_load   -- airflow at the system-curve operating point (load is Pa at 50 CFM on ΔP = k Q²)
  * efficiency -- aerodynamic efficiency at the system-curve operating point: power thriftiness

Operating points are kept on the STABLE part of the fan curve (low back-pressure). The old
2 Pa load sat in the near-stall region where the steady solve oscillates and never converges
(see docs/adversarial-review.md §3.4); every solve now reports whether its integrated flow
actually settled (`converged`/`flow_drift_pct`, the tail-mean shift; swing reported separately
as `oscillation_pct`), and unconverged results are flagged.

Lightweight manufacturability + structural gates reject un-buildable designs cheaply,
before any CFD is spent on them.
"""

from __future__ import annotations

import dataclasses
import json
import shutil
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from fansim.cfd.casing import export_casing_stl
from fansim.cfd.domain import OPTIMIZER_TIP_GAP_MM, remaining_tip_gap_mm, rig_for_impeller
from fansim.cfd.frame import export_frame_stl, stack_frame_z_start_mm
from fansim.cfd.metrics import latest_pp_file, parse_fan_metrics
from fansim.cfd.openfoam_case import (
    ASSESS_SURF_MAX_FLOOR,
    MeshResolution,
    build_case,
    run_mesh,
    run_solve,
)
from fansim.cfd.orientation import prepare_axial_cfd
from fansim.cfd.runner import OpenFOAMRunner
from fansim.cfd.sanity import FAIL as SANITY_FAIL
from fansim.cfd.sanity import overall as sanity_overall
from fansim.cfd.sanity import run_sanity
from fansim.cfd.sanity import summarize as summarize_sanity
from fansim.cfd.stator import export_stator_stl
from fansim.fan_spec import (
    A12X25,
    FanSpec,
    check_build,
    estimate_weight_g,
    mount_min_hub_radius,
    over_spec_flags,
)
from fansim.geometry import build_impeller, export_stl, watertight_report
from fansim.geometry.blade import (
    BladeParams,
    blade_solidity,
    min_blade_wall_mm,
    signed_design_camber,
    validate_blade_params,
)
from fansim.manufacturability.fdm_rules import check_printability
from fansim.optimize.near_stall import near_stall_report
from fansim.optimize.print_penalty import apply_print_penalty, tip_section_thickness
from fansim.optimize.system_curve import (
    REF_CFM,
    SystemCurveError,
    bem_exploit_reason,
    bem_screen_cfm,
    derated_probe_pa,
    refine_operating_metrics,
    score_operating_point,
)
from fansim.structural.deflection import (
    deflection_report,
    root_bending_stress,
    tip_deflection_mm,
)
from fansim.structural.flutter import flutter_report
from fansim.structural.stress import centrifugal_root_stress

INFEASIBLE = -1.0e6      # rejected value for MAXIMIZED objectives (optimizer avoids them)
INFEASIBLE_NOISE = 1.0e6  # rejected value for the MINIMIZED noise objective (high = bad)
# Free-air metrics written as soon as that solve finishes, so a run killed during the load solve
# still reports its free-air result (fansim.optimize.isolated_eval.partial_free_note).
PARTIAL_FREE_FILE = "_partial_free.json"
FREE_HISTORY_DIR = "free_history"  # free-air outletFlow + moment histories, kept past the load solve

# Layered GCI campaign (roadmap §1.5 / §10.8): p≈0.28, GCI_fine≈21%, not asymptotic.
# Do not quote screening CFM with a 3–5% bar. Shared by axial / mixed / CROR / volute evaluate.
SCREENING_GRID_STAMP = {
    "grid_converged": False,
    "grid_note": "screening mesh not grid-converged (GCI_fine≈21%, p≈0.28)",
}


@dataclass
class ObjectiveResult:
    feasible: bool
    cfm_free: float = INFEASIBLE
    cfm_load: float = INFEASIBLE
    efficiency: float = INFEASIBLE
    noise_swl: float = INFEASIBLE_NOISE  # Proudman broadband SWL [dB] at free delivery (minimize)
    actual_rpm: float = 0.0            # RPM the motor actually holds under load (<= rated if power-limited)
    over_spec: list = field(default_factory=list)  # nominal limits exceeded within leeway (flags)
    reason: str = ""
    raw: dict = field(default_factory=dict)
    runtime_s: float = 0.0

    def as_tuple(self, with_noise: bool = False):
        """Objective tuple for the optimizer: (cfm_free, cfm_load, efficiency[, noise_swl])."""
        base = (self.cfm_free, self.cfm_load, self.efficiency)
        return base + (self.noise_swl,) if with_noise else base

    def to_dict(self) -> dict:
        return asdict(self)


def _infeasible(reason: str, t0: float, raw: dict | None = None) -> ObjectiveResult:
    return ObjectiveResult(False, reason=reason, runtime_s=round(time.time() - t0, 1),
                           raw=raw or {})


def _operating_point_reason(
    exc: Exception,
    *,
    free_signed: float,
    probe_signed: float,
    derate: float,
    p_free_pa: float,
    p_probe_pa: float,
    converged: bool,
    free_drift_pct: float,
    load_drift_pct: float,
    free_osc_pct: float = 0.0,
    load_osc_pct: float = 0.0,
) -> str:
    """Human-readable reason when the system-curve intersection fails, degrading gracefully.

    Rather than surface the raw ``probe CFM must be positive``, report the free-air delivery and
    *why* there is no loaded operating point. Two physical cases, distinguished by the SIGNED CFD
    flow (metrics.py: negative reads as reverse flow, never masked by abs):

    * free delivery itself reversed -> almost always a duct/spin sign problem (actionable hint);
    * free delivery is fine but the hose probe reversed -> the fan's CFD static ceiling is below
      the hose, so it stalls at this load (CFD's static ceiling is a little below the datasheet's,
      about 10 %; G4 / QA-71). Suggest a lighter
      hose instead of a cryptic reject.
    """
    conv = "" if converged else (
        f"; steady solve UNCONVERGED (free mean shift {free_drift_pct:.1f}%, "
        f"osc {free_osc_pct:.1f}%; load mean shift {load_drift_pct:.1f}%, "
        f"osc {load_osc_pct:.1f}%) — number is a solver artifact near stall")
    if free_signed <= 0.0:
        return (
            f"system-curve: {exc} — free outletFlow {free_signed:+.1f} CFM (signed); "
            "reverse/zero flow usually means the rotor orientation or axial BC fought the blades "
            f"(see fansim/cfd/orientation.py).{conv}"
        )
    if probe_signed <= 0.0:
        return (
            f"stalls at this hose — free delivery {free_signed * derate:.1f} CFM, but the "
            f"{p_probe_pa:.1f} Pa probe reverses to {probe_signed:+.1f} CFM (CFD static ceiling "
            f"is below the hose; CFD's static ceiling is a little below the datasheet's, about 10 %). "
            f"Try a lighter hose.{conv}"
        )
    return (
        f"system-curve: {exc} (free {p_free_pa:.1f} Pa, probe {p_probe_pa:.1f} Pa)"
    )


def evaluate_candidate(
    params: BladeParams,
    workdir: str | Path,
    procs: int = 8,
    base_cell: float = 0.005,
    iters: int = 1000,
    load_pa: float = 1.0,
    material: str = "PETG",
    min_sol_mid: float | None = None,
    min_sol_tip: float | None = None,
    with_noise: bool = False,
    noise_model: str = "loading",
    spec: FanSpec = A12X25,
    require_mountable: bool = False,
    bem_prescreen_cfm: float = 0.0,
    exploit_guard: bool = True,
    tip_gap_mm: float | None = None,
    surrogate_prescreen_cfm: float = 0.0,
    surrogate=None,
    surrogate_load=None,
    refine_op: bool = False,
    print_penalty: bool = True,
    wall_ks_mm: float | None = None,
    stator: bool = False,
    stator_stack: bool = False,
    stator_stagger_deg: float | None = None,
    stator_n_extra: int | None = None,
    stepped_inlet: bool = False,
    rpm: float | None = None,
    parallel_mesh: bool = False,
    surf_max_floor: int | None = None,
) -> ObjectiveResult:
    """Gate, mesh once, solve at free-delivery and at ``load_pa``, return objectives.

    ``min_sol_mid``/``min_sol_tip`` impose a per-blade-loading cap: a solidity FLOOR. Low solidity
    means each blade carries more load (higher diffusion factor -> more broadband noise), so a floor
    forces the search to spread load over enough blade area rather than overloading a few blades.
    ``require_mountable`` gates (pre-CFD) designs whose hub is too small to house the fan model's
    motor — so the search only produces impellers that can actually be mounted.

    ``parallel_mesh`` runs snappyHexMesh on ``procs`` ranks instead of one (meshing was ~9 min
    serial on a 1M-cell case); the mesh is equivalent but not bit-identical to serial."""
    if stator and stator_stack:
        raise ValueError("cannot combine stator and stator_stack")
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    target_rpm = float(rpm) if rpm is not None else float(spec.rpm)

    # One hub for validate, CFD and export (R1.7 / QA-44): grow to the motor cup with
    # the extra height below the blades, matching ``mount_hub_params``.
    if spec.motor_mount is not None:
        from fansim.manufacturability.print_export import mount_hub_params
        params, _grow_note = mount_hub_params(params, spec.motor_mount)
    # Every gate below (centrifugal stress ∝ rpm², resonance vs blade-pass ∝ rpm) and the CFD must
    # judge the speed the design will run at: the fan model's rpm or an Optuna --search-rpm sample.
    # A copy, so the caller's params are not changed (RV-3: gates used to see the stale params.rpm).
    params = dataclasses.replace(params, rpm=target_rpm)

    # --- Cheap gates first (no CFD) ---
    if require_mountable:
        need = mount_min_hub_radius(spec)
        if need is not None and params.hub_radius < need:
            return _infeasible(
                f"not mountable: hub radius {params.hub_radius:.1f} < {need:.1f} mm "
                f"needed to house the {spec.name} motor", t0)
    try:
        validate_blade_params(params)
    except ValueError as exc:
        return _infeasible(str(exc), t0)
    printable = check_printability(params)
    if not printable.printable:
        return _infeasible(f"unprintable: {printable.reason}", t0)
    stress = centrifugal_root_stress(params, material=material)
    if not stress.ok:
        return _infeasible(f"overstressed: {stress.reason}", t0)
    bend = root_bending_stress(params, material=material, load_pa=float(load_pa))
    if not bend.ok:
        return _infeasible(f"root bending: {bend.reason}", t0)
    # Resonance gate (UI Assess material picker / §7.6 flutter) — stamps beam_regime (§19.18).
    flutter = flutter_report(params, material=material)
    # WARNING, not a reject (user decision 2026-10-08): the Euler-Bernoulli beam model is
    # order-of-magnitude (§19.18) and unverified against printed blades. Stamped on the result;
    # revisit once print/measure data exists (roadmap §23.40).
    vibration_warning = "" if flutter.ok else f"⚠ vibration risk (unverified until prints): {flutter.reason}"

    if tip_gap_mm is None:
        tip_gap_mm = OPTIMIZER_TIP_GAP_MM
    floor = float(tip_gap_mm)
    casing_id = float(spec.tip_dia_mm[1])
    remaining = remaining_tip_gap_mm(params, casing_id)
    gap_raw = {
        "tip_gap_mm": remaining,
        "casing_id_mm": casing_id,
        "tip_gap_floor_mm": floor,
        "beam_aspect": float(flutter.beam_aspect),
        "beam_regime_ok": bool(flutter.beam_regime_ok),
        "f1_hz": float(flutter.f1_hz),
        "bpf_hz": float(flutter.bpf_hz),
        "f1_bpf_margin": float(flutter.margin),
        "vibration_warning": vibration_warning,
        **SCREENING_GRID_STAMP,
    }
    if remaining < floor:
        return _infeasible(
            f"{spec.name}: tip gap {remaining:.2f} mm < min {floor:.2f} mm "
            f"to {casing_id:.0f} mm frame",
            t0, raw=gap_raw)
    # FSI tip-rub gate (§7.6): δ ≥ leftover tip gap.
    defl = deflection_report(
        params, tip_gap_mm=remaining, material=material, load_pa=float(load_pa),
    )
    gap_raw["tip_deflection_mm"] = float(defl.tip_deflection_mm)
    gap_raw["beam_aspect"] = float(defl.beam_aspect)
    gap_raw["beam_regime_ok"] = bool(defl.beam_regime_ok and flutter.beam_regime_ok)
    if defl.reason and "WARN" in defl.reason:
        gap_raw["beam_regime_warn"] = defl.reason
    elif flutter.reason and "WARN" in flutter.reason:
        gap_raw["beam_regime_warn"] = flutter.reason
    if not defl.ok:
        return _infeasible(defl.reason, t0, raw=gap_raw)

    # --- Exploit guard (QA-4): always on, ~0.1 s. Refuse blades the axial-force BEM says cannot pump
    # (paddles, wrong-hand blades) instead of spending a ~20 min CFD run on them. Never ranks. ---
    if exploit_guard:
        try:
            why = bem_exploit_reason(params, target_rpm, remaining)
        except Exception as exc:  # noqa: BLE001 - the guard must never break the eval
            why = ""
            gap_raw["exploit_guard_error"] = f"{type(exc).__name__}: {exc}"
        if why:
            return _infeasible(f"bem-guard: {why} (axial-force BEM; skipped CFD)", t0, raw=gap_raw)

    # --- Near-stall warning (25.10): stamp only. Never skips CFD, never changes scores. ---
    try:
        ns = near_stall_report(params, float(target_rpm), float(load_pa), remaining)
        gap_raw["near_stall"] = bool(ns.flagged)
        gap_raw["near_stall_rule"] = ns.rule
        gap_raw["near_stall_reason"] = ns.reason
    except Exception as exc:  # noqa: BLE001 - warning must never break the eval
        gap_raw["near_stall_error"] = f"{type(exc).__name__}: {exc}"

    # --- BEM pre-screen (roadmap §7.1c): reject clearly-non-viable designs before CFD.
    # Floor is on hose operating CFM (same axis as CFD cfm_load), not free-delivery.
    # Off (0.0) by default. Cheap; never allowed to break the eval. ---
    if bem_prescreen_cfm > 0.0:
        try:
            bem_free, bem_op = bem_screen_cfm(
                params, target_rpm, load_pa, remaining, stator=bool(stator))
            gap_raw["bem_cfm_free"] = bem_free
            gap_raw["bem_cfm_load"] = bem_op
            if bem_op < bem_prescreen_cfm:
                return _infeasible(
                    f"bem-prescreen: {bem_op:.0f} CFM load < {bem_prescreen_cfm:.0f} "
                    f"floor (free {bem_free:.0f}; skipped CFD)",
                    t0, raw=gap_raw,
                )
        except Exception as exc:  # noqa: BLE001 - the screen must never break the eval
            # RV-3: stamp it. A silent pass sent the design to CFD with no trace of the crash.
            gap_raw["bem_prescreen_error"] = f"{type(exc).__name__}: {exc}"

    # --- Catalog GP pre-screen (roadmap §7.4): skip CFD when the GP is confident the
    # predicted CFM is below the floor (mean + 1 std). Prefer the load-line GP when fitted.
    # Uncertain (large std) still goes to CFD. Off by default. Predict crashes are
    # infeasible — never silent CFD (§9.6). ---
    screen = surrogate_load if surrogate_load is not None else surrogate
    label = "load" if surrogate_load is not None else "free"
    raw_mu = "surr_cfm_load" if surrogate_load is not None else "surr_cfm_free"
    if surrogate_prescreen_cfm > 0.0 and screen is not None:
        try:
            from fansim.surrogate.features import feature_vector, would_skip
            mu, sigma = screen.predict(
                feature_vector(params).reshape(1, -1), return_std=True)
            mu, sigma = float(mu[0]), float(sigma[0])
            gap_raw[raw_mu] = mu
            gap_raw["surr_std"] = sigma
            if would_skip(mu, sigma, surrogate_prescreen_cfm):
                return _infeasible(
                    f"surrogate-prescreen: {mu:.0f}+/-{sigma:.0f} CFM {label} < "
                    f"{surrogate_prescreen_cfm:.0f} (skipped CFD)",
                    t0, raw=gap_raw)
        except Exception as exc:  # noqa: BLE001 - stamp; do not fall through to CFD (§9.6)
            gap_raw["surrogate_prescreen_error"] = f"{type(exc).__name__}: {exc}"
            return _infeasible(
                f"surrogate-prescreen failed: {type(exc).__name__}: {exc} (skipped CFD)",
                t0, raw=gap_raw)

    # --- Geometry ---
    try:
        stl = export_stl(build_impeller(params), workdir / "impeller.stl")
    except Exception as exc:  # noqa: BLE001 - geometry/loft/boolean failure -> infeasible
        return _infeasible(f"geometry failed: {type(exc).__name__}: {exc}", t0, raw=gap_raw)
    rep = watertight_report(stl)
    if not rep.ok:
        return _infeasible(f"not watertight ({rep.n_bodies} bodies)", t0, raw=gap_raw)
    # Fan-model build gate: tip/hub diameter, depth, and printed weight must fit the model's spec.
    (xmin, ymin, zmin), (xmax, ymax, zmax) = rep.bounds_mm
    dia = 2.0 * max(abs(xmin), abs(xmax), abs(ymin), abs(ymax))
    depth = zmax - zmin
    hub_dia = 2.0 * params.hub_radius
    try:
        import trimesh
        weight_g = estimate_weight_g(abs(float(trimesh.load(str(stl)).volume)), material)
    except Exception:  # noqa: BLE001 - weight optional; skip the weight gate if volume unavailable
        weight_g = None
    ok, reason = check_build(spec, dia, hub_dia, depth, weight_g)
    if not ok:
        return _infeasible(reason, t0, raw=gap_raw)
    # Per-blade-loading cap (solidity floor): reject too-sparse blades that overload each vane.
    if min_sol_mid is not None or min_sol_tip is not None:
        sol = blade_solidity(params)
        if min_sol_mid is not None and sol["mid"] < min_sol_mid:
            return _infeasible(f"overloaded blades (sol_mid {sol['mid']:.2f} < {min_sol_mid})",
                               t0, raw=gap_raw)
        if min_sol_tip is not None and sol["tip"] < min_sol_tip:
            return _infeasible(f"overloaded blades (sol_tip {sol['tip']:.2f} < {min_sol_tip})",
                               t0, raw=gap_raw)

    # --- Mesh once, then solve each operating point ---
    # Duct lengths matter: short ducts put the outlet boundary too close to the fan and
    # under-predict flow ~15% + hurt convergence (2.0/4.0 diameters converge cleanly to ~77/81
    # for trial 2; the earlier 1.0/1.5 gave ~65/71 unconverged — see adversarial-review §3.4).
    # Reusing one meshed dir across back-pressures was verified to NOT contaminate results.
    gap_raw["stator"] = (
        "stack" if stator_stack else ("stator" if stator else "frame"))
    gap_raw["inlet"] = "stepped" if stepped_inlet else "plain"
    if wall_ks_mm is not None and float(wall_ks_mm) > 0:
        gap_raw["wall_ks_mm"] = float(wall_ks_mm)
    rig0 = rig_for_impeller(
        params,
        tip_gap_mm=remaining,
        casing_id_mm=casing_id,
        inlet_diameters=2.0,
        outlet_diameters=4.0,
    )
    # Audit #1: CFD solves the designed rotation only with the rotor flipped (spin stays −1), and
    # the MRF zone must contain the whole rotor, so size it from the oriented STL.
    stl, rig0 = prepare_axial_cfd(stl, rig0, workdir, source="builder",
                                   design_camber=signed_design_camber(params))  # audit 2026-10-10
    frame_path = None
    stator_path = None
    try:
        if stator or stator_stack:
            stator_path = workdir / "stator.stl"
            export_stator_stl(
                params, rig0, stator_path,
                stagger_deg=stator_stagger_deg, n_extra=stator_n_extra)
        if not stator or stator_stack:
            frame_path = workdir / "frame.stl"
            z_start = stack_frame_z_start_mm(rig0) if stator_stack else None
            export_frame_stl(params, rig0, frame_path, z_start_mm=z_start)
    except Exception as exc:  # noqa: BLE001 - stator/frame build failure -> infeasible
        which = "stator" if (stator or stator_stack) and frame_path is None else "frame"
        return _infeasible(f"{which} failed: {type(exc).__name__}: {exc}", t0, raw=gap_raw)

    casing_path = None
    if stepped_inlet:
        casing_path = workdir / "casing.stl"
        try:
            export_casing_stl(rig0, casing_path, stepped=True)
        except Exception as exc:  # noqa: BLE001 - casing build failure -> infeasible
            return _infeasible(f"casing failed: {type(exc).__name__}: {exc}", t0, raw=gap_raw)

    runner = OpenFOAMRunner(workdir)
    # Adapt surface refinement to the blade's thinnest wall: a thin plate meshed to ~1 cell
    # loses ~30% of its loading and reads an artificially low, mesh-sensitive CFM (the a12x25
    # refit investigation). Thick blades keep the cheap baseline level.
    # surf_max_floor: override the Assess floor (mesh-fairness check, roadmap §23.39).
    mesh0 = MeshResolution.for_blade(
        base_cell, min_blade_wall_mm(params),
        min_surf_max=ASSESS_SURF_MAX_FLOOR if surf_max_floor is None else int(surf_max_floor))
    gap_raw["surf_max"] = int(mesh0.surf_max)  # stamped so coarser-mesh scores can be flagged
    gap_raw["hub_clip"] = bool(getattr(params, "clip_below_hub", True))  # blades cut at the hub face
    gap_raw["motor_eff"] = float(spec.motor_efficiency)  # derate budget this score used (audit 2026-10-10)
    try:
        build_case(workdir, stl, rig0, mesh=mesh0,
                   n_iters=iters, n_subdomains=procs, back_pressure_pa=0.0,
                   frame_stl_mm=frame_path, casing_stl_mm=casing_path,
                   stator_stl_mm=stator_path, wall_ks_mm=wall_ks_mm)
        # parallel_mesh: snappyHexMesh on ``procs`` ranks (see openfoam_case.mesh_pipeline).
        run_mesh(runner, n_procs=procs if parallel_mesh else 1)
    except Exception as exc:  # noqa: BLE001 - meshing failure -> infeasible
        return _infeasible(f"mesh failed: {type(exc).__name__}: {exc}", t0, raw=gap_raw)

    # Sanity checks (fansim.cfd.sanity) are report-only: they flag, they never make a design
    # infeasible. Each solve's postProcessing is wiped by the NEXT solve, so we must run them
    # here, immediately after parsing that solve's metrics, keyed by which operating point
    # ("free"/"load") this call is for.
    sanity_by_label: dict[str, list] = {}
    sanity_errors: dict[str, str] = {}

    def solve_at(back_pa: float, label: str | None = None):
        build_case(workdir, stl, rig0, mesh=mesh0,
                   n_iters=iters, n_subdomains=procs, back_pressure_pa=back_pa,
                   frame_stl_mm=frame_path, casing_stl_mm=casing_path,
                   stator_stl_mm=stator_path, wall_ks_mm=wall_ks_mm)
        run_solve(runner, n_procs=procs)
        m = parse_fan_metrics(workdir, omega_rad_s=rig0.omega_rad_s)
        if label is not None:
            try:
                sanity_by_label[label] = run_sanity(
                    workdir, metrics=m, omega_signed=rig0.omega_signed)
            except Exception as exc:  # noqa: BLE001 - sanity is report-only, must never break the eval
                sanity_by_label[label] = []
                sanity_errors[label] = f"{type(exc).__name__}: {exc}"  # RV-3: not "no warnings"
        return m

    noise_swl = INFEASIBLE_NOISE
    try:
        if with_noise and noise_model == "proudman":
            # Proudman broadband proxy needs the free field on disk: solve LOAD first, FREE last,
            # reconstruct, integrate turbulence over the domain. (Ranks LBM noise POORLY, rho~0.21.)
            m_load = solve_at(load_pa, "load")
            m_free = solve_at(0.0, "free")
            try:
                from fansim.acoustics.case import proudman_swl_from_case
                runner.run("reconstructPar -latestTime", check=False)
                noise_swl = float(proudman_swl_from_case(workdir))
            except Exception:  # noqa: BLE001 - noise read failed -> worst score, won't be selected
                noise_swl = INFEASIBLE_NOISE
        else:
            m_free = solve_at(0.0, "free")
            try:
                (workdir / PARTIAL_FREE_FILE).write_text(
                    json.dumps(m_free.to_dict()), encoding="utf-8")
                # The load solve wipes postProcessing; keep the free-air iteration history
                # (screening-tier audits replay it, e.g. scripts/screen_rank_audit.py).
                hist = workdir / FREE_HISTORY_DIR
                for fo, name in (("outletFlow", "surfaceFieldValue.dat"),
                                 ("forces", "moment.dat")):
                    try:
                        src = latest_pp_file(workdir, fo, name)
                    except FileNotFoundError:
                        continue
                    (hist / fo).mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(src, hist / fo / name)
            except Exception as exc:  # noqa: BLE001 - salvage file is best-effort
                gap_raw["free_salvage_error"] = f"{type(exc).__name__}: {exc}"
            m_load = solve_at(load_pa, "load")
            if with_noise:  # default: cheap calibrated LOADING proxy (no reconstruct; tracks LBM
                # dipole better than Proudman -- blade count + per-blade thrust). See acoustics/loading.
                from fansim.acoustics.loading import loading_proxy_from_rans
                noise_swl = float(loading_proxy_from_rans(params.n_blades, m_free.thrust_n))
    except Exception as exc:  # noqa: BLE001 - any solver failure makes this design infeasible
        return _infeasible(f"solve failed: {type(exc).__name__}: {exc}", t0, raw=gap_raw)

    # Sanity: flag-only. A FAIL is stamped into raw/reason for visibility but never rejects
    # the design (user decision, .superpowers/sdd/constraints-sanity.md).
    sanity_checks_all = [
        *sanity_by_label.get("free", []),
        *sanity_by_label.get("load", []),
    ]
    if sanity_errors:
        sanity_status = "ERROR"
        gap_raw["sanity_error"] = sanity_errors
    else:
        sanity_status = sanity_overall(sanity_checks_all) if sanity_checks_all else "SKIP"
    sanity_dicts = [
        {"phase": phase, **asdict(c)}
        for phase, checks in sanity_by_label.items()
        for c in checks
    ]
    gap_raw["sanity"] = sanity_dicts
    gap_raw["sanity_status"] = sanity_status
    sanity_note = ""
    if sanity_status == SANITY_FAIL:
        sanity_note = summarize_sanity(sanity_checks_all)

    # Flag under-converged solves: near the stall operating point the steady RANS may not
    # settle within the iteration budget, making the number untrustworthy (see the
    # adversarial review). We surface it rather than silently trusting it.
    # RPM is NOT fixed. The motor targets target_rpm but under a load it can't power (heavy/high-
    # solidity blades, static pressure) it settles at a LOWER RPM. Fan affinity laws: power ∝ RPM³,
    # flow ∝ RPM, pressure ∝ RPM², efficiency ~invariant. So a design that would draw more shaft
    # power than the motor's budget at rated RPM doesn't fail -- it spins slower and delivers
    # proportionally less flow. We DERATE to that actual RPM instead of rejecting. (Envelope + weight
    # are hard physical limits and were already gated; power is not -- it derates the speed.)
    budget = spec.max_shaft_power_w_leeway
    shaft_rated = max(m_free.shaft_power_w, m_load.shaft_power_w, 1e-9)
    derate = min(1.0, (budget / shaft_rated) ** (1.0 / 3.0))
    actual_rpm = target_rpm * derate
    cfm_free = m_free.cfm * derate                       # flow ∝ RPM
    cfm_load = max(m_load.cfm, 0.0) * derate
    over = over_spec_flags(spec, dia, depth, weight_g)   # geometry over-spec; power now derates RPM

    cfm_probe = cfm_load
    # Affinity: probe CFD was at rated RPM with back-pressure ``load_pa``. After CFM∝RPM
    # derate, the fan-line probe pressure must scale as λ² (hose k unchanged). Mixed/CROR/volute
    # already do this; axial must match.
    p_probe_pa = derated_probe_pa(load_pa, derate)
    # CFD free (zero BP) is not forced to ΔP=0 — stamp measured static (affinity λ²) so the
    # fan line matches the free endpoint. BEM still uses p_free=0 by construction.
    p_free_pa = max(0.0, float(m_free.static_pressure_rise_pa)) * (derate * derate)
    if p_probe_pa <= p_free_pa:
        # Typical when Assess hose is "1 Pa legacy": free CFD residual static is a few Pa,
        # so the probe is not downstream of free on the fan line. Application presets
        # (case 8 / heatsink 20 / radiator 35) clear this.
        return _infeasible(
            f"system-curve: free static {p_free_pa:.1f} Pa ≥ hose probe {p_probe_pa:.1f} Pa "
            f"— use Case / Heatsink / Radiator (1 Pa legacy is below free residual)",
            t0,
            raw={**gap_raw, "p_free_pa": p_free_pa, "p_probe_pa": p_probe_pa,
                 "load_pa": float(load_pa)},
        )
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
        free_signed = float(m_free.cfm)
        probe_signed = float(m_load.cfm)
        reason = _operating_point_reason(
            exc,
            free_signed=free_signed,
            probe_signed=probe_signed,
            derate=derate,
            p_free_pa=p_free_pa,
            p_probe_pa=p_probe_pa,
            converged=bool(m_free.converged and m_load.converged),
            free_drift_pct=float(m_free.flow_drift_pct),
            load_drift_pct=float(m_load.flow_drift_pct),
            free_osc_pct=float(m_free.oscillation_pct),
            load_osc_pct=float(m_load.oscillation_pct),
        )
        return _infeasible(
            reason,
            t0,
            raw={**gap_raw, "p_free_pa": p_free_pa, "p_probe_pa": p_probe_pa,
                 "cfm_free_signed": free_signed, "cfm_probe_signed": probe_signed,
                 # free-air delivery (derated) so the UI can still report it on a stalled hose
                 "cfm_free": free_signed * derate,
                 "converged": bool(m_free.converged and m_load.converged)},
        )
    cfm_load = op.q_op_cfm
    efficiency = max(op.eta * 100.0, 0.0)
    if refine_op:
        refined = refine_operating_metrics(op, derate, load_pa, m_load, solve_at)
        cfm_load = refined.q_op_cfm
        efficiency = max(refined.eta * 100.0, 0.0)
        gap_raw["cfm_op_alg"] = refined.cfm_op_alg
        gap_raw["op_cfd"] = refined.op_cfd

    conv_note = vibration_warning
    if derate < 0.995:
        conv_note += ("  " if conv_note else "") + (
            f"motor-limited: {actual_rpm:.0f} RPM "
            f"({derate * 100:.0f}% of {target_rpm:.0f})")
    if not (m_free.converged and m_load.converged):
        conv_note += ("  " if conv_note else "") + (
            f"UNCONVERGED (free mean shift {m_free.flow_drift_pct:.1f}%, "
            f"osc {m_free.oscillation_pct:.1f}%; load mean shift {m_load.flow_drift_pct:.1f}%, "
            f"osc {m_load.oscillation_pct:.1f}%)")
    if sanity_note:
        conv_note += ("  " if conv_note else "") + sanity_note

    # Sim→print knockdown (§7.6): report printed CFM/η from smooth-wall (or ks) RANS.
    tip_t = tip_section_thickness(params)
    try:
        tip_defl = tip_deflection_mm(params, material=material, load_pa=float(load_pa))
    except Exception:  # noqa: BLE001
        tip_defl = None
    cfm_free, cfm_load, efficiency, print_stamps = apply_print_penalty(
        cfm_free,
        cfm_load,
        efficiency,
        enabled=print_penalty,
        tip_thickness=tip_t,
        tip_deflection_mm=tip_defl,
        tip_gap_mm=float(remaining),
    )

    return ObjectiveResult(
        feasible=True,
        cfm_free=cfm_free,
        cfm_load=cfm_load,
        efficiency=efficiency,
        noise_swl=noise_swl,
        actual_rpm=actual_rpm,
        over_spec=over,
        reason=conv_note,
        raw={**gap_raw, "free": m_free.to_dict(), "load": m_load.to_dict(),
             "converged": bool(m_free.converged and m_load.converged),
             "noise_swl": noise_swl, "actual_rpm": actual_rpm, "derate": derate,
             "shaft_power_rated_w": shaft_rated,
             "min_wall_mm": printable.min_section_thickness_mm,
             "sigma_root_mpa": stress.sigma_root_mpa,
             "k": op.k, "dp_op_pa": op.p_op_pa, "q_ref_cfm": REF_CFM, "cfm_probe": cfm_probe,
             "p_probe_pa": p_probe_pa, "p_free_pa": p_free_pa,
             **print_stamps},
        runtime_s=round(time.time() - t0, 1),
    )
