<!-- RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md. -->

# Winglet × Shroud Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Couple the winglet and shroud levers so a winglet is applied only when the tip has a leakage path (open or TE-anchored partial ring), never under a full-span ring — in the optimizer, in design rebuilds, and (via rebuild) in the cockpit.

**Architecture:** One shared rule, `not shroud_is_full(params)`, gates `apply_winglet` at the two geometry-assembly sites in `fansim/optimize/search_space.py` — `suggest_params` (optimizer sample) and `blade_from_flat` (rebuild from a stored trial / the cockpit). `--shroud` gains a searchable `shroud_height_frac ∈ [0.30, 1.0]`; winglet DOFs stay always-sampled (static NSGA-II space) but inert on a full ring. CFD gap logic and the fan BEM are untouched.

**Tech Stack:** Python 3.12 (uv), Optuna (NSGA-II / FixedTrial), CadQuery geometry, pytest.

## Global Constraints

- `shroud_is_full(params)` already exists in `fansim/geometry/blade.py`: `thick > 0 and frac >= 1 - SHROUD_FULL_EPS` (eps `1e-9`). Reuse it; do not redefine the rule.
- Ring **thickness** stays fixed at `SHROUD_DEFAULT_MM` (1.6 mm) — do NOT make thickness a search DOF.
- Searchable shroud height range is exactly `[0.30, 1.0]`, param name `shroud_height_frac`, TE-anchored.
- Winglet DOFs (`winglet_sweep`, `winglet_lean`) must remain sampled on every `--winglet` trial (static search space); only their *application* is gated.
- Do NOT change `fansim/fan_bem.py`, the CFD ring-to-frame gap in `fansim/optimize/objectives.py`, `apply_winglet` internals, or the `WINGLET` DOF bounds.
- No CFD/Docker in any test (`-m "not docker and not slow"` must stay green).
- Winglet application signal for tests: `apply_winglet` turns the 3-station blade into a 4-station blade (inserts a shoulder + deflected tip). `len(params.stations) == 4` ⇒ winglet applied; `== 3` ⇒ suppressed.
- Commit-message trailer on every commit:
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`

---

### Task 1: Searchable shroud height + winglet gate in `suggest_params`

**Files:**
- Modify: `fansim/optimize/search_space.py:10` (import), `fansim/optimize/search_space.py:180-188` (winglet/shroud blocks)
- Test: `tests/test_shroud.py`

**Interfaces:**
- Consumes: `suggest_params(trial, *, with_shroud, with_winglet, ...)`, `SHROUD_DEFAULT_MM`, `WINGLET` (all already in `search_space.py`); `shroud_is_full` (from `fansim.geometry.blade`).
- Produces: `suggest_params` now samples float param `shroud_height_frac ∈ [0.30, 1.0]` whenever `with_shroud`, and applies the winglet only when `not shroud_is_full(bp)`. Adds `shroud_is_full` to the module's top import (Task 2 relies on that import already being present).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_shroud.py`:

```python
def test_suggest_params_searches_shroud_height():
    study = optuna.create_study(directions=["maximize", "maximize", "maximize"])
    fracs = [suggest_params(study.ask(), with_shroud=True).shroud_height_frac
             for _ in range(25)]
    assert all(0.30 <= f <= 1.0 for f in fracs)
    assert max(fracs) - min(fracs) > 0.05   # actually varying, not pinned to a constant


def test_suggest_params_full_ring_suppresses_winglet():
    from optuna.trial import FixedTrial
    base = {
        "n_blades": 7, "stagger_root": 26, "stagger_mid": 24, "stagger_tip": 20,
        "chord_root": 30, "chord_mid": 34, "chord_tip": 26, "sweep_mid": 3, "sweep_tip": 5,
        "lean_mid": 8, "lean_tip": 12, "max_camber": 0.05,
        "winglet_sweep": 9.0, "winglet_lean": 15.0,
    }
    full = suggest_params(FixedTrial({**base, "shroud_height_frac": 1.0}),
                          with_shroud=True, with_winglet=True)
    assert len(full.stations) == 3   # full ring -> winglet suppressed (no shoulder station)


def test_suggest_params_partial_ring_keeps_winglet():
    from optuna.trial import FixedTrial
    base = {
        "n_blades": 7, "stagger_root": 26, "stagger_mid": 24, "stagger_tip": 20,
        "chord_root": 30, "chord_mid": 34, "chord_tip": 26, "sweep_mid": 3, "sweep_tip": 5,
        "lean_mid": 8, "lean_tip": 12, "max_camber": 0.05,
        "winglet_sweep": 9.0, "winglet_lean": 15.0,
    }
    part = suggest_params(FixedTrial({**base, "shroud_height_frac": 0.5}),
                          with_shroud=True, with_winglet=True)
    assert len(part.stations) == 4   # partial ring leaves a leak -> winglet applied
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run python -m pytest tests/test_shroud.py::test_suggest_params_full_ring_suppresses_winglet tests/test_shroud.py::test_suggest_params_partial_ring_keeps_winglet tests/test_shroud.py::test_suggest_params_searches_shroud_height -v`
Expected: FAIL — today `suggest_params` samples no `shroud_height_frac` (frac stays 1.0) and always applies the winglet (4 stations even on a full ring).

- [ ] **Step 3: Add `shroud_is_full` to the import**

In `fansim/optimize/search_space.py`, change line 10 from:

```python
from fansim.geometry.blade import BladeParams, RadialStation, SHROUD_DEFAULT_MM, normalize_shroud_thick_mm
```

to:

```python
from fansim.geometry.blade import (
    BladeParams, RadialStation, SHROUD_DEFAULT_MM, normalize_shroud_thick_mm, shroud_is_full,
)
```

- [ ] **Step 4: Reorder to set the shroud first, then gate the winglet**

In `suggest_params`, replace the current winglet/spacing/shroud blocks (the three `if with_winglet` / `if with_spacing` / `if with_shroud` clauses just before `return bp`) with, in this order:

```python
    if with_shroud:                       # set the ring FIRST so the winglet gate can see it
        bp.shroud_thick_mm = SHROUD_DEFAULT_MM
        bp.shroud_height_frac = trial.suggest_float("shroud_height_frac", 0.30, 1.0)
    if with_winglet:                      # sample always (static space); apply only with a leak path
        wl_sweep = trial.suggest_float("winglet_sweep", *WINGLET["winglet_sweep"])
        wl_lean = trial.suggest_float("winglet_lean", *WINGLET["winglet_lean"])
        if not shroud_is_full(bp):        # §7.5: a full ring kills the tip leak -> winglet is blockage
            from fansim.geometry.blade import apply_winglet
            apply_winglet(bp, sweep_add=wl_sweep, lean_add=wl_lean)
    if with_spacing:
        _apply_spacing(bp, trial.suggest_float("spacing_spread", 0.0, 0.6),
                       trial.suggest_int("spacing_seed", 0, 99999))
    return bp
```

- [ ] **Step 5: Run the new tests + the existing shroud suite**

Run: `uv run python -m pytest tests/test_shroud.py -v`
Expected: PASS — including the pre-existing `test_suggest_params_stamps_default_shroud` (thickness still `SHROUD_DEFAULT_MM`).

- [ ] **Step 6: Commit**

```bash
git add fansim/optimize/search_space.py tests/test_shroud.py
git commit -m "$(printf 'Search shroud height and gate the winglet on it in suggest_params\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

### Task 2: Winglet gate on rebuild (`blade_from_flat`) — covers the cockpit

**Files:**
- Modify: `fansim/optimize/search_space.py:229-233` (the winglet block in `blade_from_flat`)
- Test: `tests/test_shroud.py`

**Interfaces:**
- Consumes: `shroud_is_full` (imported into the module by Task 1); `blade_from_flat(p, features=None)`. In `blade_from_flat`, `bp.shroud_thick_mm` and `bp.shroud_height_frac` are already set (lines 225-228) before the winglet block, so `shroud_is_full(bp)` is valid there.
- Produces: `blade_from_flat` applies the winglet only when `not shroud_is_full(bp)`. The cockpit inherits this — it builds every design via `blade_from_flat(edit_flat(), ...)`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_shroud.py`:

```python
_WL_GEOM = {
    "n_blades": 7, "chord_root": 34, "chord_mid": 44, "chord_tip": 38,
    "stagger_root": 26, "stagger_mid": 26, "stagger_tip": 22,
    "sweep_mid": 3, "sweep_tip": 5, "max_camber": 0.05,
    "winglet_sweep": 8.0, "winglet_lean": 12.0,
}


def test_open_tip_keeps_winglet_on_rebuild():
    p = blade_from_flat(dict(_WL_GEOM))            # no shroud
    assert len(p.stations) == 4                    # baseline: winglet applied on an open tip


def test_full_ring_blocks_winglet_on_rebuild():
    p = blade_from_flat({**_WL_GEOM,
                         "shroud_thick_mm": SHROUD_DEFAULT_MM, "shroud_height_frac": 1.0})
    assert len(p.stations) == 3                    # full ring -> winglet suppressed on rebuild


def test_partial_ring_keeps_winglet_on_rebuild():
    p = blade_from_flat({**_WL_GEOM,
                         "shroud_thick_mm": SHROUD_DEFAULT_MM, "shroud_height_frac": 0.5})
    assert len(p.stations) == 4                    # partial ring keeps the winglet
```

- [ ] **Step 2: Run the tests to verify the full-ring case fails**

Run: `uv run python -m pytest tests/test_shroud.py::test_full_ring_blocks_winglet_on_rebuild tests/test_shroud.py::test_partial_ring_keeps_winglet_on_rebuild tests/test_shroud.py::test_open_tip_keeps_winglet_on_rebuild -v`
Expected: `test_full_ring_blocks_winglet_on_rebuild` FAILS (today a full-ring rebuild still regrows the winglet → 4 stations); the other two PASS already.

- [ ] **Step 3: Gate the winglet in `blade_from_flat`**

In `fansim/optimize/search_space.py`, replace the winglet block (currently lines 229-233):

```python
    if float(p.get("winglet_sweep", 0.0)) or float(p.get("winglet_lean", 0.0)):
        from fansim.geometry.blade import apply_winglet   # tip curls beyond winglet_span
        apply_winglet(bp, span_frac=float(p.get("winglet_span", 0.85)),
                      sweep_add=float(p.get("winglet_sweep", 0.0)),
                      lean_add=float(p.get("winglet_lean", 0.0)))
```

with:

```python
    if (not shroud_is_full(bp)) and (
            float(p.get("winglet_sweep", 0.0)) or float(p.get("winglet_lean", 0.0))):
        from fansim.geometry.blade import apply_winglet   # §7.5: no winglet under a full ring
        apply_winglet(bp, span_frac=float(p.get("winglet_span", 0.85)),
                      sweep_add=float(p.get("winglet_sweep", 0.0)),
                      lean_add=float(p.get("winglet_lean", 0.0)))
```

- [ ] **Step 4: Run the rebuild tests + the existing shroud suite**

Run: `uv run python -m pytest tests/test_shroud.py -v`
Expected: PASS (all three new rebuild tests + the existing ones).

- [ ] **Step 5: Commit**

```bash
git add fansim/optimize/search_space.py tests/test_shroud.py
git commit -m "$(printf 'Suppress the winglet under a full ring on blade_from_flat rebuilds\n\nCovers the cockpit, which builds every design through blade_from_flat.\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

### Task 3: Surface the coupling — CLI help, cockpit note, roadmap

**Files:**
- Modify: `scripts/run_optimization.py:83-88` (`--winglet` / `--shroud` help)
- Modify: `fansim/cockpit/app.py:2136` (winglet/shroud caption)
- Modify: `docs/roadmap.md` (§7.5 + recommended sequence)
- Test: `tests/test_shroud.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `--winglet`/`--shroud` help text and the cockpit caption both state the coupling; roadmap §7.5 marked done.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_shroud.py`:

```python
def test_run_optimization_help_notes_winglet_shroud_coupling():
    text = Path("scripts/run_optimization.py").read_text(encoding="utf-8")
    assert "disables the winglet" in text          # coupling is documented in CLI help
    assert "shroud_height_frac" in text or "0.30" in text


def test_cockpit_caption_notes_winglet_auto_disabled():
    text = Path("fansim/cockpit/app.py").read_text(encoding="utf-8")
    assert "disables the winglet" in text
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run python -m pytest tests/test_shroud.py::test_run_optimization_help_notes_winglet_shroud_coupling tests/test_shroud.py::test_cockpit_caption_notes_winglet_auto_disabled -v`
Expected: FAIL — the phrase "disables the winglet" is not in either file yet.

- [ ] **Step 3: Update the `--winglet` help**

In `scripts/run_optimization.py`, replace the `--winglet` help (lines 83-84):

```python
    ap.add_argument("--winglet", action="store_true",
                    help="search a tip winglet too (CFD: mild winglet ~+4%% airflow; adds tip depth)")
```

with:

```python
    ap.add_argument("--winglet", action="store_true",
                    help="search a tip winglet too (CFD: mild winglet ~+4%% airflow; adds tip depth). "
                         "Coupled to --shroud (roadmap 7.5): a full-span ring disables the winglet — "
                         "a full ring already kills the tip leak, so a winglet there is pure blockage.")
```

- [ ] **Step 4: Update the `--shroud` help**

In `scripts/run_optimization.py`, replace the `--shroud` help (lines 85-88):

```python
    ap.add_argument("--shroud", action="store_true",
                    help="fuse a 1.6 mm tip ring on every trial and shrink the tip-radius cap so "
                         "the grown OD still fits the frame (roadmap 2.1). CFD sits in the spec "
                         "frame ID; leftover gap must be >= --tip-gap.")
```

with:

```python
    ap.add_argument("--shroud", action="store_true",
                    help="fuse a 1.6 mm tip ring and search its TE-anchored height "
                         "(shroud_height_frac in [0.30, 1.0]); shrink the tip-radius cap so the grown "
                         "OD still fits the frame (roadmap 2.1). CFD sits in the spec frame ID; leftover "
                         "gap must be >= --tip-gap. A full ring (frac 1.0) disables any --winglet.")
```

- [ ] **Step 5: Update the cockpit caption**

In `fansim/cockpit/app.py`, replace the caption string at line 2136:

```python
                                                    html.Div("0 thickness = off. First thickness step is 0.8 mm (two walls); 1.6 mm is four walls. Height 1.0 covers the full tip; below 1.0 the hoop starts at the trailing edge and BEM still treats it as an open tip. A full ring usually makes winglets worse — leave winglet at 0.",
```

with:

```python
                                                    html.Div("0 thickness = off. First thickness step is 0.8 mm (two walls); 1.6 mm is four walls. Height 1.0 covers the full tip; below 1.0 the hoop starts at the trailing edge and BEM still treats it as an open tip. A full ring (height 1.0) disables the winglet automatically — once the tip is fully covered a winglet only adds blockage.",
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `uv run python -m pytest tests/test_shroud.py -v`
Expected: PASS.

- [ ] **Step 7: Update the roadmap**

In `docs/roadmap.md`:

1. In §7.5 (line ~178), change `- [ ] **7.5 ...` to `- [x] **7.5 ... DONE 2026-09-03.**` and replace "winglet×shroud policy is not." with: "Winglet×shroud policy DONE 2026-09-03: `--shroud` searches a TE-anchored `shroud_height_frac ∈ [0.30, 1.0]`; a winglet is applied only when the ring is not full-span (`shroud_is_full`), enforced in `suggest_params` and `blade_from_flat` (cockpit inherits it)."
2. In the ★ Recommended sequence item 1 (line ~17-19), change "winglet interaction remains (§7.5)." to "winglet×shroud policy done 2026-09-03 — tip-shroud thread closed (remaining: circular AMCA rig / absolute pressure, tracked in §1.1/§1.5)."
3. In §2.1 (line ~62-67), append after "remaining winglet interaction (§7.5).": "DONE 2026-09-03 — see §7.5."
4. In the "Recently shipped" block (line ~198-208), append: "winglet×shroud policy: searchable partial-ring height + winglet gated off on full rings (§7.5)."

- [ ] **Step 8: Commit**

```bash
git add scripts/run_optimization.py fansim/cockpit/app.py docs/roadmap.md tests/test_shroud.py
git commit -m "$(printf 'Document the winglet x shroud coupling and mark roadmap 7.5 done\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

### Task 4: Full fast-suite regression

**Files:** none (verification only).

- [ ] **Step 1: Run the whole non-CFD suite**

Run: `uv run python -m pytest -m "not docker and not slow" -rf --tb=short -q`
Expected: `test_shroud.py`, `test_placement.py`, and `test_search_extended.py` all green, and **exactly the 6 pre-existing baseline failures below** remain — no new ones.

**Recorded baseline (branch `winglet-shroud-policy`, before this plan — 6 failed, 288 passed):** these are pre-existing, unrelated to the winglet×shroud work (all downstream of the corrected a12x25 spec), and must NOT be "fixed" in this plan:
- `tests/test_fan_spec.py::test_check_build_pass_and_fail`
- `tests/test_fan_spec.py::test_leeway_allows_over_nominal_but_flags_it`
- `tests/test_fan_spec.py::test_over_voltage_leeway_raises_power_budget`
- `tests/test_print_export.py::test_motor_mount_refuses_small_hub`
- `tests/test_print_export.py::test_fan_spec_motor_mount_roundtrips`
- `tests/test_printability_score.py::test_thin_walls_need_resin`

- [ ] **Step 2: If any pre-existing baseline failures remain, report them**

Do not "fix" unrelated pre-existing failures inside this plan. List them for the user with a one-line root-cause guess each, so they can decide whether to spin off a separate task.

## Self-Review

**Spec coverage:**
- Rule `not shroud_is_full` at both assembly sites → Tasks 1 (suggest_params) & 2 (blade_from_flat). ✓
- Searchable `shroud_height_frac ∈ [0.30, 1.0]` → Task 1. ✓
- Winglet DOFs always sampled, inert on full → Task 1 (sampled before the gate). ✓
- Cockpit inherits via `blade_from_flat` + note → Task 2 (mechanism) + Task 3 (caption). ✓
- CFD gap + BEM unchanged → no task touches `objectives.py`/`fan_bem.py`; `test_bem_partial_ring_matches_open_tip` already guards the BEM. ✓
- CLI help names the coupling; no `★` → Task 3 (existing `test_run_optimization_declares_shroud_flag` asserts no `★`). ✓
- Tests, no CFD → all tests are pure geometry/param; Task 4 runs `-m "not docker and not slow"`. ✓

**Placeholder scan:** none — every code step shows the exact before/after.

**Type consistency:** `shroud_is_full` (bool), `shroud_height_frac` (float param name), `len(params.stations)` 3-vs-4 signal, and the phrase `"disables the winglet"` are used identically across Tasks 1-3. ✓
