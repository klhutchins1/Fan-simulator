# Prop Open-Air GCI Ladder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run an honest 3-level open-air mesh ladder on both drone_radial STLs, compute Roache GCI on `thrust_g`, and document the uncertainty band (or honest `gci: null`).

**Architecture:** Small library helpers parse cell lists and build GCI summaries from level dicts (unit-tested, no Docker). A CLI loops `evaluate_prop_cfd` over `0.005/0.0035/0.0025`, writes per-rung `result.json` + summary JSON, then the campaign updates the validation report and roadmap.

**Tech Stack:** Python 3.12 (uv), pytest, OpenFOAM v2406 Docker, `fansim.analyze.grid_convergence`, `fansim.propeller.cfd.evaluate_prop_cfd`.

**Spec:** `docs/superpowers/specs/2026-09-22-prop-cfd-grid-independence-design.md`

## Global Constraints

- Ladder cells (coarse→fine input order OK; Roache needs fine&lt;med&lt;coarse `h`): **0.005, 0.0035, 0.0025**.
- Ops: obj_1 RPM **38100**, obj_2 RPM **25257**; **iters=800**, **procs=8** on every rung.
- Do **not** stitch smoke/refine fixtures as ladder rungs.
- Do **not** overwrite `*_smoke.json` or `*_refine.json`.
- Docker image: `opencfd/openfoam-default:2406`. CI: no Docker.
- Force-tail drift is **diagnostic only** (record; do not gate).
- Skip staging `catalog/catalog.db`. Commit when the user asks (plan steps may still list commits).

## File map

| File | Role |
|------|------|
| `fansim/propeller/gci_ladder.py` | `parse_cells`, `build_gci_summary` (pure; testable) |
| `scripts/run_prop_grid_convergence.py` | Ladder CLI → `evaluate_prop_cfd` → summary |
| `tests/test_prop_gci_ladder.py` | Unit tests for helpers + CLI parser |
| `docs/validation/drone_radial_open_air_cfd.md` | GCI section |
| `docs/roadmap.md` | §4.3 GCI note |
| `docs/superpowers/specs/2026-09-22-prop-cfd-grid-independence-design.md` | Mark implemented / partial |
| optional `validation/reference/drone_radial/cfd/*_gci.json` | After clean campaign |

Reuse unchanged: `fansim/analyze/grid_convergence.py`, `fansim/propeller/cfd.py`, `fansim/propeller/cfd_fixture.py` (`force_z_tail_drift_pct`).

---

### Task 1: GCI summary helpers (TDD)

**Files:**
- Create: `fansim/propeller/gci_ladder.py`
- Create: `tests/test_prop_gci_ladder.py`

**Interfaces:**
- Produces:
  - `parse_cells(s: str) -> list[float]` — comma-separated; must yield exactly 3 positive finite values; returns sorted **coarse→fine** (descending `h`) for ladder iteration, or document ascending — **choose descending for CLI loop order matching spec tables**.
  - `build_gci_summary(*, stl: str, rpm: float, iters: int, levels: list[dict]) -> dict` — each level dict has at least `base_cell`, `thrust_g`, optional `shaft_power_w`, `tip_mach`, `force_tail_drift_pct`, `ok`/`error`. Returns `{"stl", "rpm", "iters", "levels", "gci": {...}|null, "gci_reason": str|null}`. Roache call uses fine/med/coarse = sorted ascending `h` → `h1,h2,h3` with matching `thrust_g`.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_prop_gci_ladder.py
from __future__ import annotations

import math

import pytest

from fansim.propeller.gci_ladder import build_gci_summary, parse_cells


def test_parse_cells_three_values_coarse_to_fine():
    assert parse_cells("0.005,0.0035,0.0025") == [0.005, 0.0035, 0.0025]


def test_parse_cells_sorts_descending():
    assert parse_cells("0.0025,0.005,0.0035") == [0.005, 0.0035, 0.0025]


def test_parse_cells_rejects_bad():
    with pytest.raises(ValueError):
        parse_cells("0.005,0.0035")
    with pytest.raises(ValueError):
        parse_cells("0.005,0.005,0.0025")


def test_build_gci_summary_roache_on_thrust():
    # Synthetic f = 100 - C*h_mm^2 on base_cell in metres → p≈2
    levels = [
        {"base_cell": 0.004, "thrust_g": 100.0 - (4.0**2), "ok": True},
        {"base_cell": 0.002, "thrust_g": 100.0 - (2.0**2), "ok": True},
        {"base_cell": 0.001, "thrust_g": 100.0 - (1.0**2), "ok": True},
    ]
    s = build_gci_summary(stl="x.stl", rpm=1000.0, iters=800, levels=levels)
    assert s["gci"] is not None
    assert s["gci"]["p"] == pytest.approx(2.0, abs=1e-4)
    assert s["gci"]["f_extrapolated"] == pytest.approx(100.0, abs=1e-3)
    assert s["gci_reason"] is None


def test_build_gci_summary_null_when_rung_failed():
    levels = [
        {"base_cell": 0.005, "thrust_g": 10.0, "ok": True},
        {"base_cell": 0.0035, "thrust_g": None, "ok": False, "error": "solve failed"},
        {"base_cell": 0.0025, "thrust_g": 12.0, "ok": True},
    ]
    s = build_gci_summary(stl="x.stl", rpm=1.0, iters=800, levels=levels)
    assert s["gci"] is None
    assert "failed" in (s["gci_reason"] or "").lower() or "incomplete" in (s["gci_reason"] or "").lower()


def test_build_gci_summary_null_when_flat():
    levels = [
        {"base_cell": 0.005, "thrust_g": 50.0, "ok": True},
        {"base_cell": 0.0035, "thrust_g": 50.0, "ok": True},
        {"base_cell": 0.0025, "thrust_g": 50.0, "ok": True},
    ]
    s = build_gci_summary(stl="x.stl", rpm=1.0, iters=800, levels=levels)
    assert s["gci"] is None
    assert s["gci_reason"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_prop_gci_ladder.py -v --tb=short`  
Expected: FAIL — `ModuleNotFoundError: fansim.propeller.gci_ladder`.

- [ ] **Step 3: Implement helpers**

```python
# fansim/propeller/gci_ladder.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_prop_gci_ladder.py -v --tb=short`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add fansim/propeller/gci_ladder.py tests/test_prop_gci_ladder.py
git commit -m "feat(prop): GCI ladder summary helpers for open-air thrust"
```

---

### Task 2: Ladder CLI script

**Files:**
- Create: `scripts/run_prop_grid_convergence.py`
- Modify: `tests/test_prop_gci_ladder.py` (CLI parser test)

**Interfaces:**
- Consumes: `parse_cells`, `build_gci_summary`, `evaluate_prop_cfd`, `force_z_tail_drift_pct`, `get_prop_spec`, `image_available`
- Produces: CLI with `--stl`, `--rpm`, `--cells`, `--iters`, `--procs`, `--out`, `--force`, `--spec` (dummy for datasheet stamp; default `fpv_5inch`), `--both` optional
- Per rung dir: `{out}/{base_cell}/result.json`
- Summary: `{out}_gci_summary.json` if `--out` ends with case name, **or** `{out.parent}/{out.name}_gci_summary.json` — lock: write `{out}/gci_summary.json` **and** also `{out.parent}/{out.name}_gci_summary.json` when `--out` is `.../gci/obj_1` so layout matches spec (`obj_1_gci_summary.json` sibling). Prefer: **`{out.parent / (out.name + "_gci_summary.json")}`** only (matches spec layout exactly).

- [ ] **Step 1: Write failing CLI parser test**

```python
def test_cli_parser_defaults_and_cells():
    import importlib.util
    from pathlib import Path

    path = Path("scripts/run_prop_grid_convergence.py")
    spec = importlib.util.spec_from_file_location("run_prop_grid_convergence", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    ap = mod.build_parser()
    args = ap.parse_args([
        "--stl", "validation/reference/drone_radial/obj_1_ccw_impeller.stl",
        "--rpm", "38100",
        "--out", "runs/drone_radial_cfd/gci/obj_1",
    ])
    assert args.rpm == pytest.approx(38100.0)
    assert args.iters == 800
    assert args.cells == "0.005,0.0035,0.0025"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_prop_gci_ladder.py::test_cli_parser_defaults_and_cells -v --tb=short`  
Expected: FAIL — script missing.

- [ ] **Step 3: Implement CLI**

```python
# scripts/run_prop_grid_convergence.py
"""Honest 3-level open-air GCI ladder for prop STLs (roadmap §4.3).

Usage:
    uv run python scripts/run_prop_grid_convergence.py \\
      --stl validation/reference/drone_radial/obj_1_ccw_impeller.stl \\
      --rpm 38100 --out runs/drone_radial_cfd/gci/obj_1

    uv run python scripts/run_prop_grid_convergence.py --both
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from fansim.cfd.runner import image_available  # noqa: E402
from fansim.prop_spec import get_prop_spec  # noqa: E402
from fansim.propeller.cfd_fixture import force_z_tail_drift_pct  # noqa: E402
from fansim.propeller.gci_ladder import build_gci_summary, parse_cells  # noqa: E402
from fansim.propeller.stl_import import spin_hint_from_name  # noqa: E402

BOTH = (
    {
        "stl": PROJECT / "validation/reference/drone_radial/obj_1_ccw_impeller.stl",
        "rpm": 38100.0,
        "out": PROJECT / "runs/drone_radial_cfd/gci/obj_1",
    },
    {
        "stl": PROJECT / "validation/reference/drone_radial/obj_2_ccw.stl",
        "rpm": 25257.0,
        "out": PROJECT / "runs/drone_radial_cfd/gci/obj_2",
    },
)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Prop open-air GCI mesh ladder")
    ap.add_argument("--stl", type=Path, default=None)
    ap.add_argument("--rpm", type=float, default=None)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--cells", default="0.005,0.0035,0.0025")
    ap.add_argument("--iters", type=int, default=800)
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--spec", default="fpv_5inch", help="PropSpec key for stamps only")
    ap.add_argument("--force", action="store_true", help="re-solve even if result.json exists")
    ap.add_argument("--both", action="store_true", help="run obj_1 then obj_2 at locked RPMs")
    return ap


def _spin_for(stl: Path) -> int:
    hint = spin_hint_from_name(stl.name)
    return int(hint if hint is not None else -1)


def _rung_done(result_path: Path) -> bool:
    if not result_path.is_file():
        return False
    try:
        data = json.loads(result_path.read_text(encoding="utf-8"))
        tg = float(data["thrust_g"])
        return math.isfinite(tg)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False


def run_ladder(
    *,
    stl: Path,
    rpm: float,
    out: Path,
    cells: list[float],
    iters: int,
    procs: int,
    spec_key: str,
    force: bool,
) -> dict:
    from fansim.propeller.cfd import evaluate_prop_cfd

    spec = get_prop_spec(spec_key)
    spin = _spin_for(stl)
    out.mkdir(parents=True, exist_ok=True)
    levels: list[dict] = []

    for h in cells:
        rung = out / f"{h:g}"
        rung.mkdir(parents=True, exist_ok=True)
        result_path = rung / "result.json"
        level: dict = {"base_cell": float(h), "workdir": str(rung)}
        try:
            if force or not _rung_done(result_path):
                if not image_available():
                    raise RuntimeError("OpenFOAM Docker image not available")
                data = evaluate_prop_cfd(
                    spec,
                    rung,
                    rpm=float(rpm),
                    iters=int(iters),
                    procs=int(procs),
                    base_cell=float(h),
                    spec_key=spec_key,
                    stl_mm=stl,
                    spin=spin,
                )
                result_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            else:
                data = json.loads(result_path.read_text(encoding="utf-8"))
            level["thrust_g"] = float(data["thrust_g"])
            level["shaft_power_w"] = data.get("shaft_power_w")
            level["tip_mach"] = data.get("tip_mach")
            try:
                level["force_tail_drift_pct"] = force_z_tail_drift_pct(rung)
            except (OSError, ValueError, FileNotFoundError):
                level["force_tail_drift_pct"] = None
            level["ok"] = math.isfinite(float(level["thrust_g"]))
            if not level["ok"]:
                level["error"] = "non-finite thrust_g"
        except Exception as exc:  # noqa: BLE001 — rung isolation
            level["ok"] = False
            level["thrust_g"] = None
            level["error"] = str(exc)
        levels.append(level)

    summary = build_gci_summary(
        stl=str(stl), rpm=float(rpm), iters=int(iters), levels=levels,
    )
    summary_path = out.parent / f"{out.name}_gci_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return summary


def main() -> int:
    args = build_parser().parse_args()
    cells = parse_cells(args.cells)

    jobs = []
    if args.both:
        jobs = list(BOTH)
    else:
        if args.stl is None or args.rpm is None or args.out is None:
            print("ERROR: need --stl --rpm --out (or --both)", file=sys.stderr)
            return 2
        jobs = [{"stl": args.stl, "rpm": float(args.rpm), "out": args.out}]

    rc = 0
    for job in jobs:
        stl = Path(job["stl"])
        if not stl.is_file():
            print(f"ERROR: STL not found: {stl}", file=sys.stderr)
            rc = 2
            continue
        try:
            run_ladder(
                stl=stl,
                rpm=float(job["rpm"]),
                out=Path(job["out"]),
                cells=cells,
                iters=int(args.iters),
                procs=int(args.procs),
                spec_key=args.spec,
                force=bool(args.force),
            )
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR: ladder failed for {stl}: {exc}", file=sys.stderr)
            rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run unit tests**

Run: `uv run python -m pytest tests/test_prop_gci_ladder.py -v --tb=short`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/run_prop_grid_convergence.py tests/test_prop_gci_ladder.py
git commit -m "feat(prop): CLI for open-air GCI mesh ladder"
```

---

### Task 3: Docker GCI campaign (both STLs)

**Files:**
- Create (runtime): `runs/drone_radial_cfd/gci/obj_{1,2}/…`
- Create (runtime): `runs/drone_radial_cfd/gci/obj_{1,2}_gci_summary.json`
- Optional commit: `validation/reference/drone_radial/cfd/obj_1_ccw_impeller_gci.json`, `obj_2_ccw_gci.json` (copy of summaries if GCI computed or honest null)

**Interfaces:**
- Consumes: Task 2 CLI
- Produces: six rung results + two summaries

- [ ] **Step 1: Confirm Docker image**

Run: `docker image inspect opencfd/openfoam-default:2406 --format "{{.Id}}"`  
Expected: image id printed. If missing, pull first.

- [ ] **Step 2: Run both ladders**

Run (long — hours):

```bash
uv run python scripts/run_prop_grid_convergence.py --both --procs 8
```

Expected: prints two JSON summaries; writes under `runs/drone_radial_cfd/gci/`. Resume-safe if interrupted (re-run same command).

- [ ] **Step 3: Sanity-check summaries**

Run:

```bash
uv run python -c "import json,pathlib; p=pathlib.Path('runs/drone_radial_cfd/gci');
for n in ('obj_1_gci_summary.json','obj_2_gci_summary.json'):
 d=json.loads((p/n).read_text()); print(n, 'gci=', d.get('gci'), 'reason=', d.get('gci_reason'));
 [print(' ',lv.get('base_cell'), lv.get('thrust_g'), lv.get('ok'), lv.get('error')) for lv in d['levels']]"
```

Expected: three levels each; `gci` dict or non-empty `gci_reason`.

- [ ] **Step 4: Optional stamp into validation/reference**

If summaries look coherent, copy:

```bash
cp runs/drone_radial_cfd/gci/obj_1_gci_summary.json validation/reference/drone_radial/cfd/obj_1_ccw_impeller_gci.json
cp runs/drone_radial_cfd/gci/obj_2_gci_summary.json validation/reference/drone_radial/cfd/obj_2_ccw_gci.json
```

- [ ] **Step 5: Commit stamps only if present (skip runs/)**

```bash
git add validation/reference/drone_radial/cfd/*_gci.json
git commit -m "data(prop): drone_radial open-air GCI ladder summaries"
```

(Skip this commit if campaign incomplete / user prefers md-only.)

---

### Task 4: Validation report + roadmap + spec status

**Files:**
- Modify: `docs/validation/drone_radial_open_air_cfd.md`
- Modify: `docs/roadmap.md` (§4.3)
- Modify: `docs/superpowers/specs/2026-09-22-prop-cfd-grid-independence-design.md` (status line)

**Interfaces:**
- Consumes: summary JSON from Task 3
- Produces: GCI section in validation md; roadmap note; spec `Status: implemented` or `partial`

- [ ] **Step 1: Extend validation md**

Append a section like:

```markdown
## Grid independence (GCI)

**Status:** recorded YYYY-MM-DD  
**Ladder:** `base_cell` 0.005 / 0.0035 / 0.0025 · **iters** 800 · same RPM as smoke Ma≈0.35  
**Metric:** `thrust_g` (Roache GCI via `fansim.analyze.grid_convergence`)  
**Script:** `scripts/run_prop_grid_convergence.py`

| Case | RPM | thrust @0.005 | @0.0035 | @0.0025 | Richardson | GCI_fine % | asymptotic |
|------|-----|---------------|---------|---------|------------|------------|------------|
| obj_1 | 38100 | … | … | … | … | … | … |
| obj_2 | 25257 | … | … | … | … | … | … |

Fill cells from the summary JSON. If `gci` is null, put the reason in the Richardson/GCI columns.

Honesty: GCI is discretization uncertainty for steady compressible-MRF open-air — not datasheet-grade.
```

Also bump the top status line to mention GCI.

- [ ] **Step 2: Roadmap §4.3 note**

After the refine bullet block, add:

```markdown
  **drone_radial GCI (YYYY-MM-DD):** honest ladder 0.005/0.0035/0.0025 on both STLs;
  Roache on thrust_g; report `docs/validation/drone_radial_open_air_cfd.md`.
  Spec/plan: `docs/superpowers/specs/2026-09-22-prop-cfd-grid-independence-design.md`,
  `docs/superpowers/plans/2026-09-22-prop-cfd-grid-independence.md`.
```

Update the “Remaining for a full tier” line so grid-independence is noted done for this screening stamp (AMI/polars/datasheet still remaining).

- [ ] **Step 3: Spec status**

Set header to `**Status:** implemented (YYYY-MM-DD)` or `partial` if one STL has `gci: null`.

- [ ] **Step 4: Run unit tests once more**

Run: `uv run python -m pytest tests/test_prop_gci_ladder.py tests/test_grid_convergence.py -q --tb=short`  
Expected: PASS.

- [ ] **Step 5: Commit docs**

```bash
git add docs/validation/drone_radial_open_air_cfd.md docs/roadmap.md \
  docs/superpowers/specs/2026-09-22-prop-cfd-grid-independence-design.md
git commit -m "docs(prop): record drone_radial open-air GCI ladder"
```

---

## Self-review (plan vs spec)

| Spec requirement | Task |
|------------------|------|
| Both STLs, cells 0.005/0.0035/0.0025 | Task 2 `--both` + Task 3 |
| Fixed RPM/iters; no smoke/refine stitch | Global + Task 2 |
| Roache on thrust_g | Task 1 `build_gci_summary` |
| Script + run layout + summaries | Task 2 |
| Failure → gci null; continue other STL | Task 1 + Task 2 rung try/except |
| Drift diagnostic only | Task 2 records `force_tail_drift_pct` |
| CI unit tests no Docker | Task 1–2 |
| Validation md + roadmap | Task 4 |
| Smoke/refine untouched | Global Constraints |
| Optional `*_gci.json` stamps | Task 3 Step 4 |

No placeholders / TBD left in steps.
