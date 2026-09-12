# Tip Shroud / Ring (Stage 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A printable full-span tip ring on the impeller, visible in the cockpit, searchable with `--shroud`, and scored by the fan BEM as an un-tipped (no leak) machine.

**Architecture:** `BladeParams.shroud_thick_mm` (0 = off) drives a hoop fused at the **built** tip envelope (`open_tip_rmax_mm` + thickness). `blade_max_dia` adds `2 * shroud_thick_mm` so Fit/frame/catalog see the real OD. BEM sets Prandtl `F = 1` and skips gap leak when the ring is on. Optimizer `--shroud` stamps 1.6 mm and shrinks `max_tip_radius` by the same amount. Cockpit is one Tip-panel slider.

**Tech Stack:** Python 3.12 via uv, CadQuery, pytest, Optuna CLI, Trame/Vuetify3 cockpit.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-01-tip-shroud-design.md`
- Python `>=3.12,<3.13` via `uv`; tests: `uv run python -m pytest -q -m "not docker and not slow"`
- `shroud_thick_mm = 0` is a no-op (existing recipes unchanged)
- Ring sits on **built** tip envelope, not nominal `tip_radius`
- Default on-thickness is **1.6 mm**; printability rejects `0 < thick < 0.8`
- Embed inner face `0.8 mm` inside `open_tip_rmax_mm`
- Do **not** scale `shroud_thick_mm` in `scale_to_hub` (it is a wall, not a planform length)
- Do **not** auto-zero winglets; hint only
- No partial-height ring, no tip-gap CFD, no Propeller-tab change
- Windows: CadQuery may heap-corrupt on teardown (exit 3221226356 / -1073741819) — judge tests by assertion output, not process exit code
- No `★` in Windows CLI help text
- Commit after each task; do not `git push`

---

## File structure

| Path | Responsibility |
|---|---|
| `fansim/geometry/blade.py` | `shroud_thick_mm`, `open_tip_rmax_mm`, ring solid, fuse + preview mesh |
| `fansim/cockpit/placement.py` | `blade_max_dia` includes ring OD |
| `fansim/manufacturability/fdm_rules.py` | Reject too-thin ring |
| `fansim/fan_bem.py` | Skip tip-loss when shrouded |
| `fansim/optimize/search_space.py` | `blade_from_flat` + `suggest_params(with_shroud=)` |
| `fansim/optimize/study.py` | `--shroud` shrinks `max_tip_radius`, stamps 1.6 mm |
| `scripts/run_optimization.py` | `--shroud` flag |
| `fansim/cockpit/app.py` | Tip-panel slider + flat round-trip |
| `tests/test_shroud.py` | Diameter, printability, BEM, flat round-trip, CLI flag |
| `tests/test_geometry.py` | Watertight shrouded impeller |
| `docs/roadmap.md` | Check off §2.1 stage 1; note remaining §7.5 |
| `docs/superpowers/specs/2026-09-01-tip-shroud-design.md` | Status → `accepted` |

Constants (define once in `fansim/geometry/blade.py`, import elsewhere):

```python
SHROUD_EMBED_MM = 0.8
SHROUD_DEFAULT_MM = 1.6
SHROUD_MIN_WALL_MM = 0.8
```

---

### Task 1: Param + diameter (no CAD)

**Files:**
- Modify: `fansim/geometry/blade.py` (`BladeParams` + `open_tip_rmax_mm`)
- Modify: `fansim/cockpit/placement.py` (`blade_max_dia`)
- Test: `tests/test_shroud.py`

**Interfaces:**
- Consumes: existing `_interp_stations` / `_section_points_3d` in `blade.py`
- Produces:
  - `BladeParams.shroud_thick_mm: float = 0.0`
  - `open_tip_rmax_mm(params: BladeParams) -> float` — max `hypot(x,y)` of section points, **ignoring** the ring
  - `blade_max_dia(params) -> float` equals `2 * open_tip_rmax_mm(params)` when thick is 0, and that plus `2 * shroud_thick_mm` when thick > 0

Move the section-point radial walk currently inlined in `placement.blade_max_dia` into `open_tip_rmax_mm` so the ring builder (Task 3) and Fit/frame share one envelope. Keep `blade_z_extent` where it is.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_shroud.py`:

```python
from fansim.cockpit.placement import blade_max_dia
from fansim.geometry.blade import BladeParams, SHROUD_DEFAULT_MM


def test_zero_shroud_is_same_diameter_as_today():
    p = BladeParams()
    assert getattr(p, "shroud_thick_mm", None) == 0.0
    open_dia = blade_max_dia(p)
    p.shroud_thick_mm = 0.0
    assert blade_max_dia(p) == open_dia


def test_shroud_grows_diameter_by_twice_thickness():
    p = BladeParams()
    open_dia = blade_max_dia(p)
    p.shroud_thick_mm = SHROUD_DEFAULT_MM
    assert abs(blade_max_dia(p) - (open_dia + 2.0 * SHROUD_DEFAULT_MM)) < 1e-6
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_shroud.py -q --tb=short`

Expected: collection or assert fail (`shroud_thick_mm` missing, or diameter does not grow).

- [ ] **Step 3: Implement**

On `BladeParams` (after `features`, before `blade_angles_deg`):

```python
    shroud_thick_mm: float = 0.0  # 0 = no tip ring; else radial wall outside the built tip
```

Add:

```python
SHROUD_EMBED_MM = 0.8
SHROUD_DEFAULT_MM = 1.6
SHROUD_MIN_WALL_MM = 0.8


def open_tip_rmax_mm(params: BladeParams) -> float:
    """Max radial extent (mm) of blade section points — no ring."""
    import math
    from fansim.geometry.features import Features as _F

    it = _interp_stations(params, params.n_span)
    r0 = params.hub_radius - params.root_embed
    rmax = 0.0
    for i in range(params.n_span):
        rf = float(it["r_frac"][i])
        r = r0 + (params.tip_radius - r0) * rf
        pts = _section_points_3d(
            r=r, r_frac=rf,
            chord=float(it["chord"][i]), stagger_deg=float(it["stagger_deg"][i]),
            thickness=float(it["thickness"][i]), max_camber=float(it["max_camber"][i]),
            camber_pos=float(it["camber_pos"][i]), sweep=float(it["sweep"][i]),
            skew=float(it["skew"][i]), le_sweep=float(it["le_sweep"][i]),
            lean_deg=float(it["lean_deg"][i]), n_chord=params.n_chord, features=_F(),
        )
        for v in pts:
            rr = math.hypot(v.x, v.y)
            if rr > rmax:
                rmax = rr
    return rmax
```

Replace the body of `placement.blade_max_dia` with:

```python
def blade_max_dia(params) -> float:
    """Max impeller DIAMETER (mm) from section points + optional tip ring.

    Open tips bulge past 2*tip_radius. A shroud sits on that built envelope and
    adds 2 * shroud_thick_mm to the diameter.
    """
    from fansim.geometry.blade import open_tip_rmax_mm

    dia = 2.0 * open_tip_rmax_mm(params)
    thick = float(getattr(params, "shroud_thick_mm", 0.0) or 0.0)
    if thick > 0.0:
        dia += 2.0 * thick
    return dia
```

Delete the inlined section walk from `blade_max_dia` (keep `blade_z_extent` unchanged).

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_shroud.py tests/test_placement.py -q --tb=short`

Expected: PASS (ignore CadQuery teardown exit code).

- [ ] **Step 5: Commit**

```bash
git add fansim/geometry/blade.py fansim/cockpit/placement.py tests/test_shroud.py
git commit -m "Add shroud thickness to the built tip diameter"
```

---

### Task 2: Printability gate

**Files:**
- Modify: `fansim/manufacturability/fdm_rules.py`
- Test: `tests/test_shroud.py`

**Interfaces:**
- Consumes: `params.shroud_thick_mm`, `SHROUD_MIN_WALL_MM` (or `MIN_WALL_PERIMETERS * nozzle_mm`)
- Produces: `check_printability` returns infeasible when `0 < shroud_thick_mm < 0.8`

A 1.6 mm ring on a printable blade must still pass.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_shroud.py`:

```python
from fansim.manufacturability.fdm_rules import check_printability


def test_thin_shroud_is_unprintable():
    p = BladeParams()
    p.shroud_thick_mm = 0.4
    r = check_printability(p)
    assert r.printable is False
    assert "shroud" in r.reason.lower()


def test_default_shroud_on_baseline_is_printable():
    p = BladeParams()
    p.shroud_thick_mm = SHROUD_DEFAULT_MM
    assert check_printability(p).printable
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_shroud.py::test_thin_shroud_is_unprintable -q --tb=short`

Expected: FAIL (`printable is True`).

- [ ] **Step 3: Implement**

At the start of `check_printability`, after computing `body_wall`:

```python
    thick = float(getattr(params, "shroud_thick_mm", 0.0) or 0.0)
    if 0.0 < thick < body_wall:
        return PrintabilityReport(
            False, min_section_thickness_mm(params), body_wall,
            f"shroud wall {thick:.2f} mm < min wall {body_wall:.2f} mm",
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_shroud.py tests/test_optimize.py -q --tb=short`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add fansim/manufacturability/fdm_rules.py tests/test_shroud.py
git commit -m "Reject a tip ring thinner than two FDM walls"
```

---

### Task 3: Fuse the ring + preview mesh

**Files:**
- Modify: `fansim/geometry/blade.py` (`_tip_z_span`, `_shroud_solid`, `build_impeller`, `build_impeller_preview`)
- Test: `tests/test_geometry.py`, `tests/test_shroud.py`

**Interfaces:**
- Consumes: `open_tip_rmax_mm`, `SHROUD_EMBED_MM`, `shroud_thick_mm`
- Produces: fused hoop; preview concatenates a ring mesh and adds its volume

Ring dims (spec):

| Dim | Value |
|---|---|
| Outer radius | `open_tip_rmax_mm + shroud_thick_mm` |
| Inner radius | `open_tip_rmax_mm - SHROUD_EMBED_MM` |
| Axial span | Z min/max of the **tip** section (`r_frac == 1` station via `_section_points_3d`) |

Use `cq.Solid.makeCylinder` + `cut`, same as `_cylinder_hub`. If inner radius <= 0, skip the ring (should not happen on real tips).

Default `BladeParams` + 1.6 mm ring is **larger than a 120 mm frame** — do **not** reuse `test_impeller_fits_a12x25_envelope` for the shrouded solid. Only assert watertight + one body + volume greater than the open impeller.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_shroud.py`:

```python
def test_preview_volume_grows_with_shroud():
    from fansim.geometry.blade import build_impeller_preview

    open_mesh, open_vol = build_impeller_preview(BladeParams())
    p = BladeParams()
    p.shroud_thick_mm = SHROUD_DEFAULT_MM
    _, sh_vol = build_impeller_preview(p)
    assert sh_vol > open_vol
```

Append to `tests/test_geometry.py`:

```python
def test_shrouded_impeller_is_watertight_single_body(tmp_path):
    from fansim.geometry.blade import SHROUD_DEFAULT_MM

    p = BladeParams()
    p.shroud_thick_mm = SHROUD_DEFAULT_MM
    out = export_stl(build_impeller(p), tmp_path / "shroud.stl")
    rep = watertight_report(out)
    assert rep.ok, f"shrouded impeller not print/mesh-ready: {rep}"
    assert rep.n_bodies == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_shroud.py::test_preview_volume_grows_with_shroud tests/test_geometry.py::test_shrouded_impeller_is_watertight_single_body -q --tb=short`

Expected: FAIL (preview volume unchanged and/or STL has no extra body fused — watertight may still pass on blades+hub alone).

- [ ] **Step 3: Implement**

```python
def _tip_z_span(params: BladeParams) -> tuple[float, float]:
    st = max(params.stations, key=lambda s: s.r_frac)
    r = params.hub_radius - params.root_embed
    r = r + (params.tip_radius - r) * st.r_frac
    pts = _section_points_3d(
        r=r, r_frac=st.r_frac, chord=st.chord, stagger_deg=st.stagger_deg,
        thickness=st.thickness, max_camber=st.max_camber, camber_pos=st.camber_pos,
        sweep=st.sweep, skew=st.skew, le_sweep=st.le_sweep, lean_deg=st.lean_deg,
        n_chord=params.n_chord, features=Features(),
    )
    zs = [p.z for p in pts]
    return min(zs), max(zs)


def _shroud_solid(params: BladeParams) -> cq.Solid | None:
    t = float(params.shroud_thick_mm or 0.0)
    if t <= 0.0:
        return None
    r_max = open_tip_rmax_mm(params)
    r_out = r_max + t
    r_in = r_max - SHROUD_EMBED_MM
    if r_in <= 0.0 or r_out <= r_in:
        return None
    z0, z1 = _tip_z_span(params)
    h = max(z1 - z0, 1.0)
    outer = cq.Solid.makeCylinder(r_out, h, cq.Vector(0, 0, z0), cq.Vector(0, 0, 1))
    inner = cq.Solid.makeCylinder(r_in, h + 0.4, cq.Vector(0, 0, z0 - 0.2), cq.Vector(0, 0, 1))
    return outer.cut(inner)
```

In `build_impeller`, after `fused = hub.fuse(*blades).clean()`:

```python
    ring = _shroud_solid(params)
    if ring is not None:
        fused = fused.fuse(ring).clean()
```

In `build_impeller_preview`, after hub/blade volume sum:

```python
    ring = _shroud_solid(params)
    if ring is not None:
        parts.append(_tm(ring))
        volume_mm3 += float(ring.Volume())
        mesh = trimesh.util.concatenate(parts)
```

(Keep the existing `mesh = concatenate` — either concatenate once at the end including the ring, or concatenate twice. Do not drop the hub/blades.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_shroud.py tests/test_geometry.py -q --tb=short`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add fansim/geometry/blade.py tests/test_shroud.py tests/test_geometry.py
git commit -m "Fuse a printable tip ring onto the impeller"
```

---

### Task 4: BEM skips tip-loss when shrouded

**Files:**
- Modify: `fansim/fan_bem.py` (`operating_point`)
- Test: `tests/test_shroud.py`

**Interfaces:**
- Consumes: `params.shroud_thick_mm`
- Produces: shrouded `F = 1` and no `K_TIP_LEAK`; shrouded shut-off > open-tipped on `BladeParams()` at 2000 RPM

- [ ] **Step 1: Write the failing test**

```python
def test_bem_shrouded_shutoff_beats_open_tip():
    from fansim.fan_bem import pq_curve

    open_c = pq_curve(BladeParams(), rpm=2000)
    p = BladeParams()
    p.shroud_thick_mm = SHROUD_DEFAULT_MM
    sh_c = pq_curve(p, rpm=2000)
    assert sh_c.shutoff_dp_pa > open_c.shutoff_dp_pa
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_shroud.py::test_bem_shrouded_shutoff_beats_open_tip -q --tb=short`

Expected: FAIL (equal shut-off).

- [ ] **Step 3: Implement**

In `operating_point`, replace the Prandtl + leak block with:

```python
        shrouded = float(getattr(params, "shroud_thick_mm", 0.0) or 0.0) > 0.0
        if shrouded:
            F = 1.0
        else:
            f_tip = (B / 2.0) * max(tip_r - r, 0.0) / max(r * math.sin(phi), 1e-4)
            F = max(0.10, (2.0 / math.pi) * math.acos(math.exp(-min(f_tip, 20.0))))
            r_norm = (r - hub_r) / (tip_r - hub_r) if tip_r > hub_r else 0.0
            if r_norm > 0.65:
                F *= max(0.2, 1.0 - K_TIP_LEAK * (tip_gap_mm / 1000.0) / max(c, 1e-3))
```

Keep `vth_eff = SLIP * F * vth` and the rest of the loop unchanged.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_shroud.py tests/test_fan_bem.py -q --tb=short`

Expected: PASS. Existing BEM band tests still use `shroud_thick_mm = 0`.

- [ ] **Step 5: Commit**

```bash
git add fansim/fan_bem.py tests/test_shroud.py
git commit -m "Drop BEM tip-loss on a shrouded impeller"
```

---

### Task 5: Optimizer `--shroud` and flat round-trip

**Files:**
- Modify: `fansim/optimize/search_space.py` (`suggest_params`, `blade_from_flat`)
- Modify: `fansim/optimize/study.py`
- Modify: `scripts/run_optimization.py`
- Test: `tests/test_shroud.py`

**Interfaces:**
- Consumes: `SHROUD_DEFAULT_MM`
- Produces:
  - `blade_from_flat` reads `shroud_thick_mm` (default 0)
  - `suggest_params(..., with_shroud: bool = False)` sets `bp.shroud_thick_mm = SHROUD_DEFAULT_MM` when True
  - `run_study(..., with_shroud: bool = False)` passes the flag and subtracts `SHROUD_DEFAULT_MM` from `max_tip_radius`
  - CLI `--shroud` (store_true), help without `★`

Do not add thickness as a search DOF. Do not add `shroud_thick_mm` to `scale_to_hub` `scale_keys`.

- [ ] **Step 1: Write the failing tests**

```python
import optuna
from pathlib import Path

from fansim.optimize.search_space import blade_from_flat, suggest_params


def test_blade_from_flat_roundtrips_shroud():
    p = blade_from_flat({
        "n_blades": 7, "chord_root": 34, "chord_mid": 44, "chord_tip": 38,
        "stagger_root": 26, "stagger_mid": 26, "stagger_tip": 22,
        "sweep_mid": 3, "sweep_tip": 5, "max_camber": 0.05,
        "shroud_thick_mm": SHROUD_DEFAULT_MM,
    })
    assert p.shroud_thick_mm == SHROUD_DEFAULT_MM


def test_blade_from_flat_defaults_shroud_off():
    p = blade_from_flat({
        "n_blades": 7, "chord_root": 34, "chord_mid": 44, "chord_tip": 38,
        "stagger_root": 26, "stagger_mid": 26, "stagger_tip": 22,
        "sweep_mid": 3, "sweep_tip": 5, "max_camber": 0.05,
    })
    assert p.shroud_thick_mm == 0.0


def test_suggest_params_stamps_default_shroud():
    study = optuna.create_study(directions=["maximize", "maximize", "maximize"])
    p = suggest_params(study.ask(), with_shroud=True)
    assert p.shroud_thick_mm == SHROUD_DEFAULT_MM


def test_run_optimization_declares_shroud_flag():
    text = Path("scripts/run_optimization.py").read_text(encoding="utf-8")
    assert "--shroud" in text
    assert "★" not in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_shroud.py::test_blade_from_flat_roundtrips_shroud tests/test_shroud.py::test_suggest_params_stamps_default_shroud tests/test_shroud.py::test_run_optimization_declares_shroud_flag -q --tb=short`

Expected: FAIL.

- [ ] **Step 3: Implement**

`suggest_params`: add `with_shroud: bool = False`. After `bp = BladeParams(...)` (and winglet/spacing), if `with_shroud`: `bp.shroud_thick_mm = SHROUD_DEFAULT_MM`.

`blade_from_flat`: after constructing `bp`, before winglet:

```python
    if float(p.get("shroud_thick_mm", 0.0)) > 0.0:
        bp.shroud_thick_mm = float(p["shroud_thick_mm"])
```

`run_study`: add `with_shroud: bool = False`. After computing `max_tip_radius = spec.tip_dia_mm[1] / 2.0 - 4.0`:

```python
    if with_shroud:
        from fansim.geometry.blade import SHROUD_DEFAULT_MM
        max_tip_radius -= SHROUD_DEFAULT_MM
```

Pass `with_shroud=with_shroud` into `suggest_params`.

`scripts/run_optimization.py`: next to `--winglet`:

```python
    ap.add_argument("--shroud", action="store_true",
                    help="fuse a 1.6 mm tip ring on every trial and shrink the tip-radius cap so the grown OD still fits the frame (roadmap 2.1).")
```

Pass `with_shroud=args.shroud` into `run_study`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_shroud.py tests/test_optimize.py tests/test_placement.py -q --tb=short`

Expected: PASS. `test_fit_envelope_shrinks_tip_inside_110mm_frame` still holds for unshrouded `_base()`.

- [ ] **Step 5: Commit**

```bash
git add fansim/optimize/search_space.py fansim/optimize/study.py scripts/run_optimization.py tests/test_shroud.py
git commit -m "Add --shroud to the optimizer search"
```

---

### Task 6: Cockpit slider

**Files:**
- Modify: `fansim/cockpit/app.py`
- Test: none required beyond existing `_apply_editor_flat` coverage; add a tiny mapping test only if you extract a helper. Prefer a focused check that `edit_flat` would include the key — if that is not unit-testable without Trame, skip and verify by reading the three round-trip sites.

**Interfaces:**
- Consumes: `shroud_thick_mm` in flats
- Produces: `e_shroud_thick` slider 0–3 step 0.2; round-trip in `_init_editor`, `edit_flat`, `_apply_editor_flat`; listed in `EDITOR_VARS`; `CONTROL_DESC` entry; hint under the slider

Copy (exact):

- Slider label: `Shroud thickness (mm)`
- Hint: `0 = no ring. A full ring usually makes winglets worse — leave winglet at 0.`
- `CONTROL_DESC["e_shroud_thick"]`: `Radial wall of a ring fused at the blade tips (mm). 0 = open tip. Grows the outer diameter by twice this amount.`

- [ ] **Step 1: Locate the three round-trip sites**

Confirm these exist (line numbers will have drifted): `_init_editor` (`state.e_winglet_*`), `edit_flat()`, `_apply_editor_flat` mapping, `EDITOR_VARS`, Tip accordion after winglet sliders.

- [ ] **Step 2: Wire the slider** (no failing Trame test — this is UI glue on an established pattern)

`_init_editor`: `state.e_shroud_thick = float(p.get("shroud_thick_mm", 0.0))`

`edit_flat`: `shroud_thick_mm=state.e_shroud_thick`

`_apply_editor_flat` mapping: `"shroud_thick_mm": ("e_shroud_thick", float)`

`EDITOR_VARS`: add `"e_shroud_thick"` next to the winglet keys.

Tip panel, after winglet lean:

```python
                                                    _slider("Shroud thickness (mm)", "e_shroud_thick", 0, 3, 0.2)
                                                    html.Div("0 = no ring. A full ring usually makes winglets worse — leave winglet at 0.",
                                                             classes="text-caption mb-1")
```

Add `CONTROL_DESC["e_shroud_thick"]` as specified above.

Optional: randomize may leave shroud at 0 (do not randomly turn it on).

- [ ] **Step 3: Sanity-check Python import**

Run: `uv run python -c "from fansim.cockpit.app import CONTROL_DESC; assert 'e_shroud_thick' in CONTROL_DESC"`

Expected: no exception. (If `app.py` import pulls Trame/viz extras, run `uv run --extra viz python -c "..."` instead.)

- [ ] **Step 4: Commit**

```bash
git add fansim/cockpit/app.py
git commit -m "Add a cockpit slider for tip-ring thickness"
```

---

### Task 7: Spec accepted + roadmap

**Files:**
- Modify: `docs/superpowers/specs/2026-09-01-tip-shroud-design.md` — `Status: accepted`
- Modify: `docs/roadmap.md`

Mark §2.1 as stage-1 done. Leave §7.5 open (partial height, designed gap CFD, winglet study). Update the recommended sequence: next is honest optimizer CFD (§1.1 / §1.2). Mention `--shroud` in recently shipped.

Suggested §2.1 replacement:

```markdown
- [x] **2.1 Tip shroud / ring (stage 1). DONE 2026-09-01** (`BladeParams.shroud_thick_mm`,
  cockpit slider, `--shroud`). Printable full-span ring on the built tip envelope;
  BEM drops tip-loss when the ring is on. Remaining: partial-height ring, ring-to-frame
  gap in CFD, winglet interaction (§7.5 / §1.1).
```

- [ ] **Step 1: Edit the two docs**

- [ ] **Step 2: Run the full cheap suite**

Run: `uv run python -m pytest -q -m "not docker and not slow"`

Expected: all collected tests PASS. Ignore Windows CadQuery teardown exit code.

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/specs/2026-09-01-tip-shroud-design.md docs/roadmap.md
git commit -m "Accept the tip-shroud spec and mark roadmap 2.1 stage 1 done"
```

---

## Self-review

1. **Spec coverage:** Geometry hoop, diameter, printability, BEM F=1, `--shroud` + max tip shrink, cockpit slider, tests, non-goals (no partial height, no CFD gap, no winglet auto-disable). All have tasks.
2. **Placeholders:** none.
3. **Names:** `shroud_thick_mm`, `SHROUD_DEFAULT_MM`, `open_tip_rmax_mm`, `e_shroud_thick`, `--shroud` / `with_shroud` are consistent across tasks.
