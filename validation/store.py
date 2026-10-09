"""Design-linked physical-measurement store — where real print+test results live.

ingest.py has the measurement TYPE and the sim->reality calibration math, but a MeasuredPoint has no
link to WHICH design it measured. This store ties each measurement to the design that produced it
(run/trial/STL/material) alongside that design's SIM PREDICTION, so every record is a self-contained
sim-vs-real comparison. One JSON per design under validation/measurements/. Feeds ingest.calibrate over
the whole store to correct future sim numbers (the digital-twin loop). Nothing here needs an instrument
to EXIST — it's the home results land in the moment any reading is taken.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date as _date
from pathlib import Path

from validation.ingest import Calibration, MeasuredPoint, calibrate

STORE_DIR = Path("validation/measurements")
# quantity -> (measured attr, sim-prediction key). Physical free-air CFM compares to sim free delivery.
_COMPARE = {
    "cfm": ("cfm", "cfm_free"),
    "static_pressure_pa": ("static_pressure_pa", "static_pressure_pa"),
    "noise_dba": ("noise_dba", "noise_dba"),
}


@dataclass
class DesignMeasurement:
    """All physical measurements of one design + the design's sim prediction, for sim-vs-real."""
    design_id: str                                   # stable id, e.g. "opt_extended2_t36"
    run: str = ""
    trial: int | None = None
    stl_path: str = ""
    material: str = ""                                # what it was actually printed in (may differ from spec)
    print_type: str = ""                             # process: FDM, SLA/resin, SLS, etc.
    weight_g: float | None = None                    # measured printed weight (g)
    print_settings: dict = field(default_factory=dict)
    sim: dict = field(default_factory=dict)          # predicted cfm_free/cfm_load/efficiency/noise_*
    measured: list[dict] = field(default_factory=list)  # MeasuredPoint dicts (multi operating points)
    instrument: str = ""
    date: str = ""
    notes: str = ""


def make_design_id(run: str, trial) -> str:
    """Stable id from a run + trial (None trial -> just the run)."""
    run = (run or "design").replace("/", "_").replace("\\", "_")
    return f"{run}_t{int(trial)}" if trial is not None else run


def _path(design_id: str, store_dir: Path) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in design_id)
    return Path(store_dir) / f"{safe}.json"


def load_record(design_id: str, store_dir: Path | str = STORE_DIR) -> DesignMeasurement | None:
    p = _path(design_id, Path(store_dir))
    if not p.exists():
        return None
    return DesignMeasurement(**json.loads(p.read_text()))


def save_record(rec: DesignMeasurement, store_dir: Path | str = STORE_DIR) -> Path:
    store_dir = Path(store_dir)
    store_dir.mkdir(parents=True, exist_ok=True)
    p = _path(rec.design_id, store_dir)
    p.write_text(json.dumps(asdict(rec), indent=2), encoding="utf-8")
    return p


def record_measurement(design_id: str, point: MeasuredPoint, *, run: str = "", trial=None,
                       stl_path: str = "", material: str = "", print_type: str = "",
                       weight_g: float | None = None, sim: dict | None = None,
                       print_settings: dict | None = None, instrument: str = "", notes: str = "",
                       store_dir: Path | str = STORE_DIR) -> DesignMeasurement:
    """Append one measured point to a design's record (creating it if new), then save.

    The design's identity + sim prediction are set on first record and kept; later calls just add
    operating points. Returns the updated record."""
    rec = load_record(design_id, store_dir)
    if rec is None:
        rec = DesignMeasurement(design_id=design_id, run=run, trial=trial, stl_path=stl_path,
                                material=material, print_type=print_type, weight_g=weight_g,
                                sim=sim or {}, print_settings=print_settings or {},
                                instrument=instrument, date=_date.today().isoformat(), notes=notes)
    # let later records fill in the actual-print details if they weren't set the first time
    if material and not rec.material:
        rec.material = material
    if print_type and not rec.print_type:
        rec.print_type = print_type
    if weight_g is not None:
        rec.weight_g = weight_g
    if instrument and not rec.instrument:
        rec.instrument = instrument
    if notes:
        rec.notes = (rec.notes + " | " + notes).strip(" |") if rec.notes else notes
    rec.measured.append({k: v for k, v in asdict(point).items()})
    save_record(rec, store_dir)
    return rec


def load_store(store_dir: Path | str = STORE_DIR) -> list[DesignMeasurement]:
    store_dir = Path(store_dir)
    if not store_dir.exists():
        return []
    out = []
    for p in sorted(store_dir.glob("*.json")):
        try:
            out.append(DesignMeasurement(**json.loads(p.read_text())))
        except Exception:  # noqa: BLE001 - skip a corrupt record
            continue
    return out


def sim_vs_real(rec: DesignMeasurement) -> list[dict]:
    """Per measured point, the delta/ratio of each quantity vs the design's sim prediction."""
    rows = []
    for m in rec.measured:
        row = {"rpm": m.get("rpm"), "source": m.get("source", "")}
        for q, (mk, sk) in _COMPARE.items():
            mv, sv = m.get(mk), rec.sim.get(sk)
            if mv is None or sv is None:
                continue
            if q == "noise_dba":                 # dB is additive
                row[q] = {"measured": mv, "sim": sv, "delta_db": round(mv - sv, 2)}
            else:
                row[q] = {"measured": mv, "sim": sv,
                          "ratio_real_over_sim": round(mv / sv, 4) if sv else None,
                          "pct_error": round(100.0 * (sv - mv) / mv, 1) if mv else None}
        rows.append(row)
    return rows


def calibration_from_store(store_dir: Path | str = STORE_DIR) -> Calibration:
    """Aggregate every measured point across the store into sim->reality calibration factors."""
    measured: list[MeasuredPoint] = []
    simulated: list[dict] = []
    for rec in load_store(store_dir):
        for m in rec.measured:
            measured.append(MeasuredPoint(
                rpm=m.get("rpm", 0.0), cfm=m.get("cfm"),
                static_pressure_pa=m.get("static_pressure_pa"), noise_dba=m.get("noise_dba"),
                source=m.get("source", ""), notes=m.get("notes", ""),
                restriction_id=m.get("restriction_id", "") or "",
                dp_pa=m.get("dp_pa"), tach_rpm=m.get("tach_rpm"),
                ambient_c=m.get("ambient_c"), humidity_pct=m.get("humidity_pct")))
            simulated.append({"cfm": rec.sim.get("cfm_free"),
                              "static_pressure_pa": rec.sim.get("static_pressure_pa"),
                              "noise_dba": rec.sim.get("noise_dba")})
    return calibrate(measured, simulated)
