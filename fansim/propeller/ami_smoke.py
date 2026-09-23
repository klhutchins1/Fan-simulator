"""obj_2 compressible AMI smoke helpers (roadmap §4.3)."""
from __future__ import annotations

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
