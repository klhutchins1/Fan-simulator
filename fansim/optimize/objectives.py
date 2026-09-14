# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Evaluate one blade design into multi-objective performance numbers.

Objectives (all maximized):
  * cfm_free   -- airflow at free delivery (back-pressure 0): raw flow capability
  * cfm_load   -- airflow at the system-curve operating point (load is Pa at 50 CFM on ΔP = k Q²)
  * efficiency -- aerodynamic efficiency at the system-curve operating point: power thriftiness

Operating points are kept on the STABLE part of the fan curve (low back-pressure). The old
2 Pa load sat in the near-stall region where the steady solve oscillates and never converges
(see docs/adversarial-review.md §3.4); every solve now reports whether its integrated flow
actually settled (`converged`/`flow_drift_pct`), and unconverged results are flagged.

Lightweight manufacturability + structural gates reject un-buildable designs cheaply,
before any CFD is spent on them.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from fansim.cfd.domain import OPTIMIZER_TIP_GAP_MM, remaining_tip_gap_mm, rig_for_impeller
from fansim.cfd.frame import export_frame_stl
from fansim.cfd.metrics import parse_fan_metrics
from fansim.cfd.openfoam_case import MeshResolution, build_case, run_mesh, run_solve
from fansim.cfd.runner import OpenFOAMRunner
from fansim.geometry import build_impeller, export_stl, watertight_report
from fansim.fan_spec import (
    A12X25,
    FanSpec,
    check_build,
    estimate_weight_g,
    mount_min_hub_radius,
    over_spec_flags,
)
from fansim.geometry.blade import BladeParams, blade_solidity
from fansim.manufacturability.fdm_rules import check_printability
from fansim.optimize.system_curve import REF_CFM, SystemCurveError, score_operating_point
from fansim.structural.stress import centrifugal_root_stress

INFEASIBLE = -1.0e6      # rejected value for MAXIMIZED objectives (optimizer avoids them)
INFEASIBLE_NOISE = 1.0e6  # rejected value for the MINIMIZED noise objective (high = bad)

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
    tip_gap_mm: float | None = None,
    surrogate_prescreen_cfm: float = 0.0,
    surrogate=None,
    surrogate_load=None,
) -> ObjectiveResult:
    """Gate, mesh once, solve at free-delivery and at ``load_pa``, return objectives.

    ``min_sol_mid``/``min_sol_tip`` impose a per-blade-loading cap: a solidity FLOOR. Low solidity
    means each blade carries more load (higher diffusion factor -> more broadband noise), so a floor
    forces the search to spread load over enough blade area rather than overloading a few blades.
    ``require_mountable`` gates (pre-CFD) designs whose hub is too small to house the fan model's
    motor — so the search only produces impellers that can actually be mounted."""
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    # --- Cheap gates first (no CFD) ---
    if require_mountable:
        need = mount_min_hub_radius(spec)
        if need is not None and params.hub_radius < need:
            return _infeasible(
                f"not mountable: hub radius {params.hub_radius:.1f} < {need:.1f} mm "
                f"needed to house the {spec.name} motor", t0)
    printable = check_printability(params)
    if not printable.printable:
        return _infeasible(f"unprintable: {printable.reason}", t0)
    stress = centrifugal_root_stress(params, material=material)
    if not stress.ok:
        return _infeasible(f"overstressed: {stress.reason}", t0)

    if tip_gap_mm is None:
        tip_gap_mm = OPTIMIZER_TIP_GAP_MM
    floor = float(tip_gap_mm)
    casing_id = float(spec.tip_dia_mm[1])
    remaining = remaining_tip_gap_mm(params, casing_id)
    gap_raw = {
        "tip_gap_mm": remaining,
        "casing_id_mm": casing_id,
        "tip_gap_floor_mm": floor,
        **SCREENING_GRID_STAMP,
    }
    if remaining < floor:
        return _infeasible(
            f"{spec.name}: tip gap {remaining:.2f} mm < min {floor:.2f} mm "
            f"to {casing_id:.0f} mm frame",
            t0, raw=gap_raw)

    # --- BEM pre-screen (roadmap §7.1c): reject clearly-non-viable designs before the ~5-min CFD (and
    # even the geometry build). CONSERVATIVE by design — the mean-line BEM ranks CFD at only ~0.62, so
    # the floor should be well below any viable design so we only skip the clearly-bad ones. Off (0.0)
    # by default. Cheap (milliseconds); never allowed to break the eval. ---
    if bem_prescreen_cfm > 0.0:
        try:
            from fansim.fan_bem import pq_curve
            bem_cfm = pq_curve(params, spec.rpm, tip_gap_mm=remaining).free_delivery_cfm
            if bem_cfm < bem_prescreen_cfm:
                return _infeasible(f"bem-prescreen: {bem_cfm:.0f} CFM free < {bem_prescreen_cfm:.0f} "
                                   "floor (skipped CFD)", t0, raw=gap_raw)
        except Exception:  # noqa: BLE001 - the screen must never break the eval
            pass

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
    except Exception as exc:  # geometry/loft/boolean failure
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
    params.rpm = spec.rpm  # spin the CFD at the selected fan model's operating speed
    rig0 = rig_for_impeller(
        params,
        tip_gap_mm=remaining,
        casing_id_mm=casing_id,
        inlet_diameters=2.0,
        outlet_diameters=4.0,
    )
    frame_path = workdir / "frame.stl"
    try:
        export_frame_stl(params, rig0, frame_path)
    except Exception as exc:
        return _infeasible(f"frame failed: {type(exc).__name__}: {exc}", t0, raw=gap_raw)

    runner = OpenFOAMRunner(workdir)
    try:
        build_case(workdir, stl, rig0, mesh=MeshResolution(base_cell=base_cell),
                   n_iters=iters, n_subdomains=procs, back_pressure_pa=0.0,
                   frame_stl_mm=frame_path)
        run_mesh(runner)
    except Exception as exc:
        return _infeasible(f"mesh failed: {type(exc).__name__}: {exc}", t0, raw=gap_raw)

    def solve_at(back_pa: float):
        build_case(workdir, stl, rig0, mesh=MeshResolution(base_cell=base_cell),
                   n_iters=iters, n_subdomains=procs, back_pressure_pa=back_pa,
                   frame_stl_mm=frame_path)
        run_solve(runner, n_procs=procs)
        return parse_fan_metrics(workdir, omega_rad_s=rig0.omega_rad_s)

    noise_swl = INFEASIBLE_NOISE
    try:
        if with_noise and noise_model == "proudman":
            # Proudman broadband proxy needs the free field on disk: solve LOAD first, FREE last,
            # reconstruct, integrate turbulence over the domain. (Ranks LBM noise POORLY, rho~0.21.)
            m_load = solve_at(load_pa)
            m_free = solve_at(0.0)
            try:
                from fansim.acoustics.case import proudman_swl_from_case
                runner.run("reconstructPar -latestTime", check=False)
                noise_swl = float(proudman_swl_from_case(workdir))
            except Exception:  # noqa: BLE001 - noise read failed -> worst score, won't be selected
                noise_swl = INFEASIBLE_NOISE
        else:
            m_free = solve_at(0.0)
            m_load = solve_at(load_pa)
            if with_noise:  # default: cheap calibrated LOADING proxy (no reconstruct; tracks LBM
                # dipole better than Proudman -- blade count + per-blade thrust). See acoustics/loading.
                from fansim.acoustics.loading import loading_proxy_from_rans
                noise_swl = float(loading_proxy_from_rans(params.n_blades, m_free.thrust_n))
    except Exception as exc:
        return _infeasible(f"solve failed: {type(exc).__name__}", t0, raw=gap_raw)

    # Flag under-converged solves: near the stall operating point the steady RANS may not
    # settle within the iteration budget, making the number untrustworthy (see the
    # adversarial review). We surface it rather than silently trusting it.
    # RPM is NOT fixed. The motor targets spec.rpm but under a load it can't power (heavy/high-
    # solidity blades, static pressure) it settles at a LOWER RPM. Fan affinity laws: power ∝ RPM³,
    # flow ∝ RPM, pressure ∝ RPM², efficiency ~invariant. So a design that would draw more shaft
    # power than the motor's budget at rated RPM doesn't fail -- it spins slower and delivers
    # proportionally less flow. We DERATE to that actual RPM instead of rejecting. (Envelope + weight
    # are hard physical limits and were already gated; power is not -- it derates the speed.)
    budget = spec.max_shaft_power_w_leeway
    shaft_rated = max(m_free.shaft_power_w, m_load.shaft_power_w, 1e-9)
    derate = min(1.0, (budget / shaft_rated) ** (1.0 / 3.0))
    actual_rpm = spec.rpm * derate
    cfm_free = m_free.cfm * derate                       # flow ∝ RPM
    cfm_load = max(m_load.cfm, 0.0) * derate
    over = over_spec_flags(spec, dia, depth, weight_g)   # geometry over-spec; power now derates RPM

    cfm_probe = cfm_load
    try:
        op = score_operating_point(
            q_free_cfm=cfm_free,
            q_probe_cfm=cfm_probe,
            p_probe_pa=load_pa,
            eta_free=m_free.efficiency,
            eta_load=m_load.efficiency,
            load_pa=load_pa,
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
            f"UNCONVERGED (free drift {m_free.flow_drift_pct:.1f}%, "
            f"load drift {m_load.flow_drift_pct:.1f}%)")

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
             "k": op.k, "dp_op_pa": op.p_op_pa, "q_ref_cfm": REF_CFM, "cfm_probe": cfm_probe},
        runtime_s=round(time.time() - t0, 1),
    )
