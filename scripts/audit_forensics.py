#!/usr/bin/env python3
"""Name the first master commit that changed each part of an audited unit (RV-4).

Method matches ``docs/validation/audits/2026-11-24-audit-drift-forensics.md``:
fingerprint parts are target AST hashes, lib versions, registry fields, and
check-file AST hashes. For each file-backed part, report the newest first-parent
commit after the unit's ledger report that touched the backing path(s).

Usage::

    python scripts/audit_forensics.py fan.bem_prescreen
    python scripts/audit_forensics.py --json cfd.flow_report
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fansim.audit.fingerprint import (
    ROOT as FP_ROOT,
)
from fansim.audit.fingerprint import (
    _checks_source,
    _unit_fields_json,
    fingerprint_target,
    lib_versions,
)
from fansim.audit.registry import REGISTRY_PATH, load_registry
from fansim.audit.status import LEDGER_PATH, load_ledger


@dataclass(frozen=True)
class PartInfo:
    part: str
    head_hash: str
    paths: tuple[str, ...]
    first_commit: str | None
    first_subject: str | None


def target_to_path(target: str, root: Path = FP_ROOT) -> Path | None:
    """Map a registry target to its source file (None for data: targets)."""
    if target.startswith("data:"):
        return root / target[len("data:") :]
    mod = target.split(":", 1)[0]
    path = root.joinpath(*mod.split(".")).with_suffix(".py")
    return path if path.is_file() else None


def part_inventory(unit_id: str, root: Path = FP_ROOT) -> dict[str, tuple[str, tuple[str, ...]]]:
    """Return ``{part_name: (hash, backing_paths)}`` for one unit (pure enough to unit-test)."""
    unit = load_registry(root / "fansim" / "audit" / "registry.yaml").units[unit_id]
    out: dict[str, tuple[str, tuple[str, ...]]] = {}
    for t in sorted(unit.targets):
        p = target_to_path(t, root)
        paths = (str(p.relative_to(root)),) if p is not None else ()
        out[f"target:{t}"] = (fingerprint_target(t, root), paths)
    for k, v in sorted(lib_versions(unit.libs).items()):
        out[f"lib:{k}"] = (v, ())
    unit_blob = _unit_fields_json(unit)
    out["unit"] = (
        hashlib.sha256(unit_blob.encode()).hexdigest()[:16],
        (str(REGISTRY_PATH.relative_to(root)),),
    )
    for c in sorted(unit.checks):
        if c.startswith("ref:"):
            continue
        check_blob = _checks_source(c, root)
        out[f"check:{c}"] = (
            hashlib.sha256(check_blob.encode()).hexdigest()[:16],
            (c,),
        )
    return out


def _git(*args: str, cwd: Path = FP_ROOT) -> str:
    r = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return r.stdout.strip()


def first_commit_touching(
    paths: tuple[str, ...],
    since_commit: str,
    tip: str = "HEAD",
    cwd: Path = FP_ROOT,
) -> tuple[str | None, str | None]:
    """Newest first-parent commit in ``since..tip`` that touches any of ``paths``."""
    if not paths:
        return None, None
    # git log A..B is commits reachable from B not from A; we want after since.
    rng = f"{since_commit}..{tip}"
    line = _git(
        "log",
        "--first-parent",
        "-1",
        "--format=%H\t%s",
        rng,
        "--",
        *paths,
        cwd=cwd,
    )
    if not line:
        return None, None
    sha, _, subj = line.partition("\t")
    return sha[:12], subj or None


def ledger_since_commit(unit_id: str, tip: str = "HEAD", cwd: Path = FP_ROOT) -> str:
    """Best-effort commit where this unit's ledger report was introduced."""
    rec = load_ledger().get("units", {}).get(unit_id) or {}
    report = rec.get("report") or ""
    if report:
        try:
            return _git("log", "-1", "--format=%H", tip, "--", report, cwd=cwd)
        except subprocess.CalledProcessError:
            pass
    # Fall back: first commit that set this unit id in ledger.json
    try:
        return _git(
            "log",
            "-1",
            "--format=%H",
            "-S",
            f'"{unit_id}"',
            tip,
            "--",
            str(LEDGER_PATH.relative_to(cwd)),
            cwd=cwd,
        )
    except subprocess.CalledProcessError:
        return _git("rev-list", "--max-parents=0", tip, cwd=cwd).splitlines()[-1]


def forensics_report(unit_id: str, tip: str = "HEAD", root: Path = FP_ROOT) -> list[PartInfo]:
    since = ledger_since_commit(unit_id, tip=tip, cwd=root)
    inv = part_inventory(unit_id, root=root)
    rows: list[PartInfo] = []
    for part, (h, paths) in sorted(inv.items()):
        commit, subj = first_commit_touching(paths, since_commit=since, tip=tip, cwd=root)
        rows.append(PartInfo(part, h, paths, commit, subj))
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("unit_id", help="registry unit id, e.g. fan.bem_prescreen")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--tip", default="HEAD")
    args = ap.parse_args(argv)

    if args.unit_id not in load_registry().units:
        print(f"unknown unit: {args.unit_id}", file=sys.stderr)
        return 2

    rows = forensics_report(args.unit_id, tip=args.tip)
    if args.json:
        print(json.dumps([asdict(r) for r in rows], indent=2))
        return 0
    print(f"unit {args.unit_id}")
    for r in rows:
        if r.first_commit:
            print(f"  {r.part}: first touch {r.first_commit} — {r.first_subject}")
        elif r.paths:
            print(f"  {r.part}: no path change since ledger write (hash {r.head_hash})")
        else:
            print(f"  {r.part}: env/lib only (hash {r.head_hash})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
