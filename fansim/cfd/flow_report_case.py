"""Flow report <-> saved CFD case: samples, geometry, test settings, cached metrics (§24)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from fansim.cfd.flow_report import (
    FLOW_REPORT_VERSION, FlowMetrics, FlowReportUnavailable, FlowSamples, compute_metrics,
)
from fansim.cfd.spanwise import load_case_radii_omega

REPORT_FILE = "flow_report.json"


def _default_loader(case_dir):
    from fansim.cfd.cockpit_viz import load_case_mesh
    return load_case_mesh(case_dir)


def samples_from_mesh(mesh) -> FlowSamples:
    g = mesh
    if "U" not in g.cell_data and "U" in g.point_data:
        g = g.point_data_to_cell_data()
    if "U" not in g.cell_data:
        raise FlowReportUnavailable("no velocity field")
    pts = np.asarray(g.cell_centers().points, float)
    n = pts.shape[0]
    u = np.asarray(g.cell_data["U"], float).reshape(n, -1)
    p = np.asarray(g.cell_data["p"], float).reshape(-1) if "p" in g.cell_data else np.zeros(n)
    sizes = g.compute_cell_sizes(length=False, area=False, volume=True)
    w = np.abs(np.asarray(sizes.cell_data["Volume"], float))
    k = np.asarray(g.cell_data["k"], float).reshape(-1) if "k" in g.cell_data else None
    om = np.asarray(g.cell_data["omega"], float).reshape(-1) if "omega" in g.cell_data else None
    return FlowSamples(pts=pts, u=u, p=p, w=w, k=k, omega=om)


def case_geometry(case_dir, mesh) -> tuple[float, float, float]:
    hub_r, tip_r, _omega = load_case_radii_omega(case_dir)
    b = getattr(mesh, "bounds", None)
    z_fan = 0.0 if b is None or float(b[4]) < 0.0 < float(b[5]) else 0.5 * (float(b[4]) + float(b[5]))
    return float(hub_r), float(tip_r), float(z_fan)


def _json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def test_settings(case_dir) -> dict:
    case_dir = Path(case_dir)
    raw = _json(case_dir / "_eval_result.json").get("raw") or {}
    meta = _json(case_dir / "constant" / "case_meta.json")
    bp = None
    try:
        der = float(raw.get("derate") or 1.0)
        bp = round(float(raw["p_probe_pa"]) / (der * der) * 2.0) / 2.0
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        bp = None
    return {"back_pressure_pa": bp, "surf_max": raw.get("surf_max"),
            "cfd_version": meta.get("cfd_version"), "rpm": meta.get("rpm"),
            "duct_shape": meta.get("duct_shape"), "casing": meta.get("casing")}


_LABELS = {"back_pressure_pa": "hose back pressure", "surf_max": "mesh level",
           "cfd_version": "solver version", "rpm": "rpm", "duct_shape": "duct shape",
           "casing": "casing"}


def first_mismatch(a: dict, b: dict) -> str | None:
    if a.get("surf_max") is None or b.get("surf_max") is None:
        return "mesh level not recorded"
    for key, label in _LABELS.items():
        if a.get(key) != b.get(key):
            return f"different {label} ({a.get(key)} vs {b.get(key)})"
    return None


def report_json_path(case_dir) -> Path:
    return Path(case_dir) / REPORT_FILE


def latest_time(case_dir) -> str:
    case_dir = Path(case_dir)
    roots = [case_dir] + sorted(case_dir.glob("processor0"))
    times = []
    for root in roots:
        for d in root.iterdir() if root.is_dir() else []:
            if d.is_dir():
                try:
                    times.append((float(d.name), d.name))
                except ValueError:
                    pass
    return max(times)[1] if times else "0"


def load_or_compute_metrics(case_dir, *, mesh=None, loader=None) -> FlowMetrics:
    case_dir = Path(case_dir)
    path = report_json_path(case_dir)
    t = latest_time(case_dir)
    cached = _json(path)
    if cached.get("version") == FLOW_REPORT_VERSION and cached.get("time") == t and cached.get("metrics"):
        try:
            return FlowMetrics.from_dict(cached["metrics"])
        except (KeyError, TypeError):
            pass
    if mesh is None:
        mesh = (loader or _default_loader)(case_dir)
    if mesh is None:
        raise FlowReportUnavailable("no saved flow fields")
    hub_r, tip_r, z_fan = case_geometry(case_dir, mesh)
    m = compute_metrics(samples_from_mesh(mesh), hub_r=hub_r, tip_r=tip_r, z_fan=z_fan)
    try:
        path.write_text(json.dumps({"version": FLOW_REPORT_VERSION, "time": t,
                                    "metrics": m.to_dict()}, indent=1), encoding="utf-8")
    except OSError:
        pass
    return m
