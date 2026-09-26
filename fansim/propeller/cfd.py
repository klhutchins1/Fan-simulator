"""Open-air compressible MRF evaluate for drone props (roadmap §4.3 stage 1)."""
from __future__ import annotations
import math
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import trimesh

from fansim.cfd import templates as T
from fansim.cfd.domain import MM_TO_M
from fansim.cfd.openfoam_case import MeshResolution, _write, run_mesh, snappy_layers_mapping

if TYPE_CHECKING:
    from fansim.geometry.blade import BladeParams

CMU = 0.09
TURB_INTENSITY = 0.05
P_INF = 101325.0
T_INF = 300.0


def _turb_from_u(u: float, tip_radius: float) -> tuple[float, float]:
    u_eps = float(u)
    k = 1.5 * (TURB_INTENSITY * max(u_eps, 1e-3)) ** 2
    length_scale = 0.07 * max(2.0 * float(tip_radius), 1e-6)
    omega_turb = math.sqrt(k) / (CMU**0.25 * length_scale)
    return k, omega_turb


def set_prop_freestream(
    case_dir: str | Path,
    u_freestream: float,
    *,
    tip_radius_m: float,
) -> None:
    """Rewrite ``0/U``, ``0/k``, ``0/omega`` for a new axial freestream (mesh unchanged)."""
    case_dir = Path(case_dir)
    u = float(u_freestream)
    k, omega_turb = _turb_from_u(u, tip_radius_m)
    _write(case_dir / "0/U", T.PROP_U, "volVectorField", "U", {"U_EPS": u})
    _write(case_dir / "0/k", T.PROP_K, "volScalarField", "k", {"K": k})
    _write(case_dir / "0/omega", T.PROP_OMEGA, "volScalarField", "omega", {"OMEGAT": omega_turb})


def purge_prop_time_dirs(case_dir: str | Path) -> None:
    """Remove OpenFOAM time directories (keep ``0``) so the next solve restarts cleanly."""
    case_dir = Path(case_dir)
    keep = {"0", "constant", "system", "logs", "postProcessing"}
    for p in list(case_dir.iterdir()):
        if not p.is_dir() or p.name in keep:
            continue
        try:
            float(p.name)
        except ValueError:
            continue
        if abs(float(p.name)) < 1e-15:
            continue
        shutil.rmtree(p, ignore_errors=True)
    pp = case_dir / "postProcessing"
    if pp.is_dir():
        shutil.rmtree(pp, ignore_errors=True)

@dataclass
class PropOpenAir:
    tip_radius: float
    domain_radius: float
    z_min: float
    z_max: float
    mrf_z_min: float
    mrf_z_max: float
    rpm: float
    omega_signed: float
    u_freestream: float = 1.0

def prop_open_air(
    tip_radius_m: float,
    z_lo_m: float,
    z_hi_m: float,
    rpm: float,
    *,
    spin: int = -1,
    radial_mult: float = 5.0,
    up_mult: float = 2.0,
    down_mult: float = 4.0,
    u_eps: float = 1.0,
    mrf_margin_m: float = 0.005,
) -> PropOpenAir:
    R = float(tip_radius_m)
    omega = float(rpm) * 2.0 * math.pi / 60.0
    return PropOpenAir(
        tip_radius=R,
        domain_radius=radial_mult * R,
        z_min=z_lo_m - up_mult * R,
        z_max=z_hi_m + down_mult * R,
        mrf_z_min=z_lo_m - mrf_margin_m,
        mrf_z_max=z_hi_m + mrf_margin_m,
        rpm=float(rpm),
        omega_signed=float(spin) * omega,
        u_freestream=float(u_eps),
    )


def build_prop_case(
    case_dir: str | Path,
    impeller_stl_mm: str | Path,
    domain: PropOpenAir,
    *,
    mesh: MeshResolution | None = None,
    n_iters: int = 400,
    n_subdomains: int = 8,
) -> Path:
    """Write a ready-to-run OpenFOAM compressible propeller MRF case.

    ``impeller_stl_mm`` is a millimeter-scale STL. It is scaled mm -> m into the case.
    Domain extents come from :class:`PropOpenAir`.
    """
    case_dir = Path(case_dir)
    mesh = mesh or MeshResolution()
    for sub in ("0", "constant/triSurface", "system"):
        (case_dir / sub).mkdir(parents=True, exist_ok=True)

    # --- Scale the impeller STL mm -> m into the case ---
    surf = trimesh.load(str(impeller_stl_mm), force="mesh")
    surf.apply_scale(MM_TO_M)
    surf.export(str(case_dir / "constant/triSurface/impeller.stl"))

    # --- Derived flow / turbulence quantities ---
    u_eps = float(domain.u_freestream)
    k, omega_turb = _turb_from_u(u_eps, domain.tip_radius)

    H = float(domain.domain_radius)
    zmin, zmax = float(domain.z_min), float(domain.z_max)
    nx = max(10, round(2 * H / mesh.base_cell))
    nz = max(20, round((zmax - zmin) / mesh.base_cell))
    write_int = max(1, n_iters // 2)  # field snapshots (kept small via purgeWrite)
    fo_int = max(1, n_iters // 100)  # denser FO history for force-tail gate

    # locationInMesh must be inside the domain but outside the impeller surface.
    locx = 0.9 * H
    locy = 0.9 * H
    locz = 0.5 * (zmin + zmax)

    # --- system/ ---
    _write(case_dir / "system/blockMeshDict", T.BLOCK_MESH, "dictionary", "blockMeshDict", {
        "XMIN": -H, "XMAX": H, "YMIN": -H, "YMAX": H, "ZMIN": zmin, "ZMAX": zmax,
        "NX": nx, "NY": nx, "NZ": nz,
    })
    _write(case_dir / "system/snappyHexMeshDict", T.SNAPPY, "dictionary", "snappyHexMeshDict", {
        "FEATLVL": mesh.feature_level, "SURFMIN": mesh.surf_min, "SURFMAX": mesh.surf_max,
        "LOCX": locx, "LOCY": locy, "LOCZ": locz,
        "FRAME_GEOM": "", "FRAME_FEAT": "", "FRAME_SURF": "",
        "CASING_GEOM": "", "CASING_FEAT": "", "CASING_SURF": "",
        "STATOR_GEOM": "", "STATOR_FEAT": "", "STATOR_SURF": "",
        **snappy_layers_mapping(mesh),
    })
    _write(case_dir / "system/surfaceFeatureExtractDict", T.SURFACE_FEATURES,
           "dictionary", "surfaceFeatureExtractDict", {
               "FRAME_EXTRACT": "", "CASING_EXTRACT": "", "STATOR_EXTRACT": "",
           })
    _write(case_dir / "system/topoSetDict", T.TOPOSET, "dictionary", "topoSetDict", {
        "MRFZMIN": float(domain.mrf_z_min),
        "MRFZMAX": float(domain.mrf_z_max),
        "MRFRADIUS": 1.05 * float(domain.tip_radius),
    })
    _write(case_dir / "system/controlDict", T.PROP_CONTROL_DICT, "dictionary", "controlDict", {
        "ENDTIME": n_iters, "WRITEINT": write_int, "FOINT": fo_int,
    })
    _write(case_dir / "system/fvSchemes", T.PROP_FV_SCHEMES, "dictionary", "fvSchemes", {})
    _write(case_dir / "system/fvSolution", T.PROP_FV_SOLUTION, "dictionary", "fvSolution", {})
    _write(case_dir / "system/fvOptions", T.PROP_FV_OPTIONS, "dictionary", "fvOptions", {})
    _write(case_dir / "system/decomposeParDict", T.DECOMPOSE_PAR,
           "dictionary", "decomposeParDict", {"NPROCS": n_subdomains})

    # --- constant/ ---
    _write(case_dir / "constant/thermophysicalProperties", T.PROP_THERMO,
           "dictionary", "thermophysicalProperties", {})
    _write(case_dir / "constant/turbulenceProperties", T.PROP_TURBULENCE,
           "dictionary", "turbulenceProperties", {})
    _write(case_dir / "constant/MRFProperties", T.PROP_MRF, "dictionary", "MRFProperties", {
        "OMEGA": float(domain.omega_signed),
    })

    # --- 0/ ---
    _write(case_dir / "0/T", T.PROP_T, "volScalarField", "T", {"T_INF": T_INF})
    _write(case_dir / "0/p", T.PROP_P, "volScalarField", "p", {"P_INF": P_INF})
    _write(case_dir / "0/U", T.PROP_U, "volVectorField", "U", {"U_EPS": u_eps})
    _write(case_dir / "0/k", T.PROP_K, "volScalarField", "k", {"K": k})
    _write(case_dir / "0/omega", T.PROP_OMEGA, "volScalarField", "omega", {"OMEGAT": omega_turb})
    _write(case_dir / "0/nut", T.PROP_NUT, "volScalarField", "nut", {})
    _write(case_dir / "0/alphat", T.PROP_ALPHAT, "volScalarField", "alphat", {})

    return case_dir


def parse_prop_metrics(case_dir: str | Path, omega_rad_s: float) -> dict:
    """Parse prop thrust/torque from OpenFOAM forces output.

    Reuses the fan-metrics file helpers, but does not apply rho scaling and does not
    derive flow/CFM or pressure-rise metrics.
    """
    from fansim.cfd.metrics import _last_data_row, _pp_file

    case_dir = Path(case_dir)
    force = _last_data_row(_pp_file(case_dir, "forces", "force.dat"))
    moment = _last_data_row(_pp_file(case_dir, "forces", "moment.dat"))

    # Layout: time, total(x,y,z), pressure(x,y,z), viscous(x,y,z).
    thrust = float(force[3])          # total force z
    torque = abs(float(moment[3]))    # total moment about z
    omega = float(omega_rad_s)
    return {
        "thrust_n": thrust,
        "thrust_g": thrust / 9.80665 * 1000.0,
        "torque_nm": torque,
        "shaft_power_w": torque * omega,
    }


def run_solve_prop(runner, n_procs: int = 8) -> None:
    """Solve with rhoSimpleFoam, in parallel via MPI when ``n_procs`` > 1.

    Skips potentialFoam — that incompressible seeder fights compressible thermo/alphat.
    """
    runner.run("rm -rf processor* postProcessing", check=False)
    if n_procs and n_procs > 1:
        runner.run("decomposePar -force")
        mpi = f"mpirun --allow-run-as-root --oversubscribe -np {int(n_procs)}"
        runner.run(f"{mpi} rhoSimpleFoam -parallel")
    else:
        runner.run("rhoSimpleFoam")


def evaluate_prop_cfd(
    spec,
    workdir: str | Path,
    *,
    rpm: float | None = None,
    iters: int = 400,
    procs: int = 8,
    base_cell: float = 0.005,
    mesh: MeshResolution | None = None,
    spec_key: str | None = None,
    params: BladeParams | None = None,
    bemt_floor_g: float = 0.0,
    u_freestream: float | None = None,
    spin: int | None = None,
    stl_mm: str | Path | None = None,
    prepare_stl: bool = True,
    direction: str = "auto",
) -> dict:
    """Build STL, mesh, solve rhoSimpleFoam, and return prop metrics + stamps.

    ``u_freestream`` overrides the open-air axial freestream (default ~1 m/s ε for static
    smoke). Forward-flight polars should prefer :func:`fansim.propeller.polar.run_cfd_polar`.

    Pass ``stl_mm`` to evaluate an external millimeter STL (drone radial impeller, scanned
    prop, etc.). Tip radius and axial bounds come from the mesh; BEMT floor is skipped.
    When ``prepare_stl`` is True (default), the mesh is centered / normal-fixed first.

    ``direction`` is ``"auto"`` (default) to derive orientation/spin from the mesh-only proof
    (:func:`fansim.propeller.direction.prop_direction`), orienting the CFD copy if needed and
    overriding ``spin``; or ``"manual"`` to keep the caller's ``spin``/orientation as-is (the
    explicit override for parts whose geometry proof is INCONCLUSIVE). ``spin`` must be left
    ``None`` in ``"auto"`` mode -- spin is derived from geometry there, so passing an explicit
    value that the geometry might silently override is a footgun; pass ``direction="manual"``
    to set spin yourself.
    """
    if direction not in ("auto", "manual"):
        raise ValueError(f"direction must be 'auto' or 'manual', got {direction!r}")
    if direction == "auto" and spin is not None:
        raise ValueError(
            "spin is derived from geometry in auto mode; use direction='manual' to set spin yourself"
        )

    from fansim.cfd.orientation import orient_impeller_for_cfd
    from fansim.cfd.runner import OpenFOAMRunner
    from fansim.geometry import build_impeller, export_stl, watertight_report
    from fansim.propeller.calibrate import datasheet_compare, normalize_metrics_sign
    from fansim.propeller.direction import prop_direction
    from fansim.propeller.geometry import build_prop, prop_blade_params
    from fansim.propeller.optimize import bemt_thrust_g
    from fansim.propeller.stl_import import measure_prop_stl, prepare_prop_stl

    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    rpm = float(0.7 * float(spec.rpm_max) if rpm is None else rpm)
    omega_rad_s = rpm * 2.0 * math.pi / 60.0
    spin_i = -1 if spin is None else int(spin)
    external = stl_mm is not None

    bemt_g = None
    if not external:
        blade = params if params is not None else prop_blade_params(spec)
        bemt_g = float(bemt_thrust_g(blade, spec, rpm=rpm))
        if float(bemt_floor_g) > 0.0 and bemt_g < float(bemt_floor_g):
            return {
                "skipped": True,
                "reason": f"bemt_thrust_g {bemt_g:.6g} < bemt_floor_g {float(bemt_floor_g):.6g}",
                "bemt_thrust_g": bemt_g,
                "tip_mach": float(spec.tip_mach(rpm)),
                "rpm": rpm,
                "spin": spin_i,
                "spec": spec_key or getattr(spec, "name", None) or str(spec),
            }

    stl = workdir / "prop.stl"
    if external:
        src = Path(stl_mm)
        if not src.is_file():
            raise FileNotFoundError(f"prop STL not found: {src}")
        if prepare_stl:
            prepare_prop_stl(src, stl)
        elif src.resolve() != stl.resolve():
            shutil.copy2(src, stl)
        metrics = measure_prop_stl(stl)
        tip_radius_m = metrics.tip_radius_m
        tip_mach = (math.pi * 2.0 * tip_radius_m * rpm / 60.0) / 343.0
    elif params is None:
        build_prop(spec, stl)
        tip_radius_m = float(spec.diameter_mm) / 2000.0
        tip_mach = float(spec.tip_mach(rpm))
    else:
        export_stl(build_impeller(blade), stl, tolerance=0.02, angular_tolerance=0.1)
        tip_radius_m = float(spec.diameter_mm) / 2000.0
        tip_mach = float(spec.tip_mach(rpm))

    orientation_used = None
    if direction == "auto":
        d = prop_direction(stl, name_hint=Path(stl_mm).name if external else None)
        if d.orientation == "flipped":
            orient_impeller_for_cfd(stl, stl, "flipped")
        spin_i = d.spin
        direction_source = d.source
        orientation_used = d.orientation
    else:
        direction_source = "manual"

    # 180° rotation about X (proper rotation; z-range reverses), so bounds must be re-measured
    # after orientation.
    rep = watertight_report(stl)
    (_, _, z0), (_, _, z1) = rep.bounds_mm

    u_kw = {} if u_freestream is None else {"u_eps": float(u_freestream)}
    dom = prop_open_air(
        tip_radius_m, z0 / 1000.0, z1 / 1000.0, rpm=rpm, spin=spin_i, **u_kw,
    )

    runner = OpenFOAMRunner(workdir)
    mesh_used = mesh if mesh is not None else MeshResolution(base_cell=float(base_cell))
    build_prop_case(
        workdir,
        stl,
        dom,
        mesh=mesh_used,
        n_iters=int(iters),
        n_subdomains=int(procs),
    )
    run_mesh(runner)
    run_solve_prop(runner, n_procs=int(procs))

    out = parse_prop_metrics(workdir, omega_rad_s=omega_rad_s)
    out = normalize_metrics_sign(out, spin=spin_i)
    out["bemt_thrust_g"] = bemt_g
    out["solver"] = "rhoSimpleFoam"
    out["domain"] = "open_air"
    out["regime"] = "compressible-MRF"
    out["tip_mach"] = tip_mach
    out["tip_radius_mm"] = tip_radius_m * 1000.0
    out["rpm"] = rpm
    out["u_freestream"] = float(dom.u_freestream)
    out["spec"] = spec_key or getattr(spec, "name", None) or str(spec)
    out["stl"] = str(stl_mm) if external else None
    out["direction_source"] = direction_source
    out["orientation"] = orientation_used
    out["datasheet"] = datasheet_compare(
        thrust_g=out["thrust_g"],
        power_w=out.get("shaft_power_w"),
        rpm=rpm,
        spec=spec,
    )
    return out
