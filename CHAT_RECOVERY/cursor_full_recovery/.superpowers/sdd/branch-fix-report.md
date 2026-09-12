# Branch fix report — tip-shroud whole-branch review

Fixes the three review findings on the stage-1 tip-shroud work: the ring did not actually seal the
tip, `shroud_thick_mm` did not survive a round-trip through Optuna, and the CFD duct wall sat inside
the built ring.

## 1. Critical — the ring now contains the whole tip section

`_shroud_solid` sized the bore as `open_tip_rmax_mm - 0.8`. `open_tip_rmax_mm` is the MAX hypot of
the tip section, which occurs at the LE/TE corners (a staggered chord swings its ends outboard), so
the bore landed at 58.38 mm while mid-chord sits at 56.50 mm — a ~1.9 mm open radial channel past
most of the chord, with only the corners fused. BEM's `F = 1` (no tip leak) was false.

New sizing (intentionally departs from the spec table, which was geometrically wrong):

| | before | after |
|---|---|---|
| outer | `open_tip_rmax_mm + thick` = 60.784 | unchanged, 60.784 |
| inner | `open_tip_rmax_mm - 0.8` = **58.384** | `tip_section_rmin_mm - 0.8` = **55.700** |

Baseline tip section spans hypot 56.500 .. 59.184 mm, so it is now strictly inside 55.700 .. 60.784.
BEM `F = 1` stands, because the ring finally earns it. Added `tip_section_points` and
`tip_section_rmin_mm`; `_tip_z_span` reuses the shared section helper. Skip-if guards
(`r_in <= 0`, `r_out <= r_in`) kept.

### TDD evidence

Tests written first, in `tests/test_shroud.py`:

- `test_ring_wall_contains_every_tip_section_point` — every tip-section point's hypot must lie
  strictly between the bore and the outer wall.
- `test_ring_bore_is_below_the_corner_only_radius` — guards against regressing to the corner-only
  `open_tip_rmax_mm - embed` bore.

RED (before the geometry change):

```text
E   ImportError: cannot import name 'tip_section_points' from 'fansim.geometry.blade'
E   ImportError: cannot import name 'tip_section_rmin_mm' from 'fansim.geometry.blade'
7 failed, 12 passed in 25.67s
```

The import-level RED is intentional: the helper the containment check needs did not exist. Under the
old formula the containment assertion also fails on the numbers — the measured tip-section minimum is
56.500 mm against a bore of 58.384 mm, so `min(radii) > r_in` is false by 1.88 mm.

GREEN (after): see the test run below. Manual confirmation that the fused part is still one sealed
solid, not just that the numbers line up:

```text
build 25.9s  solids=1  volume=67253 mm3  valid=True
```

## 2. Important — `shroud_thick_mm` persists on trials

`--shroud` stamps `BladeParams` outside the search space, so `trial.params` never saw it and every
rebuild (catalog, cockpit, `blade_from_flat`) came back open-tip.

- `run_study` sets `trial.set_user_attr("shroud_thick_mm", ...)` on every trial, including 0.
- New `study.with_shroud_attr(trial)` returns `dict(trial.params)` with the user attr merged in.
- `pareto_summary` rows carry `shroud_thick_mm` as a column *and* inside `params`.
- `cockpit/data.py::load_designs` and `scripts/extract_design_rules.py` use the merged dict.

Tests: `test_pareto_summary_carries_shroud_thick`,
`test_pareto_summary_without_shroud_attr_stays_open_tip`, `test_load_designs_merges_shroud_user_attr`
(real sqlite study in `tmp_path`). All three RED with `KeyError: 'shroud_thick_mm'` first.

## 3. Important — CFD duct clears the built envelope

`rig_for_impeller` used `params.tip_radius + tip_gap` (56.5 + 1.0 = 57.5 mm), which is inside both the
blade corners (59.18 mm) and the ring (60.78 mm). Now
`open_tip_rmax_mm + shroud_thick_mm + tip_gap`, which also fixes the pre-existing blade-corner case
at shroud 0. `tests/test_cfd.py::test_rig_dimensions_and_operating_point` updated (the old 57.5 mm
expectation encoded the bug); `test_rig_duct_clears_the_tip_ring` added. `--shroud` help now states
that ring-to-frame clearance follows the existing `tip_gap`, not an optimized shroud gap.

## Tests

```text
uv run python -m pytest tests/test_shroud.py tests/test_geometry.py tests/test_cfd.py tests/test_optimize.py -q --tb=short
34 passed in 79.35s
```

Exit code -1073741819 on teardown is the known CadQuery/OCCT shutdown crash, not a test failure.

## Concerns

- The sealing bore is 2.68 mm deeper than the spec's, so the baseline ring is ~26.5 cm³ (~33 g PLA)
  and the shrouded impeller ~67.3 cm³ total. The volume/weight gate — deliberately left alone — will
  reject a lot of shrouded candidates. A thinner default or a bore that follows the tip helix rather
  than a plain cylinder is the real fix, and is stage-2 work.
- `TestRig.tip_speed` (`duct_radius - tip_gap`) now reports the envelope radius rather than
  `tip_radius`. Only `scripts/run_baseline.py` prints it; no model consumes it.
