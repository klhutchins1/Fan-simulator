"""obj_2 compressible AMI smoke helpers (roadmap §4.3)."""
from __future__ import annotations

import json
import math
from pathlib import Path

from fansim.cfd import templates as T
from fansim.cfd.openfoam_case import _write
from fansim.propeller.cfd import P_INF, T_INF

MRF_REF_THRUST_G = 938.0
BAND_FRAC = 0.25
FLOOR_G = 10.0
N_REVS = 2
DELTA_T = 4e-5
G_PER_NEWTON = 1000.0 / 9.80665


def rev_period_s(rpm: float) -> float:
    return 60.0 / float(rpm)


def end_time_s(rpm: float, n_revs: int = N_REVS) -> float:
    return float(n_revs) * rev_period_s(rpm)


def band_limits() -> tuple[float, float]:
    return (
        MRF_REF_THRUST_G * (1.0 - BAND_FRAC),
        MRF_REF_THRUST_G * (1.0 + BAND_FRAC),
    )


def window_thrust_g(
    rows: list[list[float]],
    *,
    end_time: float,
    rpm: float,
) -> tuple[float | None, int]:
    t0 = float(end_time) - rev_period_s(rpm)
    window = [r for r in rows if len(r) > 3 and float(r[0]) >= t0]
    if not window:
        return None, 0
    grams = [abs(float(r[3])) / 9.80665 * 1000.0 for r in window]
    return sum(grams) / len(grams), len(grams)


def assess_band(mean_thrust_g: float | None) -> dict:
    lo, hi = band_limits()
    finite = mean_thrust_g is not None and math.isfinite(float(mean_thrust_g))
    mean = float(mean_thrust_g) if finite else None
    passed = bool(finite and mean is not None and lo <= mean <= hi and abs(mean) >= FLOOR_G)
    return {
        "mean_thrust_g": mean,
        "band_pass": passed,
        "band_lo_g": lo,
        "band_hi_g": hi,
        "mrf_ref_thrust_g": MRF_REF_THRUST_G,
        "floor_g": FLOOR_G,
    }


def ami_exit_code(summary: dict) -> int:
    mean = summary.get("mean_thrust_g")
    if mean is None:
        return 1
    try:
        value = float(mean)
    except (TypeError, ValueError):
        return 1
    if not math.isfinite(value):
        return 1
    return 0 if summary.get("band_pass") else 2


def apply_ami_overlay(
    case_dir,
    *,
    omega_signed: float,
    ami_radius: float,
    ami_z_min: float,
    ami_z_max: float,
    end_time: float,
    delta_t: float,
    u_freestream: float,
    k: float,
    omega_turb: float,
) -> None:
    case_dir = Path(case_dir)
    cyclic = {"AMI_CYCLIC": T.AMI_CYCLIC}
    _write(case_dir / "system/controlDict", T.PROP_AMI_CONTROL_DICT, "dictionary", "controlDict", {
        "ENDTIME": end_time,
        "DELTAT": delta_t,
        "WRITEINT": 50,
    })
    _write(case_dir / "system/fvSchemes", T.PROP_AMI_FV_SCHEMES, "dictionary", "fvSchemes", {})
    _write(case_dir / "system/fvSolution", T.PROP_AMI_FV_SOLUTION, "dictionary", "fvSolution", {})
    _write(case_dir / "system/dynamicMeshDict", T.PROP_AMI_DYNAMIC_MESH, "dictionary", "dynamicMeshDict", {
        "OMEGA": omega_signed,
    })
    _write(case_dir / "system/createBafflesDict", T.PROP_AMI_CREATE_BAFFLES, "dictionary", "createBafflesDict", {
        "ZMIN": ami_z_min,
        "ZMAX": ami_z_max,
        "RADIUS": ami_radius,
    })
    _write(case_dir / "0/U", T.PROP_AMI_U, "volVectorField", "U", {"U_EPS": u_freestream, **cyclic})
    _write(case_dir / "0/T", T.PROP_AMI_T, "volScalarField", "T", {"T_INF": T_INF, **cyclic})
    _write(case_dir / "0/p", T.PROP_AMI_P, "volScalarField", "p", {"P_INF": P_INF, **cyclic})
    _write(case_dir / "0/k", T.PROP_AMI_K, "volScalarField", "k", {"K": k, **cyclic})
    _write(case_dir / "0/omega", T.PROP_AMI_OMEGA, "volScalarField", "omega", {"OMEGAT": omega_turb, **cyclic})
    _write(case_dir / "0/nut", T.PROP_AMI_NUT, "volScalarField", "nut", cyclic)
    _write(case_dir / "0/alphat", T.PROP_AMI_ALPHAT, "volScalarField", "alphat", cyclic)
    _write(
        case_dir / "0/pointDisplacement",
        T.PROP_AMI_POINT_DISPLACEMENT,
        "pointVectorField",
        "pointDisplacement",
        {},
    )
    mrf = case_dir / "constant/MRFProperties"
    if mrf.is_file():
        mrf.unlink()


AMI_MESH_PIPELINE = [
    "surfaceFeatureExtract",
    "blockMesh",
    "snappyHexMesh -overwrite",
    "createBaffles -overwrite",
    "topoSet",
    "renumberMesh -overwrite",
    "checkMesh -allTopology",
]


def run_mesh_ami(runner) -> None:
    for cmd in AMI_MESH_PIPELINE:
        runner.run(cmd)


def run_solve_ami(runner, n_procs: int = 8) -> None:
    runner.run("rm -rf processor* postProcessing", check=False)
    if n_procs and int(n_procs) > 1:
        runner.run("decomposePar -force")
        mpi = f"mpirun --allow-run-as-root --oversubscribe -np {int(n_procs)}"
        runner.run(f"{mpi} rhoPimpleFoam -parallel")
    else:
        runner.run("rhoPimpleFoam")


def read_force_rows(case_dir) -> list[list[float]]:
    from fansim.cfd.metrics import _all_data_rows, _pp_file

    path = _pp_file(Path(case_dir), "forces", "force.dat")
    return _all_data_rows(path)


def summary_from_rows(
    rows: list[list[float]],
    *,
    stl: str,
    rpm: float,
    base_cell: float,
    reason: str | None = None,
) -> dict:
    end = end_time_s(rpm)
    mean, count = window_thrust_g(rows, end_time=end, rpm=rpm)
    summary = assess_band(mean)
    summary.update({
        "thrust_g_samples": count,
        "regime": "compressible-AMI",
        "solver": "rhoPimpleFoam",
        "rpm": float(rpm),
        "end_time": end,
        "delta_t": DELTA_T,
        "stl": stl,
        "base_cell": float(base_cell),
    })
    if mean is None:
        summary["reason"] = reason or "non-finite mean thrust"
    return summary


def result_is_resumable(path) -> bool:
    path = Path(path)
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return math.isfinite(float(data["mean_thrust_g"]))
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return False
