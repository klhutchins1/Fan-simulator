"""Quick screening CFD: one coarse free-air solve, to decide which ideas earn a full Assess.

NOT a performance number. It exists only to RANK candidates, and is trusted for that only once
``scripts/screen_rank_audit.py`` shows its ranking agrees with the full Assess (pre-registered
criteria in docs/validation/audits/2026-10-07-screen-rank-audit.md). The case setup mirrors
``objectives.evaluate_candidate`` (same rig, orientation, frame, tip gap); only the mesh, the
iteration count and the single free-air operating point differ.

Run as ``python -m fansim.optimize.quick_screen <job.json>`` (isolated worker, writes ``out``).
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

# Screening tier pre-registered 2026-10-07: background cell 8 mm (Assess: 6 mm), fixed surface
# level 3 -> 1.0 mm finest cell (Assess: >= level 3 on 6 mm = 0.75 mm), free-air only, 300 iters.
QUICK_BASE_CELL = 0.008
QUICK_SURF_LEVEL = 3
QUICK_ITERS = 300


@dataclass
class QuickResult:
    ok: bool
    cfm_free_raw: float = 0.0     # signed CFD free-air CFM at rated RPM (no derate / print penalty)
    cfm_load_raw: float | None = None  # signed CFD CFM at the load back-pressure (Q3 tier only)
    torque_nm: float = 0.0
    converged: bool = False
    flow_drift_pct: float = 999.0
    cells: int | None = None
    wall_s: float = 0.0
    reason: str = ""
    extra: dict = field(default_factory=dict)


def quick_free_air(params, workdir, spec, *, base_cell: float = QUICK_BASE_CELL,
                   surf_level: int = QUICK_SURF_LEVEL, iters: int = QUICK_ITERS,
                   procs: int = 8, load_pa: float | None = None) -> QuickResult:
    """Coarse free-air solve; with ``load_pa`` also a second solve at that back-pressure (Q3)."""
    from fansim.cfd.domain import OPTIMIZER_TIP_GAP_MM, remaining_tip_gap_mm, rig_for_impeller
    from fansim.cfd.frame import export_frame_stl
    from fansim.cfd.metrics import parse_fan_metrics
    from fansim.cfd.openfoam_case import MeshResolution, build_case, run_mesh, run_solve
    from fansim.cfd.orientation import prepare_axial_cfd
    from fansim.cfd.runner import OpenFOAMRunner
    from fansim.cfd.timing import mesh_cells
    from fansim.geometry import build_impeller, export_stl, watertight_report

    t0 = time.time()
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    casing_id = float(spec.tip_dia_mm[1])
    remaining = remaining_tip_gap_mm(params, casing_id)
    if remaining < OPTIMIZER_TIP_GAP_MM:
        return QuickResult(False, reason=f"tip gap {remaining:.2f} mm < {OPTIMIZER_TIP_GAP_MM}")
    try:
        stl = export_stl(build_impeller(params), workdir / "impeller.stl")
    except Exception as exc:  # noqa: BLE001
        return QuickResult(False, reason=f"geometry failed: {type(exc).__name__}: {exc}")
    if not watertight_report(stl).ok:
        return QuickResult(False, reason="not watertight")
    params.rpm = float(spec.rpm)
    rig0 = rig_for_impeller(params, tip_gap_mm=remaining, casing_id_mm=casing_id,
                            inlet_diameters=2.0, outlet_diameters=4.0)
    stl, rig0 = prepare_axial_cfd(stl, rig0, workdir, source="builder")
    frame = workdir / "frame.stl"
    export_frame_stl(params, rig0, frame)
    mesh = MeshResolution(base_cell=base_cell, surf_min=max(1, surf_level - 1),
                          surf_max=surf_level, feature_level=surf_level)
    runner = OpenFOAMRunner(workdir)
    try:
        build_case(workdir, stl, rig0, mesh=mesh, n_iters=iters, n_subdomains=procs,
                   back_pressure_pa=0.0, frame_stl_mm=frame)
        run_mesh(runner, n_procs=procs)
        run_solve(runner, n_procs=procs)
        m = parse_fan_metrics(workdir, omega_rad_s=rig0.omega_rad_s)
        m_load = None
        if load_pa is not None:
            build_case(workdir, stl, rig0, mesh=mesh, n_iters=iters, n_subdomains=procs,
                       back_pressure_pa=float(load_pa), frame_stl_mm=frame)
            run_solve(runner, n_procs=procs)
            m_load = parse_fan_metrics(workdir, omega_rad_s=rig0.omega_rad_s)
    except Exception as exc:  # noqa: BLE001
        return QuickResult(False, reason=f"cfd failed: {type(exc).__name__}: {exc}",
                           cells=mesh_cells(workdir), wall_s=round(time.time() - t0, 1))
    return QuickResult(True, cfm_free_raw=float(m.cfm), torque_nm=float(m.torque_nm),
                       cfm_load_raw=None if m_load is None else float(m_load.cfm),
                       converged=bool(m.converged), flow_drift_pct=float(m.flow_drift_pct),
                       cells=mesh_cells(workdir), wall_s=round(time.time() - t0, 1),
                       extra={"base_cell": base_cell, "surf_level": surf_level, "iters": iters,
                              "load_pa": load_pa})


def main() -> int:
    job = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    from dataclasses import asdict

    from fansim.fan_spec import fan_spec_from_dict
    from fansim.geometry.features import features_from_flat
    from fansim.optimize.search_space import blade_from_flat

    params = blade_from_flat(job["flat"], features_from_flat(job["flat"]))
    res = quick_free_air(params, job["workdir"], fan_spec_from_dict(job["spec"]),
                         base_cell=float(job.get("base_cell", QUICK_BASE_CELL)),
                         surf_level=int(job.get("surf_level", QUICK_SURF_LEVEL)),
                         iters=int(job.get("iters", QUICK_ITERS)),
                         procs=int(job.get("procs", 8)),
                         load_pa=job.get("load_pa"))
    Path(job["out"]).write_text(json.dumps(asdict(res)), encoding="utf-8")
    sys.stdout.flush()
    os._exit(0)  # skip the known OCP/VTK teardown segfault; the result is already written


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        sys.stderr.write(f"{type(exc).__name__}: {exc}\n")
        os._exit(3)
