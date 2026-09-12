# Ring-to-Frame Gap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Spec-backed optimizer CFD sits in the fan-frame ID; leftover radial gap is scored; leftover tighter than `--tip-gap` is refused; open/partial BEM uses that leftover.

**Architecture:** `remaining_tip_gap_mm` is `casing_id/2 − (open_tip_rmax + shroud thick)`. `rig_for_impeller(..., casing_id_mm=)` pins `duct_radius` to that ID. `evaluate_candidate` always has a `FanSpec`, so it pins, gates leftover `<` floor, then passes leftover into `pq_curve`. `--tip-gap` is the floor (default 0.5 mm). Callers that omit `casing_id_mm` keep today’s growing duct.

**Tech Stack:** Python 3.12 via uv, pytest. No Docker CFD campaign.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-02-ring-to-frame-gap-design.md`
- Python `>=3.12,<3.13` via `uv`; tests: `uv run python -m pytest -q -m "not docker and not slow"`
- Pin ID = `spec.tip_dia_mm[1]` (110 mm a12x25, 119 mm generic_120)
- `--tip-gap` / `OPTIMIZER_TIP_GAP_MM` (0.5) is the **minimum leftover**, not a growing-duct clearance
- Refuse when `remaining < floor` (equal 0.5 mm passes); no STL, no BEM, no mesh
- Full ring still `shroud_is_full` → BEM `F = 1`; ring-to-frame leak stays CFD-only
- `pq_curve` default `tip_gap_mm` stays `DEFAULT_TIP_GAP_MM` (0.5) when no spec is passed
- `rig_for_impeller` without `casing_id_mm` stays growing (`envelope + tip_gap_mm`, default 1.0)
- No catalog backfill; do not commit `catalog/catalog.db`
- No winglet policy, no circular AMCA, no extra barrel STL, no Propeller-tab change
- No `★` in Windows CLI help
- Windows: CadQuery teardown exit 3221226356 / -1073741819 / 3221225477 is not a test failure — judge by assertion output
- Work on branch `ring-to-frame-gap`; do not commit to `master`; do not `git push`
- Unrelated dirty files (`fansim/catalog.py`, a12x25 test updates, `catalog.db`) stay out of every commit
- Commit after each task

---

## File structure

| Path | Responsibility |
|---|---|
| `fansim/cfd/domain.py` | `remaining_tip_gap_mm`, `casing_id_mm` on `rig_for_impeller` |
| `fansim/optimize/objectives.py` | Floor gate, pin, BEM leftover, stamp `raw` |
| `fansim/optimize/study.py` | Trial attrs from `result.raw` (actual leftover, not the CLI floor) |
| `fansim/cockpit/data.py` | Pass `casing_id_mm` / `tip_gap_floor_mm` through `Design.extra` |
| `scripts/run_optimization.py` | `--tip-gap` and `--shroud` help text |
| `tests/test_cfd.py` | Helper + pin vs growing duct |
| `tests/test_optimize.py` | Floor gate, default envelope, BEM-prescreen fitting blade, trial attrs, CLI |
| `tests/test_fan_bem.py` | Open-tip leftover 2 mm vs 0.5 mm; full ring still beats open |
| `docs/roadmap.md` + spec | §7.5 CFD clearance done; spec `accepted` |

Do **not** change `fansim/fan_bem.py` signatures (`tip_gap_mm` already exists). Do **not** change `check_build`.

Fitting-blade helper used in Task 2 tests (short chord so leftover vs 110 mm is unambiguously ≥ 0.5):

```python
def _a12x25_fitting_params() -> BladeParams:
    return BladeParams(
        tip_radius=50.0,
        stations=[
            RadialStation(0.0, 18.0, 40.0, thickness=0.12, max_camber=0.04),
            RadialStation(0.5, 18.0, 40.0, thickness=0.10, max_camber=0.04),
            RadialStation(1.0, 14.0, 40.0, thickness=0.08, max_camber=0.04),
        ],
    )
```

If `remaining_tip_gap_mm(p, 110.0) < 0.5` on that recipe, shrink `tip_radius` (do not grow the casing).

---

### Task 1: Helper + pinned rig

**Files:**
- Modify: `fansim/cfd/domain.py`
- Test: `tests/test_cfd.py`

**Interfaces:**
- Consumes: `open_tip_rmax_mm(params)`, `params.shroud_thick_mm`, `MM_TO_M`
- Produces:
  - `remaining_tip_gap_mm(params: BladeParams, casing_id_mm: float) -> float`
  - `rig_for_impeller(..., casing_id_mm: float | None = None)`
    - `None`: `duct_radius = (open_tip_rmax + shroud_thick + tip_gap_mm) * MM_TO_M` (today)
    - set: `duct_radius = casing_id_mm / 2 * MM_TO_M`; `TestRig.tip_gap` = leftover metres (`duct_radius − envelope_m`). Ignore `tip_gap_mm` for sizing.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_cfd.py`:

```python
def test_remaining_tip_gap_is_half_casing_minus_built_r():
    from fansim.cfd.domain import remaining_tip_gap_mm
    from fansim.geometry.blade import SHROUD_DEFAULT_MM, open_tip_rmax_mm

    params = BladeParams()
    casing = 200.0
    expect = casing / 2.0 - open_tip_rmax_mm(params)
    assert remaining_tip_gap_mm(params, casing) == pytest.approx(expect)
    params.shroud_thick_mm = SHROUD_DEFAULT_MM
    expect_sh = casing / 2.0 - (open_tip_rmax_mm(params) + SHROUD_DEFAULT_MM)
    assert remaining_tip_gap_mm(params, casing) == pytest.approx(expect_sh)


def test_rig_without_casing_id_still_grows_by_tip_gap():
    from fansim.geometry.blade import open_tip_rmax_mm

    params = BladeParams()
    rig = rig_for_impeller(params, tip_gap_mm=1.0)
    assert rig.duct_radius == pytest.approx((open_tip_rmax_mm(params) + 1.0) / 1000.0)


def test_rig_with_casing_id_pins_duct_and_uses_leftover_gap():
    from fansim.cfd.domain import remaining_tip_gap_mm

    params = BladeParams(tip_radius=40.0)
    rig = rig_for_impeller(params, tip_gap_mm=9.0, casing_id_mm=110.0)
    leftover = remaining_tip_gap_mm(params, 110.0)
    assert leftover > 0.5
    assert rig.duct_radius == pytest.approx(0.055)
    assert rig.tip_gap == pytest.approx(leftover / 1000.0)


def test_rig_pinned_leftover_half_mm_when_casing_is_built_plus_one():
    from fansim.cfd.domain import remaining_tip_gap_mm
    from fansim.geometry.blade import open_tip_rmax_mm

    params = BladeParams(tip_radius=40.0)
    built = open_tip_rmax_mm(params) + float(params.shroud_thick_mm or 0.0)
    casing = 2.0 * (built + 0.5)
    rig = rig_for_impeller(params, casing_id_mm=casing)
    assert remaining_tip_gap_mm(params, casing) == pytest.approx(0.5)
    assert rig.duct_radius == pytest.approx(casing / 2.0 / 1000.0)
    assert rig.tip_gap == pytest.approx(0.0005)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_cfd.py::test_remaining_tip_gap_is_half_casing_minus_built_r tests/test_cfd.py::test_rig_with_casing_id_pins_duct_and_uses_leftover_gap -q --tb=short`

Expected: FAIL (`remaining_tip_gap_mm` not defined / unexpected keyword `casing_id_mm`).

- [ ] **Step 3: Implement helper + pin**

In `fansim/cfd/domain.py`:

Update the module layout comment to:

```text
                      duct radius = casing_id/2 when pinned, else built envelope (+ tip ring) + tip_gap
```

Add next to `OPTIMIZER_TIP_GAP_MM`:

```python
def remaining_tip_gap_mm(params: BladeParams, casing_id_mm: float) -> float:
    """Radial leftover (mm) between the built OD (ring included) and a circular casing ID."""
    from fansim.geometry.blade import open_tip_rmax_mm

    built_r = open_tip_rmax_mm(params) + float(params.shroud_thick_mm or 0.0)
    return float(casing_id_mm) / 2.0 - built_r
```

Change `rig_for_impeller` signature to add `casing_id_mm: float | None = None` after `tip_gap_mm`. Replace the duct-sizing block with:

```python
    from fansim.geometry.blade import open_tip_rmax_mm

    envelope_mm = open_tip_rmax_mm(params) + float(params.shroud_thick_mm or 0.0)
    if casing_id_mm is not None:
        duct_r = float(casing_id_mm) * MM_TO_M / 2.0
        tip_gap_m = duct_r - envelope_mm * MM_TO_M
    else:
        tip_gap_m = tip_gap_mm * MM_TO_M
        duct_r = envelope_mm * MM_TO_M + tip_gap_m
```

Docstring: when `casing_id_mm` is set, the duct is the frame ID and `tip_gap_mm` is ignored for sizing.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_cfd.py -q --tb=short`

Expected: PASS (ignore CadQuery teardown exit if `build_case` tests trip it).

- [ ] **Step 5: Commit**

```bash
git add fansim/cfd/domain.py tests/test_cfd.py
git commit -m "Pin the CFD duct to a casing ID and expose leftover tip gap"
```

---

### Task 2: Floor gate, pin evaluate_candidate, leftover BEM

**Files:**
- Modify: `fansim/optimize/objectives.py`
- Test: `tests/test_optimize.py`

**Interfaces:**
- Consumes: `remaining_tip_gap_mm`, `rig_for_impeller(..., casing_id_mm=)`, `pq_curve(..., tip_gap_mm=)`
- Produces: spec-backed eval always pins; `raw` always includes `tip_gap_mm` (leftover), `casing_id_mm`, `tip_gap_floor_mm` once the gap gate has run; infeasible reason contains `tip gap`, the leftover, the floor, and the frame name/ID

`_infeasible` must accept optional `raw`:

```python
def _infeasible(reason: str, t0: float, raw: dict | None = None) -> ObjectiveResult:
    return ObjectiveResult(False, reason=reason, runtime_s=round(time.time() - t0, 1),
                           raw=raw or {})
```

Gate order after stress (before BEM):

```python
    if tip_gap_mm is None:
        tip_gap_mm = OPTIMIZER_TIP_GAP_MM
    floor = float(tip_gap_mm)
    casing_id = float(spec.tip_dia_mm[1])
    remaining = remaining_tip_gap_mm(params, casing_id)
    gap_raw = {
        "tip_gap_mm": remaining,
        "casing_id_mm": casing_id,
        "tip_gap_floor_mm": floor,
    }
    if remaining < floor:
        return _infeasible(
            f"{spec.name}: tip gap {remaining:.2f} mm < min {floor:.2f} mm "
            f"to {casing_id:.0f} mm frame",
            t0, raw=gap_raw)
```

Import `remaining_tip_gap_mm` from `fansim.cfd.domain`.

BEM prescreen (only reached when leftover ≥ floor):

```python
            bem_cfm = pq_curve(params, spec.rpm, tip_gap_mm=remaining).free_delivery_cfm
```

Remove the later `if tip_gap_mm is None: tip_gap_mm = OPTIMIZER_TIP_GAP_MM` block. Rig call:

```python
    rig0 = rig_for_impeller(
        params,
        tip_gap_mm=remaining,
        casing_id_mm=casing_id,
        inlet_diameters=2.0,
        outlet_diameters=4.0,
    )
```

(`tip_gap_mm=remaining` is unused for sizing when `casing_id_mm` is set; passing it keeps `TestRig.tip_gap` consistent if someone later reads the arg.)

On the feasible `ObjectiveResult`, merge `gap_raw` into `raw`.

Printability/stress failures stay empty `raw` (gate has not run).

- [ ] **Step 1: Write the failing tests**

Add `_a12x25_fitting_params` (see File structure) to `tests/test_optimize.py`.

Replace `test_bem_prescreen_rejects_below_floor_before_geometry` body so it uses `_a12x25_fitting_params()` instead of `BladeParams()`. Keep the 500 CFM floor, `bem-prescreen` in `reason`, and no `impeller.stl`.

Add:

```python
def test_default_bladeparams_fails_a12x25_gap_floor_before_geometry(tmp_path):
    from fansim.cfd.domain import remaining_tip_gap_mm
    from fansim.fan_spec import A12X25

    p = BladeParams()
    assert remaining_tip_gap_mm(p, A12X25.tip_dia_mm[1]) < 0.5
    res = evaluate_candidate(p, tmp_path / "big", procs=1)
    assert res.feasible is False
    assert "tip gap" in res.reason.lower()
    assert "frame" in res.reason.lower()
    assert not (tmp_path / "big" / "impeller.stl").exists()
    assert res.raw["casing_id_mm"] == A12X25.tip_dia_mm[1]
    assert res.raw["tip_gap_floor_mm"] == 0.5


def test_leftover_below_floor_is_infeasible_without_stl(tmp_path):
    from dataclasses import replace

    from fansim.cfd.domain import remaining_tip_gap_mm
    from fansim.fan_spec import A12X25
    from fansim.geometry.blade import open_tip_rmax_mm

    p = _a12x25_fitting_params()
    built = open_tip_rmax_mm(p) + float(p.shroud_thick_mm or 0.0)
    spec = replace(A12X25, tip_dia_mm=(80.0, 2.0 * (built + 0.4)))
    assert remaining_tip_gap_mm(p, spec.tip_dia_mm[1]) == pytest.approx(0.4, abs=1e-6)
    res = evaluate_candidate(p, tmp_path / "tight", procs=1, spec=spec)
    assert res.feasible is False
    assert "tip gap" in res.reason.lower()
    assert "0.40" in res.reason or "0.4" in res.reason
    assert not (tmp_path / "tight" / "impeller.stl").exists()
    assert res.raw["tip_gap_mm"] == pytest.approx(0.4, abs=1e-6)
    assert res.raw["tip_gap_floor_mm"] == 0.5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_optimize.py::test_default_bladeparams_fails_a12x25_gap_floor_before_geometry tests/test_optimize.py::test_leftover_below_floor_is_infeasible_without_stl tests/test_optimize.py::test_bem_prescreen_rejects_below_floor_before_geometry -q --tb=short`

Expected: default `BladeParams()` currently dies later (geometry/`check_build`) or BEM; new tests FAIL until the floor exists. The bem-prescreen test FAIL if it still uses `BladeParams()` (gap gate would steal the reason) — that is the signal to switch to `_a12x25_fitting_params`.

- [ ] **Step 3: Implement the gate, pin, and BEM leftover**

As specified in Interfaces. Do not mesh. Do not change `check_build`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_optimize.py tests/test_cfd.py tests/test_mountable.py -q --tb=short`

Expected: PASS. `test_evaluate_candidate_gate_is_cheap_and_infeasible` still fails on **unprintable** (printability runs before the gap floor).

- [ ] **Step 5: Commit**

```bash
git add fansim/optimize/objectives.py tests/test_optimize.py
git commit -m "Refuse spec-backed CFD when leftover frame gap is below --tip-gap"
```

---

### Task 3: BEM leftover ranking + trial bookkeeping + CLI help

**Files:**
- Modify: `fansim/optimize/study.py` (copy gap keys from `result.raw` onto the trial)
- Modify: `fansim/cockpit/data.py` (`Design.extra`)
- Modify: `scripts/run_optimization.py` (`--tip-gap` and `--shroud` help)
- Test: `tests/test_fan_bem.py`, `tests/test_optimize.py`

**Interfaces:**
- Consumes: Task 2 `result.raw` keys `tip_gap_mm`, `casing_id_mm`, `tip_gap_floor_mm`
- Produces: trial user attrs use **actual leftover** when `raw` has `tip_gap_mm`, else fall back to the CLI floor; Pareto / `load_designs` expose `casing_id_mm` and `tip_gap_floor_mm` (None if absent — old studies still load)

In `run_study` after `evaluate_candidate`, replace the hardcoded floor stamp:

```python
        leftover = result.raw.get("tip_gap_mm")
        trial.set_user_attr(
            "tip_gap_mm",
            float(leftover) if leftover is not None else float(tip_gap_mm),
        )
        trial.set_user_attr("casing_id_mm", result.raw.get("casing_id_mm"))
        trial.set_user_attr(
            "tip_gap_floor_mm",
            result.raw.get("tip_gap_floor_mm", float(tip_gap_mm)),
        )
```

`pareto_summary`: add `"casing_id_mm"` and `"tip_gap_floor_mm"` the same way as `k` (float or None).

`load_designs` extra: same two keys.

CLI:

```python
    ap.add_argument("--tip-gap", type=float, default=OPTIMIZER_TIP_GAP_MM,
                    help="minimum leftover radial gap (mm) between the built impeller and the spec "
                         "frame ID. Default 0.5. Tighter than this is infeasible (not meshed).")
    ap.add_argument("--shroud", action="store_true",
                    help="fuse a 1.6 mm tip ring on every trial and shrink the tip-radius cap so "
                         "the grown OD still fits the frame (roadmap 2.1). CFD sits in the spec "
                         "frame ID; leftover gap must be >= --tip-gap.")
```

No `★`.

- [ ] **Step 1: Write the failing tests**

`tests/test_fan_bem.py`:

```python
def test_open_tip_larger_gap_screens_worse():
    p = BladeParams()
    tight = pq_curve(p, rpm=2000, tip_gap_mm=0.5)
    leaky = pq_curve(p, rpm=2000, tip_gap_mm=2.0)
    assert leaky.free_delivery_cfm <= tight.free_delivery_cfm
    assert leaky.shutoff_dp_pa <= tight.shutoff_dp_pa


def test_full_ring_still_beats_open_at_same_leftover():
    from fansim.geometry.blade import SHROUD_DEFAULT_MM

    open_c = pq_curve(BladeParams(), rpm=2000, tip_gap_mm=2.0)
    p = BladeParams()
    p.shroud_thick_mm = SHROUD_DEFAULT_MM
    sh_c = pq_curve(p, rpm=2000, tip_gap_mm=2.0)
    assert sh_c.shutoff_dp_pa > open_c.shutoff_dp_pa
```

`tests/test_optimize.py` — extend CLI test and add a `run_study` monkeypatch:

```python
def test_run_optimization_tip_gap_help_is_minimum_leftover():
    from pathlib import Path

    text = Path("scripts/run_optimization.py").read_text(encoding="utf-8")
    assert "minimum leftover" in text
    assert "follows the existing tip_gap" not in text
    assert "★" not in text


def test_run_study_stamps_actual_leftover_not_floor(tmp_path, monkeypatch):
    from fansim.optimize import study as study_mod
    from fansim.optimize.objectives import ObjectiveResult

    def fake_evaluate_candidate(_params, workdir, *_args, **_kwargs):
        from pathlib import Path

        Path(workdir).mkdir(parents=True, exist_ok=True)
        return ObjectiveResult(
            feasible=True,
            cfm_free=10.0,
            cfm_load=5.0,
            efficiency=1.0,
            raw={"k": 1.25, "dp_op_pa": 8.0, "q_ref_cfm": 50.0,
                 "tip_gap_mm": 2.1, "casing_id_mm": 110.0, "tip_gap_floor_mm": 0.5},
        )

    monkeypatch.setattr(study_mod, "evaluate_candidate", fake_evaluate_candidate)
    study = study_mod.run_study(n_trials=1, out_dir=tmp_path, procs=1, iters=1, base_cell=0.02)
    assert study.trials[0].user_attrs["tip_gap_mm"] == 2.1
    assert study.trials[0].user_attrs["casing_id_mm"] == 110.0
    assert study.trials[0].user_attrs["tip_gap_floor_mm"] == 0.5
```

In `test_pareto_summary_carries_tip_gap_and_frame_stl` and `test_load_designs_includes_tip_gap_and_frame_stl_extra`, set `casing_id_mm` / `tip_gap_floor_mm` on the fake trial and assert they round-trip. In `test_load_designs_sets_system_curve_keys_none_when_absent`, assert the new keys are None when missing.

Keep `test_run_optimization_declares_tip_gap_flag` (still asserts `--tip-gap` and no `★`).

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_fan_bem.py::test_open_tip_larger_gap_screens_worse tests/test_optimize.py::test_run_optimization_tip_gap_help_is_minimum_leftover tests/test_optimize.py::test_run_study_stamps_actual_leftover_not_floor -q --tb=short`

Expected: FAIL (missing tests / help still says “duct wall” / trial still stores 0.5).

- [ ] **Step 3: Implement bookkeeping + help**

As specified. Existing `test_run_study_sets_system_curve_user_attrs_from_result_raw` stays green because missing `raw["tip_gap_mm"]` falls back to the CLI floor 0.5.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_fan_bem.py tests/test_optimize.py tests/test_cfd.py tests/test_shroud.py -q --tb=short`

Expected: PASS (CadQuery teardown on `test_shroud` ignored).

- [ ] **Step 5: Commit**

```bash
git add fansim/optimize/study.py fansim/cockpit/data.py scripts/run_optimization.py tests/test_fan_bem.py tests/test_optimize.py
git commit -m "Store leftover frame gap on trials and document --tip-gap as a floor"
```

---

### Task 4: Spec accepted + roadmap

**Files:**
- `docs/superpowers/specs/2026-09-02-ring-to-frame-gap-design.md` — `Status: accepted`
- `docs/roadmap.md`

§1.1 remaining line today still says “designed shroud-to-frame gap (§7.5)”. Change remaining to circular AMCA only.

§2.1 remaining: drop “ring-to-frame gap in CFD”; keep winglet interaction.

§7.5 stays **unchecked**. Add that CFD clearance (pinned frame ID + leftover ≥ 0.5 mm) is in; winglet×shroud policy is not.

Recommended sequence item 1: still §7.5, but “ring-to-frame CFD gap done; winglet interaction remains”.

Recently shipped: mention pinned frame-ID duct / leftover `--tip-gap` floor.

- [ ] **Step 1: Edit the two docs**

- [ ] **Step 2: Run** `uv run python -m pytest tests/test_cfd.py tests/test_optimize.py tests/test_fan_bem.py tests/test_shroud.py tests/test_frame.py -q --tb=short -m "not docker"`

Expected: assertions PASS. CadQuery teardown exit is not a failure.

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/specs/2026-09-02-ring-to-frame-gap-design.md docs/roadmap.md
git commit -m "Accept the ring-to-frame gap spec and mark §7.5 CFD clearance done"
```

---

## Self-review

**Spec coverage**

| Spec requirement | Task |
|---|---|
| `remaining_tip_gap_mm` | 1 |
| Pin `rig_for_impeller(casing_id_mm=)` / growing default | 1 |
| Spec-backed `evaluate_candidate` pins to `tip_dia_mm[1]` | 2 |
| `--tip-gap` is min leftover; refuse `<` floor; no STL/BEM/mesh | 2 |
| Gate after stress, before BEM | 2 |
| Default `BladeParams()` infeasible on a12x25 before CAD | 2 |
| BEM prescreen uses leftover; fitting-blade test | 2 |
| Full ring `F = 1`; open leftover 2 vs 0.5 | 3 |
| Trial/catalog keys; no backfill | 3 |
| CLI help; no `★`; `--shroud` wording | 3 |
| Validation / no-spec growing duct | 1 (unchanged path) |
| Spec accepted + roadmap | 4 |
| Non-goals (AMCA, winglet, search DOF, `check_build`, catalog.db, Propeller) | Global Constraints; no task implements them |

**Placeholders:** none. Fitting-blade recipe is concrete; only allowed tweak is shrinking `tip_radius` if leftover is still `< 0.5`.

**Types:** `remaining_tip_gap_mm(params, casing_id_mm: float) -> float`; `casing_id_mm: float | None = None` on `rig_for_impeller`; raw keys `tip_gap_mm` / `casing_id_mm` / `tip_gap_floor_mm` as floats.
