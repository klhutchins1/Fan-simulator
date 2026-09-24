"""Shut-off report from multi-back P–Q rows (converged points only)."""

from __future__ import annotations

from fansim.analyze.fan_curve import shut_off_pa

PUB_SHUTOFF_PA = 22.9


def shutoff_report_from_pq_rows(
    pq_rows: list[dict],
    *,
    published_pa: float = PUB_SHUTOFF_PA,
    q_near_zero: float = 5.0,
    interim_tol_pa: float = 5.0,
) -> dict:
    """Build the ``shutoff`` block stamped on validation summaries.

    Prefers ``shut_off_pa`` when the lowest **converged** CFM is within
    ``q_near_zero``. Otherwise falls back to a last-two-converged linear proxy
    (historical §9/§11 method) and notes that it is not a Q=0 solve.
    """
    conv = [r for r in pq_rows if r.get("converged")]
    band = [float(published_pa) - interim_tol_pa, float(published_pa) + interim_tol_pa]
    if len(conv) < 2:
        return {
            "method": "insufficient_converged",
            "shutoff_pa": None,
            "published_pa": float(published_pa),
            "error_pa": None,
            "interim_band_pa": band,
            "interim_pass": False,
            "n_converged": len(conv),
            "lowest_converged_cfm": None,
            "note": "Need ≥2 converged P–Q points for shut-off",
        }
    points = [
        {"cfm": float(r["cfm"]), "static_pa": float(r["back_pa"])}
        for r in conv
    ]
    lowest = min(p["cfm"] for p in points)
    honest = shut_off_pa(points, q_near_zero=q_near_zero)
    if honest is not None:
        so = float(honest)
        method = (
            f"shut_off_pa (q_near_zero={q_near_zero:g}; "
            f"lowest converged CFM={lowest:.2f})"
        )
        note = "Converged near-zero branch — preferred over last-two proxy"
    else:
        pts = sorted(points, key=lambda p: p["cfm"])
        a, b = pts[0], pts[1]
        q1, p1 = float(a["cfm"]), float(a["static_pa"])
        q2, p2 = float(b["cfm"]), float(b["static_pa"])
        so = p1 + (p2 - p1) / (q2 - q1) * (0.0 - q1) if q2 != q1 else p1
        method = (
            f"last_two_converged proxy "
            f"({p1:g} Pa / {q1:.2f} CFM, {p2:g} Pa / {q2:.2f} CFM)"
        )
        note = (
            f"Lowest converged CFM {lowest:.2f} > q_near_zero={q_near_zero:g}; "
            "proxy only — not a converged Q=0 solve"
        )
    err = so - float(published_pa)
    return {
        "method": method,
        "shutoff_pa": round(so, 2),
        "published_pa": float(published_pa),
        "error_pa": round(err, 2),
        "interim_band_pa": band,
        "interim_pass": band[0] <= so <= band[1],
        "n_converged": len(conv),
        "lowest_converged_cfm": round(lowest, 2),
        "note": note,
    }
