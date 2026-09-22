# Drone Radial Open-Air CFD Smoke Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Document two smoke `rhoSimpleFoam` open-air solves on prepared `drone_radial` STLs (obj_1 then gated obj_2), freeze small JSON fixtures, and land a validation report — without new solver physics.

**Architecture:** Library `fansim/propeller/cfd_fixture.py` owns force-tail drift, gate checks, and fixture build/write. CLI `scripts/freeze_prop_cfd_fixture.py` freezes a green `runs/.../result.json`. Campaign uses existing `scripts/evaluate_prop_cfd.py --stl` under Docker. Docs + roadmap note after green runs.

**Tech Stack:** Python 3.12 (uv), pytest, OpenFOAM v2406 Docker (`opencfd/openfoam-default:2406`), existing `evaluate_prop_cfd` / `OpenFOAMRunner`.

**Spec:** `docs/superpowers/specs/2026-09-21-prop-drone-radial-cfd-design.md`

## Global Constraints

- Docker image: `opencfd/openfoam-default:2406` (canonical). WSL-native OpenFOAM is out of scope for this milestone.
- Smoke knobs: `--base-cell 0.005`, `--iters 400`, `--procs 8` unless the validation md records a change.
- Always pass explicit `--rpm` (tip Mach 0.35–0.45 from STL `.meta.json`).
- Stamps exact: `solver=rhoSimpleFoam`, `domain=open_air`, `regime=compressible-MRF`.
- Gate before obj_2: solver ok + finite metrics + `|thrust_g| ≥ 10` + force-z tail drift **< 10%** over last 25% of `force.dat`.
- `runs/` stays gitignored; do **not** commit case trees.
- CI: no Docker solve. Unit tests only (`-m "not docker and not slow"`).
- Skip staging `catalog/catalog.db`. Commit when the user asks (plan steps may still list commits).
- No BEMT floor / datasheet on external STL; no Optuna/cockpit/AMI/DES.

## File map

| File | Role |
|------|------|
| `fansim/propeller/cfd_fixture.py` | Drift gate, smoke gate, fixture build/write |
| `scripts/freeze_prop_cfd_fixture.py` | CLI freezer |
| `tests/test_prop_cfd_fixture.py` | Always-on unit tests |
| `docs/validation/drone_radial_open_air_cfd.md` | Human report + exact commands |
| `validation/reference/drone_radial/cfd/*.json` | Frozen smoke fixtures (after Docker) |
| `validation/reference/README.md` | Pointer |
| `docs/roadmap.md` | §4.3 stage note after green runs |
| `docs/superpowers/specs/2026-09-21-prop-drone-radial-cfd-design.md` | Mark approved/implemented |

Reuse unchanged: `fansim/propeller/cfd.py`, `scripts/evaluate_prop_cfd.py`, `fansim/cfd/runner.py`, `fansim/cfd/metrics.py` (`_pp_file`, `_all_data_rows`).

---

### Task 1: Force-tail drift + smoke gate helpers

**Files:**
- Create: `fansim/propeller/cfd_fixture.py`
- Test: `tests/test_prop_cfd_fixture.py`

**Interfaces:**
- Produces:
  - `FORCE_TAIL_FRAC = 0.25`
  - `FORCE_DRIFT_TOL_PCT = 10.0`
  - `THRUST_G_FLOOR = 10.0`
  - `force_z_tail_drift_pct(case_dir: str | Path, *, tail_frac: float = FORCE_TAIL_FRAC) -> float`
  - `prop_cfd_smoke_gate(result: dict, case_dir: str | Path | None = None, *, thrust_g_floor: float = THRUST_G_FLOOR, drift_tol_pct: float = FORCE_DRIFT_TOL_PCT, tail_frac: float = FORCE_TAIL_FRAC) -> tuple[bool, list[str]]`  
    Returns `(ok, reasons)`. `reasons` empty when ok; otherwise human-readable failure strings. When `case_dir` is None, skip drift check (unit tests that only have `result.json`).

Force column layout matches `parse_prop_metrics`: time, total(x,y,z), … — **z thrust is index 3**.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_prop_cfd_fixture.py
from __future__ import annotations

from pathlib import Path

import pytest


def _write_force_dat(case_dir: Path, zs: list[float]) -> None:
    pp = case_dir / "postProcessing" / "forces" / "0"
    pp.mkdir(parents=True)
    lines = ["# Time total(x y z) pressure(x y z) viscous(x y z)\n"]
    for i, z in enumerate(zs):
        # total z = z; other components 0
        lines.append(
            f"{float(i)} (0 0 {z}) (0 0 0) (0 0 0)\n"
        )
    (pp / "force.dat").write_text("".join(lines), encoding="utf-8")


def test_force_z_tail_drift_pct_stable(tmp_path: Path):
    from fansim.propeller.cfd_fixture import force_z_tail_drift_pct

    # 20 samples ~100 ± 1 → drift well under 10%
    zs = [100.0 + (0.5 if i % 2 else -0.5) for i in range(20)]
    _write_force_dat(tmp_path, zs)
    drift = force_z_tail_drift_pct(tmp_path)
    assert drift < 5.0


def test_force_z_tail_drift_pct_unstable(tmp_path: Path):
    from fansim.propeller.cfd_fixture import force_z_tail_drift_pct

    zs = [10.0 + 50.0 * (i / 19.0) for i in range(20)]  # large ramp
    _write_force_dat(tmp_path, zs)
    drift = force_z_tail_drift_pct(tmp_path)
    assert drift >= 10.0


def test_prop_cfd_smoke_gate_pass_without_case():
    from fansim.propeller.cfd_fixture import prop_cfd_smoke_gate

    result = {
        "thrust_n": 1.0,
        "thrust_g": 100.0,
        "torque_nm": 0.05,
        "shaft_power_w": 200.0,
    }
    ok, reasons = prop_cfd_smoke_gate(result, case_dir=None)
    assert ok and reasons == []


def test_prop_cfd_smoke_gate_fails_low_thrust():
    from fansim.propeller.cfd_fixture import prop_cfd_smoke_gate

    result = {
        "thrust_n": 0.01,
        "thrust_g": 1.0,
        "torque_nm": 0.001,
        "shaft_power_w": 1.0,
    }
    ok, reasons = prop_cfd_smoke_gate(result, case_dir=None)
    assert not ok
    assert any("thrust" in r.lower() for r in reasons)


def test_prop_cfd_smoke_gate_fails_nonfinite():
    from fansim.propeller.cfd_fixture import prop_cfd_smoke_gate

    result = {
        "thrust_n": float("nan"),
        "thrust_g": float("nan"),
        "torque_nm": 0.05,
        "shaft_power_w": 200.0,
    }
    ok, reasons = prop_cfd_smoke_gate(result, case_dir=None)
    assert not ok
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_prop_cfd_fixture.py -v --tb=short`  
Expected: FAIL — `ModuleNotFoundError` or missing symbols.

- [ ] **Step 3: Minimal implementation**

```python
# fansim/propeller/cfd_fixture.py
"""Freeze / gate helpers for prop open-air CFD smoke fixtures (roadmap §4.3)."""
from __future__ import annotations

import math
from pathlib import Path

FORCE_TAIL_FRAC = 0.25
FORCE_DRIFT_TOL_PCT = 10.0
THRUST_G_FLOOR = 10.0


def force_z_tail_drift_pct(
    case_dir: str | Path,
    *,
    tail_frac: float = FORCE_TAIL_FRAC,
) -> float:
    """Peak-to-peak range of total force z over the tail, as % of |mean|."""
    from fansim.cfd.metrics import _all_data_rows, _pp_file

    path = _pp_file(Path(case_dir), "forces", "force.dat")
    rows = _all_data_rows(path)
    if len(rows) < 4:
        return 999.0
    tail = rows[max(1, int(len(rows) * (1.0 - float(tail_frac)))) :]
    zs = [float(r[3]) for r in tail]
    mean = sum(zs) / len(zs)
    drift = (max(zs) - min(zs)) / (abs(mean) + 1e-12) * 100.0
    return float(drift)


def prop_cfd_smoke_gate(
    result: dict,
    case_dir: str | Path | None = None,
    *,
    thrust_g_floor: float = THRUST_G_FLOOR,
    drift_tol_pct: float = FORCE_DRIFT_TOL_PCT,
    tail_frac: float = FORCE_TAIL_FRAC,
) -> tuple[bool, list[str]]:
    """Return (ok, reasons) for the §4.3 smoke gate before obj_2."""
    reasons: list[str] = []
    keys = ("thrust_n", "thrust_g", "torque_nm", "shaft_power_w")
    for k in keys:
        v = result.get(k)
        try:
            fv = float(v)
        except (TypeError, ValueError):
            reasons.append(f"{k} missing or non-numeric")
            continue
        if not math.isfinite(fv):
            reasons.append(f"{k} not finite ({v!r})")
    try:
        tg = abs(float(result.get("thrust_g", float("nan"))))
    except (TypeError, ValueError):
        tg = float("nan")
    if math.isfinite(tg) and tg < float(thrust_g_floor):
        reasons.append(
            f"|thrust_g|={tg:.6g} < floor {float(thrust_g_floor):.6g}"
        )
    if case_dir is not None:
        try:
            drift = force_z_tail_drift_pct(case_dir, tail_frac=tail_frac)
        except (OSError, ValueError, FileNotFoundError) as exc:
            reasons.append(f"force-tail drift unavailable: {exc}")
        else:
            if drift >= float(drift_tol_pct):
                reasons.append(
                    f"force_z_tail_drift_pct={drift:.4g} >= {float(drift_tol_pct):.4g}"
                )
    return (len(reasons) == 0, reasons)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_prop_cfd_fixture.py -v --tb=short`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add fansim/propeller/cfd_fixture.py tests/test_prop_cfd_fixture.py
git commit -m "feat(prop): smoke gate + force-tail drift for drone_radial CFD"
```

---

### Task 2: Fixture builder + write + round-trip test

**Files:**
- Modify: `fansim/propeller/cfd_fixture.py`
- Modify: `tests/test_prop_cfd_fixture.py`

**Interfaces:**
- Produces:
  - `REQUIRED_FIXTURE_KEYS: frozenset[str]` — top-level keys from the spec schema
  - `OPENFOAM_IMAGE_DEFAULT = "opencfd/openfoam-default:2406"`
  - `build_prop_cfd_fixture(*, result: dict, fixture_id: str, stl: str, spin: int, mesh: dict, openfoam_image: str = OPENFOAM_IMAGE_DEFAULT, force_tail_drift_pct: float | None = None, date: str | None = None, notes: str = "smoke screening; not datasheet-grade") -> dict`
  - `write_prop_cfd_fixture(fixture: dict, path: str | Path) -> Path` — writes JSON + trailing newline; creates parent dirs

`build_prop_cfd_fixture` pulls `rpm`, `tip_mach`, `tip_radius_mm`, metrics from `result`; stamps solver/domain/regime exactly. Prefer `result` stamps when present; else hardcode the three stamp strings.

- [ ] **Step 1: Write failing tests**

Append to `tests/test_prop_cfd_fixture.py`:

```python
import json
from datetime import date as date_cls


def test_build_and_write_prop_cfd_fixture(tmp_path: Path):
    from fansim.propeller.cfd_fixture import (
        REQUIRED_FIXTURE_KEYS,
        build_prop_cfd_fixture,
        write_prop_cfd_fixture,
    )

    result = {
        "thrust_n": 1.23,
        "thrust_g": 125.4,
        "torque_nm": 0.04,
        "shaft_power_w": 150.0,
        "rpm": 41000.0,
        "tip_mach": 0.38,
        "tip_radius_mm": 30.089,
        "solver": "rhoSimpleFoam",
        "domain": "open_air",
        "regime": "compressible-MRF",
    }
    fixture = build_prop_cfd_fixture(
        result=result,
        fixture_id="obj_1_ccw_impeller_smoke",
        stl="validation/reference/drone_radial/obj_1_ccw_impeller.stl",
        spin=-1,
        mesh={"base_cell_m": 0.005, "iters": 400, "procs": 8},
        force_tail_drift_pct=2.5,
        date="2026-09-21",
    )
    assert REQUIRED_FIXTURE_KEYS <= set(fixture.keys())
    assert fixture["solver"] == "rhoSimpleFoam"
    assert fixture["domain"] == "open_air"
    assert fixture["regime"] == "compressible-MRF"
    assert fixture["metrics"]["thrust_g"] == pytest.approx(125.4)
    assert fixture["force_tail_drift_pct"] == pytest.approx(2.5)

    out = write_prop_cfd_fixture(fixture, tmp_path / "cfd" / "obj_1.json")
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["id"] == "obj_1_ccw_impeller_smoke"
    assert loaded["openfoam_image"] == "opencfd/openfoam-default:2406"
```

- [ ] **Step 2: Run new test to verify it fails**

Run: `uv run python -m pytest tests/test_prop_cfd_fixture.py::test_build_and_write_prop_cfd_fixture -v --tb=short`  
Expected: FAIL — missing symbols.

- [ ] **Step 3: Implement builder + writer**

Add to `fansim/propeller/cfd_fixture.py`:

```python
import json
from datetime import date as date_cls

OPENFOAM_IMAGE_DEFAULT = "opencfd/openfoam-default:2406"

REQUIRED_FIXTURE_KEYS = frozenset({
    "id", "stl", "spin", "rpm", "tip_mach", "tip_radius_mm", "mesh",
    "solver", "domain", "regime", "openfoam_image", "metrics",
    "force_tail_drift_pct", "date", "notes",
})


def build_prop_cfd_fixture(
    *,
    result: dict,
    fixture_id: str,
    stl: str,
    spin: int,
    mesh: dict,
    openfoam_image: str = OPENFOAM_IMAGE_DEFAULT,
    force_tail_drift_pct: float | None = None,
    date: str | None = None,
    notes: str = "smoke screening; not datasheet-grade",
) -> dict:
    metrics = {
        "thrust_n": float(result["thrust_n"]),
        "thrust_g": float(result["thrust_g"]),
        "torque_nm": float(result["torque_nm"]),
        "shaft_power_w": float(result["shaft_power_w"]),
    }
    return {
        "id": str(fixture_id),
        "stl": str(stl),
        "spin": int(spin),
        "rpm": float(result["rpm"]),
        "tip_mach": float(result["tip_mach"]),
        "tip_radius_mm": float(result["tip_radius_mm"]),
        "mesh": {
            "base_cell_m": float(mesh["base_cell_m"]),
            "iters": int(mesh["iters"]),
            "procs": int(mesh["procs"]),
        },
        "solver": str(result.get("solver") or "rhoSimpleFoam"),
        "domain": str(result.get("domain") or "open_air"),
        "regime": str(result.get("regime") or "compressible-MRF"),
        "openfoam_image": str(openfoam_image),
        "metrics": metrics,
        "force_tail_drift_pct": (
            None if force_tail_drift_pct is None else float(force_tail_drift_pct)
        ),
        "date": date or date_cls.today().isoformat(),
        "notes": str(notes),
    }


def write_prop_cfd_fixture(fixture: dict, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(fixture, indent=2) + "\n", encoding="utf-8")
    return path
```

- [ ] **Step 4: Run full fixture tests**

Run: `uv run python -m pytest tests/test_prop_cfd_fixture.py -v --tb=short`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add fansim/propeller/cfd_fixture.py tests/test_prop_cfd_fixture.py
git commit -m "feat(prop): build/write drone_radial CFD smoke fixtures"
```

---

### Task 3: Freeze CLI

**Files:**
- Create: `scripts/freeze_prop_cfd_fixture.py`
- Modify: `tests/test_prop_cfd_fixture.py`

**Interfaces:**
- Consumes: `build_prop_cfd_fixture`, `write_prop_cfd_fixture`, `force_z_tail_drift_pct`, `prop_cfd_smoke_gate`
- CLI flags:
  - `--result` (Path, required) — `result.json` from evaluate
  - `--out` (Path, required) — fixture JSON path
  - `--id` (str, required)
  - `--stl` (str, required) — repo-relative STL path string for the fixture
  - `--spin` (int, default -1)
  - `--base-cell` (float, default 0.005)
  - `--iters` (int, default 400)
  - `--procs` (int, default 8)
  - `--case-dir` (Path, optional) — for drift; default = parent of `--result` if `postProcessing` exists there, else skip drift and set `force_tail_drift_pct` null only if `--allow-no-case`
  - `--allow-no-case` — allow freeze without drift (tests / dry)
  - `--require-gate` — exit 2 if `prop_cfd_smoke_gate` fails
  - `--date` (optional ISO date)

- [ ] **Step 1: Write failing CLI parse / smoke test**

```python
def test_freeze_cli_parser_has_required_flags():
    import importlib.util
    from pathlib import Path

    path = Path("scripts/freeze_prop_cfd_fixture.py")
    spec = importlib.util.spec_from_file_location("freeze_prop_cfd_fixture", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    ap = mod.build_parser()
    names = {a.dest for a in ap._actions}
    for need in ("result", "out", "id", "stl", "require_gate", "allow_no_case"):
        assert need in names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_prop_cfd_fixture.py::test_freeze_cli_parser_has_required_flags -v --tb=short`  
Expected: FAIL — file missing or no `build_parser`.

- [ ] **Step 3: Implement CLI**

```python
# scripts/freeze_prop_cfd_fixture.py
"""Freeze a prop CFD result.json into validation/reference/drone_radial/cfd/."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from fansim.propeller.cfd_fixture import (  # noqa: E402
    build_prop_cfd_fixture,
    force_z_tail_drift_pct,
    prop_cfd_smoke_gate,
    write_prop_cfd_fixture,
)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Freeze prop CFD smoke fixture JSON")
    ap.add_argument("--result", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--id", required=True)
    ap.add_argument("--stl", required=True)
    ap.add_argument("--spin", type=int, default=-1)
    ap.add_argument("--base-cell", type=float, default=0.005)
    ap.add_argument("--iters", type=int, default=400)
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--case-dir", type=Path, default=None)
    ap.add_argument("--allow-no-case", action="store_true")
    ap.add_argument("--require-gate", action="store_true")
    ap.add_argument("--date", default=None)
    return ap


def main() -> int:
    args = build_parser().parse_args()
    result = json.loads(Path(args.result).read_text(encoding="utf-8"))
    case_dir = args.case_dir
    if case_dir is None:
        parent = Path(args.result).resolve().parent
        if (parent / "postProcessing").is_dir():
            case_dir = parent
    drift = None
    if case_dir is not None:
        drift = force_z_tail_drift_pct(case_dir)
    elif not args.allow_no_case:
        print("ERROR: no case-dir / postProcessing; pass --case-dir or --allow-no-case",
              file=sys.stderr)
        return 2
    if args.require_gate:
        ok, reasons = prop_cfd_smoke_gate(result, case_dir=case_dir)
        if not ok:
            print("GATE FAIL:\n" + "\n".join(reasons), file=sys.stderr)
            return 2
    fixture = build_prop_cfd_fixture(
        result=result,
        fixture_id=args.id,
        stl=args.stl,
        spin=args.spin,
        mesh={
            "base_cell_m": args.base_cell,
            "iters": args.iters,
            "procs": args.procs,
        },
        force_tail_drift_pct=drift,
        date=args.date,
    )
    path = write_prop_cfd_fixture(fixture, args.out)
    print(json.dumps({"wrote": str(path), "id": fixture["id"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests + CLI smoke on fake result**

```bash
uv run python -m pytest tests/test_prop_cfd_fixture.py -v --tb=short
```

Also manually:

```bash
# create a tiny fake result.json then:
uv run python scripts/freeze_prop_cfd_fixture.py \
  --result /tmp/fake_result.json \
  --out /tmp/fake_fixture.json \
  --id obj_1_ccw_impeller_smoke \
  --stl validation/reference/drone_radial/obj_1_ccw_impeller.stl \
  --allow-no-case
```

Expected: writes JSON; pytest PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/freeze_prop_cfd_fixture.py tests/test_prop_cfd_fixture.py
git commit -m "feat(prop): CLI to freeze drone_radial CFD smoke fixtures"
```

---

### Task 4: Validation doc scaffold + README pointer

**Files:**
- Create: `docs/validation/drone_radial_open_air_cfd.md`
- Modify: `validation/reference/README.md` (drone radial section)

**Interfaces:**
- Doc must include: honesty paragraph, RPM formula, exact commands for dry-run + obj_1 + gate + obj_2, fixture paths, Docker image tag, “WSL optional later”.
- Metrics tables start as **pending** until Task 5–6 fill real numbers.

- [ ] **Step 1: Compute RPM for Ma = 0.38 from meta**

```bash
uv run python -c "
import json, math
from pathlib import Path
for name in ('obj_1_ccw_impeller','obj_2_ccw'):
    m = json.loads(Path(f'validation/reference/drone_radial/{name}.meta.json').read_text())
    R = m['tip_radius_mm']/1000.0
    Ma = 0.38
    rpm = Ma * 343.0 * 60.0 / (2.0 * math.pi * R)
    print(name, 'R_mm=', m['tip_radius_mm'], 'rpm=', round(rpm,1), 'tip_mach@rpm=', Ma)
"
```

Record the printed RPMs into the doc (do not invent).

- [ ] **Step 2: Write `docs/validation/drone_radial_open_air_cfd.md`**

Content must include (fill RPM from Step 1):

```markdown
# Drone radial open-air CFD (smoke)

**Status:** campaign / pending measured fixtures  
**Solver:** `rhoSimpleFoam` · **Domain:** open_air · **Regime:** compressible-MRF  
**Image:** `opencfd/openfoam-default:2406` (canonical). WSL-native OpenFOAM is optional later — not documented as a second path here.

## Honesty

Steady compressible MRF on a truncated box with smoke mesh (`base_cell=0.005 m`) is a
**screening** record. Tip Mach is stamped; shocks are not resolved. Not OEM / datasheet grade.

## Geometry

| Case | STL | ~D |
|------|-----|----|
| obj_1 | `validation/reference/drone_radial/obj_1_ccw_impeller.stl` | ~60 mm |
| obj_2 | `validation/reference/drone_radial/obj_2_ccw.stl` | ~90 mm |

RPM from tip Mach ≈ 0.38: `rpm = Ma * 343 * 60 / (2π R)` (R from `.meta.json`).

| Case | RPM (Ma≈0.38) |
|------|----------------|
| obj_1 | <from step 1> |
| obj_2 | <from step 1> |

## Gate (before obj_2)

1. Solver exit 0  
2. Finite thrust/torque/power  
3. `|thrust_g| ≥ 10`  
4. Force-z tail drift < 10% over last 25% of `force.dat`

## Commands

Dry-run:

```bash
uv run python scripts/evaluate_prop_cfd.py \
  --stl validation/reference/drone_radial/obj_1_ccw_impeller.stl \
  --rpm <obj1> --base-cell 0.005 --iters 400 --procs 8 \
  --out runs/drone_radial_cfd/_dry_run/obj_1 --dry-run
```

Full obj_1 (requires Docker image):

```bash
uv run python scripts/evaluate_prop_cfd.py \
  --stl validation/reference/drone_radial/obj_1_ccw_impeller.stl \
  --rpm <obj1> --base-cell 0.005 --iters 400 --procs 8 \
  --out runs/drone_radial_cfd/obj_1_smoke
```

Gate check (Python one-liner or freeze `--require-gate` after result exists).

Obj_2 only if gate passes — same knobs, `--stl …/obj_2_ccw.stl`, `--rpm <obj2>`, `--out runs/drone_radial_cfd/obj_2_smoke`.

Freeze:

```bash
uv run python scripts/freeze_prop_cfd_fixture.py \
  --result runs/drone_radial_cfd/obj_1_smoke/result.json \
  --out validation/reference/drone_radial/cfd/obj_1_ccw_impeller_smoke.json \
  --id obj_1_ccw_impeller_smoke \
  --stl validation/reference/drone_radial/obj_1_ccw_impeller.stl \
  --spin -1 --require-gate
```

## Results

| Case | thrust_g | shaft_power_w | tip_mach | drift_% | fixture |
|------|----------|---------------|----------|---------|---------|
| obj_1 | pending | pending | pending | pending | `…/cfd/obj_1_ccw_impeller_smoke.json` |
| obj_2 | pending | pending | pending | pending | `…/cfd/obj_2_ccw_smoke.json` |
```

- [ ] **Step 3: README pointer**

In `validation/reference/README.md` under **Drone radial / impeller STL batch**, add after the existing evaluate example:

```markdown
Documented smoke CFD (after campaign): `docs/validation/drone_radial_open_air_cfd.md`
and fixtures under `validation/reference/drone_radial/cfd/`.
```

- [ ] **Step 4: Commit**

```bash
git add docs/validation/drone_radial_open_air_cfd.md validation/reference/README.md
git commit -m "docs: drone_radial open-air CFD smoke campaign scaffold"
```

---

### Task 5: Docker campaign (manual — obj_1, gate, optional obj_2)

**Files:**
- Create (local only): `runs/drone_radial_cfd/obj_1_smoke/`, optionally `obj_2_smoke/`
- Modify after success: `docs/validation/drone_radial_open_air_cfd.md` (status note only if still pending fixtures — full metrics in Task 6)

**Prereq:** `image_available()` true for `opencfd/openfoam-default:2406`.

- [ ] **Step 1: Confirm Docker image**

```bash
uv run python -c "from fansim.cfd.runner import image_available, DEFAULT_IMAGE; print(DEFAULT_IMAGE, image_available())"
```

Expected: `opencfd/openfoam-default:2406 True`. If False: pull/start Docker; do not proceed.

- [ ] **Step 2: Optional dry-run both STLs**

```bash
uv run python scripts/evaluate_prop_cfd.py \
  --stl validation/reference/drone_radial/obj_1_ccw_impeller.stl \
  --rpm <obj1_rpm> --out runs/drone_radial_cfd/_dry_run/obj_1 --dry-run
uv run python scripts/evaluate_prop_cfd.py \
  --stl validation/reference/drone_radial/obj_2_ccw.stl \
  --rpm <obj2_rpm> --out runs/drone_radial_cfd/_dry_run/obj_2 --dry-run
```

Expected: `dry_run.json` with finite tip_mach and `solver=rhoSimpleFoam`.

- [ ] **Step 3: Full solve obj_1**

```bash
uv run python scripts/evaluate_prop_cfd.py \
  --stl validation/reference/drone_radial/obj_1_ccw_impeller.stl \
  --rpm <obj1_rpm> --base-cell 0.005 --iters 400 --procs 8 \
  --out runs/drone_radial_cfd/obj_1_smoke
```

Expected: `result.json` with finite metrics. Runtime: hours-class; do not kill mid-solve without documenting.

- [ ] **Step 4: Gate obj_1**

```bash
uv run python -c "
import json
from pathlib import Path
from fansim.propeller.cfd_fixture import prop_cfd_smoke_gate
r = json.loads(Path('runs/drone_radial_cfd/obj_1_smoke/result.json').read_text())
ok, reasons = prop_cfd_smoke_gate(r, case_dir='runs/drone_radial_cfd/obj_1_smoke')
print('ok', ok); print('\n'.join(reasons))
"
```

If `ok` is False: document failure in `docs/validation/drone_radial_open_air_cfd.md` (what failed, last log hint); **stop** — skip obj_2 and Task 6 obj_2 fixture. Still freeze obj_1 only if gate criteria 1–3 pass and you explicitly decide to keep a partial record (spec: do not freeze success fixture for a failed solve; if only drift fails, document and do not proceed to obj_2).

- [ ] **Step 5: Full solve obj_2 (gate pass only)**

```bash
uv run python scripts/evaluate_prop_cfd.py \
  --stl validation/reference/drone_radial/obj_2_ccw.stl \
  --rpm <obj2_rpm> --base-cell 0.005 --iters 400 --procs 8 \
  --out runs/drone_radial_cfd/obj_2_smoke
```

Then re-run gate on obj_2 the same way (for fixture quality; not a further gate).

- [ ] **Step 6: Commit** — none (runs/ gitignored). Proceed to Task 6.

---

### Task 6: Freeze fixtures, fill doc, roadmap, fixture load tests

**Files:**
- Create: `validation/reference/drone_radial/cfd/obj_1_ccw_impeller_smoke.json`
- Create (if obj_2 ran): `validation/reference/drone_radial/cfd/obj_2_ccw_smoke.json`
- Modify: `docs/validation/drone_radial_open_air_cfd.md` (Results table + Status)
- Modify: `docs/roadmap.md` (§4.3 stage note)
- Modify: `tests/test_prop_cfd_fixture.py` (load committed fixtures)
- Modify: `docs/superpowers/specs/2026-09-21-prop-drone-radial-cfd-design.md` — Status → implemented (date)

- [ ] **Step 1: Freeze obj_1 (and obj_2 if present)**

```bash
uv run python scripts/freeze_prop_cfd_fixture.py \
  --result runs/drone_radial_cfd/obj_1_smoke/result.json \
  --out validation/reference/drone_radial/cfd/obj_1_ccw_impeller_smoke.json \
  --id obj_1_ccw_impeller_smoke \
  --stl validation/reference/drone_radial/obj_1_ccw_impeller.stl \
  --spin -1 --base-cell 0.005 --iters 400 --procs 8 --require-gate
```

Repeat for obj_2 with matching paths/`--id obj_2_ccw_smoke` only if Task 5 Step 5 ran.

- [ ] **Step 2: Add fixture load test**

```python
from pathlib import Path
import json
import math

CFD_DIR = Path("validation/reference/drone_radial/cfd")


def test_committed_smoke_fixtures_if_present():
    from fansim.propeller.cfd_fixture import REQUIRED_FIXTURE_KEYS

    paths = sorted(CFD_DIR.glob("*_smoke.json")) if CFD_DIR.is_dir() else []
    if not paths:
        pytest.skip("no committed smoke fixtures yet")
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        assert REQUIRED_FIXTURE_KEYS <= set(data.keys())
        assert data["solver"] == "rhoSimpleFoam"
        assert data["domain"] == "open_air"
        assert data["regime"] == "compressible-MRF"
        for k, v in data["metrics"].items():
            assert math.isfinite(float(v)), f"{path.name} metrics.{k}"
```

- [ ] **Step 3: Fill Results table in validation md; set Status to recorded**

Copy thrust_g / shaft_power_w / tip_mach / drift_% from fixtures into the Results table. Note date and image tag.

- [ ] **Step 4: Roadmap §4.3 note**

Under §4.3 in `docs/roadmap.md`, add a bullet like Track A notes:

```markdown
  **drone_radial smoke (2026-09-21):** open-air `rhoSimpleFoam` on prepared
  `validation/reference/drone_radial/` STLs; fixtures under
  `validation/reference/drone_radial/cfd/`; report
  `docs/validation/drone_radial_open_air_cfd.md`. Screening only — not full
  §4.3 tier / not datasheet.
```

- [ ] **Step 5: Mark design spec implemented**

In `docs/superpowers/specs/2026-09-21-prop-drone-radial-cfd-design.md` header:  
`**Status:** implemented (YYYY-MM-DD)` with the campaign date.

- [ ] **Step 6: Run tests**

```bash
uv run python -m pytest tests/test_prop_cfd_fixture.py tests/test_prop_cfd.py -q -m "not docker and not slow" --tb=short
```

Expected: PASS (or skip only if no fixtures — should not skip after freeze).

- [ ] **Step 7: Commit**

```bash
git add validation/reference/drone_radial/cfd/ \
  docs/validation/drone_radial_open_air_cfd.md \
  docs/roadmap.md \
  tests/test_prop_cfd_fixture.py \
  docs/superpowers/specs/2026-09-21-prop-drone-radial-cfd-design.md
git commit -m "docs(prop): freeze drone_radial open-air CFD smoke fixtures"
```

---

## Spec coverage checklist

| Spec requirement | Task |
|------------------|------|
| obj_1 smoke solve | Task 5 |
| Gate before obj_2 | Task 1 + Task 5 |
| obj_2 if gate passes | Task 5 |
| Fixtures under `drone_radial/cfd/` | Task 2–3 + Task 6 |
| Validation md + README | Task 4 + Task 6 |
| Roadmap §4.3 note | Task 6 |
| CI unit tests, no Docker | Tasks 1–3, 6 |
| Docker canonical / WSL note | Task 4 |
| Reuse evaluate_prop_cfd | Task 5 (no redesign) |

## Plan self-review

- No TBD placeholders remain; RPM filled at Task 4 Step 1 from meta.
- Signatures consistent: `prop_cfd_smoke_gate`, `build_prop_cfd_fixture`, `write_prop_cfd_fixture`, `force_z_tail_drift_pct`.
- Fixture schema keys match spec.
