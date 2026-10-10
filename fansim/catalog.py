"""Unified design catalog — one queryable index over every design the project has produced.

Optimization data lives in per-run islands (runs/<name>/pareto.json, cockpit_assess/, study.db) and
physical measurements live in validation/measurements/. This module AGGREGATES all of it into a single
SQLite catalog keyed by a STABLE design id (`<run>_t<trial>`, the same id the measurement store uses),
so you can ask "every design, with its sim numbers, print files, and any real measurement" in one place.

It is an INDEX, not a migration: it reads the existing stores and never moves the big OpenFOAM cases or
replaces study.db. Rebuild it any time (`build_catalog`) — the source files remain the source of truth.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field, fields
from datetime import date as _date
from pathlib import Path

from validation.store import load_store, make_design_id, sim_vs_real

_ROOT = Path(__file__).resolve().parents[1]
# Project-anchored, not relative to the launch directory (QA docs audit D6, same class as UI-19).
CATALOG_DB = _ROOT / "catalog" / "catalog.db"
REMOVED_LIST = _ROOT / "catalog" / "removed.json"   # design_ids excluded from the catalog (reversible)


def load_removed(path: str | Path = REMOVED_LIST) -> set[str]:
    p = Path(path)
    if not p.exists():
        return set()
    try:
        return set(json.loads(p.read_text()))
    except Exception:  # noqa: BLE001
        return set()


def save_removed(ids, path: str | Path = REMOVED_LIST) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(sorted(set(ids)), indent=2), encoding="utf-8")


@dataclass
class CatalogEntry:
    design_id: str
    run: str = ""
    trial: int | None = None
    source: str = ""              # "optimizer" (pareto finalist) | "user" (assessed) | "measured"
    is_pareto: bool = False
    n_blades: int | None = None
    cfm_free: float | None = None
    cfm_load: float | None = None
    efficiency: float | None = None
    noise: float | None = None
    stl_path: str = ""
    print_dir: str = ""
    has_measurement: bool = False
    measured_cfm: float | None = None
    measured_noise: float | None = None
    cfm_error_pct: float | None = None   # how far sim over/under-reads vs the measurement (if any)
    params: dict = field(default_factory=dict)
    measured: list = field(default_factory=list)
    date_indexed: str = ""
    cfd_stale: bool = False               # recovery: placed/derived design awaiting a fresh CFD
    k: float | None = None                # recovery: system-curve k (Pa at 50 CFM) when scored on load
    hub_models: list = field(default_factory=list)  # fan-spec keys this geometry fits
    fit_status: str = "unplaced"          # fits | unplaced | over_spec
    placed_on: str = ""                   # hub key when explicitly placed onto a non-fit hub
    parent_id: str = ""
    place_op: str = ""


_COLS = ("design_id", "run", "trial", "source", "is_pareto", "n_blades", "cfm_free", "cfm_load",
         "efficiency", "noise", "stl_path", "print_dir", "has_measurement", "measured_cfm",
         "measured_noise", "cfm_error_pct", "params", "measured", "date_indexed",
         "hub_models", "fit_status", "placed_on", "cfd_stale", "parent_id", "place_op")


def _merge(dst: CatalogEntry, src: CatalogEntry) -> None:
    """Fold a second sighting of the same design into ``dst`` (fill blanks, keep pareto/measurement)."""
    dst.is_pareto = dst.is_pareto or src.is_pareto
    for f in ("run", "trial", "source", "n_blades", "cfm_free", "cfm_load", "efficiency", "noise",
              "stl_path", "print_dir"):
        if not getattr(dst, f) and getattr(src, f):
            setattr(dst, f, getattr(src, f))
    if src.params and not dst.params:
        dst.params = src.params


def _from_row(run: str, row: dict, source: str, is_pareto: bool) -> CatalogEntry:
    p = row.get("params", row) if isinstance(row.get("params", row), dict) else row
    if not isinstance(p, dict):
        p = {}
    trial = row.get("trial")
    extra = row.get("extra") if isinstance(row.get("extra"), dict) else {}
    return CatalogEntry(
        design_id=make_design_id(run, trial), run=run, trial=trial, source=source,
        is_pareto=is_pareto, n_blades=p.get("n_blades") or row.get("n_blades"),
        cfm_free=row.get("cfm_free") or (row.get("objectives") or {}).get("cfm_free"),
        cfm_load=row.get("cfm_load") or (row.get("objectives") or {}).get("cfm_load"),
        efficiency=row.get("efficiency") or (row.get("objectives") or {}).get("efficiency"),
        noise=row.get("noise_swl") or extra.get("noise"),
        params=p,
        placed_on=str(extra.get("placed_on") or p.get("placed_on") or ""),
        parent_id=str(extra.get("parent_id") or ""),
        place_op=str(extra.get("place_op") or ""),
        cfd_stale=bool(extra.get("cfd_stale", False)),
    )


def _scan_runs(runs_dir: Path) -> dict[str, CatalogEntry]:
    out: dict[str, CatalogEntry] = {}

    def add(e: CatalogEntry):
        if e.design_id in out:
            _merge(out[e.design_id], e)
        else:
            out[e.design_id] = e

    for run_dir in sorted(p for p in runs_dir.glob("*") if p.is_dir()):
        run = run_dir.name
        pj = run_dir / "pareto.json"
        if pj.exists():
            try:
                data = json.loads(pj.read_text())
                rows = data if isinstance(data, list) else (data.get("designs") or data.get("pareto") or [])
                for row in rows:
                    e = _from_row(run, row, "optimizer", is_pareto=True)
                    pd = run_dir / "print" / (f"trial_{e.trial:04d}" if isinstance(e.trial, int)
                                              else f"trial_{e.trial}")
                    if pd.exists():
                        e.print_dir = str(pd)
                        if (pd / "impeller.stl").exists():
                            e.stl_path = str(pd / "impeller.stl")
                    add(e)
            except Exception:  # noqa: BLE001 - skip a corrupt pareto.json
                pass
        for dj in sorted((run_dir / "cockpit_assess").glob("design_*/design.json")):
            try:
                d = json.loads(dj.read_text())
                e = _from_row(run, d, "user", is_pareto=False)
                stl = dj.parent / "impeller.stl"
                if stl.exists():
                    e.stl_path = str(stl)
                add(e)
            except Exception:  # noqa: BLE001
                pass
    return out


def build_catalog(runs_dir: str | Path = "runs", store_dir: str | Path = "validation/measurements",
                  db: str | Path = CATALOG_DB) -> int:
    """(Re)build the catalog from every run + the measurement store. Returns the design count."""
    entries = _scan_runs(Path(runs_dir))

    for rec in load_store(store_dir):   # fold in physical measurements (create entries if new)
        e = entries.get(rec.design_id)
        if e is None:
            e = CatalogEntry(design_id=rec.design_id, run=rec.run, trial=rec.trial, source="measured",
                             n_blades=rec.sim.get("n_blades"), cfm_free=rec.sim.get("cfm_free"),
                             cfm_load=rec.sim.get("cfm_load"), efficiency=rec.sim.get("efficiency"),
                             stl_path=rec.stl_path, params=rec.sim.get("params", {}))
            entries[e.design_id] = e
        e.has_measurement = True
        e.measured = rec.measured
        if rec.measured:  # measured values come straight from the points (independent of sim coverage)
            last = rec.measured[-1]
            e.measured_cfm = last.get("cfm")
            e.measured_noise = last.get("noise_dba")
        for r in sim_vs_real(rec):  # sim-vs-real gives the error % where both sides have a value
            if "cfm" in r:
                e.cfm_error_pct = r["cfm"].get("pct_error")

    removed = load_removed(REMOVED_LIST)   # reversible dedup exclusions — hidden from the catalog
    for rid in removed:
        entries.pop(rid, None)

    for e in entries.values():
        classify_entry(e)

    db = Path(db)
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db)
    con.execute("DROP TABLE IF EXISTS designs")
    con.execute("""CREATE TABLE designs(
        design_id TEXT PRIMARY KEY, run TEXT, trial INTEGER, source TEXT, is_pareto INTEGER,
        n_blades INTEGER, cfm_free REAL, cfm_load REAL, efficiency REAL, noise REAL,
        stl_path TEXT, print_dir TEXT, has_measurement INTEGER, measured_cfm REAL,
        measured_noise REAL, cfm_error_pct REAL, params TEXT, measured TEXT, date_indexed TEXT,
        hub_models TEXT, fit_status TEXT, placed_on TEXT, cfd_stale INTEGER,
        parent_id TEXT, place_op TEXT)""")
    today = _date.today().isoformat()
    for e in entries.values():
        con.execute(
            f"INSERT INTO designs({','.join(_COLS)}) VALUES({','.join('?' * len(_COLS))})",
            (e.design_id, e.run, e.trial, e.source, int(e.is_pareto), e.n_blades, e.cfm_free,
             e.cfm_load, e.efficiency, e.noise, e.stl_path, e.print_dir, int(e.has_measurement),
             e.measured_cfm, e.measured_noise, e.cfm_error_pct, json.dumps(e.params),
             json.dumps(e.measured), today, json.dumps(list(e.hub_models or [])),
             e.fit_status or "unplaced", e.placed_on or "", int(bool(e.cfd_stale)),
             e.parent_id or "", e.place_op or ""))
    con.commit()
    con.close()
    return len(entries)


def _row_to_entry(r: sqlite3.Row) -> CatalogEntry:
    d = dict(r)
    d["is_pareto"] = bool(d.get("is_pareto", 0))
    d["has_measurement"] = bool(d.get("has_measurement", 0))
    d["cfd_stale"] = bool(d.get("cfd_stale", 0))
    d["params"] = json.loads(d.get("params") or "{}")
    d["measured"] = json.loads(d.get("measured") or "[]")
    hub_raw = d.get("hub_models")
    if isinstance(hub_raw, str):
        d["hub_models"] = json.loads(hub_raw or "[]")
    elif hub_raw is None:
        d["hub_models"] = []
    d.setdefault("fit_status", "unplaced")
    d.setdefault("placed_on", "")
    d.setdefault("parent_id", "")
    d.setdefault("place_op", "")
    for key in ("fit_status", "placed_on", "parent_id", "place_op"):
        if d.get(key) is None:
            d[key] = "" if key != "fit_status" else "unplaced"
    valid = {f.name for f in fields(CatalogEntry)}
    e = CatalogEntry(**{k: v for k, v in d.items() if k in valid})
    # Old catalog.db rows lack hub columns — classify from params so cockpit Results works.
    if e.params:
        classify_entry(e)
    return e


def load_catalog(db: str | Path = CATALOG_DB) -> list[CatalogEntry]:
    db = Path(db)
    if not db.exists():
        return []
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    rows = con.execute("SELECT * FROM designs ORDER BY cfm_free DESC").fetchall()
    con.close()
    return [_row_to_entry(r) for r in rows]


def get_entry(design_id: str, db: str | Path = CATALOG_DB) -> CatalogEntry | None:
    db = Path(db)
    if not db.exists():
        return None
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    r = con.execute("SELECT * FROM designs WHERE design_id=?", (design_id,)).fetchone()
    con.close()
    return _row_to_entry(r) if r else None


def catalog_stats(db: str | Path = CATALOG_DB) -> dict:
    e = load_catalog(db)
    return {
        "designs": len(e),
        "pareto": sum(x.is_pareto for x in e),
        "user_assessed": sum(x.source == "user" for x in e),
        "measured": sum(x.has_measurement for x in e),
        "runs": len({x.run for x in e if x.run}),
    }


def classify_entry(e: CatalogEntry) -> CatalogEntry:
    """Fill ``hub_models`` / ``fit_status`` from geometry vs each registered FanSpec."""
    from fansim.cockpit.placement import nominal_fits_spec
    from fansim.fan_spec import fan_spec_names, get_fan_spec

    p = e.params or {}
    fitted: list[str] = []
    for key in fan_spec_names():
        try:
            if nominal_fits_spec(p, get_fan_spec(key)):
                fitted.append(key)
        except (KeyError, TypeError, ValueError):
            continue
    e.hub_models = fitted
    if e.placed_on:
        # Keep an explicit over_spec stamp when geometry still misses the placed hub.
        if e.placed_on in fitted:
            e.fit_status = "fits"
        elif e.fit_status != "over_spec":
            e.fit_status = "fits" if fitted else "unplaced"
    else:
        e.fit_status = "fits" if fitted else "unplaced"
    return e


def results_for_hub(entries: list[CatalogEntry], hub_key: str) -> list[CatalogEntry]:
    return [e for e in entries if hub_key in (e.hub_models or []) or e.placed_on == hub_key]


def curve_provenance(src: dict | None) -> dict:
    """k / dp_op_pa / q_ref_cfm from a pareto row, extra dict, or ObjectiveResult.raw.

    Absent or None stays None so historical wall-scored rows are not backfilled.
    """
    src = src or {}
    out = {}
    for key in ("k", "dp_op_pa", "q_ref_cfm"):
        val = src.get(key)
        out[key] = float(val) if val is not None else None
    return out
