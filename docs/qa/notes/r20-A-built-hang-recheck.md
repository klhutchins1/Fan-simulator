# r20 A: feature-design JSON and the built-hang recheck on master (R1.8; QA-43/44/49)

grok QA bot, 2026-10-21 MDT.
- **Prereg:** `2c4380d` (`prereg_r6` branch `prereg/round20`, `qa_r20/PREREG_R20.md`, committed 08:38 MDT before any
  data).
- **Code:** master 027ebcb, run clone `qa/run_r20`. Master already merges `r33-install-guide` (fe899cd), which the
  brief calls unmerged. `fansim/`, `tests/`, `pyproject.toml`, `uv.lock` and `README.md` are identical on both, so
  testing master tests the branch.
- **Files:**
  - data: `docs/qa/r20/r20-A-built-hang-recheck.csv`
  - JSON for Cursor: `docs/qa/r20/r20-A-feature-designs.json`
  - scripts: `handoff/2026-10-21_from-qa-20/`

## A1. Feature-design JSON (for `tests/test_hub_hang.py`)
`docs/qa/r20/r20-A-feature-designs.json` has the same top-level layout as `tests/data/hub_hang_designs.json`:
`{id: {"flat", "features"}, "_source"}`.
- It covers S5_0207, S5_0073, S5_0112 and S5_0023.
- `flat` is the r7 flat with `section_wrap: "cylinder"` already in it. `features` holds the r7 tubercle, serration and
  dimple values.
- **Gate (PASS):** reloaded in a fresh process with Cursor's own recipe, all four give built hangs **bit-identical**
  to r18 (difference 0.0). That recipe is:
  - `blade_from_flat(d["flat"], Features(**d["features"]))`, then
  - `mount_hub_params(p, a12x25 mount)[0]`, then
  - `blade_hang_built_mm`.
- No `BladeParams` field differs from the r18 build.
- **Suggestion for Cursor:** merge the four entries into `tests/data/hub_hang_designs.json` (or load this file). Then
  add them to `_R18_BUILT_MM` as `S5_0207 2.829`, `S5_0073 2.303`, `S5_0112 2.626`, `S5_0023 7.322`, rebuilt with
  `_design(id)` rather than `_r16(id)`. That makes the acceptance **10/10**.

## A2. `blade_hang_built_mm` on all 10 (QA-49): PASS
| design | features | r18 built (mm) | r20 built (mm) | stage 1 (1.75× designed) | stage 2 (built) | `build_impeller_parts` |
|---|---|---|---|---|---|---|
| S2_0269 | no | 0.000 | 0.0000 | pass | pass | built |
| S5_0207 | yes | 2.829 | 2.8292 | pass (0.862 designed) | **refuse** | refused |
| S5_0073 | yes | 2.303 | 2.3032 | refuse | refuse | refused |
| S5_0112 | yes | 2.626 | 2.6264 | refuse | refuse | refused |
| S5_0023 | yes | 7.322 | 7.3221 | refuse | refuse | refused |
| G_0502 | no | 1.936 | 1.9363 | pass | pass | built |
| S1_0461 | no | 2.090 | 2.0903 | refuse | refuse | refused |
| S1_0534 | no | 0.991 | 0.9905 | pass | pass | built |
| S3_0173 | no | 1.169 | 1.1687 | pass | pass | built |
| S4_0242 | no | 5.359 | 5.3589 | refuse | refuse | refused |

- **Agreement:** max |r20 − r18| is **0.0 mm** against the unrounded r18 values, and ≤ 4.4e-5 mm against the
  4-decimal CSV. The tolerance is 0.05 mm.
- **Cursor's `_r16` recipe** (the 6 feature-free designs) gives the same numbers.
- **Passing a pre-built solid:** `blade_hang_built_mm(p, solid)` equals the version that builds its own solid.
- **Hub:**
  - `mount_hub_params` now grows hubs below the blades. The top face is unchanged to 1e-6 mm, and z_face equals my
    r18 export hub exactly.
  - Hubs already ≥ 15 mm (S5_0023 15.72, S1_0461 17.15, S1_0534 15.87, S3_0173 19.18) are left alone.
- **So QA-49 is verified fixed:** stage 2 measures the built, trimmed solid, and the R1.7 hub is the one it measures
  at.

## A3. Two-stage refusal (QA-43): PASS
- **Stage 1** refuses 5/10, exactly where 1.75 × designed > 2 mm.
- **Stage 2** refuses 6/10, exactly where built > 2 mm. S5_0207 is the one that only stage 2 catches (designed 0.862 →
  1.51 predicted, 2.83 built).
- **End to end,** `build_impeller_parts` refuses all 6 designs with built > 2 mm and builds the other 4. No design
  that hangs past the limit gets through.
- **QA-43 is verified fixed** on these 10.
- **Caveat:** the message is the same for both stages ("the printed blade would hang X mm"). In stage 1, X is
  1.75 × designed. In stage 2 it is the measured built hang. For S1_0461, `build_impeller_parts` reports 2.2 mm (the
  stage-1 estimate) while the built hang is 2.09 mm.
- **Second caveat:** S5_0112 is refused with "would hang 2.0 mm below the hub (limit 2 mm)", because 2.0495 rounds
  to 2.0.
- Both are cosmetic: the decisions are right. Printing two decimals, or naming the stage ("estimated" vs "measured"),
  would fix both. This is a proposal only, with no QA item.

## A4. One hub (QA-44): PASS, with one side finding
- **What I compared:** the Export flat (`prepare_export_flat(..., fit_frame=False, fit_hub=True)` then
  `blade_from_flat`) against `evaluate_candidate`'s `mount_hub_params` hub.
- **Agreement:**
  - z_face and z_top agree to **< 1e-6 mm** on all 10.
  - Built hang agrees to ≤ 3.6e-5 mm.
  - `section_wrap` survives the flat round trip.
- **So QA-44 is verified fixed for the hub's height and position.**
- **Side finding (new QA-54, LOW):** Export's `fit_hub` also widens `hub_radius` to the motor minimum (20.775 mm) for
  S5_0073 (20.49) and S5_0023 (19.38).
  - `evaluate_candidate` does not widen it. It only refuses such designs when `require_mountable=True`, and the
    default is False.
  - In a non-`--mountable` run, those designs are therefore scored with a narrower hub than they export with. The
    hang is unaffected here (≤ 4e-5 mm), but the root and hub differ.
  - The change is shown to the user (`frame_changes`), and `fit_hub` is a toggle, so this is a "one hub" gap, not a
    silent bug.
