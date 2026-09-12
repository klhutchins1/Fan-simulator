"""Reduce a FluidX3D shut-off time series to settled dead-head static pressure.

The LBM logs ``t_s,step,rho_intake,rho_disch,dp_pa,cfm``. Early chamber fill
overshoots; the published comparison uses the *settled* window (late portion of
the run), not the peak. See ``docs/fluidx3d-setup.md``.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

PUBLISHED_SHUTOFF_PA = 22.9


def settle_shutoff(
    csv: str | Path,
    *,
    settle_from_frac: float = 0.58,
    target_pa: float = PUBLISHED_SHUTOFF_PA,
) -> dict:
    """Mean ΔP and residual CFM over the settle window (default last ~42%).

    ``settle_from_frac`` matches the documented settle-by ~28k of 48k steps.
    """
    path = Path(csv)
    d = np.genfromtxt(path, delimiter=",", names=True)
    if d.dtype.names is None or "dp_pa" not in d.dtype.names:
        raise ValueError(f"shut-off CSV missing dp_pa: {path}")
    n = len(d)
    if n < 2:
        raise ValueError(f"shut-off CSV too short ({n} rows): {path}")
    i0 = int(np.floor(settle_from_frac * n))
    i0 = min(max(i0, 0), n - 1)
    win = d[i0:]
    dp = np.asarray(win["dp_pa"], dtype=float)
    cfm = np.asarray(win["cfm"], dtype=float) if "cfm" in d.dtype.names else np.full(len(win), np.nan)
    mean_pa = float(np.mean(dp))
    std_pa = float(np.std(dp))
    mean_cfm = float(np.mean(cfm)) if np.isfinite(cfm).any() else float("nan")
    err_pct = 100.0 * (mean_pa - target_pa) / target_pa if target_pa else float("nan")
    return {
        "shut_off_pa": round(mean_pa, 2),
        "shut_off_pa_std": round(std_pa, 2),
        "residual_cfm": round(mean_cfm, 2) if np.isfinite(mean_cfm) else None,
        "n_samples": int(n),
        "n_settle": int(len(win)),
        "settle_from_frac": settle_from_frac,
        "peak_pa": round(float(np.max(np.asarray(d["dp_pa"], dtype=float))), 2),
        "target_pa": target_pa,
        "error_pct": round(err_pct, 1),
        "csv": str(path.resolve()),
    }


def shutoff_report(csv: str | Path, **kwargs) -> dict:
    """Alias kept for script symmetry with ``curve_report`` / ``gci_report``."""
    return settle_shutoff(csv, **kwargs)
