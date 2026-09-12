# Hub-First Cockpit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the cockpit hub-first: Design is 3D for the selected hub, Results rank only designs that belong to that hub, and Library holds every recipe so a too-big fan can be placed onto the current hub.

**Architecture:** Pure functions in `fansim/cockpit/labels.py` and `fansim/cockpit/placement.py` do naming and Fit/Scale. `fansim/catalog.py` classifies rows onto hub keys. `fansim/cockpit/app.py` becomes a hub picker + Design/Results/Library layout that calls those functions. Optimizer CLI is unchanged.

**Tech Stack:** Python 3.12, pytest, CadQuery/numpy geometry already in `fansim.geometry.blade`, Trame/Vuetify3 cockpit, SQLite catalog.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-01-hub-first-cockpit-design.md`
- Python `>=3.12,<3.13` via `uv`; tests: `uv run python -m pytest -q -m "not docker and not slow"`
- A12x25 motor cup is **measured**: `cavity_dia_mm=37.25`, min hub radius `37.25/2 + 1.2 = 19.825` mm; frame tip max **110 mm**; depth max **25 mm**
- Do not rewrite `runs/` folder names; add English labels only
- Fit envelope and Scale always create a **new** design; never mutate the library original
- Propeller tab stays
- No OGV, literature presets, tip-gap study, or new optimizer campaign in this plan
- Windows: no `★` in CLI output; CadQuery may heap-corrupt on process teardown — judge tests by assertion result, not exit 3221226356
- Commit after each task; do not `git push`

---

## File structure

| Path | Responsibility |
|---|---|
| `config/run_labels.yaml` | Human names for existing run folders |
| `fansim/cockpit/labels.py` | `run_label(run_id) -> str` |
| `fansim/cockpit/placement.py` | Fit envelope, Scale, classify-without-CFD, changelog |
| `fansim/catalog.py` | Extra columns, classify on build, `results_for_hub` |
| `fansim/cockpit/app.py` | Hub bar, Design/Results/Library, wire placement |
| `scripts/catalog.py` | ASCII-safe list |
| `tests/test_mountable.py` | Measured cup |
| `tests/test_labels.py` | Labels |
| `tests/test_placement.py` | Fit/Scale |
| `tests/test_catalog.py` | Classification + hub Results set |
| `docs/known-issues.md` | Point at spec; drop stale GPU-idle claims |

---

### Task 1: Measured A12x25 cup in mountable tests

**Files:**
- Modify: `tests/test_mountable.py`

**Interfaces:**
- Consumes: `mount_min_hub_radius(get_fan_spec("a12x25"))` (already returns 19.825)
- Produces: tests that match the measured cup so later classify/Fit tests are not lying

The current test asserts `52.0 / 2 + 1.2` (27.2 mm) and gates `hub_radius=21.5` as unmountable. After the 2026-08-31 measurement, 21.5 mm **fits**. Using 21.5 as a reject case would make the test wrong.

- [ ] **Step 1: Write the failing assertions** (edit the existing tests in place)

Replace `tests/test_mountable.py` with:

```python
"""--mountable optimizer constraint: search only hubs that can house the motor + gate the rest."""

from __future__ import annotations

import optuna

from fansim.fan_spec import get_fan_spec, mount_min_hub_radius
from fansim.geometry.blade import BladeParams
from fansim.optimize.objectives import evaluate_candidate
from fansim.optimize.search_space import suggest_params

optuna.logging.set_verbosity(optuna.logging.WARNING)

A12_MIN_HUB = 37.25 / 2.0 + 1.2  # 19.825 mm — measured cup 2026-08-31


def test_mount_min_hub_radius():
    assert mount_min_hub_radius(get_fan_spec("a12x25")) == A12_MIN_HUB
    from fansim.fan_spec import FanSpec
    bare = FanSpec(name="x", tip_dia_mm=(1, 2), hub_dia_mm=(1, 2), depth_mm=(1, 2),
                   rpm=1, voltage_v=1, max_current_a=1)
    assert mount_min_hub_radius(bare) is None


def test_mountable_range_forces_big_hub():
    study = optuna.create_study(directions=["maximize", "maximize", "maximize"])
    lo, hi = A12_MIN_HUB, 24.0
    for _ in range(15):
        t = study.ask()
        bp = suggest_params(t, hub_radius_range=(lo, hi))
        assert lo <= bp.hub_radius <= hi, f"hub {bp.hub_radius} outside mountable range"
        study.tell(t, (0.0, 0.0, 0.0))


def test_extended_without_mountable_can_go_small():
    study = optuna.create_study(directions=["maximize", "maximize", "maximize"])
    small = False
    for _ in range(20):
        t = study.ask()
        bp = suggest_params(t, with_extended=True)   # EXTENDED hub is (17, 28)
        small = small or bp.hub_radius < A12_MIN_HUB
        study.tell(t, (0.0, 0.0, 0.0))
    assert small, "extended search (no --mountable) should sample hubs below the mount minimum"


def test_gate_rejects_unmountable_hub(tmp_path):
    # 16.5 mm is below the measured 19.825 mm cup + wall
    res = evaluate_candidate(BladeParams(hub_radius=16.5), tmp_path / "d", require_mountable=True)
    assert not res.feasible
    assert "not mountable" in res.reason


def test_gate_accepts_measured_min_hub(tmp_path):
    res = evaluate_candidate(BladeParams(hub_radius=21.5), tmp_path / "d", require_mountable=True)
    # 21.5 >= 19.825 — must NOT be rejected on mount (may still fail later gates / CFD)
    assert "not mountable" not in (res.reason or "")
```

- [ ] **Step 2: Run tests**

Run: `uv run python -m pytest -q tests/test_mountable.py -m "not docker" --tb=short`

Expected: `test_mount_min_hub_radius` PASS (code already has 37.25). `test_gate_accepts_measured_min_hub` PASS. `test_gate_rejects_unmountable_hub` PASS with 16.5. If `evaluate_candidate` still tries CFD after the mount gate for 21.5, that test may be slow or need Docker — if it starts meshing, stop and skip CFD by checking only that the infeasible reason is not mount: if `res.feasible` is False for another cheap gate, still assert `"not mountable" not in res.reason`.

- [ ] **Step 3: Commit**

```bash
git add tests/test_mountable.py
git commit -m "Align mountable tests with the measured A12x25 motor cup."
```

---

### Task 2: Human run labels

**Files:**
- Create: `config/run_labels.yaml`
- Create: `fansim/cockpit/labels.py`
- Test: `tests/test_labels.py`

**Interfaces:**
- Consumes: YAML at `config/run_labels.yaml`
- Produces: `run_label(run_id: str, labels_path: Path | None = None) -> str`

- [ ] **Step 1: Write the failing test**

Create `tests/test_labels.py`:

```python
from pathlib import Path

from fansim.cockpit.labels import run_label


def test_known_run_uses_english_name():
    assert run_label("opt_realframe") == "Tip constrained to 110 mm A12x25 frame"


def test_unknown_run_echoes_folder_name():
    assert run_label("opt_brand_new") == "opt_brand_new"


def test_empty_run_is_empty():
    assert run_label("") == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_labels.py -v`

Expected: FAIL with `ModuleNotFoundError: fansim.cockpit.labels`

- [ ] **Step 3: Write YAML + implementation**

Create `config/run_labels.yaml` with exactly the mapping from the spec:

```yaml
opt_run1: "First unconstrained 120 mm search"
opt_v2: "Second unconstrained search"
opt_v3: "Third unconstrained search"
opt_guided: "Guided search (design-rules bounds)"
opt_noise: "Search with noise objective"
opt_noise2: "Noise objective, second pass"
opt_extended: "Search with hub/thickness DOFs"
opt_extended2: "Extended search, second pass"
opt_mountable: "Hub sized for old 52 mm motor estimate"
opt_realframe: "Tip constrained to 110 mm A12x25 frame"
opt_overnight: "Overnight unconstrained search"
opt_loadcap: "Solidity-floor (load spreading) search"
opt_val: "Validation search"
```

Create `fansim/cockpit/labels.py`:

```python
"""English names for optimizer run folders. Folder ids on disk stay unchanged."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

_DEFAULT = Path(__file__).resolve().parents[2] / "config" / "run_labels.yaml"


@lru_cache(maxsize=4)
def _load(path: str) -> dict[str, str]:
    p = Path(path)
    if not p.exists():
        return {}
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return {str(k): str(v) for k, v in data.items()}


def run_label(run_id: str, labels_path: Path | None = None) -> str:
    """Return the human label for a run folder, or the folder name if unknown."""
    if not run_id:
        return ""
    path = str(labels_path or _DEFAULT)
    return _load(path).get(run_id, run_id)
```

- [ ] **Step 4: Run tests**

Run: `uv run python -m pytest tests/test_labels.py -v`

Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add config/run_labels.yaml fansim/cockpit/labels.py tests/test_labels.py
git commit -m "Give optimizer runs English names without renaming folders."
```

---

### Task 3: Fit envelope and Scale (pure functions)

**Files:**
- Create: `fansim/cockpit/placement.py`
- Test: `tests/test_placement.py`
- Modify later (Task 6): `fansim/cockpit/app.py` will call these and delete the per-slider snap closures

**Interfaces:**
- Consumes: `FanSpec`, `mount_min_hub_radius`, `blade_from_flat`, `check_build`
- Produces:
  - `PlaceChange(field: str, before: float, after: float, unit: str = "mm")`
  - `PlaceResult(flat: dict, changes: list[PlaceChange], fit_status: str, leftover: str)`
  - `fit_envelope(flat: dict, spec: FanSpec) -> PlaceResult`
  - `scale_to_hub(flat: dict, spec: FanSpec) -> PlaceResult` (scale then `fit_envelope`)
  - `preview_changes(changes: list[PlaceChange]) -> str`
  - `nominal_fits_spec(flat: dict, spec: FanSpec) -> bool`

Copy the **section-point** tip/depth helpers from `fansim/cockpit/app.py` (`_blade_max_dia`, `_blade_z_extent`, ~lines 209–250) into `placement.py` so catalog/cockpit do not depend on Trame state. Those helpers import `fansim.geometry.blade` (CadQuery). Keep them in placement, not catalog.

Length keys to scale: `hub_radius`, `tip_radius`, `chord_root`, `chord_mid`, `chord_tip`, `sweep_mid`, `sweep_tip`, `skew_mid`, `skew_tip`, `le_sweep_mid`, `le_sweep_tip`, `hub_height`, `hub_nose`, `winglet_sweep`. Do **not** scale: `n_blades`, any `stagger_*`, `lean_*`, `thickness_*`, `max_camber`, `camber_pos`, `winglet_lean`, feature amps/counts.

Target tip radius for scale: `spec.tip_dia_mm[1] / 2.0 - 2.0` (2 mm bulge margin). If source `tip_radius` missing, use 56.5. If source tip_radius <= 0, `PlaceResult` with same flat, empty changes, leftover `"source tip radius <= 0"`, fit_status `"unplaced"`.

Fit envelope order (mutate a copy of `flat`):
1. Hub radius = max(current, `mount_min_hub_radius(spec)` or current if None)
2. Tip: iterate like current `snap_tip_to_frame` until `_blade_max_dia <= spec.tip_dia_mm[1] - 0.15` or tip_radius < 20
3. Depth: flatten sweep + LE by factors 1.0 … 0.0; if still over, scale all three staggers by 0.97 … 0.70
4. Hub height: if `spec.motor_mount.min_hub_height_mm` and current `hub_height` (0 = auto) is below that, set `hub_height` to the min

Then `check_build(spec, built_tip_dia, hub_dia, depth)` → `fits` or `over_spec`. `leftover` is the check_build reason when over.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_placement.py`. Use a **minimal flat dict** (all keys `blade_from_flat` needs):

```python
from copy import deepcopy

from fansim.cockpit.placement import (
    fit_envelope,
    nominal_fits_spec,
    preview_changes,
    scale_to_hub,
)
from fansim.fan_spec import get_fan_spec
from fansim.optimize.search_space import blade_from_flat


def _base(**kw):
    d = dict(
        n_blades=9, stagger_root=26, stagger_mid=26, stagger_tip=22,
        chord_root=34, chord_mid=44, chord_tip=38,
        sweep_mid=3, sweep_tip=5, max_camber=0.05, camber_pos=0.4,
        lean_mid=14, lean_tip=26, le_sweep_mid=0, le_sweep_tip=0,
        skew_mid=0, skew_tip=0, winglet_span=0.85, winglet_sweep=0, winglet_lean=0,
        hub_radius=16.5, tip_radius=59.0, hub_height=0, hub_profile="cylinder",
        hub_nose=0, thickness_root=0.08, thickness_mid=0.05, thickness_tip=0.03,
    )
    d.update(kw)
    return d


def test_fit_envelope_raises_hub_to_measured_cup():
    spec = get_fan_spec("a12x25")
    r = fit_envelope(_base(), spec)
    assert r.flat["hub_radius"] >= 19.825
    assert r.flat["hub_radius"] != 16.5
    assert any(c.field == "hub_radius" for c in r.changes)


def test_fit_envelope_shrinks_tip_inside_110mm_frame():
    spec = get_fan_spec("a12x25")
    r = fit_envelope(_base(), spec)
    bp = blade_from_flat(r.flat)
    from fansim.cockpit.placement import blade_max_dia
    assert blade_max_dia(bp) <= spec.tip_dia_mm[1] + 0.01


def test_scale_halves_chords_not_stagger():
    spec = get_fan_spec("a12x25")
    src = _base(tip_radius=110.0, chord_root=40, chord_mid=40, chord_tip=40, stagger_mid=30)
    # scale_to_hub uses target tip ~ 110/2 - 2 = 53; s ≈ 53/110
    r = scale_to_hub(src, spec)
    assert r.flat["stagger_mid"] == 30
    assert r.flat["chord_root"] < 40
    assert r.flat["n_blades"] == 9


def test_scale_refuses_nonpositive_tip():
    spec = get_fan_spec("a12x25")
    r = scale_to_hub(_base(tip_radius=0.0), spec)
    assert r.flat["tip_radius"] == 0.0
    assert r.fit_status == "unplaced"
    assert "tip radius" in r.leftover.lower()


def test_preview_lists_changes():
    spec = get_fan_spec("a12x25")
    r = fit_envelope(_base(), spec)
    text = preview_changes(r.changes)
    assert "hub_radius" in text
    assert "CFD will be stale" in text


def test_nominal_fits_spec_rejects_oversized_tip():
    spec = get_fan_spec("a12x25")
    assert not nominal_fits_spec(_base(hub_radius=21.5, tip_radius=59.0), spec)
    assert nominal_fits_spec(_base(hub_radius=21.0, tip_radius=49.8), spec)


def test_parent_flat_unchanged():
    spec = get_fan_spec("a12x25")
    original = _base()
    snapshot = deepcopy(original)
    fit_envelope(original, spec)
    assert original == snapshot
```

`nominal_fits_spec` rule (no CadQuery mesh): fits iff
- hub_radius >= `mount_min_hub_radius(spec)` (if mount defined)
- hub diameter `2*hub_radius` inside `spec.hub_dia_mm`
- `2 * tip_radius + 4.0 <= spec.tip_dia_mm[1]` (4 mm bulge allowance)

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_placement.py -v --tb=short`

Expected: FAIL `ModuleNotFoundError: fansim.cockpit.placement`

- [ ] **Step 3: Implement `fansim/cockpit/placement.py`**

Implement the helpers and functions named in **Interfaces**. Port `_blade_max_dia` / `_blade_z_extent` from `app.py` as public `blade_max_dia(params)` and `blade_z_extent(params)`. `fit_envelope` and `scale_to_hub` must `deepcopy` the input dict.

`preview_changes`:

```python
def preview_changes(changes: list[PlaceChange]) -> str:
    if not changes:
        return "No geometry changes. CFD will be stale."
    lines = [f"{c.field}: {c.before:.2f} → {c.after:.2f} {c.unit}" for c in changes]
    lines.append("CFD will be stale")
    return "\n".join(lines)
```

`fit_status`: `"fits"` if `check_build` ok (use `blade_max_dia` and `blade_z_extent` for the check), else `"over_spec"`. Scale failure (tip <= 0): `"unplaced"`.

- [ ] **Step 4: Run tests**

Run: `uv run python -m pytest tests/test_placement.py -v --tb=short`

Expected: PASS. If CadQuery tears down with 3221226356 after green assertions, still treat as pass.

- [ ] **Step 5: Commit**

```bash
git add fansim/cockpit/placement.py tests/test_placement.py
git commit -m "Add Fit envelope and Scale-to-hub as tested placement ops."
```

---

### Task 4: Catalog classification and hub-scoped Results

**Files:**
- Modify: `fansim/catalog.py`
- Modify: `scripts/catalog.py`
- Modify: `tests/test_catalog.py`

**Interfaces:**
- Consumes: `nominal_fits_spec`, `fan_spec_names`, `get_fan_spec`, `run_label`
- Produces:
  - `CatalogEntry.hub_models: list[str]`
  - `CatalogEntry.fit_status: str`  (`fits` if hub_models else `unplaced`; placed rows set later)
  - `CatalogEntry.placed_on: str`
  - `CatalogEntry.cfd_stale: bool`
  - `CatalogEntry.parent_id: str`
  - `CatalogEntry.place_op: str`
  - `classify_entry(e: CatalogEntry) -> CatalogEntry` (mutates/returns with hub_models filled)
  - `results_for_hub(entries: list[CatalogEntry], hub_key: str) -> list[CatalogEntry]`
    — include if `hub_key in e.hub_models` or `e.placed_on == hub_key`; Results plot uses those with `not e.cfd_stale`

SQLite: add columns with defaults so old code paths in tests keep working. Extend `_COLS` and `CREATE TABLE`. `json.dumps` for `hub_models`.

On `build_catalog`, after assembling entries, call `classify_entry` for each (skip if `placed_on` already set — rebuild of placed rows: if params exist, still fill `hub_models` from geometry, keep `placed_on`).

`results_for_hub` is a module function used by cockpit and tests.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_catalog.py`)

```python
def test_classify_puts_small_blade_on_a12x25(tmp_path):
    from fansim.catalog import results_for_hub
    runs = tmp_path / "runs"
    params = {
        "n_blades": 5, "hub_radius": 21.0, "tip_radius": 49.8,
        "stagger_root": 26, "stagger_mid": 26, "stagger_tip": 22,
        "chord_root": 34, "chord_mid": 30, "chord_tip": 28,
        "sweep_mid": 0, "sweep_tip": 2, "max_camber": 0.02,
    }
    _make_run(runs, "opt_realframe", [{"trial": 22, "cfm_free": 53.9, "cfm_load": 50.0,
                                       "efficiency": 30.0, "params": params}])
    db = tmp_path / "cat.db"
    build_catalog(runs_dir=runs, store_dir=tmp_path / "none", db=db)
    e = get_entry("opt_realframe_t22", db)
    assert "a12x25" in e.hub_models
    assert e.fit_status == "fits"
    hits = results_for_hub(load_catalog(db), "a12x25")
    assert any(x.design_id == "opt_realframe_t22" for x in hits)


def test_oversized_tip_not_in_a12x25_results(tmp_path):
    from fansim.catalog import results_for_hub
    runs = tmp_path / "runs"
    params = {"n_blades": 9, "hub_radius": 16.5, "tip_radius": 59.0,
              "stagger_root": 26, "stagger_mid": 26, "stagger_tip": 22,
              "chord_root": 34, "chord_mid": 44, "chord_tip": 38,
              "sweep_mid": 3, "sweep_tip": 5, "max_camber": 0.05}
    _make_run(runs, "opt_run1", [{"trial": 9038, "cfm_free": 92.4, "cfm_load": 87.0,
                                  "efficiency": 35.0, "params": params}])
    db = tmp_path / "cat.db"
    build_catalog(runs_dir=runs, store_dir=tmp_path / "none", db=db)
    e = get_entry("opt_run1_t9038", db)
    assert "a12x25" not in (e.hub_models or [])
    hits = results_for_hub(load_catalog(db), "a12x25")
    assert all(x.design_id != "opt_run1_t9038" for x in hits)


def test_placed_on_includes_in_results_even_if_geometry_borderline(tmp_path):
    from fansim.catalog import results_for_hub, CatalogEntry
    e = CatalogEntry(design_id="placed_t1", hub_models=[], placed_on="a12x25",
                     cfd_stale=True, fit_status="fits")
    hits = results_for_hub([e], "a12x25")
    assert hits[0].design_id == "placed_t1"
```

Existing tests must still pass: default new fields to `hub_models=[]`, `fit_status="unplaced"`, `placed_on=""`, `cfd_stale=False`, `parent_id=""`, `place_op=""`. Params without hub/tip (old tests) → `hub_models=[]`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_catalog.py -v --tb=short`

Expected: FAIL on missing `hub_models` / `results_for_hub`

- [ ] **Step 3: Implement catalog fields + classify + results_for_hub**

In `CatalogEntry` add the six fields with defaults.

`classify_entry`:

```python
def classify_entry(e: CatalogEntry) -> CatalogEntry:
    from fansim.cockpit.placement import nominal_fits_spec
    from fansim.fan_spec import fan_spec_names, get_fan_spec
    p = e.params or {}
    fitted = []
    for key in fan_spec_names():
        try:
            if nominal_fits_spec(p, get_fan_spec(key)):
                fitted.append(key)
        except (KeyError, TypeError, ValueError):
            continue
    e.hub_models = fitted
    if e.placed_on:
        e.fit_status = "fits" if (e.placed_on in fitted or e.fit_status == "over_spec") else e.fit_status
    else:
        e.fit_status = "fits" if fitted else "unplaced"
    return e
```

For `nominal_fits_spec` on incomplete params (only `n_blades`): return False (catch KeyError inside `nominal_fits_spec` and return False).

`results_for_hub`:

```python
def results_for_hub(entries: list[CatalogEntry], hub_key: str) -> list[CatalogEntry]:
    return [e for e in entries if hub_key in (e.hub_models or []) or e.placed_on == hub_key]
```

Wire `classify_entry` at the end of `build_catalog` before INSERT. Extend `_COLS` and CREATE TABLE / INSERT.

`scripts/catalog.py` `cmd_list`: replace `★` with `*` (and the same in `cmd_show`).

- [ ] **Step 4: Run tests**

Run: `uv run python -m pytest tests/test_catalog.py tests/test_labels.py -v --tb=short`

Expected: PASS including old catalog tests.

- [ ] **Step 5: Commit**

```bash
git add fansim/catalog.py scripts/catalog.py tests/test_catalog.py
git commit -m "Classify catalog rows onto hub models so Results can stay honest."
```

---

### Task 5: Cockpit hub bar, Design / Results / Library layout

**Files:**
- Modify: `fansim/cockpit/app.py` (layout ~1728–2120 and scatter `cmax`; state for `fan_subtab`)
- Modify: `fansim/cockpit/app.py` `scatter_figure` colorbar `cmax=45` (or `max(22, max efficiencies)` if designs exist)

**Interfaces:**
- Consumes: `run_label`, `results_for_hub`, `load_catalog`, `get_fan_spec`, `preview_changes`
- Produces: UI state `fan_subtab` in `{"design","results","library"}`; hub picker at top of Fan tab; 3D on Design; scatter only on Results; library list on Library; Propeller tab unchanged

This task is layout only (no Place-creates-row yet). Fit toolbar buttons may call `fit_envelope` / `scale_to_hub` on the **current editor flat** and write sliders + `edited_stale=True` + show `preview_changes` — that is still in-editor, not a new catalog row. Task 6 adds “new design on Place from Library.”

- [ ] **Step 1: Write a failing helper test for scatter + subtab filtering**

Add `tests/test_cockpit_view.py`:

```python
from fansim.catalog import CatalogEntry, results_for_hub
from fansim.cockpit.app import scatter_figure
from fansim.cockpit.data import Design


def test_results_for_hub_hides_foreign_envelope():
    a12 = CatalogEntry(design_id="ok", hub_models=["a12x25"], cfm_free=54.0, cfm_load=50.0)
    big = CatalogEntry(design_id="big", hub_models=[], cfm_free=92.0, cfm_load=87.0)
    hits = results_for_hub([a12, big], "a12x25")
    assert [h.design_id for h in hits] == ["ok"]


def test_scatter_colorbar_not_capped_at_22():
    d = Design(trial=1, params={}, objectives={"cfm_free": 50, "cfm_load": 48, "efficiency": 36},
               feasible=True, is_pareto=True, stl_path=None)
    fig = scatter_figure([d])
    cmax = fig.data[0].marker.cmax
    assert cmax is None or cmax >= 36 or cmax >= 45
```

If `scatter_figure` still hardcodes `cmax=22`, the second test fails.

- [ ] **Step 2: Run test to verify scatter fails**

Run: `uv run python -m pytest tests/test_cockpit_view.py::test_scatter_colorbar_not_capped_at_22 -v`

Expected: FAIL assertion on cmax 22

- [ ] **Step 3: Change scatter_figure and layout**

In `scatter_figure`, replace `cmin=0, cmax=22` with:

```python
effs = [d.objectives["efficiency"] for d in study_designs] + [d.objectives["efficiency"] for d in user_designs]
cmax = max([45.0] + [e for e in effs if e is not None])
```

Use `cmin=0, cmax=cmax` on the marker.

Layout rewrite of the Fan tab (keep Propeller block):

1. Set `layout.title.set_text("Fan-simulator Cockpit")` (already there — also set the HTML title if Trame exposes it via `server.state.trame__title = "Fan-simulator Cockpit"` or `layout.title`).
2. State: `fan_subtab = "design"`; remove `fits_only` switch and its filter.
3. Fan column structure:

```
VContainer
  hub row: VSelect fan_model | model_info | VBtn Fit envelope | VBtn Scale to this hub
  VTabs fan_subtab: Design | Results | Library
  Design (v_show): VRow
    VCol cols=7: 3D card height 560px + highlight/envelope switches
    VCol cols=5: editor accordions (existing sliders, DELETE Snap to fit / Fit to frame / Fit depth buttons and their VCol wrappers; keep hub_fit_info / tip_fit_info / depth_fit_info as text)
  Results (v_show): declutter switch + Plotly scatter of hub-filtered designs + design dropdown + Assess/Sweep/measurement (move Assess here or keep on Design — spec says Results is the graph; keep Assess on Design too so you can score a draft without leaving 3D. Put a compact Assess on Design and the scatter-only on Results.)
  Library (v_show): VSelect/VList of catalog entries with run_label(run), tip/hub from params, CFM caption "score in original envelope"
```

Hub Fit/Scale buttons: `disabled` when editor has no tip_radius. Click → apply to editor sliders from `PlaceResult.flat`, set `edited_stale=True`, `preview_msg = preview_changes(...)`.

Scatter data: build `Design` list from `results_for_hub(load_catalog(), state.fan_model)` intersecting with loaded study/user designs **or** map catalog rows to scatter points. Simplest: filter `study_designs + user_designs` by catalog `results_for_hub` ids; if a loaded design has no catalog row yet, include it only when `nominal_fits_spec(its params, active spec)`.

Library: `state.library_items` from `load_catalog()` with titles `f"{run_label(e.run)} · {e.design_id} · {e.cfm_free:.0f} CFM (original envelope)"`.

Default `fan_subtab` is `"design"` so first paint is 3D, not the mixed scatter.

- [ ] **Step 4: Run tests**

Run: `uv run python -m pytest tests/test_cockpit_view.py tests/test_catalog.py tests/test_placement.py tests/test_labels.py -q -m "not docker and not slow"`

Expected: PASS. Manually: `uv run --extra viz --extra optim python scripts/cockpit.py --run runs/opt_realframe` (or any run that exists), confirm Design 3D is first, Propeller tab present, Results does not show 92 CFM stars for a12x25.

- [ ] **Step 5: Commit**

```bash
git add fansim/cockpit/app.py tests/test_cockpit_view.py
git commit -m "Put the hub first and split Design, Results, and Library."
```

---

### Task 6: Library Place creates a new stale draft

**Files:**
- Modify: `fansim/cockpit/app.py` (library Place handlers)
- Modify: `fansim/catalog.py` if you persist placed rows into `cockpit_assess` JSON (existing assess writer)

**Interfaces:**
- Consumes: `fit_envelope`, `scale_to_hub`, `PlaceResult`
- Produces: new user `Design` with `extra["parent_id"]`, `extra["place_op"]`, `extra["cfd_stale"]=True`, `extra["placed_on"]=fan_model`; original library entry unchanged

- [ ] **Step 1: Write a failing unit test for the place helper (no Trame)**

Add to `tests/test_placement.py`:

```python
from fansim.cockpit.placement import placed_child_record


def test_placed_child_record_keeps_parent_id_and_stale_cfd():
    spec = get_fan_spec("a12x25")
    parent = _base()
    rec = placed_child_record(parent, spec, op="fit_envelope", parent_id="opt_run1_t9038")
    assert rec["parent_id"] == "opt_run1_t9038"
    assert rec["place_op"] == "fit_envelope"
    assert rec["cfd_stale"] is True
    assert rec["placed_on"] == "a12x25"
    assert rec["flat"]["hub_radius"] >= 19.825
    assert parent["hub_radius"] == 16.5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_placement.py::test_placed_child_record_keeps_parent_id_and_stale_cfd -v`

Expected: FAIL `placed_child_record` not defined

- [ ] **Step 3: Implement helper and wire Library**

In `placement.py`:

```python
def placed_child_record(flat: dict, spec: FanSpec, op: str, parent_id: str) -> dict:
    from fansim.fan_spec import fan_spec_names
    key = next(k for k, v in ((n, __import__("fansim.fan_spec", fromlist=["get_fan_spec"]).get_fan_spec(n))
                              for n in fan_spec_names()) if v is spec)
```

Do **not** use that ugly next(). Pass `hub_key: str` explicitly:

```python
def placed_child_record(flat: dict, spec: FanSpec, op: str, parent_id: str, hub_key: str) -> dict:
    if op == "scale_to_hub":
        result = scale_to_hub(flat, spec)
    elif op == "fit_envelope":
        result = fit_envelope(flat, spec)
    else:
        raise ValueError(f"unknown place op {op!r}")
    return {
        "flat": result.flat,
        "fit_status": result.fit_status,
        "leftover": result.leftover,
        "changes": result.changes,
        "parent_id": parent_id,
        "place_op": op,
        "cfd_stale": True,
        "placed_on": hub_key,
    }
```

Update the test to pass `hub_key="a12x25"`.

Cockpit Library: two actions on the selected catalog id — Fit envelope / Scale to this hub. If `not state.fan_model`: set `preview_msg = "Select a hub first."` and return. Else `placed_child_record(...)`, `_init_editor(rec["flat"])`, append a `Design` with trial `next_id`, objectives copied from parent but `extra cfd_stale True` so Results list shows it under “unscored on this hub” and **excludes it from the scatter** (`cfd_stale`). Switch `fan_subtab` to `design`. Do not modify the parent catalog row.

When Assess succeeds on that draft, set `cfd_stale=False` and write live CFD on the **new** row only.

- [ ] **Step 4: Run tests**

Run: `uv run python -m pytest tests/test_placement.py tests/test_catalog.py tests/test_cockpit_view.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add fansim/cockpit/placement.py fansim/cockpit/app.py tests/test_placement.py
git commit -m "Place library recipes onto the selected hub as new stale drafts."
```

---

### Task 7: Docs sync

**Files:**
- Modify: `docs/known-issues.md`
- Modify: `docs/superpowers/specs/2026-09-01-hub-first-cockpit-design.md` status line to `accepted`

**Interfaces:** none

- [ ] **Step 1: Edit known-issues**

Replace the stale “GPU/FluidX3D still idle” / unbuilt-noise bullets with a pointer:

```markdown
## Cockpit / catalog (2026-09)

Hub-first Design / Results / Library: see
`docs/superpowers/specs/2026-09-01-hub-first-cockpit-design.md`.

Physical airflow and noise still need a Noctua on the bench. Printability was
proven once in PLA+ (that print is what measured the 37.25 mm cup).
```

Keep the historical cockpit items 1–4 as archived if still accurate, or mark them superseded.

Set spec status to `accepted`.

- [ ] **Step 2: No test**

Docs only.

- [ ] **Step 3: Commit**

```bash
git add docs/known-issues.md docs/superpowers/specs/2026-09-01-hub-first-cockpit-design.md
git commit -m "Point known-issues at the hub-first spec and drop stale GPU claims."
```

---

## Self-review

**Spec coverage**

| Spec requirement | Task |
|---|---|
| Hub picker first | 5 |
| Design = 3D, no ranking graph | 5 |
| Results = this hub only, live CFD | 4 + 5 |
| Library = all recipes, English run names | 2 + 5 |
| Fit envelope vs Scale | 3 |
| New draft, parent unchanged | 6 |
| CFD stale until Assess | 6 |
| Snap buttons off sliders | 5 |
| Propeller tab stays | 5 |
| Scatter colorbar not 0–22 | 5 |
| Title Fan-simulator Cockpit | 5 |
| fits_only removed | 5 |
| Catalog classify + no ★ | 4 |
| Mountable 19.825 | 1 |
| Windows catalog CLI | 4 |
| known-issues | 7 |
| Non-goals (OGV, presets, tip-gap, new opt run) | omitted |

**Placeholder scan:** none remaining.

**Types:** `PlaceResult`, `PlaceChange`, `placed_child_record(..., hub_key: str)`, `results_for_hub`, `run_label`, `nominal_fits_spec` are named consistently across tasks.
