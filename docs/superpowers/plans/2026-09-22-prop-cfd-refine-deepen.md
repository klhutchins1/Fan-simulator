# Prop CFD Refine Deepen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `--drift-tol` for refine freezes, wire smoke/refine mesh presets into the Prop CFD refine top-N card, run the Docker refine campaign on both drone_radial STLs, and freeze `*_refine.json` only when force-tail drift &lt; 10%.

**Architecture:** Freezer gains an explicit drift tolerance (default 25% for smoke back-compat). Cockpit Prop Optimize CFD card adds a Smoke/Refine preset that passes `base_cell`/`iters` through existing `refine_pareto_cfd(**eval_kw)`. Manual Docker campaign writes parallel refine fixtures without touching smoke JSON.

**Tech Stack:** Python 3.12 (uv), pytest, OpenFOAM v2406 Docker, existing `evaluate_prop_cfd` / `cfd_fixture` / Prop Trame card.

**Spec:** `docs/superpowers/specs/2026-09-22-prop-cfd-refine-deepen-design.md`

## Global Constraints

- Smoke fixtures under `validation/reference/drone_radial/cfd/*_smoke.json` must **not** be overwritten.
- Default `FORCE_DRIFT_TOL_PCT` stays **25.0**; refine uses **10** via `--drift-tol 10` / explicit `drift_tol_pct=10`.
- Refine knobs: `base_cell=0.004`, `iters=600`, `procs=8`, RPM Ma≈0.35 (obj_1 **38100**, obj_2 **25257**).
- Docker image: `opencfd/openfoam-default:2406`. CI: no Docker (`-m "not docker and not slow"`).
- Cockpit: extend existing CFD refine card only — no second button, no Optuna-in-loop CFD.
- Preset table: Smoke `0.005`/`400` (default); Refine `0.004`/`600`.
- Skip staging `catalog/catalog.db`. Commit when the user asks (plan steps may still list commits).

## File map

| File | Role |
|------|------|
| `scripts/freeze_prop_cfd_fixture.py` | `--drift-tol` |
| `fansim/cockpit/prop_tab.py` | CFD mesh preset state + pass knobs |
| `tests/test_prop_cfd_fixture.py` | Freezer `--drift-tol` + refine fixture load |
| `tests/test_prop_bemt_gate.py` | Assert `base_cell`/`iters` forwarded |
| `validation/reference/drone_radial/cfd/*_refine.json` | After green Docker (optional per STL) |
| `docs/validation/drone_radial_open_air_cfd.md` | Refine section |
| `docs/roadmap.md` | §4.3 refine note |
| `docs/superpowers/specs/2026-09-22-prop-cfd-refine-deepen-design.md` | Mark implemented |

Reuse unchanged: `fansim/propeller/cfd.py`, `fansim/propeller/optimize.py` (`**eval_kw` already), `fansim/propeller/cfd_fixture.py` defaults.

---

### Task 1: Freezer `--drift-tol`

**Files:**
- Modify: `scripts/freeze_prop_cfd_fixture.py`
- Modify: `tests/test_prop_cfd_fixture.py`

**Interfaces:**
- Produces: CLI `--drift-tol` (float, default `25.0`) passed to `prop_cfd_smoke_gate(..., drift_tol_pct=...)` when `--require-gate`.

- [ ] **Step 1: Write failing test**

Extend `test_freeze_cli_parser_has_required_flags` (or add):

```python
def test_freeze_cli_declares_drift_tol():
    import importlib.util
    from pathlib import Path

    path = Path("scripts/freeze_prop_cfd_fixture.py")
    spec = importlib.util.spec_from_file_location("freeze_prop_cfd_fixture", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    ap = mod.build_parser()
    args = ap.parse_args([
        "--result", "r.json", "--out", "o.json", "--id", "x", "--stl", "s.stl",
        "--drift-tol", "10",
    ])
    assert args.drift_tol == pytest.approx(10.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_prop_cfd_fixture.py::test_freeze_cli_declares_drift_tol -v --tb=short`  
Expected: FAIL — no `drift_tol` / unknown arg.

- [ ] **Step 3: Implement `--drift-tol`**

In `build_parser()`:

```python
ap.add_argument("--drift-tol", type=float, default=25.0,
                help="force-tail drift %% gate when --require-gate (default 25 smoke)")
```

In `main()` when `args.require_gate`:

```python
ok, reasons = prop_cfd_smoke_gate(
    result, case_dir=case_dir, drift_tol_pct=float(args.drift_tol),
)
```

- [ ] **Step 4: Run tests**

Run: `uv run python -m pytest tests/test_prop_cfd_fixture.py -q --tb=short`  
Expected: PASS (skip OK if no refine fixtures yet).

- [ ] **Step 5: Commit**

```bash
git add scripts/freeze_prop_cfd_fixture.py tests/test_prop_cfd_fixture.py
git commit -m "feat(prop): freeze CLI --drift-tol for refine 10% gate"
```

---

### Task 2: Forward `base_cell` / `iters` through `refine_pareto_cfd` (test)

**Files:**
- Modify: `tests/test_prop_bemt_gate.py`
- Verify: `fansim/propeller/optimize.py` (no change if `**eval_kw` already works)

**Interfaces:**
- Consumes: `refine_pareto_cfd(spec, pareto, out_dir, *, n_top, bemt_floor_g, **eval_kw)`
- Produces: proof that `base_cell` and `iters` reach `evaluate_prop_cfd`

- [ ] **Step 1: Write failing test**

Append to `tests/test_prop_bemt_gate.py`:

```python
def test_refine_pareto_cfd_forwards_mesh_knobs(tmp_path, monkeypatch):
    import fansim.propeller.optimize as po
    from fansim.prop_spec import get_prop_spec

    captured = {}

    def fake_eval(spec, workdir, **kw):
        captured.update(kw)
        return {"thrust_g": 100.0, "bemt_thrust_g": 80.0, "skipped": False}

    monkeypatch.setattr("fansim.propeller.cfd.evaluate_prop_cfd", fake_eval)
    spec = get_prop_spec("fpv_5inch")
    pareto = [
        {
            "thrust_g": 100.0,
            "params": {
                "n_blades": 3,
                "pitch_in": 4.3,
                "chord_root": 0.2,
                "chord_mid": 0.26,
                "chord_tip": 0.1,
                "camber": 0.04,
            },
        }
    ]
    rows = po.refine_pareto_cfd(
        spec, pareto, tmp_path, n_top=1, bemt_floor_g=0.0,
        base_cell=0.004, iters=600,
    )
    assert not rows[0]["skipped"]
    assert captured.get("base_cell") == pytest.approx(0.004)
    assert captured.get("iters") == 600
```

Use the same monkeypatch target as `test_refine_pareto_cfd_respects_floor`: `fansim.propeller.cfd.evaluate_prop_cfd`. Capture via `captured.update(kw)` in `fake_eval`.

- [ ] **Step 2: Run test**

Run: `uv run python -m pytest tests/test_prop_bemt_gate.py::test_refine_pareto_cfd_forwards_mesh_knobs -v --tb=short`  
Expected: PASS if `**eval_kw` works; FAIL only if forwarding is broken — then fix `optimize.py`.

- [ ] **Step 3: Commit only if code changed; else skip commit**

```bash
# If test alone: include test in Task 3 commit, or:
git add tests/test_prop_bemt_gate.py
git commit -m "test(prop): refine_pareto_cfd forwards base_cell and iters"
```

---

### Task 3: Prop cockpit Smoke / Refine preset

**Files:**
- Modify: `fansim/cockpit/prop_tab.py`
- Modify: `tests/test_prop_bemt_gate.py` or add a tiny helper test if state helpers are extracted

**Interfaces:**
- State: `prop_cfd_mesh_preset` ∈ `{"smoke","refine"}` (default `"smoke"`)
- Mapping:
  - smoke → `base_cell=0.005`, `iters=400`
  - refine → `base_cell=0.004`, `iters=600`
- `refine_prop_cfd` passes those into `refine_prop_pareto_cfd(..., base_cell=..., iters=...)`
- UI: `VSelect` or two-item select labeled “CFD mesh” next to CFD top N / BEMT floor

- [ ] **Step 1: Add preset helper (testable)**

In `fansim/cockpit/prop_tab.py` (module level or small function near top of callbacks):

```python
def prop_cfd_mesh_knobs(preset: str) -> tuple[float, int]:
    p = (preset or "smoke").strip().lower()
    if p == "refine":
        return (0.004, 600)
    return (0.005, 400)
```

Test in `tests/test_prop_bemt_gate.py` or `tests/test_prop_cfd_fixture.py`:

```python
def test_prop_cfd_mesh_knobs():
    from fansim.cockpit.prop_tab import prop_cfd_mesh_knobs
    assert prop_cfd_mesh_knobs("smoke") == (0.005, 400)
    assert prop_cfd_mesh_knobs("refine") == (0.004, 600)
    assert prop_cfd_mesh_knobs("unknown") == (0.005, 400)
```

- [ ] **Step 2: Run test RED then implement helper + state + UI + call site**

Init: `state.prop_cfd_mesh_preset = "smoke"`.

In `refine_prop_cfd` task lambda:

```python
base_cell, iters = prop_cfd_mesh_knobs(str(state.prop_cfd_mesh_preset))
...
lambda: refine_prop_pareto_cfd(
    base, pareto, out,
    n_top=n_top, bemt_floor_g=floor,
    spec_key=str(state.prop_model),
    base_cell=base_cell, iters=iters,
),
```

Busy note includes preset name and knobs.

UI (after BEMT floor col, adjust cols): add

```python
v3.VSelect(
    label="CFD mesh",
    v_model=("prop_cfd_mesh_preset",),
    items=["smoke", "refine"],
    density="compact",
    variant="outlined",
    hide_details=True,
)
```

Caption text: mention Smoke vs Refine presets.

- [ ] **Step 3: Run tests**

```bash
uv run python -m pytest tests/test_prop_bemt_gate.py tests/test_prop_cfd_fixture.py -q --tb=short
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add fansim/cockpit/prop_tab.py tests/test_prop_bemt_gate.py
git commit -m "feat(prop): Smoke/Refine mesh preset on CFD refine card"
```

---

### Task 4: Docker refine campaign (manual)

**Files:**
- Create (local): `runs/drone_radial_cfd/obj_1_refine/`, `obj_2_refine/`
- Create (if gate pass): `validation/reference/drone_radial/cfd/obj_*_refine.json`
- Modify: `docs/validation/drone_radial_open_air_cfd.md`, `docs/roadmap.md`, design spec status

**Prereq:** `image_available()` True.

- [ ] **Step 1: Confirm Docker**

```bash
uv run python -c "from fansim.cfd.runner import image_available, DEFAULT_IMAGE; print(DEFAULT_IMAGE, image_available())"
```

- [ ] **Step 2: Optional dry-runs**

```bash
uv run python scripts/evaluate_prop_cfd.py \
  --stl validation/reference/drone_radial/obj_1_ccw_impeller.stl \
  --rpm 38100 --base-cell 0.004 --iters 600 --procs 8 \
  --out runs/drone_radial_cfd/_dry_run_refine/obj_1 --dry-run
uv run python scripts/evaluate_prop_cfd.py \
  --stl validation/reference/drone_radial/obj_2_ccw.stl \
  --rpm 25257 --base-cell 0.004 --iters 600 --procs 8 \
  --out runs/drone_radial_cfd/_dry_run_refine/obj_2 --dry-run
```

- [ ] **Step 3: Full obj_1 refine**

```bash
uv run python scripts/evaluate_prop_cfd.py \
  --stl validation/reference/drone_radial/obj_1_ccw_impeller.stl \
  --rpm 38100 --base-cell 0.004 --iters 600 --procs 8 \
  --out runs/drone_radial_cfd/obj_1_refine
```

Gate:

```bash
uv run python -c "
import json
from pathlib import Path
from fansim.propeller.cfd_fixture import prop_cfd_smoke_gate, force_z_tail_drift_pct
r=json.loads(Path('runs/drone_radial_cfd/obj_1_refine/result.json').read_text())
print('drift', force_z_tail_drift_pct('runs/drone_radial_cfd/obj_1_refine'))
print(prop_cfd_smoke_gate(r, case_dir='runs/drone_radial_cfd/obj_1_refine', drift_tol_pct=10))
"
```

If pass:

```bash
uv run python scripts/freeze_prop_cfd_fixture.py \
  --result runs/drone_radial_cfd/obj_1_refine/result.json \
  --out validation/reference/drone_radial/cfd/obj_1_ccw_impeller_refine.json \
  --id obj_1_ccw_impeller_refine \
  --stl validation/reference/drone_radial/obj_1_ccw_impeller.stl \
  --spin -1 --base-cell 0.004 --iters 600 --procs 8 \
  --drift-tol 10 --require-gate \
  --date 2026-09-22
```

Set notes in fixture (or via build) to mention refine + 10% gate. Do **not** touch smoke JSON.

- [ ] **Step 4: Full obj_2 refine (always run; independent)**

Same pattern with `--rpm 25257`, `--stl …/obj_2_ccw.stl`, `--out …/obj_2_refine`, id `obj_2_ccw_refine`.

- [ ] **Step 5: Docs**

Update `docs/validation/drone_radial_open_air_cfd.md`:
- Refine knobs table
- 10% gate for refine vs 25% smoke
- Results rows for refine (pass metrics or “gate failed”)
- Point at `*_refine.json` if present

Roadmap §4.3: one bullet for refine deepen date.

Design spec status: `implemented` if both stages land, or `implemented-partial` if cockpit done but both refine gates failed.

- [ ] **Step 6: Fixture load test**

Extend `test_committed_smoke_fixtures_if_present` or add:

```python
def test_committed_refine_fixtures_if_present():
    # glob *_refine.json; same stamp checks; skip if none
```

- [ ] **Step 7: Run unit tests + commit**

```bash
uv run python -m pytest tests/test_prop_cfd_fixture.py tests/test_prop_bemt_gate.py -q --tb=short
git add validation/reference/drone_radial/cfd/ docs/validation/drone_radial_open_air_cfd.md \
  docs/roadmap.md docs/superpowers/specs/2026-09-22-prop-cfd-refine-deepen-design.md \
  tests/test_prop_cfd_fixture.py
git commit -m "docs(prop): drone_radial refine CFD campaign + fixtures"
```

(Omit fixture paths from `git add` if none passed the gate.)

---

## Spec coverage checklist

| Spec requirement | Task |
|------------------|------|
| `--drift-tol` / 10% refine freeze | Task 1 |
| Smoke fixtures untouched | Task 4 |
| Both STL refine campaigns | Task 4 |
| Cockpit Smoke/Refine preset | Task 3 |
| `base_cell`/`iters` → evaluate | Task 2–3 |
| Validation + roadmap docs | Task 4 |
| CI no Docker | Tasks 1–3 |

## Plan self-review

- No TBD placeholders; RPM/knobs copied from spec.
- `refine_pareto_cfd` already has `**eval_kw` — Task 2 verifies.
- Default gate 25% unchanged in library.
