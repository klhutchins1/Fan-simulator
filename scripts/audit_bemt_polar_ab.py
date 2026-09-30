"""§19.15 / §20.2: BEMT polar A/B (table vs NeuralFoil) on UIUC APC props.

Usage:
    uv run --extra neuralfoil python scripts/audit_bemt_polar_ab.py
    uv run python scripts/audit_bemt_polar_ab.py --residuals   # SF table diagnostic
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from fansim.propeller.bemt import (  # noqa: E402
    RHO_AIR,
    analyze,
    get_polar_backend,
    set_polar_backend,
)
from fansim.propeller.bemt_catalog import (  # noqa: E402
    UIUC_DIR,
    load_uiuc_geometry_blade,
    load_uiuc_performance,
)
from fansim.propeller.neuralfoil_polars import neuralfoil_available  # noqa: E402

_PROPS = {"apcsf_9x4.7": 9.0, "apce_9x6": 9.0}
CT_STATIC_TOL = 0.15
CP_STATIC_TOL = 0.20
CT_RMS_TOL = 0.015       # APC E 9x6
CT_RMS_TOL_SF = 0.020    # APC SF 9x4.7 re-registered 2026-09-30 (§20.2)


def _static(prefix: str) -> tuple[float, float]:
    dia = _PROPS[prefix]
    blade = load_uiuc_geometry_blade(UIUC_DIR / f"{prefix}_geom.txt", dia)
    rows = load_uiuc_performance(next(UIUC_DIR.glob(f"{prefix}_static_*.txt")))
    rpm, ct, cp = min(rows, key=lambda r: abs(r[0] - 6000.0))
    d = dia * 0.0254
    n = rpm / 60.0
    p = analyze(blade, rpm)
    return p.thrust_n / (RHO_AIR * n**2 * d**4) / ct - 1.0, (
        p.power_w / (RHO_AIR * n**3 * d**5) / cp - 1.0
    )


def _sweep_files(prefix: str) -> list[Path]:
    return sorted(
        f for f in UIUC_DIR.glob(f"{prefix}_*_*.txt")
        if "static" not in f.name and "geom" not in f.name
    )


def _ct_errors(prefix: str, path: Path) -> list[tuple[float, float, float, float]]:
    """Return list of (J, CT_meas, CT_bemt, e_CT) for one sweep file."""
    dia = _PROPS[prefix]
    blade = load_uiuc_geometry_blade(UIUC_DIR / f"{prefix}_geom.txt", dia)
    rpm = float(path.stem.split("_")[-1])
    d = dia * 0.0254
    n = rpm / 60.0
    out: list[tuple[float, float, float, float]] = []
    for j, ct, _cp, _eta in load_uiuc_performance(path):
        p = analyze(blade, rpm, v_forward=j * n * d)
        ct_b = p.thrust_n / (RHO_AIR * n**2 * d**4)
        out.append((float(j), float(ct), float(ct_b), ct_b - float(ct)))
    return out


def _rms(errs: list[float]) -> float:
    if not errs:
        return 0.0
    return math.sqrt(sum(e * e for e in errs) / len(errs))


def _attached_mask(rows: list[tuple[float, float, float, float]]) -> list[bool]:
    """True while measured CT stays > 0 (stop at first non-positive measured CT)."""
    mask: list[bool] = []
    producing = True
    for _j, ct_m, _ct_b, _e in rows:
        if ct_m <= 0.0:
            producing = False
        mask.append(producing and ct_m > 0.0)
    return mask


def _max_ct_rms(prefix: str, *, attached_only: bool = False) -> float:
    worst = 0.0
    for f in _sweep_files(prefix):
        rows = _ct_errors(prefix, f)
        mask = _attached_mask(rows) if attached_only else [True] * len(rows)
        errs = [e for (_j, _m, _b, e), keep in zip(rows, mask) if keep]
        if errs:
            worst = max(worst, _rms(errs))
    return worst


def print_residuals(prefix: str = "apcsf_9x4.7") -> None:
    """Phase-1 diagnostic: per-J residuals + full vs attached RMS (current backend)."""
    print(f"\n=== residuals {prefix} backend={get_polar_backend()} ===")
    full_worst = att_worst = 0.0
    windmill_sse = attached_sse = 0.0
    n_wm = n_att = 0
    for f in _sweep_files(prefix):
        rows = _ct_errors(prefix, f)
        mask = _attached_mask(rows)
        full = _rms([e for *_rest, e in rows])
        att_errs = [e for (_r, keep) in zip(rows, mask) if keep for e in (_r[3],)]
        att = _rms(att_errs)
        full_worst = max(full_worst, full)
        att_worst = max(att_worst, att)
        print(f"\n{f.name}  RMS_full={full:.4f}  RMS_attached={att:.4f}")
        print(f"  {'J':>6} {'CT_meas':>9} {'CT_bemt':>9} {'e_CT':>9}  flag")
        for (j, ct_m, ct_b, e), keep in zip(rows, mask):
            flag = "attached" if keep else ("windmill" if ct_m < 0 else "zero+")
            print(f"  {j:6.3f} {ct_m:9.4f} {ct_b:9.4f} {e:9.4f}  {flag}")
            if keep:
                attached_sse += e * e
                n_att += 1
            elif ct_m < 0.0:
                windmill_sse += e * e
                n_wm += 1
    print(
        f"\nsummary max RMS_full={full_worst:.4f}  max RMS_attached={att_worst:.4f}  "
        f"tol={CT_RMS_TOL}  n_attached={n_att} n_windmill={n_wm}"
    )
    if n_att + n_wm:
        print(
            f"SSE share attached={attached_sse:.5f} windmill={windmill_sse:.5f} "
            f"({100.0 * windmill_sse / max(attached_sse + windmill_sse, 1e-18):.1f}% windmill)"
        )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--residuals",
        action="store_true",
        help="Print per-J SF residuals (full vs attached RMS) for the active backends",
    )
    args = ap.parse_args(argv)

    backends = ["table"]
    if neuralfoil_available():
        backends.append("neuralfoil")
    else:
        print("NeuralFoil not installed — table only (uv sync --extra neuralfoil)")
    print(f"active default backend: {get_polar_backend()}")

    if args.residuals:
        for be in backends:
            set_polar_backend(be)
            print_residuals("apcsf_9x4.7")
        return 0

    print(f"{'prop':12} {'backend':10} {'e_CT%':>8} {'e_CP%':>8} {'CT_RMS':>8} {'attRMS':>8}  verdict")
    for be in backends:
        set_polar_backend(be)
        for prefix in _PROPS:
            e_ct, e_cp = _static(prefix)
            rms = _max_ct_rms(prefix)
            att = _max_ct_rms(prefix, attached_only=True)
            ok_ct = abs(e_ct) <= CT_STATIC_TOL
            ok_cp = abs(e_cp) <= CP_STATIC_TOL
            ok_rms = rms <= (CT_RMS_TOL_SF if prefix.startswith("apcsf") else CT_RMS_TOL)
            ok_att = att <= (CT_RMS_TOL_SF if prefix.startswith("apcsf") else CT_RMS_TOL)
            verdict = "PASS" if (ok_ct and ok_cp and ok_rms) else "FAIL"
            extra = ""
            if not ok_rms and ok_att:
                extra = " (attached PASS)"
            print(
                f"{prefix:12} {be:10} {100 * e_ct:8.1f} {100 * e_cp:8.1f} "
                f"{rms:8.4f} {att:8.4f}  {verdict}{extra}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
