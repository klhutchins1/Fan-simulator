"""One-time stamp of ``section_wrap`` on saved axial-fan designs (roadmap 27.4, cylinder sections).

Wrapped sections became the axial-fan default on 2026-10-12, and ``blade_from_flat`` reads a flat
dict with no ``section_wrap`` as "cylinder". Every design saved before that was built and scored
with planar tangent-plane sections, so this stamps them ``"planar"`` and they rebuild exactly as
they were scored. Unlike ``migrate_chord_basis.py`` there is no time cut-off: every record without
the key predates the switch (new saves always carry it).

Touches ``runs/*/cockpit_assess/design_*/design.json`` (``params``) and ``catalog/catalog.db`` axial
rows. Optuna studies are not rewritten: ``trial_attrs.trial_flat`` reads unstamped trials as planar.
Prop runs are skipped (props keep planar sections and never read the key).

Idempotent: records that already carry ``section_wrap`` are left alone.

    uv run python scripts/migrate_section_wrap.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY = "planar"


def _is_prop(run: str) -> bool:
    return "prop" in run.lower()


def _axial(params) -> bool:
    return isinstance(params, dict) and "chord_tip" in params


def migrate_design_jsons(runs: Path, dry: bool) -> int:
    n = 0
    for dj in sorted(runs.glob("*/cockpit_assess/design_*/design.json")):
        if _is_prop(dj.parents[2].name):
            continue
        d = json.loads(dj.read_text(encoding="utf-8"))
        params = d.get("params")
        if not _axial(params) or "section_wrap" in params:
            continue
        print(f"{LEGACY:8s} {dj}")
        n += 1
        if not dry:
            params["section_wrap"] = LEGACY
            dj.write_text(json.dumps(d, indent=2), encoding="utf-8")
    print(f"design.json stamped: {n}")
    return n


def migrate_catalog(db: Path, dry: bool) -> int:
    if not db.is_file():
        return 0
    con = sqlite3.connect(db)
    n = 0
    for design_id, run, raw in con.execute("SELECT design_id, run, params FROM designs").fetchall():
        if _is_prop(str(run or "")):
            continue
        try:
            params = json.loads(raw or "{}")
        except json.JSONDecodeError:
            continue
        if not _axial(params) or "section_wrap" in params:
            continue
        params["section_wrap"] = LEGACY
        n += 1
        if not dry:
            con.execute("UPDATE designs SET params = ? WHERE design_id = ?",
                        (json.dumps(params), design_id))
    if not dry:
        con.commit()
    con.close()
    print(f"catalog rows stamped: {n}")
    return n


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--runs", default=str(ROOT / "runs"))
    ap.add_argument("--catalog", default=str(ROOT / "catalog" / "catalog.db"))
    a = ap.parse_args(argv)
    migrate_design_jsons(Path(a.runs), a.dry_run)
    migrate_catalog(Path(a.catalog), a.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
