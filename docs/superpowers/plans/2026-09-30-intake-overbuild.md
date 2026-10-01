# Intake Overbuild (+Z) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Opt-in Fan Design switch that expands the allowed axial envelope on the intake (+Z) side by a configurable extra mm (default 10), without changing tip OD or growing the CFD duct in v1.

**Architecture:** Pure helpers in `fansim/cockpit/placement.py` for effective depth and outlet-anchored envelope Z-range. `active_spec()` adds the intake extra into `leeway_depth_mm` so Assess/`check_build` compose with Library leeway. `fit_envelope` gains an explicit `max_depth_mm` so Fit clamps to effective depth (not nominal-only). Viz highlight/envelope use the asymmetric Z-range. UI lives under Fit & seed.

**Tech Stack:** Python 3.12, pytest, Trame/Vuetify3 Fan cockpit.

**Spec:** `docs/superpowers/specs/2026-09-30-intake-overbuild-design.md`

## Global Constraints

- Extra mm range **0–20**, default **10**; ignored when switch off.
- `over_spec_flags` stays vs **nominal** `spec.depth_mm[1]` (honesty unchanged).
- CFD domain / OpenFOAM duct **unchanged** in v1.
- Fan tab only; Optimize search stays nominal unless later Adopt.
- Tip OD / radial leeway unchanged.
- Compose with Library `lee_depth`: allow max = nominal + lee_depth + intake_extra.

## File map

| File | Role |
|------|------|
| `fansim/cockpit/placement.py` | Helpers + `fit_envelope(..., max_depth_mm=)` |
| `tests/test_intake_overbuild.py` | Unit tests for helpers + fit clamp |
| `fansim/cockpit/fan_core.py` | State defaults; `active_spec` leeway bump |
| `fansim/cockpit/fan_editor.py` | Fit uses effective max depth; slider max refresh |
| `fansim/cockpit/fan_viz.py` | Asymmetric envelope + highlight |
| `fansim/cockpit/fan_tab_ui.py` | Fit & seed switch + slider + caption; Hub slider maxes |
| `docs/roadmap.md` | Short note under soft leftovers / new checkbox optional |
| `docs/superpowers/specs/2026-09-30-intake-overbuild-design.md` | Mark accepted |

---

### Task 1: Depth helpers + fit_envelope max_depth

**Files:**
- Modify: `fansim/cockpit/placement.py`
- Create: `tests/test_intake_overbuild.py`
- Modify: `docs/superpowers/specs/2026-09-30-intake-overbuild-design.md` (status → accepted)

**Interfaces:**
- Produces:
  - `intake_extra_mm(*, enabled: bool, extra_mm: float) -> float`
  - `effective_depth_max(spec: FanSpec, *, intake_extra: float = 0.0) -> float`
  - `depth_allow_max(spec: FanSpec, *, intake_extra: float = 0.0) -> float`
  - `intake_envelope_z_range(z_mid: float, nominal_depth: float, intake_extra: float = 0.0) -> tuple[float, float]`  # returns `(z_lo, z_hi)`
  - `fit_envelope(..., max_depth_mm: float | None = None)` — when None, use `spec.depth_mm[1]`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_intake_overbuild.py
from fansim.cockpit.placement import (
    depth_allow_max,
    effective_depth_max,
    fit_envelope,
    intake_envelope_z_range,
    intake_extra_mm,
)
from fansim.fan_spec import get_fan_spec
from fansim.geometry.features import Features
from fansim.optimize.search_space import stock_blade_flat


def test_intake_extra_mm_clamps_and_gates():
    assert intake_extra_mm(enabled=False, extra_mm=10) == 0.0
    assert intake_extra_mm(enabled=True, extra_mm=10) == 10.0
    assert intake_extra_mm(enabled=True, extra_mm=-5) == 0.0
    assert intake_extra_mm(enabled=True, extra_mm=99) == 20.0


def test_effective_and_allow_compose_with_leeway():
    import dataclasses
    spec = dataclasses.replace(get_fan_spec("a12x25"), leeway_depth_mm=2.0)
    assert effective_depth_max(spec, intake_extra=10.0) == 35.0  # 25+10
    assert depth_allow_max(spec, intake_extra=10.0) == 37.0  # 25+2+10


def test_intake_envelope_z_range_outlet_anchored():
    # nominal 25, mid 0 → lo=-12.5, hi=12.5; +10 → hi=22.5
    lo, hi = intake_envelope_z_range(0.0, 25.0, 0.0)
    assert lo == pytest.approx(-12.5)
    assert hi == pytest.approx(12.5)
    lo2, hi2 = intake_envelope_z_range(0.0, 25.0, 10.0)
    assert lo2 == pytest.approx(-12.5)
    assert hi2 == pytest.approx(22.5)


def test_fit_envelope_respects_max_depth_mm():
    import pytest
    from fansim.cockpit.placement import impeller_z_extent
    from fansim.optimize.search_space import blade_from_flat

    spec = get_fan_spec("a12x25")
    flat = stock_blade_flat("a12x25")
    # Force a deep rake so nominal fit would shrink; with high max_depth it should not need to.
    flat = {**flat, "sweep_tip": 8.0, "sweep_mid": 6.0}
    fitted_nom = fit_envelope(flat, spec, features=Features())
    fitted_wide = fit_envelope(flat, spec, features=Features(), max_depth_mm=40.0)
    d_nom = impeller_z_extent(blade_from_flat(fitted_nom.flat, Features()))
    d_wide = impeller_z_extent(blade_from_flat(fitted_wide.flat, Features()))
    assert d_nom <= spec.depth_mm[1] + 0.15
    # Wide budget should leave more axial rake than nominal clamp (or at least not deeper-cut).
    assert abs(float(fitted_wide.flat.get("sweep_tip", 0))) >= abs(float(fitted_nom.flat.get("sweep_tip", 0))) - 1e-6
```

(Add `import pytest` at top of file for the envelope test.)

- [ ] **Step 2: Run tests — expect FAIL (helpers missing)**

Run: `uv run pytest tests/test_intake_overbuild.py -v`  
Expected: import / attribute errors on new symbols.

- [ ] **Step 3: Implement helpers + fit_envelope kwarg**

In `fansim/cockpit/placement.py` (near `impeller_z_extent`):

```python
def intake_extra_mm(*, enabled: bool, extra_mm: float) -> float:
    if not enabled:
        return 0.0
    try:
        v = float(extra_mm)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(20.0, v))


def effective_depth_max(spec: FanSpec, *, intake_extra: float = 0.0) -> float:
    return float(spec.depth_mm[1]) + float(intake_extra or 0.0)


def depth_allow_max(spec: FanSpec, *, intake_extra: float = 0.0) -> float:
    return float(spec.depth_mm[1]) + float(spec.leeway_depth_mm or 0.0) + float(intake_extra or 0.0)


def intake_envelope_z_range(
    z_mid: float, nominal_depth: float, intake_extra: float = 0.0,
) -> tuple[float, float]:
    """Outlet-anchored [z_lo, z_hi]: outlet at z_mid - nominal/2; +Z grows by intake_extra."""
    nom = float(nominal_depth)
    extra = float(intake_extra or 0.0)
    z_lo = float(z_mid) - 0.5 * nom
    z_hi = z_lo + nom + extra
    return z_lo, z_hi
```

Change `fit_envelope` signature to add `max_depth_mm: float | None = None` and replace `max_d = float(spec.depth_mm[1])` with:

```python
max_d = float(spec.depth_mm[1] if max_depth_mm is None else max_depth_mm)
```

- [ ] **Step 4: Re-run tests — expect PASS**

Run: `uv run pytest tests/test_intake_overbuild.py -v`  
Expected: all PASS.

- [ ] **Step 5: Mark spec accepted** — set Status line to `accepted`.

- [ ] **Step 6: Commit** (only if user asked for commits in-session; otherwise leave working tree — this session user has asked commits before, but do not commit unless continuing that pattern; **skip commit unless user requested** for this feature batch — combine at end if user wants).

---

### Task 2: Cockpit state + active_spec + Fit wiring

**Files:**
- Modify: `fansim/cockpit/fan_core.py`
- Modify: `fansim/cockpit/fan_editor.py`

**Interfaces:**
- Consumes: `intake_extra_mm`, `effective_depth_max` from Task 1
- Produces: `state.intake_overbuild`, `state.intake_overbuild_mm`; `active_spec()` with bumped `leeway_depth_mm`

- [ ] **Step 1: Add state defaults in `init_fan_state` / core defaults**

```python
state.intake_overbuild = False
state.intake_overbuild_mm = 10.0
```

- [ ] **Step 2: Update `active_spec()`**

```python
def active_spec():
    from fansim.cockpit.placement import intake_extra_mm
    extra = intake_extra_mm(
        enabled=bool(getattr(state, "intake_overbuild", False)),
        extra_mm=float(getattr(state, "intake_overbuild_mm", 10.0) or 0.0),
    )
    return dataclasses.replace(
        get_fan_spec(state.fan_model),
        leeway_tip_dia_mm=float(state.lee_tip),
        leeway_depth_mm=float(state.lee_depth) + extra,
        leeway_weight_g=float(state.lee_weight),
        over_voltage_v=float(state.lee_overvolt),
    )
```

Note: `over_spec_flags` still uses nominal depth — Assess honesty preserved. `check_build` uses leeway including intake extra — Assess allow gate expands.

- [ ] **Step 3: Wire `on_fit_envelope` to pass effective max**

In `fan_editor.py` `on_fit_envelope`:

```python
from fansim.cockpit.placement import effective_depth_max, fit_envelope, intake_extra_mm

def on_fit_envelope():
    spec = session.active_spec()
    # active_spec already folded intake into leeway; Fit clamps to effective (nominal+intake),
    # not nominal+library-leeway-only — use effective_depth_max with the same extra.
    extra = intake_extra_mm(
        enabled=bool(getattr(state, "intake_overbuild", False)),
        extra_mm=float(getattr(state, "intake_overbuild_mm", 10.0) or 0.0),
    )
    # Strip intake from leeway for the Fit clamp base: effective = nominal + intake
    # (library leeway is allow-gate only; Fit target stays effective_depth_max)
    max_d = effective_depth_max(spec, intake_extra=extra)
    # Wait: active_spec has leeway_depth = lee + extra, but depth_mm[1] still nominal.
    # effective_depth_max(spec, intake_extra=extra) == nominal + extra. Correct.
    res = fit_envelope(
        edit_flat(), spec, features=edit_features(), max_depth_mm=max_d,
    )
    ...
```

Keep existing apply-to-editor behavior after fit.

- [ ] **Step 4: Smoke** — `uv run pytest tests/test_intake_overbuild.py tests/test_a12x25_reference_geometry.py -v`  
Expected: PASS (preserve_tip tests unchanged).

---

### Task 3: Viz asymmetric envelope + highlight

**Files:**
- Modify: `fansim/cockpit/fan_viz.py`

**Interfaces:**
- Consumes: `intake_extra_mm`, `intake_envelope_z_range`

- [ ] **Step 1: Update `_spec_limits` / highlight / envelope**

```python
def _intake_extra():
    from fansim.cockpit.placement import intake_extra_mm
    return intake_extra_mm(
        enabled=bool(getattr(state, "intake_overbuild", False)),
        extra_mm=float(getattr(state, "intake_overbuild_mm", 10.0) or 0.0),
    )

def _spec_limits():
    s = session.active_spec()
    return s.tip_dia_mm[1] / 2.0, s.depth_mm[1], _intake_extra()

def _out_of_spec_mask(mesh):
    import numpy as np
    from fansim.cockpit.placement import intake_envelope_z_range
    pts = mesh.points
    r = np.hypot(pts[:, 0], pts[:, 1])
    z = pts[:, 2]
    tip_r, nom_depth, extra = _spec_limits()
    zmid = 0.5 * (float(z.min()) + float(z.max()))
    z_lo, z_hi = intake_envelope_z_range(zmid, nom_depth, extra)
    mask = (r > tip_r) | (z < z_lo) | (z > z_hi)
    return mask.astype(float)

def _add_envelope(mesh):
    from fansim.cockpit.placement import intake_envelope_z_range
    zc = mesh.points[:, 2]
    zmid = 0.5 * (float(zc.min()) + float(zc.max()))
    tip_r, nom_depth, extra = _spec_limits()
    z_lo, z_hi = intake_envelope_z_range(zmid, nom_depth, extra)
    height = z_hi - z_lo
    center_z = 0.5 * (z_lo + z_hi)
    cyl = fan_runtime.pv.Cylinder(
        center=(0, 0, center_z),
        direction=(0, 0, 1),
        radius=tip_r,
        height=height,
        resolution=64,
    )
    ...
```

- [ ] **Step 2: Re-render on overbuild toggle**

Add `intake_overbuild`, `intake_overbuild_mm` to `@state.change` for `_on_viz_toggle`.

- [ ] **Step 3: Quick unit reuse** — no new viz test required if `intake_envelope_z_range` covered; optional assert in `test_intake_overbuild.py` already enough.

---

### Task 4: Fit & seed UI + Hub slider ceilings

**Files:**
- Modify: `fansim/cockpit/fan_tab_ui.py`
- Modify: `fansim/cockpit/fan_core.py` (optional max state vars) or bind slider max via state

**Interfaces:**
- Consumes: state keys from Task 2

- [ ] **Step 1: Add UI under Fit & seed panel** (before Fit envelope buttons)

```python
v3.VSwitch(
    v_model=("intake_overbuild",),
    density="compact",
    hide_details=True,
    color="primary",
    inset=True,
    label="Allow intake overbuild (+Z)",
    classes="mb-1",
)
v3.VSlider(
    v_model=("intake_overbuild_mm",),
    min=0,
    max=20,
    step=1,
    label="Extra intake (mm)",
    thumb_label=True,
    density="compact",
    hide_details=True,
    classes="mb-1",
    disabled=("!intake_overbuild",),
)
html.Div(
    "Stock frame depth stays nominal; on = blades/hub may extend past the inlet (+Z) "
    "by Extra. Flagged over-spec vs datasheet depth. CFD duct still stock — "
    "won't drop into a stock frame.",
    classes="text-caption text-medium-emphasis mb-2",
)
```

- [ ] **Step 2: Hub slider maxes when overbuild on**

Replace fixed Hub sliders with max bound to state (add defaults in fan_core):

```python
state.e_blade_hub_z_max = 8.0
state.e_hub_height_max = 30.0
state.e_hub_nose_max = 15.0
```

In fan_editor (or fan_core) `@state.change("intake_overbuild", "intake_overbuild_mm")`:

```python
def _refresh_intake_slider_maxes(**_):
    from fansim.cockpit.placement import intake_extra_mm
    extra = intake_extra_mm(
        enabled=bool(state.intake_overbuild),
        extra_mm=float(state.intake_overbuild_mm or 0.0),
    )
    state.e_blade_hub_z_max = 8.0 + 0.5 * extra
    state.e_hub_height_max = 30.0 + extra
    state.e_hub_nose_max = 15.0 + 0.5 * extra
```

In UI Hub panel:

```python
_slider("Hub height (0=auto)", "e_hub_height", 0, ("e_hub_height_max",), 0.5, unit="mm")
```

Check whether `_slider` accepts a state-tuple for `max`; if it only takes float, use raw `v3.VSlider` for these three or extend `_slider` to allow `mx` as str/tuple. Prefer extending `slider()` in `fan_widgets.py` minimally: if `mx` is str, use `max=(mx,)` binding.

- [ ] **Step 3: Actions chip when on** (optional one-liner under Actions hose chip)

```python
html.Div(
    "intake +{{ intake_overbuild_mm }} mm overbuild · won't drop into stock frame",
    v_show="intake_overbuild",
    classes="text-caption text-warning mb-1",
)
```

- [ ] **Step 4: Syntax / import smoke**

Run: `uv run python -c "from fansim.cockpit import fan_tab_ui, fan_core, fan_viz, fan_editor; print('ok')"`  
Expected: `ok` (VTK teardown crash on Windows exit is OK).

- [ ] **Step 5: Full targeted pytest**

Run: `uv run pytest tests/test_intake_overbuild.py tests/test_a12x25_reference_geometry.py tests/test_fan_tab_setup_smoke.py -v`  
Expected: PASS (ignore ACCESS_VIOLATION after green on Windows).

---

### Task 5: Roadmap note

**Files:**
- Modify: `docs/roadmap.md` — under soft software leftovers, one line that intake overbuild landed (or add tiny §21.3 checkbox done).

- [ ] **Step 1: Add** `- [x] **Intake overbuild (+Z)** — Design Fit & seed switch; effective depth; asymmetric envelope. DONE <date>.`
- [ ] **Step 2: Done**

---

## Spec coverage check

| Spec requirement | Task |
|------------------|------|
| Switch + extra mm 0–20 default 10 | 2, 4 |
| effective depth for Fit/Assess/highlight/envelope | 1–3 |
| +Z-only viz growth | 1, 3 |
| Widen hub sliders | 4 |
| over_spec vs nominal | 2 (leeway bump only; flags unchanged) |
| Honesty caption | 4 |
| CFD duct unchanged | non-goal / no task |
| Tests | 1 |

## Placeholder scan

None intentional. Slider `_slider` max-binding must be verified in Task 4 Step 2 against `fan_widgets.slider` signature — if only float, use explicit `VSlider`.
