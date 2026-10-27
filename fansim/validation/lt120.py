"""lt120 reference geometry (R1.1a). Hang skip only; clip stays on."""
from __future__ import annotations

import dataclasses
import json
from datetime import datetime
from pathlib import Path

import numpy as np

from fansim.geometry.blade import (
    BladeParams,
    _section_points_3d,
    _thick_scale_kw,
)
from fansim.geometry.config import blade_params_from_dict
from fansim.validation.section_compare import _measure_loop, measure_sections

ROOT = Path(__file__).resolve().parents[2]
PARAMS_JSON = ROOT / "docs" / "qa" / "benchmarks" / "lt120" / "fansim_params.json"
GEOM_JSON = ROOT / "docs" / "qa" / "benchmarks" / "lt120" / "geometry.json"
CURVE_CSV = ROOT / "docs" / "qa" / "benchmarks" / "lt120" / "curve.csv"
FREEZE_DIR = ROOT / "validation" / "reference" / "lt120"

# Pre-registered points (Pa) and published Q (m3/s) from curve.csv. 34.01 Pa is excluded.
POINTS = (
    {"dp_pa": 6.85, "q_m3s": 0.039644, "role": "high-flow"},
    {"dp_pa": 13.71, "q_m3s": 0.028317, "role": "high-flow"},
    {"dp_pa": 14.69, "q_m3s": 0.018878, "role": "report-only"},
    {"dp_pa": 17.14, "q_m3s": 0.015107, "role": "report-only"},
)
MESHES_MM = (5.8, 6.2)
DUCT_ID_MM = 121.0
TIP_GAP_MM = 0.5
CHORD_TOL = 0.03
CAMBER_TOL = 0.005
STAGGER_TOL_DEG = 1.5
CONVERGE_OSC_PCT = 2.0
CONVERGE_MASS_PCT = 1.0
CUTOFF_HOUR, CUTOFF_MINUTE = 15, 30


def lt120_params() -> BladeParams:
    """Wrapped shipping build. ``reference_build`` skips hang only."""
    data = json.loads(PARAMS_JSON.read_text(encoding="utf-8"))
    p = blade_params_from_dict(data)
    return dataclasses.replace(p, section_wrap="cylinder", reference_build=True)


def table_stations() -> list[dict]:
    geom = json.loads(GEOM_JSON.read_text(encoding="utf-8"))
    rows = []
    for st in geom["stations"]:
        rows.append({
            "r_mm": float(st["r_mm"]["value"]),
            "chord_mm": float(st["chord_mm"]["value"]),
            "stagger_deg": float(st["stagger_deg"]["value"]),
            "max_camber": float(st["max_camber"]["value"]),
        })
    return rows


def past_cutoff(now: datetime | None = None) -> bool:
    """True at or after 15:30 local. No new CFD unit starts."""
    t = now or datetime.now().astimezone()
    return (t.hour, t.minute) >= (CUTOFF_HOUR, CUTOFF_MINUTE)


def point_converged(osc_pct: float, mass_pct: float | None) -> bool:
    """Pre-registered gate: tail CFM peak-to-peak ≤ 2 % and mass imbalance ≤ 1 %."""
    if mass_pct is None or mass_pct > CONVERGE_MASS_PCT:
        return False
    return float(osc_pct) <= CONVERGE_OSC_PCT


def _json_safe(obj):
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, (np.floating, np.integer)):
        return obj.item()
    if isinstance(obj, np.bool_):
        return bool(obj)
    return obj


def _ref_loop(params: BladeParams, st, r_mm: float, omega: int, n_blades: int) -> dict | None:
    kw = _thick_scale_kw(params)
    pts = _section_points_3d(
        r=r_mm, r_frac=st.r_frac, chord=st.chord, stagger_deg=st.stagger_deg,
        thickness=st.thickness, max_camber=st.max_camber, camber_pos=st.camber_pos,
        sweep=0.0, skew=0.0, le_sweep=0.0, lean_deg=0.0, n_chord=60,
        features=params.features, **kw)
    return _measure_loop(np.array([[v.x, v.y, v.z] for v in pts]), r_mm, omega, n_blades)


def cut_check(stl_path: Path, params: BladeParams | None = None) -> list[dict]:
    """Cylinder cuts vs Table 1. r < hub is N/M (embedded root)."""
    p = params or lt120_params()
    table = table_stations()
    fracs = [row["r_mm"] / p.tip_radius for row in table]
    meas = measure_sections(stl_path, fracs, tip_radius_mm=p.tip_radius)
    out = []
    for spec, st, got in zip(table, p.stations, meas):
        rec = {
            "r_mm": spec["r_mm"],
            "table_chord_mm": spec["chord_mm"],
            "n_blades": int(got.get("n_blades") or 0),
            "chord_mm": got.get("chord_mm"),
            "stagger_deg": got.get("stagger_deg"),
            "camber_ratio": got.get("camber_ratio"),
        }
        if spec["r_mm"] < p.hub_radius or rec["n_blades"] == 0:
            rec["verdict"] = "N/M"
            rec["why"] = "inside hub" if spec["r_mm"] < p.hub_radius else "no blade loop"
            out.append(rec)
            continue
        omega = int(got.get("omega_sign") or 1)
        ref = _ref_loop(p, st, spec["r_mm"], omega, rec["n_blades"])
        chord_err = float(rec["chord_mm"]) / float(spec["chord_mm"]) - 1.0
        rec["chord_err"] = chord_err
        ok = abs(chord_err) <= CHORD_TOL
        if ref is not None:
            rec["ref_stagger_deg"] = ref["stagger_deg"]
            rec["ref_camber_ratio"] = ref["camber_ratio"]
            rec["stagger_err_deg"] = rec["stagger_deg"] - ref["stagger_deg"]
            rec["camber_err"] = rec["camber_ratio"] - ref["camber_ratio"]
            ok = (
                ok
                and abs(rec["stagger_err_deg"]) <= STAGGER_TOL_DEG
                and abs(rec["camber_err"]) <= CAMBER_TOL
            )
        rec["verdict"] = "PASS" if ok else "FAIL"
        out.append(rec)
    return out


def freeze_geometry(out_dir: Path | None = None) -> dict:
    """Build the wrapped impeller, write STL + freeze JSON. Day CPU; no CFD."""
    from fansim.audit.direction import prove_direction
    from fansim.geometry import build_impeller, export_stl, watertight_report
    import trimesh

    dest = Path(out_dir or FREEZE_DIR)
    dest.mkdir(parents=True, exist_ok=True)
    p = lt120_params()
    stl = export_stl(build_impeller(p), dest / "lt120.stl")
    wt = watertight_report(stl)
    cuts = cut_check(stl, p)
    mesh = trimesh.load(str(stl), force="mesh")
    proof = prove_direction(mesh)
    measurable = [r for r in cuts if r["verdict"] != "N/M"]
    doc = {
        "fan_id": "lt120",
        "prereg": "docs/validation/audits/2026-10-18-lt120-validation-prereg.md",
        "params_source": str(PARAMS_JSON.relative_to(ROOT)).replace("\\", "/"),
        "section_wrap": p.section_wrap,
        "reference_build": True,
        "clip_below_hub": True,
        "hub_radius_mm": p.hub_radius,
        "tip_radius_mm": p.tip_radius,
        "root_embed_mm": p.root_embed,
        "n_blades": p.n_blades,
        "rpm": p.rpm,
        "duct_id_mm": DUCT_ID_MM,
        "tip_gap_mm": TIP_GAP_MM,
        "r_23_mm": "embedded root station, not cuttable (inside hub 25 mm)",
        "tip_to_60_mm": "last table station (r 56.5 mm) reused at r_frac 1; no extra extrapolation",
        "watertight": wt.watertight,
        "n_bodies": wt.n_bodies,
        "volume_mm3": wt.volume_mm3,
        "direction": proof.verdict if hasattr(proof, "verdict") else str(proof),
        "omega_sign": getattr(proof, "omega_sign", None),
        "cut_check": cuts,
        "cut_measurable_pass": all(r["verdict"] == "PASS" for r in measurable),
        "stl": "lt120.stl",
    }
    (dest / "geometry_freeze.json").write_text(
        json.dumps(_json_safe(doc), indent=2), encoding="utf-8")
    (dest / "params.json").write_text(
        json.dumps(_json_safe(dataclasses.asdict(p)), indent=2), encoding="utf-8")
    return doc
