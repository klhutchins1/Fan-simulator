"""P–Q curve summaries from a list of {cfm, static_pa} points (no OpenFOAM).

Shut-off is the Q→0 intercept when the sweep actually reached near-zero flow.
Peak static pressure in an open-flow velocity sweep is not shut-off.
"""

from __future__ import annotations

from fansim.cfd.metrics import FanMetrics


def free_delivery_cfm(points: list[dict]) -> float | None:
    """Interpolate the CFM where static pressure crosses zero (free delivery)."""
    pts = sorted(points, key=lambda p: p["cfm"])
    for a, b in zip(pts, pts[1:]):
        pa, pb = a["static_pa"], b["static_pa"]
        if pa == 0:
            return a["cfm"]
        if (pa > 0) != (pb > 0):
            f = pa / (pa - pb)
            return a["cfm"] + f * (b["cfm"] - a["cfm"])
    return None


def shut_off_pa(points: list[dict], *, q_near_zero: float = 5.0) -> float | None:
    """Linear Q→0 static rise, or None if the sweep never got within ``q_near_zero`` CFM."""
    if not points:
        return None
    pts = sorted(points, key=lambda p: p["cfm"])
    if pts[0]["cfm"] > q_near_zero:
        return None
    if abs(pts[0]["cfm"]) < 1e-9:
        return float(pts[0]["static_pa"])
    if len(pts) < 2:
        return None
    a, b = pts[0], pts[1]
    q1, p1 = float(a["cfm"]), float(a["static_pa"])
    q2, p2 = float(b["cfm"]), float(b["static_pa"])
    if q2 == q1:
        return p1
    return p1 + (p2 - p1) / (q2 - q1) * (0.0 - q1)


def curve_report(points: list[dict]) -> dict:
    dps = [float(p["static_pa"]) for p in points]
    return {
        "free_delivery_cfm": free_delivery_cfm(points),
        "shut_off_pa": shut_off_pa(points),
        "peak_static_pa": max(dps) if dps else None,
        "n_points": len(points),
    }


def point_row(metrics: FanMetrics, inlet_v: float) -> dict:
    return {
        "inlet_v": inlet_v,
        "cfm": metrics.cfm,
        "static_pa": metrics.static_pressure_rise_pa,
        "power_w": metrics.shaft_power_w,
        "torque_mnm": metrics.torque_nm * 1e3,
        "efficiency_pct": metrics.efficiency * 100.0,
        "eta_total": metrics.eta_total,
    }
