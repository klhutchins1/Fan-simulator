"""§19.15 / §20.2: BEMT polar A/B (table vs NeuralFoil) on UIUC APC props.

Usage:
    uv run --extra neuralfoil python scripts/audit_bemt_polar_ab.py
"""

from __future__ import annotations

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
CT_RMS_TOL = 0.015


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


def _max_ct_rms(prefix: str) -> float:
    dia = _PROPS[prefix]
    blade = load_uiuc_geometry_blade(UIUC_DIR / f"{prefix}_geom.txt", dia)
    worst = 0.0
    files = sorted(
        f for f in UIUC_DIR.glob(f"{prefix}_*_*.txt")
        if "static" not in f.name and "geom" not in f.name
    )
    for f in files:
        rpm = float(f.stem.split("_")[-1])
        d = dia * 0.0254
        n = rpm / 60.0
        errs = []
        for j, ct, _cp, _eta in load_uiuc_performance(f):
            p = analyze(blade, rpm, v_forward=j * n * d)
            errs.append(p.thrust_n / (RHO_AIR * n**2 * d**4) - ct)
        worst = max(worst, math.sqrt(sum(e * e for e in errs) / len(errs)))
    return worst


def main() -> int:
    backends = ["table"]
    if neuralfoil_available():
        backends.append("neuralfoil")
    else:
        print("NeuralFoil not installed — table only (uv sync --extra neuralfoil)")
    print(f"active default backend: {get_polar_backend()}")
    print(f"{'prop':12} {'backend':10} {'e_CT%':>8} {'e_CP%':>8} {'CT_RMS':>8}  verdict")
    for be in backends:
        set_polar_backend(be)
        for prefix in _PROPS:
            e_ct, e_cp = _static(prefix)
            rms = _max_ct_rms(prefix)
            ok = (
                abs(e_ct) <= CT_STATIC_TOL
                and abs(e_cp) <= CP_STATIC_TOL
                and rms <= CT_RMS_TOL
            )
            print(
                f"{prefix:12} {be:10} {100 * e_ct:+7.1f}% {100 * e_cp:+7.1f}% "
                f"{rms:8.4f}  {'PASS' if ok else 'FAIL'}"
            )
    set_polar_backend("table")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
