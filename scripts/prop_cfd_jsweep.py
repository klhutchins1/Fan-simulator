"""Prop CFD rung B: advance-ratio sweep on APC SF 9x4.7 (release R2.2b).

Pre-registered: docs/validation/audits/2026-10-17-prop-cfd-fix-prereg.md (rung B), amended in
docs/validation/audits/2026-10-19-prereg-amendments-r17.md section 5 (J points 0.20 / 0.30 / 0.43 at 6029 rpm).
Same geometry, mesh and solver as scripts/audit_prop_cfd.py; only the freestream changes (U = J n D).
Resumable: finished J points are kept. Writes runs/prop_cfd_jsweep/summary.json after every point.

    python scripts/prop_cfd_jsweep.py
    python scripts/prop_cfd_jsweep.py --analyze
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

J_POINTS = (0.20, 0.30, 0.43)
RPM = 6029.0
TABLE = ROOT / "validation" / "reference" / "uiuc_propdb" / "apcsf_9x4.7_kt1035_6029.txt"
CT_TOL = 0.15
OUT = ROOT / "runs" / "prop_cfd_jsweep"


def uiuc_at(j: float, table: Path = TABLE) -> dict:
    """Linear interpolation of UIUC C_T, C_P at advance ratio j."""
    rows = [tuple(map(float, ln.split())) for ln in table.read_text(encoding="utf-8").splitlines()[1:] if ln.strip()]
    for (j0, t0, p0, _), (j1, t1, p1, _) in zip(rows, rows[1:]):
        if j0 <= j <= j1:
            f = (j - j0) / (j1 - j0)
            return {"j": j, "ct": t0 + f * (t1 - t0), "cp": p0 + f * (p1 - p0)}
    raise ValueError(f"J={j} outside the table {rows[0][0]}..{rows[-1][0]}")


def freestream_ms(j: float, rpm: float, diameter_in: float) -> float:
    return float(j) * (float(rpm) / 60.0) * float(diameter_in) * 0.0254


def verdict(points: dict) -> dict:
    """Rung B rules (amended): B1 static-specific / B2 sectional / otherwise report to Claude."""
    errs = {j: p["e_ct"] for j, p in points.items() if p.get("converged")}
    if len(errs) < len(J_POINTS):
        return {"verdict": "INCONCLUSIVE", "why": "a J point is missing or did not converge", "e_ct": errs}
    hi = [errs[j] for j in errs if float(j) >= 0.30]
    if all(abs(e) <= CT_TOL for e in hi):
        return {"verdict": "B1 static-specific", "e_ct": errs}
    if all(e <= -0.30 for e in errs.values()):
        return {"verdict": "B2 sectional", "e_ct": errs}
    return {"verdict": "neither: report to Claude", "e_ct": errs}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--analyze", action="store_true")
    ap.add_argument("--iters", type=int, default=1000)
    ap.add_argument("--procs", type=int, default=16)
    ap.add_argument("--base-cell", type=float, default=0.008)
    ap.add_argument("--out", type=Path, default=OUT, help="results folder (the night queue passes the main checkout's)")
    a = ap.parse_args(argv)
    out = Path(a.out)
    from audit_prop_cfd import _slim, _solved, apc_setup, mesh_for
    from fansim.cfd.runner import image_available
    from fansim.physics.air import R_AIR
    from fansim.propeller.cfd import P_INF, T_INF, evaluate_prop_cfd

    out.mkdir(parents=True, exist_ok=True)
    summ_path = out / "summary.json"
    try:
        summary = json.loads(summ_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        summary = {"points": {}}
    fx, blade, spec = apc_setup()
    mesh = mesh_for(blade, float(a.base_cell))
    rho = P_INF / (R_AIR * T_INF)
    n, d = RPM / 60.0, float(fx["diameter_in"]) * 0.0254
    for j in J_POINTS:
        key = f"{j:.2f}"
        case = out / f"J{key}"
        done = summary["points"].get(key, {}).get("converged") is not None
        if a.analyze or done:
            continue
        if not image_available():
            print("SKIPPED: OpenFOAM image not available", flush=True)
            return 2
        u = freestream_ms(j, RPM, fx["diameter_in"])
        t0 = time.time()
        try:
            res = evaluate_prop_cfd(spec, case, rpm=RPM, params=blade, iters=a.iters, procs=a.procs,
                                    mesh=mesh, bc="freestream", u_freestream=u,
                                    postprocess_only=_solved(case, a.iters))
        except Exception as exc:  # noqa: BLE001 - recorded, not retried
            summary["points"][key] = {"error": f"{type(exc).__name__}: {exc}"[:400], "converged": False}
            summ_path.write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
            print(f"J={key} ERR {exc}", flush=True)
            continue
        ref = uiuc_at(j)
        ct = float(res["thrust_n"]) / (rho * n * n * d ** 4)
        cp = float(res["shaft_power_w"]) / (rho * n ** 3 * d ** 5)
        summary["points"][key] = {"u_freestream": u, "ct": ct, "cp": cp, "uiuc": ref,
                                  "e_ct": ct / ref["ct"] - 1.0, "e_cp": cp / ref["cp"] - 1.0,
                                  "converged": bool(res.get("converged")), "wall_s": time.time() - t0,
                                  "row": _slim(res)}
        summ_path.write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
        p = summary["points"][key]
        print(f"J={key} U={u:.2f} m/s CT {ct:.4f} (UIUC {ref['ct']:.4f}, {p['e_ct']:+.1%}) "
              f"CP {cp:.4f} ({p['e_cp']:+.1%}) conv={p['converged']}", flush=True)
    summary["verdict"] = verdict(summary["points"])
    summ_path.write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    print(json.dumps(summary["verdict"]), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
