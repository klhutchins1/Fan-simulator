"""Prop open-air mesh-ladder GCI summary helpers (roadmap §4.3)."""
from __future__ import annotations

import math
from typing import Any

from fansim.analyze.grid_convergence import grid_convergence_index


def parse_cells(s: str) -> list[float]:
    """Parse comma-separated base_cell sizes; return exactly 3 unique values, coarse→fine."""
    parts = [p.strip() for p in str(s).split(",") if p.strip()]
    if len(parts) != 3:
        raise ValueError(f"need exactly 3 cell sizes, got {len(parts)} from {s!r}")
    vals = [float(p) for p in parts]
    if any(not math.isfinite(v) or v <= 0.0 for v in vals):
        raise ValueError(f"cell sizes must be positive finite: {vals}")
    if len(set(vals)) != 3:
        raise ValueError(f"cell sizes must be unique: {vals}")
    return sorted(vals, reverse=True)  # coarse → fine


def build_gci_summary(
    *,
    stl: str,
    rpm: float,
    iters: int,
    levels: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build ladder summary; gci is Roache on thrust_g or null with reason."""
    out: dict[str, Any] = {
        "stl": stl,
        "rpm": float(rpm),
        "iters": int(iters),
        "levels": levels,
        "gci": None,
        "gci_reason": None,
    }
    ok_levels = []
    for lv in levels:
        if not lv.get("ok", False):
            out["gci_reason"] = "incomplete ladder (one or more rungs failed)"
            return out
        try:
            tg = float(lv["thrust_g"])
            h = float(lv["base_cell"])
        except (KeyError, TypeError, ValueError):
            out["gci_reason"] = "incomplete ladder (missing thrust_g or base_cell)"
            return out
        if not math.isfinite(tg) or not math.isfinite(h):
            out["gci_reason"] = "incomplete ladder (non-finite thrust_g or base_cell)"
            return out
        ok_levels.append((h, tg))
    if len(ok_levels) != 3:
        out["gci_reason"] = "incomplete ladder (need exactly 3 levels)"
        return out
    ok_levels.sort(key=lambda t: t[0])  # fine → coarse for Roache (h1<h2<h3)
    (h1, f1), (h2, f2), (h3, f3) = ok_levels
    try:
        r = grid_convergence_index(h1, h2, h3, f1, f2, f3)
    except ValueError as exc:
        out["gci_reason"] = str(exc)
        return out
    out["gci"] = {
        "p": r.p,
        "f_extrapolated": r.f_extrapolated,
        "gci_fine_pct": r.gci_fine_pct,
        "gci_medium_pct": r.gci_medium_pct,
        "asymptotic_ratio": r.asymptotic_ratio,
        "converged": r.converged,
        "metric": "thrust_g",
    }
    return out
