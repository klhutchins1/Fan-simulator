"""One-time stamp of ``chord_basis`` on saved axial-fan designs (§19.7 follow-up).

Commit 37728b9 (2026-09-30 11:42 -0600) changed station ``chord`` from the loft chord to the
measured cylinder-cut chord, and ``blade_from_flat`` now reads a flat dict with no
``chord_basis`` as "measured". Designs saved before that hold loft chords, so this stamps them
``"loft"`` and they rebuild exactly as they were scored. Newer records get ``"measured"``.

Touches:
  * ``runs/*/cockpit_assess/design_*/design.json`` (``params``), classified by file mtime;
  * ``catalog/catalog.db`` axial rows, classified from the matching design.json when there is
    one, else by ``CHORD_BASIS_CUTOFF`` against nothing (= legacy "loft").
Optuna studies are not rewritten: ``fansim.optimize.trial_attrs.trial_flat`` classifies each
trial by its stamp or start time. Prop runs are skipped on purpose: their scores come from BEMT,
which already reads station chord as the physical chord.

Idempotent: records that already carry ``chord_basis`` are left alone.

    uv run python scripts/migrate_chord_basis.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fansim.optimize.trial_attrs import chord_basis_at  # noqa: E402


def _is_prop(run: str) -> bool:
    return "prop" in run.lower()


def _mtime(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)


def migrate_design_jsons(runs: Path, dry: bool) -> dict[tuple[str, str], str]:
    """Stamp design.json files; return {(run, trial) -> basis} for the catalog pass."""
    seen: dict[tuple[str, str], str] = {}
    for dj in sorted(runs.glob("*/cockpit_assess/design_*/design.json")):
        run = dj.parents[2].name
        if _is_prop(run):
            continue
        d = json.loads(dj.read_text(encoding="utf-8"))
        params = d.get("params")
        if not isinstance(params, dict) or "chord_tip" not in params:
            continue
        basis = params.get("chord_basis") or chord_basis_at(_mtime(dj))
        seen[(run, str(d.get("trial")))] = basis
        if "chord_basis" in params:
            continue
        print(f"{basis:8s} {dj.relative_to(ROOT)}")
        if not dry:
            params["chord_basis"] = basis
            dj.write_text(json.dumps(d, indent=2), encoding="utf-8")
    return seen


def migrate_catalog(db: Path, seen: dict[tuple[str, str], str], dry: bool) -> None:
    if not db.is_file():
        return
    con = sqlite3.connect(db)
    rows = con.execute("SELECT design_id, run, trial, params FROM designs").fetchall()
    n = 0
    for design_id, run, trial, raw in rows:
        if _is_prop(str(run or "")):
            continue
        try:
            params = json.loads(raw or "{}")
        except json.JSONDecodeError:
            continue
        if not isinstance(params, dict) or "chord_tip" not in params or "chord_basis" in params:
            continue
        basis = seen.get((str(run), str(trial)), "loft")
        print(f"{basis:8s} catalog {design_id}")
        params["chord_basis"] = basis
        n += 1
        if not dry:
            con.execute("UPDATE designs SET params = ? WHERE design_id = ?",
                        (json.dumps(params), design_id))
    if not dry:
        con.commit()
    con.close()
    print(f"catalog rows stamped: {n}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--runs", default=str(ROOT / "runs"))
    ap.add_argument("--catalog", default=str(ROOT / "catalog" / "catalog.db"))
    a = ap.parse_args(argv)
    seen = migrate_design_jsons(Path(a.runs), a.dry_run)
    migrate_catalog(Path(a.catalog), seen, a.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
