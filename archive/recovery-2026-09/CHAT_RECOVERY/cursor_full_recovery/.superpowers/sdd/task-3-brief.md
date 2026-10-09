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
