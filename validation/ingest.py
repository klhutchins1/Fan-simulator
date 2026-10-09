"""Physical-validation ingest hooks (plan Phase 6 — deferred; interface only, not yet wired).

The credibility backbone for a real "fan showdown": feed MEASURED CFM / static pressure / noise from
a printed part back in, compare to the simulation, and derive per-quantity calibration factors. No
measurement rig is built yet (no calibrated instruments on hand), so this is the clean interface to
fill later — nothing in the pipeline depends on it. See validation/rig.md for the rig plan.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

# Canonical CSV columns for rig_logger / load_measurements (extras are optional).
CSV_COLUMNS = (
    "rpm",
    "cfm",
    "static_pressure_pa",
    "noise_dba",
    "source",
    "notes",
    "restriction_id",
    "dp_pa",
    "tach_rpm",
    "ambient_c",
    "humidity_pct",
)


@dataclass
class MeasuredPoint:
    """One measured operating point from a physical test (ISO 5801 / AMCA 210-style P-Q, + noise)."""
    rpm: float
    cfm: float | None = None
    static_pressure_pa: float | None = None
    noise_dba: float | None = None
    source: str = ""            # instrument / rig id
    notes: str = ""
    # Low-cost P–Q rig extras (optional; older CSVs omit these)
    restriction_id: str = ""    # e.g. plate / orifice id on the swappable restriction
    dp_pa: float | None = None  # raw differential pressure (Pa) from DP sensor
    tach_rpm: float | None = None  # measured tach if distinct from commanded rpm
    ambient_c: float | None = None
    humidity_pct: float | None = None


@dataclass
class Calibration:
    """Multiplicative sim->reality factors per quantity (reality = factor * simulation)."""
    cfm: float | None = None
    static_pressure: float | None = None
    noise_dba_offset: float | None = None   # dB is additive, so an offset not a factor
    n_points: int = 0
    details: list[dict] = field(default_factory=list)


def load_measurements(path: str | Path) -> list[MeasuredPoint]:
    """Load measured points from a CSV with columns rpm,cfm,static_pressure_pa,noise_dba[,…].

    Optional columns (backward compatible): source, notes, restriction_id, dp_pa, tach_rpm,
    ambient_c, humidity_pct.
    """
    out: list[MeasuredPoint] = []
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            def num(k):
                v = row.get(k, "")
                return float(v) if v not in ("", None) else None
            out.append(MeasuredPoint(
                rpm=float(row["rpm"]), cfm=num("cfm"),
                static_pressure_pa=num("static_pressure_pa"), noise_dba=num("noise_dba"),
                source=row.get("source", "") or "", notes=row.get("notes", "") or "",
                restriction_id=row.get("restriction_id", "") or "",
                dp_pa=num("dp_pa"), tach_rpm=num("tach_rpm"),
                ambient_c=num("ambient_c"), humidity_pct=num("humidity_pct")))
    return out


def calibrate(measured: list[MeasuredPoint], simulated: list[dict]) -> Calibration:
    """Derive calibration factors by pairing measured points with simulated ones (by index).

    ``simulated`` items are dicts with any of cfm/static_pressure_pa/noise_dba. Factors are the mean
    ratio (or dB offset) over the pairs that have both values. Placeholder logic — refine when real
    measurements exist (weighting, per-operating-point factors, uncertainty).
    """
    cal = Calibration(n_points=min(len(measured), len(simulated)))
    ratios = {"cfm": [], "static_pressure": [], "noise": []}
    for m, s in zip(measured, simulated):
        if m.cfm and s.get("cfm"):
            ratios["cfm"].append(m.cfm / s["cfm"])
        if m.static_pressure_pa and s.get("static_pressure_pa"):
            ratios["static_pressure"].append(m.static_pressure_pa / s["static_pressure_pa"])
        if m.noise_dba is not None and s.get("noise_dba") is not None:
            ratios["noise"].append(m.noise_dba - s["noise_dba"])
        cal.details.append({"measured": m.__dict__, "simulated": s})
    mean = lambda xs: sum(xs) / len(xs) if xs else None
    cal.cfm = mean(ratios["cfm"])
    cal.static_pressure = mean(ratios["static_pressure"])
    cal.noise_dba_offset = mean(ratios["noise"])
    return cal
