"""Verdict logic for the loaded-branch diagnostic ladder (roadmap 19.6, Task 3).

``ladder_verdict`` takes the P-Q rows collected at one rung of the ladder (plenum,
frame, or urans) and decides PASS / FAIL / INCONCLUSIVE against the published
NF-A12x25 curve, reusing :func:`fansim.validation.pq_shutoff.shutoff_report_from_pq_rows`
for the shut-off estimate so the ladder uses the same honest-vs-proxy method as the
rest of validation.
"""

from __future__ import annotations

from fansim.validation.pq_shutoff import shutoff_report_from_pq_rows

PUB_SHUTOFF_PA = 22.9
PUB_FREE_AIR_CFM = 60.1


def ladder_verdict(
    rows: list[dict],
    *,
    published_shutoff: float = PUB_SHUTOFF_PA,
    published_free: float = PUB_FREE_AIR_CFM,
    shutoff_tol_pa: float = 5.0,
    free_tol: float = 0.10,
) -> dict:
    """Judge one ladder rung's P-Q rows against the published A12x25 curve.

    ``rows`` each have ``back_pa``, ``cfm``, and ``converged``. Returns
    ``{"verdict", "shutoff_pa", "free_air_cfm", "reasons"}`` where ``verdict`` is
    one of ``"PASS"``, ``"FAIL"``, ``"INCONCLUSIVE"``.

    Rules:
      - FAIL if free air is outside tolerance, or shut-off is outside
        ``published_shutoff`` +/- ``shutoff_tol_pa``.
      - INCONCLUSIVE if any loaded row (``back_pa > 0``) with ``cfm > 0`` is
        unconverged, or if no shut-off could be computed at all -- unless a FAIL
        rule already fired, in which case FAIL wins but the reason is still noted.
      - otherwise PASS.
    """
    reasons: list[str] = []

    free_air_row = next((r for r in rows if float(r.get("back_pa", 0.0)) == 0.0), None)
    free_air_cfm = float(free_air_row["cfm"]) if free_air_row is not None else None

    shutoff_report = shutoff_report_from_pq_rows(rows, published_pa=published_shutoff)
    shutoff_pa = shutoff_report.get("shutoff_pa")

    unconverged_loaded = [
        r for r in rows
        if float(r.get("back_pa", 0.0)) > 0.0
        and float(r.get("cfm", 0.0)) > 0.0
        and not r.get("converged", False)
    ]

    is_fail = False

    if free_air_row is None:
        is_fail = True
        reasons.append("no free-air (back_pa=0) row present")
    else:
        lo = published_free * (1.0 - free_tol)
        hi = published_free * (1.0 + free_tol)
        if not (lo <= free_air_cfm <= hi):
            is_fail = True
            reasons.append(
                f"free air {free_air_cfm:.1f} CFM outside tolerance "
                f"[{lo:.1f}, {hi:.1f}] CFM (published {published_free:g})"
            )

    if shutoff_pa is None:
        reasons.append("shut-off could not be computed (insufficient converged points)")
    else:
        lo_p = published_shutoff - shutoff_tol_pa
        hi_p = published_shutoff + shutoff_tol_pa
        if not (lo_p <= shutoff_pa <= hi_p):
            is_fail = True
            reasons.append(
                f"shut-off {shutoff_pa:.1f} Pa outside {published_shutoff:g} "
                f"+/- {shutoff_tol_pa:g} Pa"
            )

    if unconverged_loaded:
        backs = ", ".join(f"{float(r['back_pa']):g}" for r in unconverged_loaded)
        reasons.append(f"loaded point(s) at back_pa={backs} did not converge")

    if is_fail:
        verdict = "FAIL"
    elif unconverged_loaded or shutoff_pa is None:
        verdict = "INCONCLUSIVE"
    else:
        verdict = "PASS"

    return {
        "verdict": verdict,
        "shutoff_pa": shutoff_pa,
        "free_air_cfm": free_air_cfm,
        "reasons": reasons,
    }
