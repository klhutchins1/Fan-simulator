"""Freeze / gate helpers for prop open-air CFD smoke fixtures (roadmap §4.3)."""
from __future__ import annotations

import json
import math
from datetime import date as date_cls
from pathlib import Path

FORCE_TAIL_FRAC = 0.25
FORCE_DRIFT_TOL_PCT = 25.0  # smoke mesh limit-cycle; not fan-path 2% honesty
THRUST_G_FLOOR = 10.0
OPENFOAM_IMAGE_DEFAULT = "opencfd/openfoam-default:2406"

REQUIRED_FIXTURE_KEYS = frozenset({
    "id", "stl", "spin", "rpm", "tip_mach", "tip_radius_mm", "mesh",
    "solver", "domain", "regime", "openfoam_image", "metrics",
    "force_tail_drift_pct", "date", "notes",
})


def force_z_tail_drift_pct(
    case_dir: str | Path,
    *,
    tail_frac: float = FORCE_TAIL_FRAC,
) -> float:
    """Peak-to-peak range of total force z over the tail, as % of |mean|."""
    from fansim.cfd.metrics import _all_data_rows, _pp_file

    path = _pp_file(Path(case_dir), "forces", "force.dat")
    rows = _all_data_rows(path)
    if len(rows) < 4:
        return 999.0
    tail = rows[max(1, int(len(rows) * (1.0 - float(tail_frac)))) :]
    zs = [float(r[3]) for r in tail]
    mean = sum(zs) / len(zs)
    drift = (max(zs) - min(zs)) / (abs(mean) + 1e-12) * 100.0
    return float(drift)


def prop_cfd_smoke_gate(
    result: dict,
    case_dir: str | Path | None = None,
    *,
    thrust_g_floor: float = THRUST_G_FLOOR,
    drift_tol_pct: float = FORCE_DRIFT_TOL_PCT,
    tail_frac: float = FORCE_TAIL_FRAC,
) -> tuple[bool, list[str]]:
    """Return (ok, reasons) for the §4.3 smoke gate before obj_2."""
    reasons: list[str] = []
    keys = ("thrust_n", "thrust_g", "torque_nm", "shaft_power_w")
    for k in keys:
        v = result.get(k)
        try:
            fv = float(v)
        except (TypeError, ValueError):
            reasons.append(f"{k} missing or non-numeric")
            continue
        if not math.isfinite(fv):
            reasons.append(f"{k} not finite ({v!r})")
    try:
        tg = abs(float(result.get("thrust_g", float("nan"))))
    except (TypeError, ValueError):
        tg = float("nan")
    if math.isfinite(tg) and tg < float(thrust_g_floor):
        reasons.append(
            f"|thrust_g|={tg:.6g} < floor {float(thrust_g_floor):.6g}"
        )
    if case_dir is not None:
        try:
            drift = force_z_tail_drift_pct(case_dir, tail_frac=tail_frac)
        except (OSError, ValueError, FileNotFoundError) as exc:
            reasons.append(f"force-tail drift unavailable: {exc}")
        else:
            if drift >= float(drift_tol_pct):
                reasons.append(
                    f"force_z_tail_drift_pct={drift:.4g} >= {float(drift_tol_pct):.4g}"
                )
    return (len(reasons) == 0, reasons)


def build_prop_cfd_fixture(
    *,
    result: dict,
    fixture_id: str,
    stl: str,
    spin: int,
    mesh: dict,
    openfoam_image: str = OPENFOAM_IMAGE_DEFAULT,
    force_tail_drift_pct: float | None = None,
    date: str | None = None,
    notes: str = "smoke screening; not datasheet-grade",
) -> dict:
    metrics = {
        "thrust_n": float(result["thrust_n"]),
        "thrust_g": float(result["thrust_g"]),
        "torque_nm": float(result["torque_nm"]),
        "shaft_power_w": float(result["shaft_power_w"]),
    }
    return {
        "id": str(fixture_id),
        "stl": str(stl),
        "spin": int(spin),
        "rpm": float(result["rpm"]),
        "tip_mach": float(result["tip_mach"]),
        "tip_radius_mm": float(result["tip_radius_mm"]),
        "mesh": {
            "base_cell_m": float(mesh["base_cell_m"]),
            "iters": int(mesh["iters"]),
            "procs": int(mesh["procs"]),
        },
        "solver": str(result.get("solver") or "rhoSimpleFoam"),
        "domain": str(result.get("domain") or "open_air"),
        "regime": str(result.get("regime") or "compressible-MRF"),
        "openfoam_image": str(openfoam_image),
        "metrics": metrics,
        "force_tail_drift_pct": (
            None if force_tail_drift_pct is None else float(force_tail_drift_pct)
        ),
        "date": date or date_cls.today().isoformat(),
        "notes": str(notes),
    }


def write_prop_cfd_fixture(fixture: dict, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(fixture, indent=2) + "\n", encoding="utf-8")
    return path
