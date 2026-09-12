# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Assemble a complete OpenFOAM v2406 MRF case directory from an impeller + TestRig."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import trimesh

from fansim.cfd import templates as T
from fansim.cfd.domain import MM_TO_M, TestRig

RHO_AIR = 1.2
NU_AIR = 1.5e-5
CMU = 0.09
TURB_INTENSITY = 0.05


@dataclass
class MeshResolution:
    base_cell: float = 0.003  # m, background hex size
    surf_min: int = 1
    surf_max: int = 2
    feature_level: int = 2


def _header(cls: str, obj: str) -> str:
    return T.render(T.FOAM_HEADER, {"CLASS": cls, "OBJECT": obj})


def _write(path: Path, template: str, cls: str, obj: str, mapping: dict) -> None:
    body = T.render(template, {"HEADER": _header(cls, obj), **mapping})
    path.write_text(body, encoding="utf-8")


def build_case(
    case_dir: str | Path,
    impeller_stl_mm: str | Path,
    rig: TestRig,
    mesh: MeshResolution | None = None,
    n_iters: int = 800,
    n_subdomains: int = 8,
    back_pressure_pa: float | None = None,
    u_guess: float = 2.0,
) -> Path:
    """Write a ready-to-run OpenFOAM case. ``impeller_stl_mm`` is a millimeter-scale STL.

    If ``back_pressure_pa`` is given, use pressure-driven BCs (total-pressure inlet, fixed
    static back-pressure outlet) so the flow rate emerges from the blade design -- this is
    the mode used for optimization, where CFM is an objective. Otherwise use the
    velocity-driven BCs (fixed inlet velocity) used by the fan-curve sweep.
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
    u_in = rig.inlet_velocity
    k = 1.5 * (TURB_INTENSITY * max(u_in, 1e-3)) ** 2
    length_scale = 0.07 * (2.0 * rig.duct_radius)
    omega_turb = math.sqrt(k) / (CMU**0.25 * length_scale)

    H = rig.duct_radius
    zmin, zmax = rig.domain_z_min, rig.domain_z_max
    nx = max(10, round(2 * H / mesh.base_cell))
    nz = max(20, round((zmax - zmin) / mesh.base_cell))
    write_int = max(1, n_iters // 2)  # field snapshots (kept small via purgeWrite)
    fo_int = max(1, n_iters // 40)  # fine function-object sampling for convergence tracking

    # --- system/ ---
    _write(case_dir / "system/blockMeshDict", T.BLOCK_MESH, "dictionary", "blockMeshDict", {
        "XMIN": -H, "XMAX": H, "YMIN": -H, "YMAX": H, "ZMIN": zmin, "ZMAX": zmax,
        "NX": nx, "NY": nx, "NZ": nz,
    })
    _write(case_dir / "system/snappyHexMeshDict", T.SNAPPY, "dictionary", "snappyHexMeshDict", {
        "FEATLVL": mesh.feature_level, "SURFMIN": mesh.surf_min, "SURFMAX": mesh.surf_max,
        "LOCX": 0.9 * H, "LOCY": 0.9 * H, "LOCZ": 0.0,
    })
    _write(case_dir / "system/surfaceFeatureExtractDict", T.SURFACE_FEATURES,
           "dictionary", "surfaceFeatureExtractDict", {})
    _write(case_dir / "system/topoSetDict", T.TOPOSET, "dictionary", "topoSetDict", {
        "MRFZMIN": rig.mrf_z_min, "MRFZMAX": rig.mrf_z_max, "MRFRADIUS": rig.duct_radius,
    })
    _write(case_dir / "system/controlDict", T.CONTROL_DICT, "dictionary", "controlDict", {
        "ENDTIME": n_iters, "WRITEINT": write_int, "FOINT": fo_int, "RHO": RHO_AIR,
    })
    _write(case_dir / "system/fvSchemes", T.FV_SCHEMES, "dictionary", "fvSchemes", {})
    _write(case_dir / "system/fvSolution", T.FV_SOLUTION, "dictionary", "fvSolution", {})
    _write(case_dir / "system/decomposeParDict", T.DECOMPOSE_PAR,
           "dictionary", "decomposeParDict", {"NPROCS": n_subdomains})

    # --- constant/ ---
    _write(case_dir / "constant/transportProperties", T.TRANSPORT,
           "dictionary", "transportProperties", {"NU": NU_AIR})
    _write(case_dir / "constant/turbulenceProperties", T.TURBULENCE,
           "dictionary", "turbulenceProperties", {})
    _write(case_dir / "constant/MRFProperties", T.MRF_PROPERTIES,
           "dictionary", "MRFProperties", {"OMEGA": rig.omega_signed})

    # --- 0/ ---
    if back_pressure_pa is not None:
        # u_guess seeds the pressure-driven initial field; sweeping it probes whether the
        # steady solve has multiple solution branches (bistability).
        k = 1.5 * (TURB_INTENSITY * u_guess) ** 2
        omega_turb = math.sqrt(k) / (CMU**0.25 * length_scale)
        pback_kin = back_pressure_pa / RHO_AIR
        _write(case_dir / "0/U", T.FIELD_U_PDRIVEN, "volVectorField", "U",
               {"UGUESS": u_guess})
        _write(case_dir / "0/p", T.FIELD_P_PDRIVEN, "volScalarField", "p",
               {"PBACK": pback_kin})
        _write(case_dir / "0/k", T.FIELD_K_PDRIVEN, "volScalarField", "k", {"K": k})
        _write(case_dir / "0/omega", T.FIELD_OMEGA_PDRIVEN, "volScalarField", "omega",
               {"OMEGAT": omega_turb})
    else:
        _write(case_dir / "0/U", T.FIELD_U, "volVectorField", "U", {"UIN": u_in})
        _write(case_dir / "0/p", T.FIELD_P, "volScalarField", "p", {})
        _write(case_dir / "0/k", T.FIELD_K, "volScalarField", "k", {"K": k})
        _write(case_dir / "0/omega", T.FIELD_OMEGA, "volScalarField", "omega",
               {"OMEGAT": omega_turb})
    _write(case_dir / "0/nut", T.FIELD_NUT, "volScalarField", "nut", {})

    return case_dir


MESH_PIPELINE = [
    "surfaceFeatureExtract",
    "blockMesh",
    "snappyHexMesh -overwrite",
    "topoSet",
    "renumberMesh -overwrite",
    "checkMesh -allTopology",
]


def run_mesh(runner) -> None:
    """Run the serial meshing pipeline in the container."""
    for cmd in MESH_PIPELINE:
        runner.run(cmd)


def run_solve(runner, n_procs: int = 8, reconstruct: bool = False) -> None:
    """Solve with simpleFoam, in parallel via MPI when ``n_procs`` > 1.

    Metrics come from function-object output written to the case root by the master rank,
    so reconstruction is only needed when the full field is wanted (e.g. visualization).
    """
    # Clear stale decomposition and postProcessing so this run writes fresh output.
    # On restart, OpenFOAM ROTATES function-object files (old surfaceFieldValue.dat ->
    # surfaceFieldValue_0.dat) and writes the new run to the suffixed name -- which the
    # metrics parser would miss -- so wipe postProcessing to keep the canonical filename.
    runner.run("rm -rf processor* postProcessing", check=False)
    if n_procs and n_procs > 1:
        runner.run("decomposePar -force")
        mpi = f"mpirun --allow-run-as-root --oversubscribe -np {n_procs}"
        # potentialFoam seeds a divergence-free initial field -> faster, quieter convergence.
        runner.run(f"{mpi} potentialFoam -parallel -initialiseUBCs", check=False)
        runner.run(f"{mpi} simpleFoam -parallel")
        if reconstruct:
            runner.run("reconstructPar -latestTime")
    else:
        runner.run("potentialFoam -initialiseUBCs", check=False)
        runner.run("simpleFoam")
