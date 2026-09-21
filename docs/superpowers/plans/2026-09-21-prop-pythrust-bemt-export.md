# Track A Stage 2: BEMT → PyThrust CSV Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Export PyThrust-compatible JSON+CSV CT/CP catalogs from fansim BEMT (APC-like default grid, CLI overrides) and wire an Analyze-tab **Export CT/CP (PyThrust)** button beside STL export.

**Architecture:** New `fansim/propeller/pythrust_export.py` builds rows via `analyze` + `nondim` / `v_inf_from_j`, writes `{id}.json` + `{id}.csv` + `{id}.export.json`. CLI and Prop Analyze call the same helper. Optional propulsion test loads a temp dir with `PropellerDatabase`.

**Tech Stack:** Python 3.12 (uv), pytest, existing BEMT/polar; optional `setuav-pythrust==0.2.3` for load smoke only.

**Spec:** `docs/superpowers/specs/2026-09-21-prop-pythrust-bemt-export-design.md`

## Global Constraints

- CSV header **exact** (order): `rpm,speed_mps,advance_ratio,efficiency,thrust_coeff,power_coeff,power_w,torque_nm,thrust_n,thrust_per_power_n_w,mach,reynolds,figure_of_merit`
- PyThrust metadata JSON: `id`, `manufacturer` (`fansim`), `model`, `diameter_in`, `pitch_in`, `blade_count`, `data_csv`
- Fansim honesty sidecar: separate `{prop_id}.export.json` (`source=bemt`, `geometry_match`, grid, tip_radius_mm, timestamp) — do **not** put extra keys in the PyThrust JSON
- Default RPM: `1000,3000,5000,7000,9000,11000` (clamp ≤ `rpm_max` when provided); default J: `0.0` … `0.60` step `0.05`
- FoM column: BEMT `figure_of_merit` at J=0; else `0.0`. Mach: tip speed/343 when computable; else `0.0`. Reynolds: `0.0`
- No write into site-packages `apc_202602`. No Optimize batch. No motor-solve UI.
- Analyze uses default grid only. Shared `prop_export_busy` lock with STL export.
- Commit when the user asks (plan steps may still list commits). Skip `catalog/catalog.db`.

## File map

| File | Role |
|------|------|
| `fansim/propeller/pythrust_export.py` | Grid defaults, prop_id sanitize, catalog export |
| `fansim/propeller/__init__.py` | Export public helpers |
| `tests/test_pythrust_export.py` | Always-on grid + tiny CSV/JSON tests |
| `tests/test_pythrust_export_propulsion.py` | Propulsion: `PropellerDatabase.load` round-trip |
| `scripts/export_prop_pythrust_csv.py` | CLI |
| `fansim/cockpit/prop_tab.py` | Analyze button + callback |
| `docs/bibliography.md` / `docs/roadmap.md` | Short Stage 2 note |

---

### Task 1: `pythrust_export` library + always-on tests

**Files:**
- Create: `fansim/propeller/pythrust_export.py`
- Modify: `fansim/propeller/__init__.py`
- Test: `tests/test_pythrust_export.py`

**Interfaces:**
- Produces:
  - `CSV_HEADER: tuple[str, ...]` (exact 13 names above)
  - `DEFAULT_RPM_LIST`, `DEFAULT_J_LIST`
  - `default_export_grid(*, rpm_max: float | None = None) -> tuple[list[float], list[float]]`
  - `prop_id_for_export(spec_key: str, *, suffix: str = "BEMT") -> str`
  - `export_bemt_pythrust_catalog(params: BladeParams, *, prop_id: str, diameter_in: float, pitch_in: float, blade_count: int, out_dir: str | Path, rpm_list: list[float] | None = None, j_list: list[float] | None = None, rho: float = RHO_AIR, geometry_match: str = "design_blade", model: str | None = None) -> dict`

Return dict keys: `prop_id`, `csv`, `json`, `export_meta`, `n_rows`, `rpm_list`, `j_list`.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_pythrust_export.py
from __future__ import annotations
import csv
import json
from pathlib import Path

import pytest

from fansim.prop_spec import get_prop_spec
from fansim.propeller.geometry import prop_blade_params


def test_default_export_grid_includes_static_j():
    from fansim.propeller.pythrust_export import default_export_grid
    rpms, js = default_export_grid(rpm_max=9000.0)
    assert rpms  # non-empty
    assert max(rpms) <= 9000.0 + 1e-9
    assert 0.0 in js
    assert max(js) == pytest.approx(0.60)


def test_prop_id_for_export_sanitizes():
    from fansim.propeller.pythrust_export import prop_id_for_export
    assert prop_id_for_export("cine_3inch") == "FANSIM_cine_3inch_BEMT"
    assert " " not in prop_id_for_export("weird name!")


def test_export_bemt_pythrust_catalog_tiny_grid(tmp_path: Path):
    from fansim.propeller.pythrust_export import (
        CSV_HEADER,
        export_bemt_pythrust_catalog,
    )
    spec = get_prop_spec("cine_3inch")
    params = prop_blade_params(spec)
    out = export_bemt_pythrust_catalog(
        params,
        prop_id="FANSIM_TEST_TINY",
        diameter_in=spec.diameter_in,
        pitch_in=spec.pitch_in,
        blade_count=spec.n_blades,
        out_dir=tmp_path,
        rpm_list=[3000.0],
        j_list=[0.0, 0.2],
        geometry_match="design_blade",
    )
    assert out["n_rows"] == 2
    csv_path = Path(out["csv"])
    json_path = Path(out["json"])
    meta_path = Path(out["export_meta"])
    assert csv_path.is_file() and json_path.is_file() and meta_path.is_file()

    with csv_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert tuple(rows[0]) == CSV_HEADER
    assert len(rows) == 3  # header + 2
    # finite CT/CP
    for row in rows[1:]:
        ct = float(row[4])
        cp = float(row[5])
        assert ct == ct and cp == cp  # not NaN
        assert cp >= 0.0

    meta = json.loads(json_path.read_text(encoding="utf-8"))
    assert meta["id"] == "FANSIM_TEST_TINY"
    assert meta["manufacturer"] == "fansim"
    assert meta["data_csv"] == "FANSIM_TEST_TINY.csv"
    assert set(meta.keys()) == {
        "id", "manufacturer", "model", "diameter_in", "pitch_in",
        "blade_count", "data_csv",
    }

    exp = json.loads(meta_path.read_text(encoding="utf-8"))
    assert exp["source"] == "bemt"
    assert exp["geometry_match"] == "design_blade"
```

- [ ] **Step 2: Run (expect fail)**

Run: `uv run python -m pytest tests/test_pythrust_export.py -v`  
Expected: FAIL (module missing)

- [ ] **Step 3: Implement `pythrust_export.py`**

```python
# fansim/propeller/pythrust_export.py — core sketch
from __future__ import annotations
import csv
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fansim.geometry.blade import BladeParams
from fansim.propeller.bemt import RHO_AIR, analyze
from fansim.propeller.polar import nondim, v_inf_from_j

C_AIR = 343.0
CSV_HEADER = (
    "rpm", "speed_mps", "advance_ratio", "efficiency", "thrust_coeff",
    "power_coeff", "power_w", "torque_nm", "thrust_n", "thrust_per_power_n_w",
    "mach", "reynolds", "figure_of_merit",
)
DEFAULT_RPM_LIST = [1000.0, 3000.0, 5000.0, 7000.0, 9000.0, 11000.0]
DEFAULT_J_LIST = [i * 0.05 for i in range(0, 13)]  # 0.0 .. 0.60


def default_export_grid(*, rpm_max: float | None = None) -> tuple[list[float], list[float]]:
    rpms = list(DEFAULT_RPM_LIST)
    if rpm_max is not None:
        rpms = [r for r in rpms if r <= float(rpm_max) + 1e-9]
        if not rpms:
            rpms = [float(rpm_max)]
    return rpms, list(DEFAULT_J_LIST)


def prop_id_for_export(spec_key: str, *, suffix: str = "BEMT") -> str:
    raw = re.sub(r"[^A-Za-z0-9_\-]+", "_", str(spec_key).strip())
    raw = re.sub(r"_+", "_", raw).strip("_") or "prop"
    return f"FANSIM_{raw}_{suffix}"


def export_bemt_pythrust_catalog(
    params: BladeParams,
    *,
    prop_id: str,
    diameter_in: float,
    pitch_in: float,
    blade_count: int,
    out_dir: str | Path,
    rpm_list: list[float] | None = None,
    j_list: list[float] | None = None,
    rho: float = RHO_AIR,
    geometry_match: str = "design_blade",
    model: str | None = None,
) -> dict[str, Any]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rpms = list(rpm_list) if rpm_list is not None else default_export_grid()[0]
    js = list(j_list) if j_list is not None else default_export_grid()[1]
    d_m = float(params.tip_radius) * 2.0 / 1000.0
    rows: list[list[float | str]] = []
    for rpm in rpms:
        for j in js:
            v = v_inf_from_j(float(j), float(rpm), d_m)
            perf = analyze(params, rpm=float(rpm), v_forward=float(v), rho=float(rho))
            nd = nondim(
                perf.thrust_n, perf.power_w, rpm=float(rpm), diameter_m=d_m,
                v_inf=float(v), rho=float(rho),
            )
            ct, cp = float(nd["CT"] or 0.0), float(nd["CP"] or 0.0)
            eta = 0.0 if nd["eta"] is None else float(nd["eta"])
            tip_mach = (math.pi * d_m * float(rpm) / 60.0) / C_AIR
            fom = float(perf.figure_of_merit) if abs(float(j)) < 1e-12 else 0.0
            tpp = (float(perf.thrust_n) / float(perf.power_w)) if perf.power_w > 0 else 0.0
            rows.append([
                float(rpm), float(v), float(nd["J"] or j), eta, ct, cp,
                float(perf.power_w), float(perf.torque_nm), float(perf.thrust_n),
                tpp, float(tip_mach), 0.0, fom,
            ])
    csv_name = f"{prop_id}.csv"
    json_name = f"{prop_id}.json"
    export_name = f"{prop_id}.export.json"
    csv_path = out_dir / csv_name
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(CSV_HEADER)
        w.writerows(rows)
    meta = {
        "id": prop_id,
        "manufacturer": "fansim",
        "model": model or prop_id,
        "diameter_in": float(diameter_in),
        "pitch_in": float(pitch_in),
        "blade_count": int(blade_count),
        "data_csv": csv_name,
    }
    json_path = out_dir / json_name
    json_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    export_meta = {
        "source": "bemt",
        "geometry_match": geometry_match,
        "prop_id": prop_id,
        "tip_radius_mm": float(params.tip_radius),
        "rpm_list": rpms,
        "j_list": js,
        "rho": float(rho),
        "n_rows": len(rows),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    export_path = out_dir / export_name
    export_path.write_text(json.dumps(export_meta, indent=2) + "\n", encoding="utf-8")
    return {
        "prop_id": prop_id,
        "csv": str(csv_path),
        "json": str(json_path),
        "export_meta": str(export_path),
        "n_rows": len(rows),
        "rpm_list": rpms,
        "j_list": js,
    }
```

Export from `__init__.py`: `export_bemt_pythrust_catalog`, `default_export_grid`, `prop_id_for_export`, `CSV_HEADER`.

- [ ] **Step 4: Run tests**

Run: `uv run python -m pytest tests/test_pythrust_export.py -v`  
Expected: PASS

- [ ] **Step 5: Commit** (when user asks)

```bash
git add fansim/propeller/pythrust_export.py fansim/propeller/__init__.py tests/test_pythrust_export.py
git commit -m "feat(prop): export BEMT polars as PyThrust JSON+CSV catalogs"
```

---

### Task 2: Propulsion load smoke + CLI

**Files:**
- Create: `tests/test_pythrust_export_propulsion.py`
- Create: `scripts/export_prop_pythrust_csv.py`
- Test: extend `tests/test_pythrust_export.py` with CLI help assert if using `_cli_parsers`

**Interfaces:**
- Consumes: Task 1 export helper
- Produces: CLI `build_parser()` + `main()`; propulsion test that `PropellerDatabase().load(tmp)` sees `prop_id`

- [ ] **Step 1: Propulsion round-trip test**

```python
# tests/test_pythrust_export_propulsion.py
from __future__ import annotations
from pathlib import Path

import pytest

pytest.importorskip("pythrust")
pytestmark = pytest.mark.propulsion


def test_pythrust_database_loads_exported_catalog(tmp_path: Path):
    from pythrust.propellers.database import PropellerDatabase
    from fansim.prop_spec import get_prop_spec
    from fansim.propeller.geometry import prop_blade_params
    from fansim.propeller.pythrust_export import export_bemt_pythrust_catalog

    spec = get_prop_spec("cine_3inch")
    prop_id = "FANSIM_LOAD_SMOKE"
    export_bemt_pythrust_catalog(
        prop_blade_params(spec),
        prop_id=prop_id,
        diameter_in=spec.diameter_in,
        pitch_in=spec.pitch_in,
        blade_count=spec.n_blades,
        out_dir=tmp_path,
        rpm_list=[5000.0],
        j_list=[0.0, 0.1],
    )
    db = PropellerDatabase()
    assert db.load(tmp_path) is True
    entry = db.get(prop_id)
    assert entry is not None
    assert float(entry.metadata.diameter_in) == pytest.approx(spec.diameter_in)
```

- [ ] **Step 2: Implement CLI**

```python
# scripts/export_prop_pythrust_csv.py
"""Export BEMT CT/CP tables as a PyThrust catalog entry (JSON + CSV).

Usage:
    uv run python scripts/export_prop_pythrust_csv.py --spec cine_3inch
    uv run python scripts/export_prop_pythrust_csv.py --spec cine_3inch --rpm 3000,7000 --j 0,0.2,0.4
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from fansim.prop_spec import get_prop_spec  # noqa: E402
from fansim.propeller.geometry import prop_blade_params  # noqa: E402
from fansim.propeller.pythrust_export import (  # noqa: E402
    export_bemt_pythrust_catalog,
    prop_id_for_export,
)
from fansim.propeller.polar import parse_float_list  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Export BEMT polar as PyThrust JSON+CSV")
    ap.add_argument("--spec", required=True, help="PropSpec key (e.g. cine_3inch)")
    ap.add_argument("--out", type=Path, default=Path("exports/pythrust"))
    ap.add_argument("--prop-id", default=None, help="override catalog id")
    ap.add_argument("--rpm", default=None, help="comma RPM list")
    ap.add_argument("--j", default=None, help="comma advance-ratio list")
    return ap


def main() -> int:
    args = build_parser().parse_args()
    spec = get_prop_spec(args.spec)
    prop_id = args.prop_id or prop_id_for_export(args.spec)
    rpm_list = parse_float_list(args.rpm)
    j_list = parse_float_list(args.j)
    out = export_bemt_pythrust_catalog(
        prop_blade_params(spec),
        prop_id=prop_id,
        diameter_in=spec.diameter_in,
        pitch_in=spec.pitch_in,
        blade_count=spec.n_blades,
        out_dir=args.out,
        rpm_list=rpm_list,
        j_list=j_list,
        geometry_match="design_blade",
        model=spec.name,
    )
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

If `parse_float_list` is not ideal for empty→None, wrap: `None if args.rpm is None else parse_float_list(args.rpm)`.

- [ ] **Step 3: Run tests**

Run: `uv run python -m pytest tests/test_pythrust_export.py -v`  
Run: `uv run --extra propulsion python -m pytest tests/test_pythrust_export_propulsion.py -v`  
Run: `uv run python scripts/export_prop_pythrust_csv.py --spec cine_3inch --rpm 3000 --j 0,0.2 --out exports/pythrust_smoke`  
Expected: PASS / JSON paths printed

- [ ] **Step 4: Commit** (when user asks)

```bash
git add scripts/export_prop_pythrust_csv.py tests/test_pythrust_export_propulsion.py
git commit -m "feat(prop): CLI + PyThrust load smoke for BEMT catalog export"
```

---

### Task 3: Prop Analyze button + docs

**Files:**
- Modify: `fansim/cockpit/prop_tab.py` (callback + `VBtn` next to Export STL)
- Modify: `docs/bibliography.md` and/or `docs/roadmap.md` (one-liner Stage 2)
- Test: optional — if cockpit has existing button-label tests, extend; otherwise manual smoke note in report is enough for UI (library already tested)

**Interfaces:**
- Consumes: `export_bemt_pythrust_catalog`, `prop_id_for_export`, `prop_editor_params`, `prop_editor_spec` / `get_prop_spec(state.prop_model)`

- [ ] **Step 1: Add `export_prop_pythrust_csv` callback** (mirror `export_prop_stl`)

```python
def export_prop_pythrust_csv():
    """Export BEMT CT/CP table as PyThrust JSON+CSV under exports/pythrust/."""
    if state.prop_busy or state.prop_refine_busy or state.prop_export_busy:
        return
    spec = prop_editor_spec()
    out_dir = Path("exports") / "pythrust"
    prop_id = prop_id_for_export(state.prop_model)

    async def task():
        state.prop_export_busy = True
        ticker, _t0 = spawn_busy_ticker(
            action="Export CT/CP",
            msg_attr="prop_export_msg",
            busy_attr="prop_export_busy",
            note="BEMT → PyThrust CSV",
        )
        state.flush()
        loop = asyncio.get_running_loop()
        try:
            from fansim.propeller.pythrust_export import (
                export_bemt_pythrust_catalog,
                prop_id_for_export as _pid,
            )
            # prop_id already computed; re-import only export helper if preferred
            result = await loop.run_in_executor(
                None,
                lambda: export_bemt_pythrust_catalog(
                    prop_editor_params(),
                    prop_id=prop_id,
                    diameter_in=spec.diameter_in,
                    pitch_in=spec.pitch_in,
                    blade_count=spec.n_blades,
                    out_dir=out_dir,
                    geometry_match="design_blade",
                    model=spec.name,
                ),
            )
        except Exception as exc:  # noqa: BLE001
            state.prop_export_msg = (
                f"⚠ CT/CP export failed: {type(exc).__name__}: {exc}"
            )
            state.prop_export_busy = False
            ticker.cancel()
            state.flush()
            return
        state.prop_export_msg = (
            f"✓ PyThrust CT/CP → {result['csv']}  ({result['n_rows']} rows)"
        )
        state.prop_export_busy = False
        ticker.cancel()
        state.flush()

    asynchronous.create_task(task())
```

Expose `ctx.export_prop_pythrust_csv = export_prop_pythrust_csv`.

UI: insert `VBtn("Export CT/CP (PyThrust)", ...)` immediately after Export STL, same `loading`/`disabled` pattern, `click=(getattr(ctx, "export_prop_pythrust_csv"),)`.

- [ ] **Step 2: Docs one-liner**

In `docs/roadmap.md` under the Track A / §4.3 note (or prop section):  
`Track A stage 2 (2026-09-21): BEMT→PyThrust CSV export (Analyze + CLI); not a substitute for §4.3 CFD.`

In `docs/bibliography.md` PyThrust bullet: add **→ code:** `fansim/propeller/pythrust_export.py` (custom BEMT catalog bridge).

- [ ] **Step 3: Manual smoke**

Run cockpit (or at least import):  
`uv run python -c "from fansim.cockpit.prop_tab import setup_prop_tab"`  
Expected: import OK (CadQuery teardown AV on exit OK).

- [ ] **Step 4: Commit** (when user asks)

```bash
git add fansim/cockpit/prop_tab.py docs/bibliography.md docs/roadmap.md
git commit -m "feat(prop): Analyze Export CT/CP (PyThrust) button + docs"
```

---

## Spec coverage checklist

| Spec requirement | Task |
|------------------|------|
| `default_export_grid` / defaults | Task 1 |
| `export_bemt_pythrust_catalog` JSON+CSV+export.json | Task 1 |
| Header exact + FoM/Mach/Re honesty | Task 1 |
| Propulsion `PropellerDatabase.load` smoke | Task 2 |
| CLI `--spec` / `--rpm` / `--j` | Task 2 |
| Analyze button beside STL | Task 3 |
| Bib / roadmap note | Task 3 |
| No bundled APC overwrite / no Optimize batch | Global |

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-21-prop-pythrust-bemt-export.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — execute tasks in this session with checkpoints  

Which approach?
