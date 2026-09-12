# Persistent 3D Library Browse Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep the impeller 3D view visible while browsing Library; one readable recipe list; click Fits the current hub into the editor and auto-draws; Assess is what saves a Results row.

**Architecture:** Pure helpers in `fansim/cockpit/library_view.py` format rows and run editor-only Fit/Scale. `fansim/cockpit/app.py` lifts the plotter out of the Design `v_show` into a persistent left column and wires Library click to those helpers plus existing `do_preview()`. `placed_child_record` stays for tests but Library click must not append `user_designs`.

**Tech Stack:** Python 3.12 via uv, pytest, existing `fit_envelope` / `scale_to_hub` / `nominal_fits_spec`, Trame/Vuetify3 cockpit.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-01-library-browse-preview-design.md`
- Python `>=3.12,<3.13` via `uv`; tests: `uv run python -m pytest -q -m "not docker and not slow"`
- UI copy must not contain `original envelope`; use `at original size`
- Fit hint strings are exactly: `fits this hub` | `too big — click Fits it` | `no geometry yet`
- Click Fit / Scale Library actions are **editor-only** (no new trial id, no `user_designs.append`)
- Stay on Library after click (`fan_subtab` stays `"library"`)
- Propeller tab unchanged
- Do not rewrite `runs/` folder names
- Windows: CadQuery may heap-corrupt on teardown — judge tests by assertion result, not exit 3221226356
- Commit after each task; do not `git push`

---

## File structure

| Path | Responsibility |
|---|---|
| `fansim/cockpit/library_view.py` | Row/group dicts; `apply_library_recipe`; fit hint |
| `tests/test_library_view.py` | Formatter + editor-only apply |
| `fansim/cockpit/app.py` | Persistent 3D column; Library list UI; click/Scale/Assess extras |
| `tests/test_cockpit_view.py` | Library items still include both ids; no dropdown-shape assumption |
| `docs/superpowers/specs/2026-09-01-library-browse-preview-design.md` | Status → `accepted` |

---

### Task 1: Library row formatter

**Files:**
- Create: `fansim/cockpit/library_view.py`
- Test: `tests/test_library_view.py`
- Modify later (Task 3): `fansim/cockpit/app.py` (stop using `library_items_from_catalog`)

**Interfaces:**
- Consumes: `CatalogEntry`, `run_label`, `nominal_fits_spec`, `FanSpec`
- Produces:
  - `fit_hint(entry: CatalogEntry, spec: FanSpec) -> str`
  - `library_list_items(entries: list, spec: FanSpec) -> list[dict]`
  - Group dict: `{"role": "group", "title": str, "caption": str}`
  - Row dict: `{"role": "row", "value": str, "title": str, "subtitle": str, "clickable": bool}`

Hub/tip in the title are **diameters**: `round(2*hub_radius)` and `round(2*tip_radius)` millimetres, matching spec example `hub 33 mm · tip 118 mm` for radii 16.5 / 59.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_library_view.py`:

```python
from fansim.catalog import CatalogEntry
from fansim.cockpit.library_view import fit_hint, library_list_items
from fansim.fan_spec import get_fan_spec


def test_missing_params_is_no_geometry():
    spec = get_fan_spec("a12x25")
    e = CatalogEntry(design_id="x", run="opt_run1", params={"n_blades": 9})
    assert fit_hint(e, spec) == "no geometry yet"


def test_row_copy_uses_original_size_not_envelope_jargon():
    spec = get_fan_spec("a12x25")
    e = CatalogEntry(
        design_id="opt_run1_t9038",
        run="opt_run1",
        n_blades=9,
        cfm_free=92.4,
        params={"n_blades": 9, "hub_radius": 16.5, "tip_radius": 59.0},
    )
    items = library_list_items([e], spec)
    groups = [i for i in items if i["role"] == "group"]
    rows = [i for i in items if i["role"] == "row"]
    assert groups[0]["title"] == "First unconstrained 120 mm search"
    assert groups[0]["caption"] == "opt_run1"
    assert rows[0]["value"] == "opt_run1_t9038"
    assert rows[0]["title"] == "9 blades · hub 33 mm · tip 118 mm"
    assert "at original size" in rows[0]["subtitle"]
    assert "original envelope" not in rows[0]["title"].lower()
    assert "original envelope" not in rows[0]["subtitle"].lower()
    assert rows[0]["clickable"] is False or "too big" in rows[0]["subtitle"] or "fits this hub" in rows[0]["subtitle"]


def test_oversized_is_not_titled_as_fits_a12x25():
    spec = get_fan_spec("a12x25")
    e = CatalogEntry(
        design_id="big",
        run="opt_run1",
        cfm_free=92.0,
        params={"n_blades": 9, "hub_radius": 16.5, "tip_radius": 59.0,
                "stagger_root": 26, "stagger_mid": 26, "stagger_tip": 22,
                "chord_root": 34, "chord_mid": 44, "chord_tip": 38,
                "sweep_mid": 3, "sweep_tip": 5, "max_camber": 0.05},
    )
    hint = fit_hint(e, spec)
    assert hint != "fits this hub"
    assert hint in ("too big — click Fits it", "no geometry yet")
```

The oversized test may call CadQuery via `nominal_fits_spec`. That is intended.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_library_view.py -v --tb=short`

Expected: FAIL `ModuleNotFoundError: fansim.cockpit.library_view`

- [ ] **Step 3: Implement `fansim/cockpit/library_view.py`**

```python
"""Library list copy. Keep Trame/app.py free of recipe-title formatting."""

from __future__ import annotations

from fansim.catalog import CatalogEntry
from fansim.cockpit.labels import run_label
from fansim.cockpit.placement import nominal_fits_spec
from fansim.fan_spec import FanSpec

HINT_FITS = "fits this hub"
HINT_BIG = "too big — click Fits it"
HINT_NONE = "no geometry yet"


def fit_hint(entry: CatalogEntry, spec: FanSpec) -> str:
    p = entry.params or {}
    if "hub_radius" not in p or "tip_radius" not in p:
        return HINT_NONE
    try:
        if nominal_fits_spec(p, spec):
            return HINT_FITS
    except Exception:  # noqa: BLE001
        return HINT_NONE
    return HINT_BIG


def library_list_items(entries: list, spec: FanSpec) -> list[dict]:
    items: list[dict] = []
    last_run = object()
    for e in entries or []:
        run = e.run or ""
        if run != last_run:
            items.append({"role": "group", "title": run_label(run) or run or "Ungrouped", "caption": run})
            last_run = run
        p = e.params or {}
        try:
            n = int(p.get("n_blades") or e.n_blades or 0)
        except (TypeError, ValueError):
            n = 0
        try:
            hub_d = round(2.0 * float(p["hub_radius"])) if "hub_radius" in p else None
            tip_d = round(2.0 * float(p["tip_radius"])) if "tip_radius" in p else None
        except (TypeError, ValueError):
            hub_d = tip_d = None
        if n and hub_d is not None and tip_d is not None:
            title = f"{n} blades · hub {hub_d} mm · tip {tip_d} mm"
        elif n:
            title = f"{n} blades"
        else:
            title = e.design_id
        hint = fit_hint(e, spec)
        free = f"{e.cfm_free:.0f}" if isinstance(e.cfm_free, (int, float)) else "?"
        subtitle = f"{free} CFM at original size · {hint}"
        items.append({
            "role": "row",
            "value": e.design_id,
            "title": title,
            "subtitle": subtitle,
            "clickable": hint != HINT_NONE,
        })
    return items
```

Tighten `test_row_copy_uses_original_size_not_envelope_jargon` after you know the oversized fixture's hint: for params with only hub/tip and no stagger, `nominal_fits_spec` may return False via failed measure — still must not say `fits this hub` if measure fails? Failed measure → `fit_hint` catches Exception → `no geometry yet`, and `clickable` is False. Then the last assert `clickable is False or ...` still passes.

Prefer: for the copy test, do not require CadQuery. Give `test_row_copy` params **without** calling a path that needs a full blade (missing stagger is ok: Exception → HINT_NONE). The title still uses hub/tip diameters. Change the last assert in the copy test to:

```python
    assert rows[0]["clickable"] is False
    assert HINT_NONE in rows[0]["subtitle"] or HINT_BIG in rows[0]["subtitle"] or HINT_FITS in rows[0]["subtitle"]
```

Keep `test_oversized_is_not_titled_as_fits_a12x25` as the CadQuery fit-hint test with full params.

- [ ] **Step 4: Run tests**

Run: `uv run python -m pytest tests/test_library_view.py -v --tb=short`

Expected: PASS. CadQuery teardown may exit non-zero; assertions green.

- [ ] **Step 5: Commit**

```bash
git add fansim/cockpit/library_view.py tests/test_library_view.py
git commit -m "Describe library recipes in blades, size, and original CFM."
```

---

### Task 2: Editor-only Fit/Scale apply helper

**Files:**
- Modify: `fansim/cockpit/library_view.py`
- Test: `tests/test_library_view.py`

**Interfaces:**
- Consumes: `fit_envelope`, `scale_to_hub`, `PlaceResult`
- Produces: `LibraryApply(ok, message, flat, parent_id, place_op, fit_status, leftover)` and `apply_library_recipe(flat, spec, op, parent_id) -> LibraryApply`
- `op` is `"fit_envelope"` or `"scale_to_hub"` only
- `flat` is never mutated
- Return value has **no** `trial` / `design_id` / new catalog id

Exact refusal message when hub/tip missing: `This recipe has no blade numbers to Fit.`

Scale with `fit_status == "unplaced"`: `ok=False`, `flat=None`, `leftover` from `PlaceResult`, do not pretend success.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_library_view.py`:

```python
from copy import deepcopy

from fansim.cockpit.library_view import apply_library_recipe
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


def test_apply_fit_does_not_mutate_parent_or_invent_a_trial():
    spec = get_fan_spec("a12x25")
    parent = _base()
    snap = deepcopy(parent)
    rec = apply_library_recipe(parent, spec, op="fit_envelope", parent_id="opt_run1_t9038")
    assert parent == snap
    assert rec.ok is True
    assert rec.parent_id == "opt_run1_t9038"
    assert rec.place_op == "fit_envelope"
    assert rec.flat is not None
    assert rec.flat["hub_radius"] >= 19.825
    assert not hasattr(rec, "trial")
    assert "trial" not in rec.__dict__


def test_apply_refuses_empty_params():
    spec = get_fan_spec("a12x25")
    rec = apply_library_recipe({"n_blades": 9}, spec, op="fit_envelope", parent_id="x")
    assert rec.ok is False
    assert rec.flat is None
    assert rec.message == "This recipe has no blade numbers to Fit."


def test_apply_scale_unplaced_on_zero_tip():
    spec = get_fan_spec("a12x25")
    rec = apply_library_recipe(_base(tip_radius=0.0), spec, op="scale_to_hub", parent_id="x")
    assert rec.ok is False
    assert rec.flat is None
    assert rec.fit_status == "unplaced"
```

If `LibraryApply` is a dataclass, `not hasattr(rec, "trial")` is the no-new-id check. Do not add a `trial` field.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_library_view.py::test_apply_fit_does_not_mutate_parent_or_invent_a_trial -v`

Expected: FAIL `apply_library_recipe` not defined

- [ ] **Step 3: Implement apply helper in `library_view.py`**

```python
from dataclasses import dataclass

from fansim.cockpit.placement import fit_envelope, scale_to_hub

NO_PARAMS_MSG = "This recipe has no blade numbers to Fit."


@dataclass(frozen=True)
class LibraryApply:
    ok: bool
    message: str
    flat: dict | None
    parent_id: str
    place_op: str
    fit_status: str
    leftover: str


def apply_library_recipe(flat: dict, spec: FanSpec, op: str, parent_id: str) -> LibraryApply:
    p = flat or {}
    if "hub_radius" not in p or "tip_radius" not in p:
        return LibraryApply(False, NO_PARAMS_MSG, None, parent_id, op, "unplaced", "")
    if op == "scale_to_hub":
        result = scale_to_hub(p, spec)
    elif op == "fit_envelope":
        result = fit_envelope(p, spec)
    else:
        raise ValueError(f"unknown place op {op!r}")
    if result.fit_status == "unplaced":
        return LibraryApply(False, result.leftover, None, parent_id, op, result.fit_status, result.leftover)
    return LibraryApply(
        ok=True,
        message=result.leftover or "",
        flat=result.flat,
        parent_id=parent_id,
        place_op=op,
        fit_status=result.fit_status,
        leftover=result.leftover,
    )
```

Remove unused `blade_from_flat` import from the test file if you copied it and never used it.

- [ ] **Step 4: Run tests**

Run: `uv run python -m pytest tests/test_library_view.py -v --tb=short`

Expected: PASS (all Task 1 + Task 2 tests)

- [ ] **Step 5: Commit**

```bash
git add fansim/cockpit/library_view.py tests/test_library_view.py
git commit -m "Apply library Fit and Scale in the editor without creating a row."
```

---

### Task 3: Persistent 3D column and Library click

**Files:**
- Modify: `fansim/cockpit/app.py` (layout ~1956–2283; `library_items_from_catalog`; `select_library_design`; `_place_library`; `on_assess` extra; `refresh_library`)
- Modify: `tests/test_cockpit_view.py`

**Interfaces:**
- Consumes: `library_list_items`, `apply_library_recipe`, `do_preview`, `_init_editor`
- Produces: UI state `library_parent_id: str`, `library_place_op: str`, `library_leftover: str`; `library_items` is the list from `library_list_items(load_catalog(), active_spec())`

Layout (exact structure — do not leave `plotter_ui` inside `fan_subtab === 'design'`):

After the hub bar row, use:

```
VRow
  VCol cols=7: envelope switches + VCard height 560px plotter_ui  (NO v_show on fan_subtab)
  VCol cols=5:
    VTabs Design | Results | Library
    Design v_show: existing editor cards currently in the cols=5 column (sliders, Assess, leeway, …)
    Results v_show: declutter + scatter stacked, then the design dropdown + info_lines
    Library v_show: leftover caption, grouped list, Scale button (variant=outlined, not filled primary)
```

Delete the Library `VSelect`. Delete the duplicate `VList` that only repeats dropdown titles.

`refresh_library`:

```python
        spec = active_spec()
        items = library_list_items(load_catalog(), spec)
        state.library_items = items
        n = sum(1 for it in items if it.get("role") == "row")
        state.library_info = f"{n} recipe(s) — click Fits this hub and draws it. Scale shrinks a huge recipe first."
```

Initialize `state.library_parent_id = ""`, `state.library_place_op = ""`, `state.library_leftover = ""`.

Replace `select_library_design` / `_place_library` / `on_library_fit_envelope` / `on_library_scale_to_hub`:

```python
    def _apply_library_to_editor(design_id: str, op: str):
        if not state.fan_model:
            state.preview_msg = "Select a hub first."
            state.flush()
            return
        if not design_id:
            state.preview_msg = "Select a library recipe first."
            state.flush()
            return
        e = get_entry(design_id)
        if e is None:
            state.preview_msg = f"'{design_id}' not in the catalog (rebuild it if it's new)."
            state.flush()
            return
        rec = apply_library_recipe(e.params or {}, active_spec(), op=op, parent_id=design_id)
        state.library_sel = design_id
        state.library_parent_id = rec.parent_id
        state.library_place_op = rec.place_op
        state.library_leftover = rec.leftover or rec.message
        if not rec.ok or rec.flat is None:
            state.preview_msg = rec.message or rec.leftover
            state.flush()
            return
        _init_editor(rec.flat)
        _set_baseline()
        # Do not append user_designs. Do not change fan_subtab.
        do_preview()
        state.flush()

    def select_library_design(design_id=None, **_):
        if not design_id:
            return
        _apply_library_to_editor(design_id, "fit_envelope")

    def on_library_scale_to_hub():
        _apply_library_to_editor(state.library_sel, "scale_to_hub")
```

Delete `on_library_fit_envelope` if click is the Fit path. Do not call `_place_library`. Remove `_place_library` entirely.

Library template (right column only):

```python
                        with html.Div(v_show="fan_subtab === 'library'"):
                            with v3.VCard(classes="mb-2 pa-3"):
                                html.Div("{{ library_info }}", classes="text-caption mb-2")
                                html.Div("{{ library_leftover }}", classes="text-caption mb-2",
                                         v_if="library_leftover")
                                v3.VBtn("Scale to this hub", color="primary", size="small",
                                        variant="outlined", block=True, classes="mb-2",
                                        click=(on_library_scale_to_hub,),
                                        disabled=("!library_sel",))
                                with v3.VList(density="compact", lines="two"):
                                    with v3.VListSubheader(v_for="it in library_items",
                                                           v_if="it.role === 'group'",
                                                           key="it.caption"):
                                        html.Div("{{ it.title }}")
                                        html.Div("{{ it.caption }}", classes="text-caption")
                                    with v3.VListItem(v_for="it in library_items",
                                                      v_if="it.role === 'row'",
                                                      key="it.value",
                                                      disabled=("!it.clickable",),
                                                      click=(select_library_design, "[it.value]")):
                                        v3.VListItemTitle("{{ it.title }}")
                                        v3.VListItemSubtitle("{{ it.subtitle }}")
```

If Vuetify `v_for` + `v_if` on two sibling types in one `library_items` array mis-renders, split `state.library_groups` or use a single `v_for` with nested `v_if` on one `VList` child using `v3.VListSubheader` vs `VListItem` inside one loop:

```python
                                with v3.VList(density="compact", lines="two"):
                                    with html.Div(v_for="it in library_items", key="it.value || it.caption"):
                                        v3.VListSubheader(v_if="it.role === 'group'"):
                                            html.Div("{{ it.title }}")
                                            html.Div("{{ it.caption }}", classes="text-caption")
                                        v3.VListItem(v_if="it.role === 'row'",
                                                     disabled=("!it.clickable",),
                                                     click=(select_library_design, "[it.value]")):
                                            v3.VListItemTitle("{{ it.title }}")
                                            v3.VListItemSubtitle("{{ it.subtitle }}")
```

Prefer one `v_for` wrapper so group headers and rows stay in catalog order.

**Assess extras:** in `_assess` when building `extra={...}`, if `state.library_parent_id`:

```python
        extra = {"n_blades": params.n_blades, "source": "user",
                 "source_run": run_dir.name,
                 "over_spec": list(result.over_spec), "fan_model": state.fan_model,
                 "actual_rpm": round(result.actual_rpm)}
        if state.library_parent_id:
            extra["parent_id"] = state.library_parent_id
            extra["place_op"] = state.library_place_op or "fit_envelope"
            extra["placed_on"] = state.fan_model
            extra["cfd_stale"] = False
```

Successful Assess already means live CFD. Do not set `cfd_stale=True` here.

`tests/test_cockpit_view.py` — change the library assertion to the new item shape:

```python
from fansim.cockpit.library_view import library_list_items
from fansim.fan_spec import get_fan_spec
# remove library_items_from_catalog import from app if unused

def test_results_for_hub_hides_foreign_envelope():
    a12 = CatalogEntry(design_id="ok", hub_models=["a12x25"], cfm_free=54.0, cfm_load=50.0)
    big = CatalogEntry(design_id="big", hub_models=[], cfm_free=92.0, cfm_load=87.0)
    hits = results_for_hub([a12, big], "a12x25")
    assert [h.design_id for h in hits] == ["ok"]
    spec = get_fan_spec("a12x25")
    lib = library_list_items([a12, big], spec)
    assert [it["value"] for it in lib if it.get("role") == "row"] == ["ok", "big"]
```

Remove `library_items_from_catalog` from `app.py`.

Do not put a second `plotter_ui(plotter)` in Design. Propeller tab: do not edit.

- [ ] **Step 1: Write the failing test** (item shape in `test_cockpit_view.py` as above)

If `library_items_from_catalog` is still exported from app, the old test would still pass — so **change the test first** to import `library_list_items` and require `role == "row"`. Then app still exporting the old helper does not satisfy this test.

- [ ] **Step 2: Run test to verify it fails or that app still uses the old helper**

Run: `uv run python -m pytest tests/test_cockpit_view.py -v --tb=short`

Expected: FAIL import or assertion until app + library_view are wired. If Task 1 already provides `library_list_items`, this test may PASS before the layout change — that is OK. Layout has no unit test; the rest of this task is the layout + handler rewrite.

- [ ] **Step 3: Implement layout + handlers** as specified in Interfaces.

Grep before finishing: `plotter_ui(plotter)` must appear **once**. `_place_library` must be gone. `VSelect` label `Library (all recipes)` must be gone. `original envelope` must not appear in `app.py`.

- [ ] **Step 4: Run tests**

Run: `uv run python -m pytest tests/test_library_view.py tests/test_cockpit_view.py tests/test_placement.py tests/test_catalog.py tests/test_labels.py -q -m "not docker and not slow" --tb=short`

Expected: PASS.

Manual: `uv run --extra viz --extra optim python scripts/cockpit.py --run runs/opt_realframe --port 8081` — Library tab still shows 3D on the left; click a row draws without switching tabs; Results does not gain a point until Assess.

- [ ] **Step 5: Commit**

```bash
git add fansim/cockpit/app.py tests/test_cockpit_view.py
git commit -m "Keep 3D visible and Fit a library recipe on click."
```

---

### Task 4: Spec status

**Files:**
- Modify: `docs/superpowers/specs/2026-09-01-library-browse-preview-design.md` status line to `accepted`

**Interfaces:** none

- [ ] **Step 1: Set status**

Change `**Status:** draft for review` to `**Status:** accepted`.

- [ ] **Step 2: No test**

Docs only.

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/specs/2026-09-01-library-browse-preview-design.md
git commit -m "Accept the persistent-3D library browse spec."
```

---

## Self-review

**Spec coverage**

| Spec requirement | Task |
|---|---|
| 3D always left, tabs right only | 3 |
| Design editors without a second 3D | 3 |
| Results scatter in right column | 3 |
| One Library list, no dropdown | 3 |
| English group + folder caption | 1 |
| Row: blades, hub/tip dia, CFM at original size, fit hint | 1 |
| No “original envelope” | 1, 3 |
| Click Fit editor-only, auto `do_preview`, stay on Library | 2, 3 |
| Scale secondary outlined, editor-only | 2, 3 |
| over_spec leftover caption | 3 (`library_leftover`) |
| Assess tags parent_id / place_op / placed_on, live CFD | 3 |
| Toolbar Fit/Scale unchanged (still in-editor) | 3 (do not rewrite those handlers) |
| No hub / no params messages | 2, 3 |
| Scale tip ≤ 0 does not draw | 2 (`ok=False` → no `do_preview`) |
| Propeller unchanged | 3 |
| Tests for formatter, no parent mutation, no trial id | 1, 2 |

**Placeholder scan:** none.

**Types:** `LibraryApply`, `library_list_items`, `apply_library_recipe(flat, spec, op, parent_id)` used consistently in Tasks 1–3.
