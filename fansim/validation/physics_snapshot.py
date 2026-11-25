"""Physics snapshot (RV-1): pin what the physics computes so a moved number fails CI.

Cases and tolerances are pre-registered in
``docs/validation/audits/2026-11-24-physics-snapshot-prereg.md``. This is a regression pin, not a
validation: it judges no model against published data.

Every case is cheap (no geometry build, CFD or Docker) and takes its inputs from ``fansim/`` and
``config/`` only.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_PATH = ROOT / "tests" / "data" / "physics_snapshot.json"

# Pre-registered tolerances.
TOL = {"closed": 1e-9, "iter": 1e-6}

STOCK_GAP_MM = 0.5
SCREEN_LOAD_PA = 10.0
PROP_JS = (0.0, 0.2, 0.4, 0.6)
UNEVEN_7_DEG = (0.0, 47.0, 101.0, 153.0, 207.0, 259.0, 311.0)


# ---------------------------------------------------------------- compute

def _curve(c) -> dict[str, Any]:
    pts = list(c.points)
    return {
        "flow_cfm": [float(p.flow_cfm) for p in pts],
        "flow_m3s": [float(p.flow_m3s) for p in pts],
        "dp_static_pa": [float(p.dp_static_pa) for p in pts],
        "dp_total_pa": [float(p.dp_total_pa) for p in pts],
        "efficiency": [float(p.efficiency) for p in pts],
        "power_w": [float(p.power_w) for p in pts],
        "point_converged": [bool(p.converged) for p in pts],
        "free_delivery_cfm": float(c.free_delivery_cfm),
        "shutoff_dp_pa": float(c.shutoff_dp_pa),
        "peak_efficiency": float(c.peak_efficiency),
        "peak_eff_cfm": float(c.peak_eff_cfm),
        "converged": bool(c.converged),
        "free_status": str(c.free_status),
    }


def _fan_cases() -> dict[str, dict]:
    from fansim.fan_bem import pq_curve
    from fansim.geometry.blade import BladeParams
    from fansim.optimize.search_space import blade_from_flat, stock_blade_flat
    from fansim.optimize.system_curve import bem_screen_cfm
    from fansim.validation.lt120 import lt120_params

    flat = stock_blade_flat("a12x25")
    stock = blade_from_flat(flat)
    rpm = float(flat.get("rpm", 2000.0))
    lt = lt120_params()
    free, op = bem_screen_cfm(stock, rpm, SCREEN_LOAD_PA, STOCK_GAP_MM)
    return {
        "fan_bem.stock_v3": _curve(pq_curve(stock, rpm, tip_gap_mm=STOCK_GAP_MM)),
        "fan_bem.stock_v3_axial_force": _curve(
            pq_curve(stock, rpm, tip_gap_mm=STOCK_GAP_MM, pressure_model="axial_force")),
        "fan_bem.stock_v3_stator": _curve(pq_curve(stock, rpm, tip_gap_mm=STOCK_GAP_MM, stator=True)),
        "fan_bem.stock_v3_rpm1500": _curve(pq_curve(stock, 1500.0, tip_gap_mm=STOCK_GAP_MM)),
        "fan_bem.lt120": _curve(pq_curve(lt, float(lt.rpm), tip_gap_mm=STOCK_GAP_MM)),
        "fan_bem.default_params": _curve(pq_curve(BladeParams(), 2000.0, tip_gap_mm=STOCK_GAP_MM)),
        "fan_bem.screen_cfm": {"free_cfm": float(free), "op_cfm": float(op)},
    }


def _mixed_cases() -> dict[str, dict]:
    from fansim.centrifugal.bem import mixed_bem_screen_cfm
    from fansim.centrifugal.geometry import MixedFlowParams

    free, op = mixed_bem_screen_cfm(MixedFlowParams(), 3000.0, SCREEN_LOAD_PA, STOCK_GAP_MM)
    return {"mixed_bem.default": {"free_cfm": float(free), "op_cfm": float(op)}}


def _prop_cases() -> tuple[dict[str, dict], dict[str, dict]]:
    from fansim.propeller.bemt import analyze
    from fansim.propeller.bemt_catalog import approximate_prop_blade
    from fansim.propeller.noise import estimate_prop_noise
    from fansim.propeller.polar import nondim

    iters: dict[str, dict] = {}
    polar: dict[str, Any] = {}
    noise: dict[str, Any] = {}
    for cid, dia, pitch, rpm in (("apc_sf_9x4.7", 9.0, 4.7, 6026.0), ("apc_e_9x6", 9.0, 6.0, 6000.0)):
        blade = approximate_prop_blade(dia, pitch)
        d_m = dia * 0.0254
        n = rpm / 60.0
        rows: dict[str, list] = {k: [] for k in ("thrust_n", "torque_nm", "power_w", "figure_of_merit",
                                                 "figure_of_merit_raw", "prop_efficiency", "converged")}
        for j in PROP_JS:
            v = j * n * d_m
            p = analyze(blade, rpm, v_forward=v)
            rows["thrust_n"].append(float(p.thrust_n))
            rows["torque_nm"].append(float(p.torque_nm))
            rows["power_w"].append(float(p.power_w))
            rows["figure_of_merit"].append(float(p.figure_of_merit))
            rows["figure_of_merit_raw"].append(float(p.figure_of_merit_raw))
            rows["prop_efficiency"].append(None if p.prop_efficiency is None else float(p.prop_efficiency))
            rows["converged"].append(bool(p.converged))
            nd = nondim(p.thrust_n, p.power_w, rpm=rpm, diameter_m=d_m, v_inf=v)
            for k in ("J", "CT", "CP", "eta"):
                polar[f"{cid}.{k}@J{j:.1f}"] = None if nd[k] is None else float(nd[k])
            if j == 0.0:
                for k, val in estimate_prop_noise(blade, rpm, p).items():
                    if isinstance(val, (int, float)) and not isinstance(val, bool):
                        noise[f"{cid}.{k}"] = float(val)
        iters[f"prop_bemt.{cid}"] = rows
    closed = {"prop_bemt.polar": polar, "acoustics.prop_noise": noise}
    return iters, closed


def _structural_cases() -> dict[str, dict]:
    from fansim.optimize.search_space import blade_from_flat, stock_blade_flat
    from fansim.structural.balance import couple_unbalance, required_counterweight, static_unbalance
    from fansim.structural.deflection import root_bending_stress, tip_deflection_mm
    from fansim.structural.flutter import first_bending_hz
    from fansim.structural.stress import centrifugal_root_stress

    stock = blade_from_flat(stock_blade_flat("a12x25"))
    out: dict[str, Any] = {}
    for mat in ("PETG", "PLA"):
        c = centrifugal_root_stress(stock, material=mat)
        b = root_bending_stress(stock, material=mat, load_pa=10.0)
        out[f"{mat}.centrifugal_sigma_mpa"] = float(c.sigma_root_mpa)
        out[f"{mat}.centrifugal_sf"] = float(c.safety_factor)
        out[f"{mat}.centrifugal_ok"] = bool(c.ok)
        out[f"{mat}.bending_sigma_mpa"] = float(b.sigma_root_mpa)
        out[f"{mat}.bending_sf"] = float(b.safety_factor)
        out[f"{mat}.tip_deflection_mm_10pa"] = float(tip_deflection_mm(stock, material=mat, load_pa=10.0))
        out[f"{mat}.first_bending_hz"] = float(first_bending_hz(stock, material=mat))
    ang = [math.radians(a) for a in UNEVEN_7_DEG]
    u = static_unbalance(ang)
    cw_mr, cw_ang = required_counterweight(ang)
    bal = {
        "static_magnitude": float(u.magnitude),
        "static_angle_rad": float(u.angle_rad),
        "static_normalized": float(u.normalized),
        "counterweight_mr": float(cw_mr),
        "counterweight_angle_rad": float(cw_ang),
        "couple": float(couple_unbalance(ang, [0.001 * k for k in range(len(ang))])),
    }
    return {"structural.stock_v3": out, "structural.balance": bal}


def _acoustic_cases() -> dict[str, dict]:
    import numpy as np

    from fansim.acoustics.farfield import a_weighting_db, blade_pass_frequency, dipole_pressure
    from fansim.acoustics.loading import loading_noise_proxy
    from fansim.acoustics.tonal import tonal_peak_ratio

    t = np.linspace(0.0, 0.01, 101)
    force = np.stack([0.1 * np.sin(2 * np.pi * 800 * t), 0.05 * np.cos(2 * np.pi * 800 * t),
                      0.2 * np.sin(2 * np.pi * 400 * t)], axis=1)
    p = dipole_pressure(force, float(t[1] - t[0]), r_hat=(0.6, 0.0, 0.8), r_obs=1.0)
    freqs = (31.5, 100.0, 250.0, 1000.0, 4000.0, 10000.0)
    eq7 = [2 * math.pi * k / 7 for k in range(7)]
    return {"acoustics.farfield": {
        "dipole_p_rms": float(np.sqrt(np.mean(p ** 2))),
        "dipole_p_max": float(np.max(p)),
        **{f"a_weight_db@{f:g}": float(a_weighting_db(f)) for f in freqs},
        "bpf_7_2000": float(blade_pass_frequency(7, 2000.0)),
        "tonal_ratio_equal_7": float(tonal_peak_ratio(eq7)),
        "tonal_ratio_uneven_7": float(tonal_peak_ratio([math.radians(a) for a in UNEVEN_7_DEG])),
        "loading_proxy_7_0.05N": float(loading_noise_proxy(7, 0.05)),
        "loading_proxy_9_0.03N": float(loading_noise_proxy(9, 0.03)),
    }}


def _air_case() -> dict[str, dict]:
    from fansim.physics import air

    names = ("P0_PA", "T_ROOM_K", "R_AIR", "GAMMA_AIR", "RHO_AMCA", "RHO_ISA", "MU_AIR", "NU_AIR", "C0_AIR")
    return {"air": {n: float(getattr(air, n)) for n in names}}


def compute() -> dict[str, Any]:
    """Every pre-registered case, as ``{"cases": {id: {"kind": "closed"|"iter", "values": {...}}}}``."""
    cases: dict[str, dict] = {}
    iters: dict[str, dict] = {}
    closed: dict[str, dict] = {}
    iters.update(_fan_cases())
    iters.update(_mixed_cases())
    p_iter, p_closed = _prop_cases()
    iters.update(p_iter)
    closed.update(p_closed)
    closed.update(_structural_cases())
    closed.update(_acoustic_cases())
    closed.update(_air_case())
    for cid, vals in sorted(iters.items()):
        cases[cid] = {"kind": "iter", "values": vals}
    for cid, vals in sorted(closed.items()):
        cases[cid] = {"kind": "closed", "values": vals}
    return {"cases": cases}


# ---------------------------------------------------------------- compare

def _is_num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _num_diff(a: float, b: float, tol: float, scale: float) -> bool:
    """True if a and b differ beyond ``tol * scale``. inf/nan compare by identity."""
    if math.isnan(a) or math.isnan(b) or math.isinf(a) or math.isinf(b):
        return not (a == b or (math.isnan(a) and math.isnan(b)))
    return abs(a - b) > tol * scale


def _series_scale(series: list) -> float:
    vals = [abs(v) for v in series if _is_num(v) and math.isfinite(v)]
    return max(vals) if vals else 1.0


def _diff_value(path: str, snap, now, kind: str, out: list[str]) -> None:
    tol = TOL[kind]
    if isinstance(snap, list):
        if not isinstance(now, list) or len(now) != len(snap):
            out.append(f"{path}: shape {len(snap)} -> {len(now) if isinstance(now, list) else type(now).__name__}")
            return
        scale = _series_scale(snap) if kind == "iter" else None
        for i, (s, n) in enumerate(zip(snap, now)):
            _diff_scalar(f"{path}[{i}]", s, n, tol, scale, out)
        return
    _diff_scalar(path, snap, now, tol, None, out)


def _diff_scalar(path: str, s, n, tol: float, scale: float | None, out: list[str]) -> None:
    if _is_num(s) and _is_num(n):
        sc = scale if scale is not None else max(1.0, abs(float(s))) if math.isfinite(float(s)) else 1.0
        if _num_diff(float(s), float(n), tol, sc):
            out.append(f"{path}: {s!r} -> {n!r}")
    elif s != n or type(s) is not type(n):
        out.append(f"{path}: {s!r} -> {n!r}")


def compare(snap: dict, now: dict) -> list[str]:
    """Differences between a stored snapshot and a fresh ``compute()``, under the pre-registered rules."""
    out: list[str] = []
    sc, nc = snap.get("cases", {}), now.get("cases", {})
    for cid in sorted(set(sc) ^ set(nc)):
        out.append(f"{cid}: case {'missing now' if cid in sc else 'not in snapshot'}")
    for cid in sorted(set(sc) & set(nc)):
        s, n = sc[cid], nc[cid]
        if s.get("kind") != n.get("kind"):
            out.append(f"{cid}: kind {s.get('kind')} -> {n.get('kind')}")
            continue
        sv, nv = s["values"], n["values"]
        for k in sorted(set(sv) ^ set(nv)):
            out.append(f"{cid}.{k}: key {'missing now' if k in sv else 'not in snapshot'}")
        for k in sorted(set(sv) & set(nv)):
            _diff_value(f"{cid}.{k}", sv[k], nv[k], s["kind"], out)
    return out


# ---------------------------------------------------------------- io

def load(path: Path = SNAPSHOT_PATH) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(reason: str, path: Path = SNAPSHOT_PATH) -> dict[str, Any]:
    if not (reason.startswith("docs/validation/audits/") and reason.endswith(".md")):
        raise ValueError("reason must be docs/validation/audits/<file>.md")
    if not (ROOT / reason).is_file():
        raise FileNotFoundError(f"reason file {reason} does not exist; write the audit file first")
    data = {"reason": reason, **compute()}
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return data
