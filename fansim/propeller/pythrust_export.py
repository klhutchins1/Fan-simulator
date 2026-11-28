"""Export BEMT polars as PyThrust-compatible JSON + CSV catalog entries (Track A stage 2)."""

from __future__ import annotations

import csv
import json
import math
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fansim.geometry.blade import BladeParams
from fansim.physics.air import C0_AIR as C_AIR
from fansim.propeller.bemt import RHO_AIR, analyze
from fansim.propeller.polar import nondim, v_inf_from_j

CSV_HEADER = (
    "rpm",
    "speed_mps",
    "advance_ratio",
    "efficiency",
    "thrust_coeff",
    "power_coeff",
    "power_w",
    "torque_nm",
    "thrust_n",
    "thrust_per_power_n_w",
    "mach",
    "reynolds",
    "figure_of_merit",
)
DEFAULT_RPM_LIST = [1000.0, 3000.0, 5000.0, 7000.0, 9000.0, 11000.0]
DEFAULT_J_LIST = [i * 0.05 for i in range(13)]  # 0.0 .. 0.60


def default_export_grid(*, rpm_max: float | None = None) -> tuple[list[float], list[float]]:
    rpms = list(DEFAULT_RPM_LIST)
    if rpm_max is not None:
        rpms = [r for r in rpms if r <= float(rpm_max) + 1e-9]
        if not rpms:
            rpms = [float(rpm_max)]
    return rpms, list(DEFAULT_J_LIST)


def prop_id_for_export(spec_key: str, *, suffix: str = "BEMT") -> str:
    raw = re.sub(r"[^A-Za-z0-9_\-]+", "_", str(spec_key).strip())
    raw = re.sub(r"_+", "_", raw).strip("_") or "prop"
    return f"FANSIM_{raw}_{suffix}"


def export_bemt_pythrust_catalog(
    params: BladeParams,
    *,
    prop_id: str,
    diameter_in: float,
    pitch_in: float,
    blade_count: int,
    out_dir: str | Path,
    rpm_list: list[float] | None = None,
    j_list: list[float] | None = None,
    rho: float = RHO_AIR,
    geometry_match: str = "design_blade",
    model: str | None = None,
) -> dict[str, Any]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rpms = list(rpm_list) if rpm_list is not None else default_export_grid()[0]
    js = list(j_list) if j_list is not None else default_export_grid()[1]
    d_m = float(params.tip_radius) * 2.0 / 1000.0
    rows: list[list[float]] = []
    for rpm in rpms:
        for j in js:
            v = v_inf_from_j(float(j), float(rpm), d_m)
            perf = analyze(params, rpm=float(rpm), v_forward=float(v), rho=float(rho))
            nd = nondim(
                perf.thrust_n,
                perf.power_w,
                rpm=float(rpm),
                diameter_m=d_m,
                v_inf=float(v),
                rho=float(rho),
            )
            ct, cp = float(nd["CT"] or 0.0), float(nd["CP"] or 0.0)
            eta = 0.0 if nd["eta"] is None else float(nd["eta"])
            tip_mach = (math.pi * d_m * float(rpm) / 60.0) / C_AIR
            fom = float(perf.figure_of_merit) if (abs(float(j)) < 1e-12 and perf.figure_of_merit is not None) else 0.0
            tpp = (float(perf.thrust_n) / float(perf.power_w)) if perf.power_w > 0 else 0.0
            rows.append(
                [
                    float(rpm),
                    float(v),
                    float(nd["J"] or j),
                    eta,
                    ct,
                    cp,
                    float(perf.power_w),
                    float(perf.torque_nm),
                    float(perf.thrust_n),
                    tpp,
                    float(tip_mach),
                    0.0,
                    fom,
                ]
            )
    csv_name = f"{prop_id}.csv"
    json_name = f"{prop_id}.json"
    export_name = f"{prop_id}.export.json"
    csv_path = out_dir / csv_name
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(CSV_HEADER)
        w.writerows(rows)
    meta = {
        "id": prop_id,
        "manufacturer": "fansim",
        "model": model or prop_id,
        "diameter_in": float(diameter_in),
        "pitch_in": float(pitch_in),
        "blade_count": int(blade_count),
        "data_csv": csv_name,
    }
    json_path = out_dir / json_name
    json_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    export_meta = {
        "source": "bemt",
        "geometry_match": geometry_match,
        "prop_id": prop_id,
        "tip_radius_mm": float(params.tip_radius),
        "rpm_list": rpms,
        "j_list": js,
        "rho": float(rho),
        "n_rows": len(rows),
        "timestamp": datetime.now(UTC).isoformat(),
    }
    export_path = out_dir / export_name
    export_path.write_text(json.dumps(export_meta, indent=2) + "\n", encoding="utf-8")
    return {
        "prop_id": prop_id,
        "csv": str(csv_path),
        "json": str(json_path),
        "export_meta": str(export_path),
        "n_rows": len(rows),
        "rpm_list": rpms,
        "j_list": js,
    }
