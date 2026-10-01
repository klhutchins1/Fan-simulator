"""Re-score the saved AXIAL fan designs at the current CFD / geometry version (roadmap 19.8).

Stored axial scores predate the rotor-direction fix, MRF fitting, the sealed ring domain
(``CFD_VERSION`` 5), the builder airfoil LE fix and the v2 Stock recipe, so they are stale.
This script enumerates every saved axial design, rebuilds its ``BladeParams`` from the stored
params, and re-runs ``evaluate_candidate`` (via the crash-isolated subprocess wrapper the
cockpit Assess uses) at the current version.

Sources (deduped by a hash of the reconstructed BladeParams):
  * ``catalog/catalog.db`` ``designs`` rows whose run is not a prop run (params column; scoring
    settings are read from the ``design.json`` next to the row's STL when present),
  * COMPLETE trials of ``runs/opt_run1/study.db`` and ``runs/cockpit_opt_20260917-105753/study.db``.
    Trials whose stored score was a rejection (``feasible`` False) are listed and skipped unless
    ``--include-infeasible`` is given: their "old score" is a gate reject, not a CFD number.

Usage:
    uv run python scripts/rescore_designs.py --list
    uv run python scripts/rescore_designs.py --pilot     # ONE real CFD evaluation + time estimate
    uv run python scripts/rescore_designs.py             # re-score everything (resumable)

Results are written to ``docs/validation/rescore_19_8.json`` after EVERY design (old and new
values are both kept). Catalog rows are updated only for successful (feasible) re-scores; rows
are never deleted, and a ``cfd_version`` column is added to ``designs`` if it is missing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import time
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fansim.cfd.metrics import CFD_VERSION  # noqa: E402
from fansim.optimize.trial_attrs import trial_flat  # noqa: E402
from fansim.cfd.timing import format_eta  # noqa: E402
from fansim.geometry.features import Features  # noqa: E402
from fansim.optimize.search_space import blade_from_flat  # noqa: E402

DEFAULT_CATALOG = ROOT / "catalog" / "catalog.db"
DEFAULT_STUDY_DIRS = (
    ROOT / "runs" / "opt_run1",
    ROOT / "runs" / "cockpit_opt_20260917-105753",
)
DEFAULT_OUT = ROOT / "docs" / "validation" / "rescore_19_8.json"
DEFAULT_WORKROOT = ROOT / "runs" / "rescore_19_8"
MARGIN = 1.2
INFEASIBLE_SENTINEL = -1.0e5   # objective values at/below this are gate rejects, not scores

# Optimizer / cockpit-Assess defaults (used when the original settings were not recorded).
DEFAULT_SETTINGS = {
    "preset": "case", "load_pa": None, "refine_op": False, "material": "PETG",
    "wall_ks": False, "procs": 8, "base_cell": 0.006, "iters": 500, "rpm": None,
    "fan_model": "a12x25", "stator": "frame",
}
_FEATURE_KEYS = {f.name for f in fields(Features)}


@dataclass
class Candidate:
    design_id: str
    source: str                       # catalog source ("user"/"optimizer") or "study"
    origin: str                       # "catalog" | "study:<dir>#<trial>"
    flat: dict = field(default_factory=dict)
    old: dict = field(default_factory=dict)   # cfm_free/cfm_load/efficiency/cfd_version
    settings: dict = field(default_factory=dict)
    settings_source: str = "defaults"
    reconstructable: bool = True
    skip_reason: str = ""
    params_hash: str = ""
    aliases: list = field(default_factory=list)   # other design_ids with identical params


# --------------------------------------------------------------------------- reconstruction
def features_from_flat(flat: dict) -> Features:
    kw = {k: flat[k] for k in _FEATURE_KEYS if k in flat and flat[k] is not None}
    return Features(**kw)


def reconstruct(flat: dict):
    """(BladeParams, params_hash) from a flat param dict. Raises on missing/invalid params."""
    if not flat:
        raise ValueError("no params stored")
    bp = blade_from_flat(flat, features_from_flat(flat))
    return bp, params_hash(bp)


def params_hash(bp) -> str:
    def norm(o):
        if isinstance(o, float):
            return round(o, 6)
        if isinstance(o, dict):
            return {k: norm(v) for k, v in sorted(o.items())}
        if isinstance(o, (list, tuple)):
            return [norm(v) for v in o]
        return o

    d = asdict(bp)
    # Legacy loft-chord designs keep the hash they had before ``chord_basis`` existed.
    if d.get("chord_basis") == "loft":
        d.pop("chord_basis")
    blob = json.dumps(norm(d), sort_keys=True, default=str)
    return hashlib.sha1(blob.encode()).hexdigest()[:16]


def is_prop_run(run: str) -> bool:
    r = (run or "").lower()
    return r.startswith("cockpit_prop") or "_prop_" in r or r.startswith("prop_")


def _settings_from_extra(extra: dict) -> tuple[dict, str]:
    """Scoring settings recorded by cockpit Assess (extra of design.json), else defaults."""
    s = dict(DEFAULT_SETTINGS)
    if not extra:
        return s, "defaults"
    recorded = []
    if extra.get("preset"):
        s["preset"] = str(extra["preset"])
        recorded.append("preset")
    if extra.get("load_pa") is not None:
        s["load_pa"] = float(extra["load_pa"])
        recorded.append("load_pa")
    if "refine_op" in extra:
        s["refine_op"] = bool(extra["refine_op"])
        recorded.append("refine_op")
    if extra.get("material"):
        s["material"] = str(extra["material"])
        recorded.append("material")
    if extra.get("fan_model"):
        s["fan_model"] = str(extra["fan_model"])
        recorded.append("fan_model")
    if extra.get("wall_ks_mm"):
        s["wall_ks"] = True
        recorded.append("wall_ks")
    if not recorded:
        return s, "defaults"
    return s, "design.json extra (" + ",".join(recorded) + "); rest = defaults"


# --------------------------------------------------------------------------- enumeration
def _read_design_json(stl_path: str, root: Path) -> dict:
    if not stl_path:
        return {}
    p = Path(stl_path)
    if not p.is_absolute():
        p = root / p
    dj = p.parent / "design.json"
    try:
        return json.loads(dj.read_text(encoding="utf-8")).get("extra", {}) or {}
    except Exception:  # noqa: BLE001
        return {}


def enumerate_catalog(db: Path, root: Path = ROOT) -> list[Candidate]:
    out: list[Candidate] = []
    if not Path(db).exists():
        return out
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    cols = {r[1] for r in con.execute("PRAGMA table_info(designs)")}
    rows = con.execute("SELECT * FROM designs ORDER BY design_id").fetchall()
    con.close()
    for r in rows:
        d = dict(r)
        if is_prop_run(d.get("run") or ""):
            continue
        extra = _read_design_json(d.get("stl_path") or "", root)
        settings, ssrc = _settings_from_extra(extra)
        old_ver = d.get("cfd_version") if "cfd_version" in cols else None
        if old_ver is None:
            old_ver = extra.get("cfd_version")
        c = Candidate(
            design_id=d["design_id"], source=d.get("source") or "", origin="catalog",
            old={"cfm_free": d.get("cfm_free"), "cfm_load": d.get("cfm_load"),
                 "efficiency": d.get("efficiency"), "cfd_version": old_ver},
            settings=settings, settings_source=ssrc)
        try:
            c.flat = json.loads(d.get("params") or "{}")
        except Exception:  # noqa: BLE001
            c.flat = {}
        out.append(c)
    return out


def enumerate_studies(study_dirs, include_infeasible: bool = False) -> list[Candidate]:
    import optuna

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    out: list[Candidate] = []
    for sd in study_dirs:
        sd = Path(sd)
        dbp = sd / "study.db"
        if not dbp.exists():
            continue
        storage = f"sqlite:///{dbp.as_posix()}"
        for name in optuna.get_all_study_names(storage=storage):
            study = optuna.load_study(study_name=name, storage=storage)
            for t in study.trials:
                if t.state != optuna.trial.TrialState.COMPLETE:
                    continue
                vals = list(t.values or [])
                feasible = bool(t.user_attrs.get("feasible", False)) and all(
                    v > INFEASIBLE_SENTINEL for v in vals[:3])
                flat = trial_flat(t)
                for k in ("shroud_thick_mm", "sickle_mm"):
                    if k not in flat and t.user_attrs.get(k) is not None:
                        flat[k] = t.user_attrs[k]
                settings = dict(DEFAULT_SETTINGS)
                if flat.get("rpm") is not None:
                    settings["rpm"] = float(flat["rpm"])
                c = Candidate(
                    design_id=f"{sd.name}_study_t{t.number}", source="study",
                    origin=f"study:{sd.name}#{t.number}", flat=flat,
                    old={"cfm_free": vals[0] if feasible and vals else None,
                         "cfm_load": vals[1] if feasible and len(vals) > 1 else None,
                         "efficiency": vals[2] if feasible and len(vals) > 2 else None,
                         "cfd_version": t.user_attrs.get("cfd_version")},
                    settings=settings,
                    settings_source="optimizer defaults (study settings not recorded)")
                if not feasible and not include_infeasible:
                    c.reconstructable = False
                    c.skip_reason = ("original score was a rejection: "
                                     f"{str(t.user_attrs.get('reason', ''))[:80]}")
                    out.append(c)
                    continue
                if "stator_n_extra" in flat or "stator_stagger_deg" in flat:
                    c.reconstructable = False
                    c.skip_reason = "stator/stack mode not recorded in the study (not guessed)"
                out.append(c)
    return out


def dedupe(cands: list[Candidate]) -> list[Candidate]:
    """Reconstruct params, mark failures, and merge identical params into the first sighting."""
    seen: dict[str, Candidate] = {}
    out: list[Candidate] = []
    for c in cands:
        if c.reconstructable:
            try:
                _, c.params_hash = reconstruct(c.flat)
            except Exception as exc:  # noqa: BLE001
                c.reconstructable = False
                c.skip_reason = f"params not reconstructable: {type(exc).__name__}: {exc}"
        if c.reconstructable and c.params_hash:
            first = seen.get(c.params_hash)
            if first is not None:
                first.aliases.append(c.design_id)
                continue
            seen[c.params_hash] = c
        out.append(c)
    return out


def enumerate_all(catalog_db: Path = DEFAULT_CATALOG, study_dirs=DEFAULT_STUDY_DIRS,
                  include_infeasible: bool = False, root: Path = ROOT) -> list[Candidate]:
    cands = enumerate_catalog(catalog_db, root) + enumerate_studies(study_dirs, include_infeasible)
    return dedupe(cands)


# --------------------------------------------------------------------------- scoring
def _f(v):
    return None if v is None else round(float(v), 3)


def score_candidate(c: Candidate, workroot: Path):
    """Run the real CFD evaluation. Returns (ObjectiveResult, wall_s, cells)."""
    from fansim.cfd.timing import mesh_cells
    from fansim.fan_spec import get_fan_spec
    from fansim.optimize.isolated_eval import evaluate_candidate_isolated
    from fansim.optimize.presets import assess_load

    s = c.settings
    load_pa = float(s["load_pa"]) if s.get("load_pa") is not None else assess_load(s["preset"])[0]
    ks = None
    if s.get("wall_ks"):
        from fansim.cfd.wall_roughness import FDM_WALL_KS_MM
        ks = FDM_WALL_KS_MM
    bp = blade_from_flat(c.flat, features_from_flat(c.flat))
    workdir = workroot / c.design_id
    t0 = time.time()
    res = evaluate_candidate_isolated(
        c.flat, bp.features, workdir, spec=get_fan_spec(s["fan_model"]),
        procs=int(s["procs"]), base_cell=float(s["base_cell"]), iters=int(s["iters"]),
        load_pa=load_pa, refine_op=bool(s["refine_op"]), material=str(s["material"]),
        wall_ks_mm=ks)
    wall_s = time.time() - t0
    return res, wall_s, mesh_cells(workdir)


def result_record(c: Candidate, res, wall_s: float, pilot: bool = False,
                  cells: int | None = None) -> dict:
    ok = bool(res.feasible)
    raw = res.raw or {}
    s = c.settings
    iters = int(s.get("iters") or 0)
    n_solves = 2 + (1 if s.get("refine_op") else 0)  # free + load (+ optional refine)
    sec_per_iter = (wall_s / (n_solves * iters)) if iters > 0 else None
    return {
        "design_id": c.design_id, "aliases": list(c.aliases), "origin": c.origin,
        "params_hash": c.params_hash, "status": "ok" if ok else "infeasible",
        "old": c.old,
        "new": {"cfm_free": _f(res.cfm_free) if ok else None,
                "cfm_load": _f(res.cfm_load) if ok else None,
                "efficiency": _f(res.efficiency) if ok else None,
                "actual_rpm": _f(res.actual_rpm) if ok else None},
        "cfd_version": CFD_VERSION, "sanity_status": raw.get("sanity_status"),
        "converged": raw.get("converged"), "reason": res.reason,
        "settings": c.settings, "settings_source": c.settings_source,
        "cells": cells,
        "wall_s": round(wall_s, 1),
        "sec_per_iter": round(sec_per_iter, 4) if sec_per_iter is not None else None,
        "pilot": pilot,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "catalog_updated": False,
    }


def load_results(path: Path) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {"cfd_version": CFD_VERSION, "designs": {}}


def write_results(path: Path, data: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data["cfd_version"] = CFD_VERSION
    data["updated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def update_catalog(db: Path, design_ids, new: dict) -> int:
    """Write new metrics + cfd_version to catalog rows (never deletes). Returns rows updated."""
    con = sqlite3.connect(db)
    cols = {r[1] for r in con.execute("PRAGMA table_info(designs)")}
    if "cfd_version" not in cols:
        con.execute("ALTER TABLE designs ADD COLUMN cfd_version INTEGER")
    n = 0
    for did in design_ids:
        cur = con.execute(
            "UPDATE designs SET cfm_free=?, cfm_load=?, efficiency=?, cfd_version=?, cfd_stale=0 "
            "WHERE design_id=?",
            (new["cfm_free"], new["cfm_load"], new["efficiency"], CFD_VERSION, did))
        n += cur.rowcount
    con.commit()
    con.close()
    return n


# --------------------------------------------------------------------------- CLI
def _fmt(v, w=8):
    return f"{v:{w}.1f}" if isinstance(v, (int, float)) else f"{'-':>{w}}"


def print_list(cands: list[Candidate]) -> None:
    print(f"current CFD_VERSION = {CFD_VERSION}\n")
    print(f"{'design_id':<40} {'source':<9} {'cfm_free':>8} {'cfm_load':>8} {'eff%':>8} "
          f"{'old_ver':>7}  reconstructable")
    for c in cands:
        o = c.old
        ver = o.get("cfd_version")
        rec = "yes" if c.reconstructable else f"NO - {c.skip_reason}"
        extra = f"  (same params: {', '.join(c.aliases)})" if c.aliases else ""
        print(f"{c.design_id:<40} {c.source:<9} {_fmt(o.get('cfm_free'))} {_fmt(o.get('cfm_load'))} "
              f"{_fmt(o.get('efficiency'))} {('unstamped' if ver is None else str(ver)):>7}  "
              f"{rec}{extra}")
    good = [c for c in cands if c.reconstructable]
    print(f"\n{len(cands)} unique designs: {len(good)} reconstructable, "
          f"{len(cands) - len(good)} skipped")


def _apply(c: Candidate, rec: dict, catalog_db: Path, apply_catalog: bool) -> None:
    if apply_catalog and rec["status"] == "ok" and Path(catalog_db).exists():
        ids = [c.design_id, *c.aliases] if c.origin == "catalog" else list(c.aliases)
        if c.origin == "catalog" or ids:
            n = update_catalog(catalog_db, ids, rec["new"])
            rec["catalog_updated"] = n > 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--list", action="store_true", help="print the design table (no CFD)")
    ap.add_argument("--pilot", action="store_true", help="re-score ONE design, time it, estimate all")
    ap.add_argument("--include-infeasible", action="store_true",
                    help="also re-score study trials whose old score was a gate rejection")
    ap.add_argument("--force", action="store_true", help="re-run designs already scored OK")
    ap.add_argument("--catalog", default=str(DEFAULT_CATALOG))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--workroot", default=str(DEFAULT_WORKROOT))
    args = ap.parse_args(argv)

    catalog_db, out_path, workroot = Path(args.catalog), Path(args.out), Path(args.workroot)
    cands = enumerate_all(catalog_db, DEFAULT_STUDY_DIRS, args.include_infeasible)
    if args.list:
        print_list(cands)
        return 0
    todo = [c for c in cands if c.reconstructable]
    if not todo:
        print("nothing to re-score")
        return 1
    data = load_results(out_path)

    if args.pilot:
        c = todo[0]
        print(f"pilot: {c.design_id} (settings: {c.settings_source})", flush=True)
        res, wall, cells = score_candidate(c, workroot)
        rec = result_record(c, res, wall, pilot=True, cells=cells)
        data["designs"][c.design_id] = rec
        write_results(out_path, data)
        est = wall * len(todo) * MARGIN
        print(json.dumps({k: rec[k] for k in ("old", "new", "status", "sanity_status", "converged",
                                              "reason", "cells", "wall_s", "sec_per_iter")}, indent=2))
        print(f"\nmeasured wall time per design: {format_eta(wall)} ({wall:.0f} s)")
        print(f"estimate for all {len(todo)} designs (x{MARGIN} margin): {format_eta(est)}")
        return 0

    for i, c in enumerate(todo, 1):
        prev = data["designs"].get(c.design_id)
        if prev and prev.get("status") == "ok" and not args.force:
            print(f"[{i}/{len(todo)}] {c.design_id}: already scored, skipping")
            if not prev.get("catalog_updated"):
                _apply(c, prev, catalog_db, True)
                write_results(out_path, data)
            continue
        print(f"[{i}/{len(todo)}] {c.design_id} ...", flush=True)
        try:
            res, wall, cells = score_candidate(c, workroot)
            rec = result_record(c, res, wall, cells=cells)
        except Exception as exc:  # noqa: BLE001 - one bad design must not stop the batch
            rec = {"design_id": c.design_id, "aliases": list(c.aliases), "origin": c.origin,
                   "params_hash": c.params_hash, "status": "error", "old": c.old, "new": None,
                   "cfd_version": CFD_VERSION, "sanity_status": None, "converged": None,
                   "reason": f"{type(exc).__name__}: {exc}", "settings": c.settings,
                   "cells": None, "wall_s": None, "sec_per_iter": None,
                   "settings_source": c.settings_source, "catalog_updated": False,
                   "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        _apply(c, rec, catalog_db, True)
        data["designs"][c.design_id] = rec
        write_results(out_path, data)
        print(f"    {rec['status']}: new={rec['new']} sanity={rec['sanity_status']} "
              f"converged={rec['converged']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
