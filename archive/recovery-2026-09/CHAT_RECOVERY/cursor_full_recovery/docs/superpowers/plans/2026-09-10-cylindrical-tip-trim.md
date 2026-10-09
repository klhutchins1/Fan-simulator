# Cylindrical Tip Trim Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a toggle that radially clamps loft section points so the blade tip OD matches `tip_radius` (cover circle), without Tip Round’s petal taper.

**Architecture:** `BladeParams.cylindrical_tip` (default `True`) threads into `_section_loop` / `_section_points_3d`. After lean placement, any point with \(\sqrt{x^2+y^2} > tip_radius\) is scaled onto that cylinder (Z unchanged). Cockpit checkbox + flat round-trip; no NSGA variable.

**Tech Stack:** Python, CadQuery loft (unchanged), Trame/Vuetify cockpit, pytest.

## Global Constraints

- No new Python dependencies; no `catalog/catalog.db` commits; do not re-open tip-round / bio-feature NSGA.
- Trim radius = `tip_radius` only; Tip Round still applies first (stations), clamp during loft.
- Absent flat key → trim on; explicit false/0 → off.
- Axial loft path only (mixed-flow / CROR / prop out of scope).

## File map

| File | Role |
|---|---|
| `fansim/geometry/blade.py` | field + clamp + thread through loft / open_tip / tip helpers |
| `fansim/optimize/search_space.py` | `blade_from_flat` / `blade_to_flat`; optional `cylindrical_tip=` on tip cap |
| `fansim/cockpit/placement.py` | pass flag into `_section_points_3d` |
| `fansim/cockpit/app.py` | checkbox, help, edit_flat / load / EDITOR_VARS |
| `tests/test_cylindrical_tip.py` | new hypot / round-trip / tip-round combo tests |
| `tests/test_search_space.py` / `tests/test_shroud.py` | bulge-assuming tests use `cylindrical_tip=False` |

---

### Task 1: Geometry clamp + tests

**Files:**
- Modify: `fansim/geometry/blade.py`
- Create: `tests/test_cylindrical_tip.py`
- Modify: `tests/test_shroud.py` (bore bulge guard)
- Modify: `fansim/cockpit/placement.py`

**Interfaces:**
- Produces: `BladeParams.cylindrical_tip: bool = True`
- Produces: `_section_points_3d(..., cylindrical_tip: bool = False, tip_clamp_radius: float | None = None)`
- Consumes: callers pass `params.cylindrical_tip` and `params.tip_radius`

- [ ] **Step 1: Write failing tests** in `tests/test_cylindrical_tip.py`

```python
import math
import pytest
from fansim.geometry.blade import (
    BladeParams, RadialStation, apply_tip_shape, build_blade_solid,
    open_tip_rmax_mm, tip_section_points,
)

def _bulgy() -> BladeParams:
    return BladeParams(
        cylindrical_tip=False,
        tip_radius=50.0,
        stations=[
            RadialStation(0.0, 18.0, 40.0, thickness=0.10, lean_deg=0.0),
            RadialStation(0.5, 30.0, 40.0, thickness=0.08, lean_deg=25.0),
            RadialStation(1.0, 40.0, 40.0, thickness=0.06, lean_deg=45.0),
        ],
    )

def test_default_cylindrical_tip_on():
    assert BladeParams().cylindrical_tip is True

def test_trim_off_allows_tip_bulge():
    p = _bulgy()
    assert open_tip_rmax_mm(p) > p.tip_radius + 0.5

def test_trim_on_caps_tip_hypot():
    p = _bulgy()
    p.cylindrical_tip = True
    assert open_tip_rmax_mm(p) <= p.tip_radius + 1e-6
    for v in tip_section_points(p):
        assert math.hypot(v.x, v.y) <= p.tip_radius + 1e-6

def test_tip_round_plus_trim_still_capped():
    p = _bulgy()
    p.cylindrical_tip = True
    apply_tip_shape(p, tip_round=0.7, start_frac=0.80)
    assert open_tip_rmax_mm(p) <= p.tip_radius + 1e-6
    solid = build_blade_solid(p)
    assert solid is not None
```

- [ ] **Step 2: Run tests — expect fail** (`BladeParams` has no `cylindrical_tip`)

Run: `uv run pytest tests/test_cylindrical_tip.py -v`

- [ ] **Step 3: Implement clamp in `blade.py`**

Add field after `tip_notch_depth_mm`:

```python
cylindrical_tip: bool = True  # clamp section points to tip_radius OD
```

Helper + `_section_loop` kwargs `cylindrical_tip: bool = False`, `tip_clamp_radius: float | None = None`. After building `pts`, if enabled and radius set:

```python
R = float(tip_clamp_radius)
if cylindrical_tip and R > 0.0:
    clamped = []
    for v in pts:
        rho = math.hypot(v.x, v.y)
        if rho > R and rho > 0.0:
            s = R / rho
            clamped.append(cq.Vector(v.x * s, v.y * s, v.z))
        else:
            clamped.append(v)
    pts = clamped
```

Thread through `_section_points_3d`, `open_tip_rmax_mm`, `build_blade_solid`, `_root_axial_span`, `tip_section_points`, `tip_le_te_z`, and `placement.blade_z_extent` with `params.cylindrical_tip` and `params.tip_radius`.

- [ ] **Step 4: Fix shroud bulge guard** — `test_ring_bore_is_below_the_corner_only_radius` set `p.cylindrical_tip = False`.

- [ ] **Step 5: Run** `uv run pytest tests/test_cylindrical_tip.py tests/test_shroud.py::test_ring_bore_is_below_the_corner_only_radius tests/test_shroud.py::test_ring_wall_contains_every_tip_section_point -v`

- [ ] **Step 6: Commit** geometry + tests

---

### Task 2: Flat / tip-cap / cockpit

**Files:**
- Modify: `fansim/optimize/search_space.py`
- Modify: `fansim/cockpit/app.py`
- Modify: `tests/test_search_space.py`
- Modify: `tests/test_cylindrical_tip.py` (flat round-trip)

- [ ] **Step 1: `blade_from_flat` / `blade_to_flat`**

```python
# blade_from_flat, after bp construction:
if "cylindrical_tip" in p:
    v = p["cylindrical_tip"]
    if isinstance(v, str):
        bp.cylindrical_tip = v.strip().lower() not in ("0", "false", "no", "off", "")
    else:
        bp.cylindrical_tip = bool(v)
# absent → leave default True

# blade_to_flat:
cylindrical_tip=bool(getattr(params, "cylindrical_tip", True)),
```

Optional kwarg on `tip_radius_cap_mm(..., cylindrical_tip: bool | None = None)` passed into `BladeParams(...)`.

- [ ] **Step 2: Update `test_high_lean_cap_is_tighter_than_low_lean`** to pass `cylindrical_tip=False`. Add assert that with default trim, high-lean cap is within 0.5 mm of low-lean cap.

- [ ] **Step 3: Cockpit** — `CONTROL_DESC["e_cylindrical_tip"]`, `_init_editor` default True from `p.get("cylindrical_tip", True)`, `edit_flat` key, `_apply_editor_flat` bool, `EDITOR_VARS`, `_help_switch` in Tip panel above Tip round.

- [ ] **Step 4: Flat round-trip test**

```python
def test_blade_from_flat_cylindrical_tip_roundtrip():
    from fansim.optimize.search_space import blade_from_flat, blade_to_flat
    base = blade_to_flat(BladeParams())
    assert blade_from_flat(base).cylindrical_tip is True
    off = dict(base, cylindrical_tip=False)
    assert blade_from_flat(off).cylindrical_tip is False
    assert "cylindrical_tip" not in {} or blade_from_flat({**base}).cylindrical_tip is True
    slim = {k: v for k, v in base.items() if k != "cylindrical_tip"}
    assert blade_from_flat(slim).cylindrical_tip is True
```

- [ ] **Step 5: Run** `uv run pytest tests/test_cylindrical_tip.py tests/test_search_space.py tests/test_hub.py -v --timeout=120`

- [ ] **Step 6: Commit**

- [ ] **Step 7: Mark spec status `accepted`** in design md; commit.

---

### Spec coverage self-check

| Spec item | Task |
|---|---|
| Field default on | 1 |
| Radial clamp | 1 |
| Tip Round + trim | 1 |
| blade_from_flat / to_flat | 2 |
| Cockpit checkbox | 2 |
| Fit / open_tip sees clamp | 1 |
| No NSGA variable | (none added) |
| Tests listed in spec | 1–2 |
