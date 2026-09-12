# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Reclaim disk by pruning the heavy, regenerable internals of finished OpenFOAM cases.

Each solved case keeps ~85 MB of mesh + decomposed processor copies + solver logs — but those are
fully REGENERABLE from the impeller STL, and the actual results already live in study.db / result.json
/ the unified catalog. So once a run is done, the case internals are safe to delete: the numbers stay,
the STL stays (so print/preview/catalog still work), and the case can be re-meshed + re-run any time.

PRESERVED (never touched): impeller.stl, result.json, design.json, the case system/ + constant/ dicts,
postProcessing/ (tiny raw FO output), and every run-level file (pareto.json, study.db, print/).
PRUNED: constant/polyMesh (the mesh), processor*/ (decomposed copies), logs/, dynamicCode/.

Dry-run by default everywhere — deletion only happens when the caller passes apply=True.
"""

from __future__ import annotations

import shutil
from pathlib import Path

# Regenerable case internals, relative to a case dir. processor* dirs are matched by glob separately.
PRUNABLE_RELPATHS = ("constant/polyMesh", "constant/extendedFeatureEdgeMesh", "logs", "dynamicCode")


def is_case_dir(d: Path) -> bool:
    """An OpenFOAM case = a dir with both system/ and constant/ (avoids touching anything else)."""
    return (d / "system").is_dir() and (d / "constant").is_dir()


def _dir_bytes(p: Path) -> int:
    if p.is_file():
        try:
            return p.stat().st_size
        except OSError:
            return 0
    total = 0
    for f in p.rglob("*"):
        if f.is_file():
            try:
                total += f.stat().st_size
            except OSError:
                pass
    return total


def prunable_targets(case_dir: Path) -> list[Path]:
    """The regenerable paths inside one case that are safe to delete (only those that exist)."""
    targets = [case_dir / rel for rel in PRUNABLE_RELPATHS]
    targets += sorted(case_dir.glob("processor*"))
    return [t for t in targets if t.exists()]


def find_cases(run_dir: Path) -> list[Path]:
    """Every OpenFOAM case ANYWHERE under a run — trials/, cockpit_assess/, run-level (repro/validate
    runs), or named variant subdirs (e.g. stall_study/tubercles_bp3). A case never nests inside another
    (no dir has two system/+constant/ signatures), so a simple recursive scan is exact."""
    if is_case_dir(run_dir):
        return [run_dir]
    return [d for d in run_dir.rglob("*") if d.is_dir() and is_case_dir(d)]


def scan_run(run_dir: Path) -> dict:
    """Find every case under a run and total its reclaimable bytes."""
    targets, size = [], 0
    cases = find_cases(run_dir)
    for case in cases:
        for t in prunable_targets(case):
            targets.append(t)
            size += _dir_bytes(t)
    return {"run": run_dir.name, "cases": len(cases), "bytes": size, "targets": targets}


def scan_all(runs_dir: str | Path = "runs", only: str | None = None) -> list[dict]:
    runs_dir = Path(runs_dir)
    out = []
    for run_dir in sorted(p for p in runs_dir.glob("*") if p.is_dir()):
        if only and run_dir.name != only:
            continue
        r = scan_run(run_dir)
        if r["cases"]:
            out.append(r)
    return out


def prune(targets: list[Path], apply: bool = False) -> int:
    """Delete the given targets when apply=True; return the bytes freed either way (dry-run if not)."""
    freed = 0
    for t in targets:
        if not t.exists():
            continue
        freed += _dir_bytes(t)
        if apply:
            try:
                if t.is_dir():
                    shutil.rmtree(t, ignore_errors=True)
                else:
                    t.unlink(missing_ok=True)
            except OSError:
                pass
    return freed


def human(nbytes: int) -> str:
    x = float(nbytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if x < 1024 or unit == "TB":
            return f"{x:.1f} {unit}"
        x /= 1024
    return f"{x:.1f} TB"
