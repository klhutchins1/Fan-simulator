# Partial-Height Tip Ring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A cockpit height fraction that draws a TE-anchored partial tip ring while the full-span ring and un-tipped BEM stay the default.

**Architecture:** `BladeParams.shroud_height_frac` (default 1.0) feeds `shroud_axial_range`, which `_shroud_solid` uses for the cylinder Z. Fraction 1.0 is today’s tip Z-span. Below 1.0 the hoop grows from the TE toward the LE, floored at `SHROUD_MIN_WALL_MM`. BEM calls `shroud_is_full` so a 30% band keeps open-tip tip-loss. `--shroud` is unchanged.

**Tech Stack:** Python 3.12 via uv, CadQuery, pytest, Trame/Vuetify3 cockpit. No Docker.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-02-partial-shroud-design.md`
- Python `>=3.12,<3.13` via `uv`; tests: `uv run python -m pytest -q -m "not docker and not slow"`
- `shroud_thick_mm = 0` is the only off switch; height is ignored
- `shroud_height_frac` default **1.0** (stage 1 full tip Z-span)
- Partial hoop grows from TE (`x = 1`) toward LE (`x = 0`)
- `frac = 1.0` cylinder Z must match today’s `_tip_z_span` (not a reconstructed TE–LE span)
- `frac = 0` with thickness on clamps axial height to `SHROUD_MIN_WALL_MM` (0.8 mm), or full span if the tip is shorter
- BEM un-tipped only when `shroud_is_full` (thick > 0 and frac `>= 1.0 - 1e-9`)
- Do **not** scale `shroud_height_frac` in `scale_to_hub`
- Do **not** auto-zero winglets; no `--shroud-height` / `--shroud-partial`; no search DOF
- No ring-to-frame CFD gap, no Propeller-tab change, no catalog backfill
- No `★` in Windows CLI help
- Windows: CadQuery teardown exit 3221226356 / -1073741819 / 3221225477 is not a test failure — judge by assertion output
- Work on branch `partial-shroud`; do not commit to `master`; do not `git push`
- Do not commit `catalog/catalog.db`
- Commit after each task

---

## File structure

| Path | Responsibility |
|---|---|
| `fansim/geometry/blade.py` | `shroud_height_frac`, `shroud_is_full`, `tip_le_te_z`, `shroud_axial_range`, `_shroud_solid` Z |
| `fansim/fan_bem.py` | Un-tipped law only when `shroud_is_full` |
| `fansim/optimize/search_space.py` | `blade_from_flat` reads frac, default 1.0 |
| `fansim/cockpit/app.py` | Height slider, `edit_flat` / `_init_editor` round-trip |
| `tests/test_shroud.py` | Axial range, TE anchor, BEM partial, flat default, CLI unchanged |
| `tests/test_geometry.py` | Watertight fused impeller at frac 0.3 |
| `tests/test_placement.py` | `scale_to_hub` leaves frac alone |
| `docs/roadmap.md` + spec | Geometry slice of §7.5; spec `accepted` |

Constants (already in `blade.py`; do not duplicate):

```python
SHROUD_EMBED_MM = 0.8
SHROUD_DEFAULT_MM = 1.6
SHROUD_MIN_WALL_MM = 0.8
```

Add next to them:

```python
SHROUD_FULL_EPS = 1e-9
```

---

### Task 1: Param + axial range (no solid change)

**Files:**
- Modify: `fansim/geometry/blade.py` (`BladeParams`, helpers)
- Test: `tests/test_shroud.py`

**Interfaces:**
- Consumes: `_section_points_3d` / `naca4` chord fraction `x` (0 = LE, 1 = TE), `_tip_z_span`, `SHROUD_MIN_WALL_MM`
- Produces:
  - `BladeParams.shroud_height_frac: float = 1.0`
  - `shroud_is_full(params: BladeParams) -> bool`
  - `tip_le_te_z(params: BladeParams) -> tuple[float, float]` → `(z_le, z_te)`
  - `shroud_axial_range(params: BladeParams) -> tuple[float, float] | None` → `(z_lo, z_hi)` with `z_hi > z_lo`, or `None` when `shroud_thick_mm <= 0`

`_shroud_solid` stays full-span this task so existing geometry tests keep passing.

Refactor `_section_points_3d` through `_section_loop` that also returns the chord-fraction array `x` (same `x` as `naca4` after dropping the closing duplicate). Do not change radii or stagger math.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_shroud.py`:

```python
def test_height_frac_defaults_to_full():
    p = BladeParams()
    assert p.shroud_height_frac == 1.0


def test_thick_off_ignores_height_frac():
    from fansim.geometry.blade import shroud_axial_range

    p = BladeParams()
    p.shroud_height_frac = 0.3
    assert shroud_axial_range(p) is None
    open_dia = blade_max_dia(p)
    p.shroud_thick_mm = 0.0
    assert blade_max_dia(p) == open_dia


def test_full_frac_matches_tip_z_span():
    from fansim.geometry.blade import shroud_axial_range, tip_section_points

    p = BladeParams()
    p.shroud_thick_mm = SHROUD_DEFAULT_MM
    p.shroud_height_frac = 1.0
    zs = [v.z for v in tip_section_points(p)]
    lo, hi = shroud_axial_range(p)
    assert abs(lo - min(zs)) < 1e-9 and abs(hi - max(zs)) < 1e-9


def test_partial_band_is_te_anchored():
    from fansim.geometry.blade import shroud_axial_range, tip_le_te_z, tip_section_points

    p = BladeParams()
    p.shroud_thick_mm = SHROUD_DEFAULT_MM
    p.shroud_height_frac = 0.3
    z_le, z_te = tip_le_te_z(p)
    lo, hi = shroud_axial_range(p)
    span = max(v.z for v in tip_section_points(p)) - min(v.z for v in tip_section_points(p))
    assert abs((hi - lo) - 0.3 * span) < 1e-6
    if z_te >= z_le:
        assert abs(hi - z_te) < 1e-6
    else:
        assert abs(lo - z_te) < 1e-6


def test_zero_frac_clamps_to_min_wall():
    from fansim.geometry.blade import SHROUD_MIN_WALL_MM, shroud_axial_range

    p = BladeParams()
    p.shroud_thick_mm = SHROUD_DEFAULT_MM
    p.shroud_height_frac = 0.0
    lo, hi = shroud_axial_range(p)
    assert abs((hi - lo) - SHROUD_MIN_WALL_MM) < 1e-6


def test_partial_frac_does_not_change_od():
    p = BladeParams()
    open_dia = blade_max_dia(p)
    p.shroud_thick_mm = SHROUD_DEFAULT_MM
    p.shroud_height_frac = 0.3
    assert abs(blade_max_dia(p) - (open_dia + 2.0 * SHROUD_DEFAULT_MM)) < 1e-6
```

- [ ] **Step 2: Run tests — expect FAIL**

Run: `uv run python -m pytest tests/test_shroud.py::test_height_frac_defaults_to_full tests/test_shroud.py::test_thick_off_ignores_height_frac tests/test_shroud.py::test_full_frac_matches_tip_z_span tests/test_shroud.py::test_partial_band_is_te_anchored tests/test_shroud.py::test_zero_frac_clamps_to_min_wall tests/test_shroud.py::test_partial_frac_does_not_change_od -q --tb=short`

Expected: AttributeError / import fail (`shroud_height_frac` or helpers missing).

- [ ] **Step 3: Implement**

On `BladeParams`, after `shroud_thick_mm`:

```python
    shroud_height_frac: float = 1.0  # 1 = full tip Z-span; ignored if shroud_thick_mm == 0
```

Next to the SHROUD_* constants:

```python
SHROUD_FULL_EPS = 1e-9


def shroud_is_full(params: BladeParams) -> bool:
    t = float(getattr(params, "shroud_thick_mm", 0.0) or 0.0)
    f = min(max(float(getattr(params, "shroud_height_frac", 1.0) or 0.0), 0.0), 1.0)
    return t > 0.0 and f >= 1.0 - SHROUD_FULL_EPS
```

Split `_section_points_3d` so the chord-fraction array is available:

```python
def _section_loop(
    r, r_frac, chord, stagger_deg, thickness, max_camber, camber_pos,
    sweep, skew, le_sweep, lean_deg, n_chord, features,
) -> tuple["np.ndarray", list]:
    """Same construction as today's `_section_points_3d`, plus naca4 chord fraction `x`."""
    # Move the existing body here. `x = loop[:, 0]` after dropping the closing duplicate.
    # Return `(x, [cq.Vector(...), ...])`.


def _section_points_3d(...) -> list:
    _, pts = _section_loop(...)
    return pts
```

`tip_section_points` keeps calling `_section_points_3d`. Add:

```python
def tip_le_te_z(params: BladeParams) -> tuple[float, float]:
    """Axial Z of LE (`x` min) and TE (`x` max) on the tip section."""
    st = max(params.stations, key=lambda s: s.r_frac)
    r = params.hub_radius - params.root_embed
    r = r + (params.tip_radius - r) * st.r_frac
    x, pts = _section_loop(
        r=r, r_frac=st.r_frac, chord=st.chord, stagger_deg=st.stagger_deg,
        thickness=st.thickness, max_camber=st.max_camber, camber_pos=st.camber_pos,
        sweep=st.sweep, skew=st.skew, le_sweep=st.le_sweep, lean_deg=st.lean_deg,
        n_chord=params.n_chord, features=Features(),
    )
    i_le = int(x.argmin())
    i_te = int(x.argmax())
    return float(pts[i_le].z), float(pts[i_te].z)


def shroud_axial_range(params: BladeParams) -> tuple[float, float] | None:
    t = float(params.shroud_thick_mm or 0.0)
    if t <= 0.0:
        return None
    z0, z1 = _tip_z_span(params)
    span = z1 - z0
    frac = min(max(float(params.shroud_height_frac or 0.0), 0.0), 1.0)
    if frac >= 1.0 - SHROUD_FULL_EPS:
        return z0, z1
    h = frac * span
    if span >= SHROUD_MIN_WALL_MM:
        h = min(max(h, SHROUD_MIN_WALL_MM), span)
    else:
        h = span
    z_le, z_te = tip_le_te_z(params)
    if z_te >= z_le:
        z_hi = z_te
        z_lo = z_te - h
    else:
        z_lo = z_te
        z_hi = z_te + h
    return (z_lo, z_hi) if z_hi >= z_lo else (z_hi, z_lo)
```

- [ ] **Step 4: Re-run the same pytest command — PASS**

Also run: `uv run python -m pytest tests/test_shroud.py tests/test_geometry.py -q --tb=short -m "not docker"`

Existing ring tests must still pass (solid still full-span). CadQuery teardown non-zero exit is OK.

- [ ] **Step 5: Commit**

```bash
git add fansim/geometry/blade.py tests/test_shroud.py
git commit -m "Add TE-anchored shroud height fraction (axial range)"
```

---

### Task 2: Fuse the shorter hoop

**Files:**
- Modify: `fansim/geometry/blade.py` (`_shroud_solid`)
- Test: `tests/test_shroud.py`, `tests/test_geometry.py`

**Interfaces:**
- Consumes: `shroud_axial_range`
- Produces: `_shroud_solid` cylinder from `z_lo` with height `z_hi - z_lo`; preview/export pick it up automatically

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_shroud.py`:

```python
def test_preview_partial_ring_is_shorter_than_full():
    from fansim.geometry.blade import build_impeller_preview

    full = BladeParams()
    full.shroud_thick_mm = SHROUD_DEFAULT_MM
    full.shroud_height_frac = 1.0
    _, v_full = build_impeller_preview(full)
    part = BladeParams()
    part.shroud_thick_mm = SHROUD_DEFAULT_MM
    part.shroud_height_frac = 0.3
    _, v_part = build_impeller_preview(part)
    assert v_part > 0
    assert v_part < v_full
```

Append to `tests/test_geometry.py` (next to the existing full-ring watertight test):

```python
def test_partial_shroud_impeller_is_watertight(tmp_path):
    from fansim.geometry.blade import SHROUD_DEFAULT_MM

    p = BladeParams()
    p.shroud_thick_mm = SHROUD_DEFAULT_MM
    p.shroud_height_frac = 0.3
    out = export_stl(build_impeller(p), tmp_path / "partial_shroud.stl")
    rep = watertight_report(out)
    assert rep.ok, f"partial shroud impeller not print/mesh-ready: {rep}"
    assert rep.n_bodies == 1
```

- [ ] **Step 2: Run tests — expect FAIL**

Run: `uv run python -m pytest tests/test_shroud.py::test_preview_partial_ring_is_shorter_than_full tests/test_geometry.py::test_partial_shroud_impeller_is_watertight -q --tb=short`

Expected: `test_preview_partial_ring_is_shorter_than_full` fails (`v_part == v_full` because `_shroud_solid` still uses full `_tip_z_span`).

- [ ] **Step 3: Implement**

In `_shroud_solid`, after the radius checks, replace the `_tip_z_span` / `makeCylinder(..., z0)` block with:

```python
    zr = shroud_axial_range(params)
    if zr is None:
        return None
    z_lo, z_hi = zr
    h = max(z_hi - z_lo, 1e-6)
    outer = cq.Solid.makeCylinder(r_out, h, cq.Vector(0, 0, z_lo), cq.Vector(0, 0, 1))
    inner = cq.Solid.makeCylinder(r_in, h + 0.4, cq.Vector(0, 0, z_lo - 0.2), cq.Vector(0, 0, 1))
    return outer.cut(inner)
```

Radii stay `open_tip_rmax_mm + t` and `tip_section_rmin_mm - SHROUD_EMBED_MM`.

- [ ] **Step 4: Re-run — PASS**

Run: `uv run python -m pytest tests/test_shroud.py tests/test_geometry.py -q --tb=short -m "not docker"`

Judge by assertions. Existing `test_preview_volume_grows_with_shroud` and full-ring watertight must still pass.

- [ ] **Step 5: Commit**

```bash
git add fansim/geometry/blade.py tests/test_shroud.py tests/test_geometry.py
git commit -m "Fuse a TE-anchored partial tip ring"
```

---

### Task 3: BEM full-only + flat round-trip

**Files:**
- Modify: `fansim/fan_bem.py` (the `shrouded = ...` line)
- Modify: `fansim/optimize/search_space.py` (`blade_from_flat`)
- Test: `tests/test_shroud.py`, `tests/test_placement.py`

**Interfaces:**
- Consumes: `shroud_is_full`
- Produces: un-tipped BEM only for a full ring; `blade_from_flat` sets `shroud_height_frac` from the flat (default 1.0, clamped to [0, 1]); `scale_to_hub` does not multiply the frac

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_shroud.py`:

```python
def test_bem_partial_ring_matches_open_tip():
    from fansim.fan_bem import pq_curve

    open_c = pq_curve(BladeParams(), rpm=2000)
    p = BladeParams()
    p.shroud_thick_mm = SHROUD_DEFAULT_MM
    p.shroud_height_frac = 0.3
    part_c = pq_curve(p, rpm=2000)
    assert part_c.shutoff_dp_pa == open_c.shutoff_dp_pa


def test_blade_from_flat_defaults_height_full():
    p = blade_from_flat({
        "n_blades": 7, "chord_root": 34, "chord_mid": 44, "chord_tip": 38,
        "stagger_root": 26, "stagger_mid": 26, "stagger_tip": 22,
        "sweep_mid": 3, "sweep_tip": 5, "max_camber": 0.05,
        "shroud_thick_mm": SHROUD_DEFAULT_MM,
    })
    assert p.shroud_height_frac == 1.0


def test_blade_from_flat_roundtrips_height_frac():
    p = blade_from_flat({
        "n_blades": 7, "chord_root": 34, "chord_mid": 44, "chord_tip": 38,
        "stagger_root": 26, "stagger_mid": 26, "stagger_tip": 22,
        "sweep_mid": 3, "sweep_tip": 5, "max_camber": 0.05,
        "shroud_thick_mm": SHROUD_DEFAULT_MM,
        "shroud_height_frac": 0.3,
    })
    assert p.shroud_height_frac == 0.3


def test_run_optimization_has_no_shroud_height_flag():
    text = Path("scripts/run_optimization.py").read_text(encoding="utf-8")
    assert "--shroud" in text
    assert "--shroud-height" not in text
    assert "--shroud-partial" not in text
    assert "★" not in text
```

Append to `tests/test_placement.py`:

```python
def test_scale_does_not_change_shroud_height_frac():
    spec = get_fan_spec("a12x25")
    src = _base(tip_radius=110.0, shroud_thick_mm=1.6, shroud_height_frac=0.3)
    r = scale_to_hub(src, spec)
    assert r.flat["shroud_height_frac"] == 0.3
```

(`_base` already spreads kwargs into the flat dict. Confirm it does; if a key is dropped, set `src["shroud_height_frac"] = 0.3` after `_base(...)`.)

- [ ] **Step 2: Run tests — expect FAIL**

Run: `uv run python -m pytest tests/test_shroud.py::test_bem_partial_ring_matches_open_tip tests/test_shroud.py::test_blade_from_flat_defaults_height_full tests/test_shroud.py::test_blade_from_flat_roundtrips_height_frac tests/test_shroud.py::test_run_optimization_has_no_shroud_height_flag tests/test_placement.py::test_scale_does_not_change_shroud_height_frac -q --tb=short`

Expected: BEM test fails (`shutoff` still higher than open because `thick > 0` still skips tip-loss). Round-trip fails (`frac` stays 1.0). CLI grep should already pass (no new flag). Scale test should already pass if `scale_keys` omits the field — if `_base` drops unknown keys, fix the test setup, not `scale_to_hub`.

- [ ] **Step 3: Implement**

In `fansim/fan_bem.py`, replace the shrouded line:

```python
        from fansim.geometry.blade import shroud_is_full
        shrouded = shroud_is_full(params)
```

Keep the `if shrouded: F = 1.0` / else Prandtl + `K_TIP_LEAK` block.

In `blade_from_flat`, after the `shroud_thick_mm` block:

```python
    if "shroud_height_frac" in p:
        bp.shroud_height_frac = min(max(float(p["shroud_height_frac"]), 0.0), 1.0)
```

Do **not** add `shroud_height_frac` to `scale_to_hub`’s `scale_keys`.

Existing `test_bem_shrouded_shutoff_beats_open_tip` stays valid (default frac 1.0).

- [ ] **Step 4: Re-run the same pytest command — PASS**

Also: `uv run python -m pytest tests/test_shroud.py tests/test_placement.py -q --tb=short`

- [ ] **Step 5: Commit**

```bash
git add fansim/fan_bem.py fansim/optimize/search_space.py tests/test_shroud.py tests/test_placement.py
git commit -m "Score BEM as un-tipped only for a full-span ring"
```

---

### Task 4: Cockpit height slider

**Files:**
- Modify: `fansim/cockpit/app.py`
- Test: `tests/test_shroud.py` (source contract; do not boot Trame)

**Interfaces:**
- Consumes: `shroud_height_frac` on flats from Task 3
- Produces: `e_shroud_height` ↔ `shroud_height_frac`; slider 0–1 step 0.1, disabled when `e_shroud_thick == 0`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_shroud.py`:

```python
def test_cockpit_declares_shroud_height_slider():
    text = Path("fansim/cockpit/app.py").read_text(encoding="utf-8")
    assert "e_shroud_height" in text
    assert "Shroud height (tip chord)" in text
    assert "trailing edge" in text.lower()
    assert "shroud_height_frac" in text
    assert "e_shroud_thick == 0" in text
```

- [ ] **Step 2: Run — expect FAIL**

Run: `uv run python -m pytest tests/test_shroud.py::test_cockpit_declares_shroud_height_slider -q --tb=short`

Expected: assert fail (strings missing).

- [ ] **Step 3: Implement**

`CONTROL_DESC` after `e_shroud_thick`:

```python
    "e_shroud_height": "How much of the tip chord the ring covers. 1 = full span. Below 1 the hoop starts at the trailing edge. BEM still treats a partial ring as an open tip.",
```

Extend `_slider` with an optional disabled binding (both VSlider construction sites):

```python
def _slider(label: str, model: str, mn: float, mx: float, step: float, disabled=None):
    extra = {}
    if disabled is not None:
        extra["disabled"] = disabled
    ...
            v3.VSlider(..., **extra)
```

`_init_editor`: after `e_shroud_thick`:

```python
        state.e_shroud_height = min(max(float(p.get("shroud_height_frac", 1.0)), 0.0), 1.0)
```

`edit_flat` dict:

```python
            shroud_thick_mm=shroud,
            shroud_height_frac=min(max(float(state.e_shroud_height or 0.0), 0.0), 1.0),
```

`_apply_editor_flat` mapping:

```python
            "shroud_height_frac": ("e_shroud_height", float),
```

`EDITOR_VARS`: add `"e_shroud_height"` next to `"e_shroud_thick"`.

Tip accordion, after the thickness slider:

```python
                                                    _slider("Shroud thickness (mm)", "e_shroud_thick", 0, 3, 0.8)
                                                    _slider("Shroud height (tip chord)", "e_shroud_height", 0, 1, 0.1,
                                                            disabled=("e_shroud_thick == 0",))
                                                    html.Div("0 thickness = off. First thickness step is 0.8 mm (two walls); 1.6 mm is four walls. Height 1.0 covers the full tip; below 1.0 the hoop starts at the trailing edge and BEM still treats it as an open tip. A full ring usually makes winglets worse — leave winglet at 0.",
                                                             classes="text-caption mb-1")
```

Delete the old caption Div so there is only one.

- [ ] **Step 4: Re-run — PASS**

Run: `uv run python -m pytest tests/test_shroud.py::test_cockpit_declares_shroud_height_slider tests/test_shroud.py -q --tb=short`

- [ ] **Step 5: Commit**

```bash
git add fansim/cockpit/app.py tests/test_shroud.py
git commit -m "Add a cockpit slider for shroud height fraction"
```

---

### Task 5: Spec accepted + roadmap

**Files:**
- `docs/superpowers/specs/2026-09-02-partial-shroud-design.md` — `Status: accepted`
- `docs/roadmap.md` — note §7.5 geometry (partial height) done; remaining ring-to-frame gap + winglet policy

§2.1 remaining line today says “partial-height ring, ring-to-frame gap…”. Change to: partial-height ring (cockpit `shroud_height_frac`, TE-anchored) done 2026-09-02; remaining ring-to-frame gap in CFD and winglet interaction.

§7.5 stays unchecked. Add one sentence that stage 2 geometry (partial hoop) is in; CFD clearance and winglet policy are not.

Recommended sequence item 1: still §7.5, but “partial-height ring (stage 2) done”.

Recently shipped: mention TE-anchored partial ring / height slider.

- [ ] **Step 1: Edit the two docs**
- [ ] **Step 2: Run** `uv run python -m pytest tests/test_shroud.py tests/test_geometry.py tests/test_placement.py -q --tb=short -m "not docker"`
- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/specs/2026-09-02-partial-shroud-design.md docs/roadmap.md
git commit -m "Accept the partial-shroud spec and mark §7.5 geometry done"
```

---

## Self-review

1. Spec coverage: param default 1.0, thick=0 ignores frac, TE-anchored partial, frac=1 matches tip Z-span, 0.8 mm floor, OD unchanged, BEM full-only, blade_from_flat default, no scale, cockpit slider+disabled+hint, no new CLI flag, no CFD gap / winglet policy / catalog backfill / Propeller. Tasks 1–5 each map to those.
2. Placeholders: none.
3. Names: `shroud_height_frac`, `shroud_is_full`, `tip_le_te_z`, `shroud_axial_range`, `e_shroud_height`, `SHROUD_FULL_EPS` consistent.
