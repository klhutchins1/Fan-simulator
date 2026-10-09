### Task 2: Floor gate, pin evaluate_candidate, leftover BEM

**Files:**
- Modify: `fansim/optimize/objectives.py`
- Test: `tests/test_optimize.py`

Fitting-blade helper (put in `tests/test_optimize.py`). If leftover vs 110 mm is still `< 0.5`, shrink `tip_radius` (do not grow the casing):

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

Add `_a12x25_fitting_params` to `tests/test_optimize.py`.

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
