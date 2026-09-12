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
