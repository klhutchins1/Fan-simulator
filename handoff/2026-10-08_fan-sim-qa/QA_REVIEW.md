# QA Review — Fan Simulator

Running QA list maintained by Fan Sim QA (Kimball's QA bot). The QA bot only edits this file; it never edits code.

## How to use this file (for Claude / whoever fixes things)
- Each item has an ID (`QA-n` for code/math, `UI-n` for cockpit UI). Keep IDs stable; never renumber.
- When you fix something, change its **Status** to `fixed (pending QA)` and add the commit hash. The QA bot re-tests and marks it `verified` or `reopened`.
- Use `wontfix` or `by design` with a one-line reason if you disagree.
- Known recovery gaps from README_RECOVERY.md / RECOVERY_TODO.md are not counted as bugs.
- Paths like `/workspace/fansim/...` and `qa/...` are on the QA bot's machine (screenshots, scratch scripts); ask if you need one.

## Tested build
- Source: copy of `T:\Projects\Fan Simulator` working tree, 2026-10-08 (no `.git`, so no commit hash). Linux, Python 3.12, no Docker/OpenFOAM/CFD.

## Tracker
| ID | Sev | Area | Summary | Status |
|---|---|---|---|---|
| QA-1 | HIGH | Geometry/Stock | 7-station Stock A12x25 recipe cut to 3 stations by `blade_to_flat`/`stock_blade_flat` | open |
| QA-2 | MED | Geometry | No validation for axial/mixed-flow inputs (hub>tip, neg chord, 0 blades, NaN) | open |
| QA-3 | MED | BEM | Free delivery falls back to sweep max when pressure never > 0 (0 blades = 129 CFM) | open |
| QA-4 | MED | BEM/polars | AoA clamped to table edges; paddles/reversed blades score as good fans | open |
| QA-5 | MED | Audit/tests | `motor_side()` returns None with 5 mm centre bore (2 failing tests) | open |
| QA-6 | LOW | CI | Ruff F811 in `fansim/cockpit/fan_viz.py:46` fails "Ruff critical" | open |
| QA-7 | LOW/MED | Tests | `audit_archetype_direction_cfd.py` not registered with rotor-orientation guard | open |
| QA-8 | LOW | Math | `camber_from_turning_rad` ~2x circular-arc camber | open |
| QA-9 | LOW | Math | Two different "solidity" definitions; docstring mismatch | open |
| QA-10 | LOW | Docs | README quickstart test command needs `--extra dev` | open |
| UI-1 | HIGH | Volute | Export STLs fails: `TypeError: object of type 'PosixPath' has no len()` (verify on Windows) | open |
| UI-2 | MED | Fan | Unedited Reference shows "Edited since assessment" on load | open |
| UI-3 | MED | Fan | Reset leaves 3-D viewer empty | open |
| UI-4 | MED | Fan/CROR | Preview ~65-70 s, progress bar jumps/looks stuck | open |
| UI-5 | MED | Prop | 5" FPV prop reports 2087 g / 743 W (implausible) | open |
| UI-6 | LOW | Fan | Export only saved server-side, ~2 min, `design_100000` name | open |
| UI-7 | LOW | Fan | Stale "Saved..." message after Randomize | open |
| UI-8 | LOW | Fan | Slider tooltip vs side label disagree; tooltip overlaps label | open |
| UI-9 | LOW | Fan | Poor first-load framing; colour bar zero range | open |
| UI-10 | LOW | Volute | Casing hides impeller; clipped labels | open |
| UI-11 | LOW | Mixed/Prop/Volute | No slider values; leftover blurry render | open |
| UI-12 | LOW | Mixed | Flat unshaded preview | open |
| UI-13 | LOW | Prop/CROR | Disabled buttons look enabled | open |
| UI-14 | LOW | All | Tab tooltip covers neighbouring tabs | open |
| UI-15 | LOW | All | Console 405 on POST /paraview/ | open |

## Details
(Numbered bugs below map to QA-n.)

## Environment and what I tested

- **Box:** Linux x86_64, 8 cores, 16 GB RAM, no swap. Source is `/workspace/fansim/src`, a copy of `T:\Projects\Fan Simulator` with the working tree as of 2026-10-08. The copy has **no `.git`**, so I could not diff the uncommitted edits in `fansim/centrifugal/isolated.py` and `fansim/cfd/*`.
- **Setup:** `uv sync --extra dev` worked with no errors: uv 0.12.23 downloaded CPython 3.12.15 and installed 109 packages, including cadquery 2.8.0, trimesh 5.1.0, pyvista 0.48.4, trame 3.13.2 and vtk 9.6.2. The whole package imports on Linux, `fansim.cockpit.app` included.
- **Scope (per Kimball):** no Docker, no OpenFOAM and no CFD (Assess, Sweep, solver). Tests marked `docker` or `slow` were deselected (22 tests). For geometry, preview, export, STL checks, unit tests and the cockpit UI, see below.
- **Fans generated:** I built 21 valid configs through the project's APIs (`blade_from_flat`, `load_blade_params`, `build_impeller`, `build_impeller_with_mount`, `export_mixed_flow_stl`, `build_cror`, `build_prop`, `export_wind_turbine_stl`):
  - **Axial:** default, Stock YAML, design_space YAML, 1/2/3/5/9/11/13 blades, 40 / 250 / 600 mm diameter, hub ratio 0.7, full shroud, notch + sickle + winglet + tip-round, and motor cup.
  - **Other types:** mixed-flow with cup, CROR, FPV 5" prop, and a 200 mm wind turbine.

  Other runs:
  - `scripts/export_a12x25_print_ready.py` (Fit on).
  - One "Stock via cockpit flat" build, used for bug #1.
  - Six invalid-input probes. Four errored; two built anyway (bug #2).

  The original spread had about 55 configs. I cut it to roughly this many after the scope change.
- **STL checks:** trimesh 5.1.1 in a separate venv (`/workspace/fansim/qa/.venv`; `check_stl.py`). The report is `/workspace/fansim/qa_exports/stl_report.csv` and `.json`.
- **Math checks:** `qa/math_checks.py` writes `qa/math_checks.json`.
- **Cockpit:** `runs/qa_synthetic_bem` holds an Optuna study I generated. It has 16 trials sampled with the project's `suggest_params(space="guided")` and **scored by BEM, not CFD**. Each trial carries the user attribute `qa_synthetic=True` and the reason "QA SYNTHETIC: BEM-scored, NOT CFD". The cockpit runs at http://127.0.0.1:8080 and logs to `/workspace/fansim/cockpit.log`.

### Test results (pytest, `-m "not docker and not slow"`, 1533 selected out of 1555)
- **Totals:** 1513 passed, **3 failed**, 18 skipped, 1 xfailed, 22 deselected.
- **Failures:**
  - `tests/audit/test_direction_geometry.py::test_motor_side_with_centre_bore[1]` and `[-1]` (bug #5).
  - `tests/test_axial_scripts_oriented.py::test_no_unlisted_script_calls_build_case` (bug #7).
- **How it ran:** The single full-suite run was OOM-killed (see Platform #1). I then ran it in 6 sequential chunks, and re-ran the chunk that was killed again one file per process. Logs are in `/workspace/fansim/qa/pytest_tchunk_0*.log` and `pytest_chunk01_perfile.log`.

### STL results
- **25 STLs checked:** All 25 are watertight, winding-consistent and `is_volume`, with positive volume and normals pointing outward. Each is a single body, with 0 degenerate faces, 0 duplicate faces, 0 non-manifold edges and 0 boundary edges.
- **Units and symmetry:** Everything is in mm. Rotating each part by 360°/N maps it onto itself (95th-percentile deviation ≤ 0.03 mm). The one exception is mixed-flow at 0.2 mm, because its 20 grip pads don't divide by 9 blades. Rotating by 360°/(N+1) does not match, so the blade count is confirmed.
- **Euler number / genus:** 2 for plain rotors, 0 where there is a through-bore (motor cup, mixed-flow, prop, print-ready), and −12 for the full shroud (7 handles, as expected).
- **Diameter flags:** 3 flags, none of them a mesh defect:
  - `INVALID_axial_hub_gt_tip`: +20 mm, the disc from bug #2.
  - Full shroud: +3.2 mm, because the ring is by design outside `tip_radius` (2 × (54 + 1.6) = 111.2 mm).
  - Mixed-flow: −0.64 mm, from the frame-clearance clamp by design.
- **Every other STL** has diameter exactly 2 × `tip_radius`, and height within the 25 mm A12x25 depth where that applies.

---

## Bugs

### 1. [HIGH] Geometry/Stock: the Stock A12x25 recipe is cut from 7 stations to 3 when it goes through the flat dict (cockpit Reference, print-ready export, Fit)
- **Area:** `fansim/optimize/search_space.py` `blade_to_flat()` (lines ~314-383), reached through `stock_blade_flat()` (~391).
- **Repro:**
  ```
  uv run python -c "from fansim.optimize.search_space import stock_blade_flat, blade_from_flat; from fansim.geometry.config import load_blade_params; y=load_blade_params('config/problems/a12x25_reference.yaml'); f=blade_from_flat(stock_blade_flat()); print(len(y.stations), len(f.stations))"
  ```
  This prints `7 3`.
- **Expected:** The "◆ Reference · Noctua A12x25" design in the cockpit and `scripts/export_a12x25_print_ready.py` should build the signed-off 7-station refit recipe (`a12x25_reference.yaml`, promoted 2026-09-29, golden test frozen).
- **Actual:** `blade_to_flat` keeps only the stations nearest r_frac 0, 0.5 and 1. It drops r_frac 0.22, 0.38, 0.69 and 0.84, and it re-labels the 0.533 station as 0.5. Measured sections from my two builds (`measure_sections`):

  | r/R | stagger, YAML build | stagger, cockpit/print-ready flat build |
  |---|---|---|
  | 0.45 | 35.3° | 26.6° |
  | 0.55 | 38.4° | 29.1° |
  | 0.85 | 24.7° | 30.0° |
  | 0.95 | 22.2° | 26.7° |

  Single-blade volume barely changes (2074 vs 2083 mm³), so the volume and weight checks don't catch it. STLs: `qa_exports/axial_stock_reference_yaml_9b.stl` and `qa_exports/axial_stock_via_cockpit_flat_9b.stl`.
- **Suspected cause:** The flat dict format only has root/mid/tip slots, and its docstring says "Flatten a 3-station BladeParams". `stock_blade_flat` passes it a 7-station recipe anyway. Nothing warns or raises when stations are dropped. The "⚠ Edited since assessment" banner on a freshly loaded Reference in the UI may be the same issue; that link is unconfirmed.

### 2. [MEDIUM] Geometry: no input validation on axial `BladeParams` / `blade_from_flat` (and mixed-flow `n_blades` / `z_span`)
- **Area:** `fansim/geometry/blade.py` `BladeParams` (no `__post_init__`), `fansim/optimize/search_space.py:213` `blade_from_flat`, and `fansim/centrifugal/geometry.py` `MixedFlowParams.__post_init__`.
- **Repro:** Run `/workspace/fansim/qa/gen_all.py INVALID_axial_hub_gt_tip INVALID_axial_neg_chord INVALID_axial_0_blades INVALID_axial_nan_tip INVALID_mixed_0_blades INVALID_mixed_neg_zspan`. These use the default flat dict with one field overridden.
- **Expected:** A clear `ValueError` for impossible inputs. `VoluteParams` and `WindTurbineParams` already do this.
- **Actual:**
  - `hub_radius=60, tip_radius=50` builds and exports a "valid" watertight single-body STL that is just a 120 mm disc (`qa_exports/INVALID_axial_hub_gt_tip.stl`).
  - `chord_mid=-5` builds without complaint.
  - `n_blades=0` raises `ZeroDivisionError` at `blade.py:280` (`blade_solidity`); `build_impeller` would hit the same thing at `blade.py:784`.
  - `tip_radius=NaN` fails deep in OCCT with `Standard_Failure: Courbes non jointives`.
  - `n_blades=1` builds silently, giving an unbalanced single blade.
  - Mixed-flow with `n_blades=0` or `z_span_mm=-5` passes `__post_init__`, then dies with `ValueError: Null TopoDS_Shape object`.
- **Suspected cause:** Validation exists only for the volute, wind and the mixed eye/back radii. The axial path relies on optimizer bounds, but the cockpit editor and YAML loader can go outside them.

### 3. [MEDIUM] BEM: free-delivery falls back to the sweep's maximum flow when static pressure never crosses zero
- **Area:** `fansim/fan_bem.py:198-203` (`pq_curve`).
- **Repro:**
  ```
  uv run python -c "from fansim.geometry.blade import BladeParams; from fansim.fan_bem import pq_curve; print(pq_curve(BladeParams(n_blades=0),2000).free_delivery_cfm)"
  ```
  This prints **129.0** CFM for a fan with no blades.
- **Expected:** `None`, NaN or 0, plus a flag when there is no zero crossing.
- **Actual:** `free_cfm = pts[-1].flow_cfm` (q_max = 0.6·U_tip·A). Any design whose static rise is already ≤ 0 at the first sweep point is reported at the maximum flow and would rank best in a BEM prescreen. In the same check, `hub_radius > tip_radius` returns 0/0 silently.
- **Suspected cause:** The fallback initialiser was meant for "free delivery is past the end of the sweep" but also catches "never positive".

### 4. [MEDIUM] BEM/polars: angle of attack is clamped to the table edges (no post-stall model), so paddles and reversed blades score as good fans
- **Area:** `fansim/propeller/polars.py:76-86` (`_interp_alpha` clamps cl/cd to the table edge), used by `fansim/fan_bem.py:142`.
- **Repro:** Set every station's stagger and run `pq_curve(...)` at 2000 rpm (`qa/math_checks.py`, `/tmp/bem2.py`).
  - Reference stock: free 58.2 CFM, shut-off 38.9 Pa, peak efficiency 0.536.
  - stagger 89° (axial paddle): **74.8 CFM**, 41 Pa, efficiency 0.558.
  - camber −0.06 at 45°: 79.0 CFM.
  - stagger −45° or −60° (wrong hand): shut-off **+36.8 Pa**, efficiency 0.554.
  - stagger 0°: 20.5 CFM, efficiency 0.585.
- **Expected:** Post-stall, cl should drop and cd should rise toward ~1.2-2 near 90°. A reversed blade should not produce positive pressure at 55 % efficiency.
- **Actual:** For α ≥ ~30°, cl is pinned at 0.769 and cd at 0.10. For α ≤ ~−10°, cl is pinned at −0.276. With negative lift, swirl is driven entirely by the drag term `cd·cosφ` (`fan_bem.py:144`), which still produces a positive Euler Δp.
- **Notes:** BEM is documented as ranking-only. Even so, these cases invert the ranking: the paddle beats stock. The search bounds (stagger ≤ 48°) limit how often the optimizer hits this, but the cockpit editor allows any value.

### 5. [MEDIUM] Test failure: `motor_side()` returns None for a fan with a 5 mm centre bore
- **Area:** `fansim/audit/direction.py:272-283`. Tests: `tests/audit/test_direction_geometry.py::test_motor_side_with_centre_bore[1]` and `[-1]`.
- **Repro:** `uv run --extra dev python -m pytest tests/audit/test_direction_geometry.py -k centre_bore`
- **Expected:** +1 or −1 (the cup side).
- **Actual:** None. `_tip_radius` = 50.00000000000001, so the first probe radius is 0.1·tip = 5.000000000000001. That lies on the bore wall (bore_r = 5.0), where the cut already returns 5 loops. So `r_root` = 5.0, `r_cap` = 4.5, and every probe band falls inside the empty bore: 0 of 64 rays hit. All bands return None.
- **Suspected cause:** `r_root` detection takes the first radius with ≥ 3 loops. It doesn't skip the bore wall or check that the loop count matches the blade count. This may be numerically platform-sensitive (the radius lands exactly on the bore wall, and Linux has no embree), but the logic flaw is real. The sibling `..._with_realistic_centre_bore` passes.

### 6. [LOW] CI: the "Ruff critical" gate fails (F811)
- **Repro:** `uv run --extra dev ruff check fansim tests scripts --select F811,F821`
- **Actual:** `fansim/cockpit/fan_viz.py:46:25 F811 Redefinition of unused Path from line 13`. The `ci.yml` step "Ruff critical" will go red on push. Ruff also warns about an invalid `# noqa` at `tests/test_cockpit_errors.py:48`. `mypy` passes.

### 7. [LOW/MEDIUM] Test failure: new CFD script not registered with the rotor-orientation guard
- **Area:** `tests/test_axial_scripts_oriented.py::test_no_unlisted_script_calls_build_case` and `scripts/audit_archetype_direction_cfd.py` (mtime 2026-10-02; it calls `build_case` at lines ~105 and ~159).
- **Repro:** `uv run --extra dev python -m pytest tests/test_axial_scripts_oriented.py`
- **Actual:** `AssertionError: audit_archetype_direction_cfd.py: add to AXIAL_SCRIPTS or EXEMPT`.
- **Impact:** The Audit #1 guard (every CFD case is built in the designed rotation) is red, so it is unverified whether this script orients the rotor. Either register the script or exempt it with a reason.

### 8. [LOW] Math: `meanline.camber_from_turning_rad` overestimates camber by about 2×
- **Area:** `fansim/optimize/meanline.py` `camber_from_turning_rad` (m = |ε|/4).
- **Expected:** For a circular-arc camber line, the maximum camber height is (c/2)·tan(θ/4) ≈ θ/8. A NACA 4-digit line gives θ ≈ 2m/(p(1−p)) → m ≈ θ/8.3 at p = 0.4.
- **Actual:** At 10°, 20° and 30° turning the code gives 0.0436, 0.0873 and 0.131; the circular arc gives 0.0218, 0.0437 and 0.0658. The cockpit meanline seed suggests about twice the camber.
- **Everything else in meanline matched hand calculation exactly:** U, Cz, Cu2 (free vortex), W1, W2, Lieblein DF, de Haller, stagger from the disk, and Cordier σ. See `qa/math_checks.json`.

### 9. [LOW] Math/naming: two different "solidity" definitions
- **Area:** `fansim/geometry/blade.py:261-282` `blade_solidity` returns c·cosβ/s, while its docstring says "chord / circumferential pitch". `fansim/optimize/meanline.py` `solidity` returns c/s.
- **Evidence:** Default 7-blade fan, hub/mid/tip: `blade_solidity` gives 1.58/1.13/0.69; c/s by hand gives 1.76/1.26/0.75.
- **Impact:** The `--loadcap` floors (`min_sol_mid`/`min_sol_tip`, `objectives.py:323`) and `printability_score.py:110` use the projected value; the meanline DF uses c/s. Either the docstring or one of the formulas is wrong.

### 10. [LOW] Docs: the README quickstart test command fails after the documented `uv sync`
- **Area:** `README.md` Quickstart, `RECOVERY_TODO.md`, and `pyproject.toml`, where pytest is only in the `[dev]` extra.
- **Repro:** Fresh clone, then `uv sync`, then `uv run python -m pytest -q -m "not docker"` → `No module named pytest`. The RECOVERY_TODO command (`--extra optim`) doesn't add pytest either. CI uses `--extra dev`, which works.

---

## Platform / setup issues (not counted as app bugs)
1. **Test-suite memory:** A single pytest process grows to about 4-6 GB. The full fast suite was **OOM-killed twice** on this 16 GB box (`dmesg`: anon-rss 5.4 GB and 6.3 GB, the second while a chunk was running `tests/test_a12x25_validation_cli.py` … `tests/test_cror.py`). I worked around it by running the suite in 6 sequential chunks and re-running the killed chunk one file per process. This looks like accumulated OCCT/VTK memory, not a single failing test.
2. **Windows-only hardcoded paths:** `scripts/evaluate_noise.py:23-25` and `scripts/evaluate_shutoff.py:27-29` hardcode `E:/Projects/programming_2/FluidX3D`, `FluidX3D.exe` and `C:\msys64\ucrt64\bin`; the README says `../FluidX3D`. `scripts/import_prop_stls.py` uses `C:/Users/Kimball/Downloads/...` as a usage example. These were not run (GPU/LBM is out of scope).
3. **No embree on Linux:** `trimesh.ray.has_embree=False`, so ray tests use the pure-Python intersector. That is slower and possibly numerically different from his PC; it may affect #5.
4. **No git metadata** in the copy, so the uncommitted edits could not be isolated. ruff F checks on `fansim/cfd` and `fansim/centrifugal` are clean.
5. **Docker/OpenFOAM** were not installed or run, per scope. 22 `docker`/`slow` tests were deselected, and the cockpit Assess/Sweep/CFD-refine buttons were not exercised.
6. **Cockpit log noise caused by my probing:** `HTTPBadRequest` from a plain `curl /ws`, `KeyError <session id>` and `ClientConnectionResetError` from headless clients I killed, and the browser console's `405 POST /paraview/` (a trame-vtk probe). These look benign.

## Suspicious but unconfirmed
1. **Shared cockpit UI state:** A fresh browser opened on the CROR tab because an earlier headless client had left it there. Trame state is shared by all clients, which is probably by design. The browser tester should click **FAN · CFD** first.
2. **"⚠ Edited since assessment — the shown CFM/efficiency are for the un-edited design"** appears on a freshly loaded, unedited Reference (see `qa/ui_fan_tab.png`). It may be caused by bug #1; check in the browser.
3. **Fan 3-D viewport:** The first render looked like an extreme zoomed-in close-up. Check that the camera resets after Preview.
4. **Stock YAML blades hang below the hub:** The raw YAML build's bbox z_min is −9.10 while the hub bottom is −8.16, so about 0.94 mm of blade sits below the hub. The print-ready path (after Fit) is fine: the cup measured 13.0 mm deep in the hub and the mount gauge reported OK.
5. **`_root_axial_span` uses `params.stations[0]` without sorting** (`blade.py:626`), while `_interp_stations` and `tip_section_points` sort or use max. Unsorted stations (YAML, `blade_angles`) would size the hub from the wrong station.
6. **`_trim_blade_to_tip_cylinder` can still return an untrimmed blade** if all 4 intersect retries come back empty (`blade.py:1080-1084`), even though the comment says that is what it avoids. This did not happen in my 23 builds.
7. **`build_impeller_preview` doesn't check that `blade_angles_deg` has `n_blades` entries** (`blade.py:841-844`); `build_impeller` does.
8. **`chord_realisation._station_measure_fracs` hard-codes `f < 0.47`** as "inside the hub". That is an A12x25 hub ratio; for hub ratio ≳ 0.47 the root station is measured inside the hub annulus.
9. **Props:** Pitch twist is evaluated at r = hub_r (6.0 mm) and 0.5(hub+R) (34.75 mm), but the loft places those stations at 4.5 and 34.0 mm because of `root_embed` (`propeller/geometry.py:64-67`). The error is small, mostly at the root.
10. **Mixed-flow:** Blades are lofted along a straight eye→tip diagonal while the hub is a cone, so only the root section attaches to the hub. The wall between the motor cup and the cone is about 1.66 mm at z = +2 mm.
11. **Wind scaffold:** `tip_speed_ratio` is not used by the geometry, and Cp saturates for n_blades ≥ 4 (5 and 10 blades give the same Cp, 0.4267). This is a scaffold, as labelled.

## Known recovery gaps (not counted; see RECOVERY_TODO.md and README_RECOVERY.md)
- `RECOVERED-FROM-CHAT` banners remain in `README.md`, `scripts/cockpit.py`, `scripts/export_finalists.py`, `scripts/validate_stl.py`, `scripts/run_baseline.py` and others. RECOVERY_TODO says the source headers were stripped from `fansim/*.py` only.
- `fansim/cockpit/app.py.INCOMPLETE_990base` is still in the tree (marked do-not-use).
- `runs/**`, `catalog/catalog.db`, `exports/**` and `docs/control_images/*.png` are regenerable and absent by design.
- BEM is ranking-only, and absolute CFM is validation-gated (documented in `fan_bem.py` and the README status). #3 and #4 are counted because they invert the ranking, not because of absolute error.
- Stock↔close-ref absolute volume is about 1.4× (RECOVERY_TODO "Provenance / trust").

## UI pass (cockpit in browser, 2026-10-08, no CFD/Assess/Optimize clicked)
Screenshots in /workspace/fansim/qa/ui/. Browser viewport was 1024x594.

- UI-1 HIGH  VOLUTE: Preview then "Export STLs" -> "Export failed: TypeError: object of type 'PosixPath' has no len()". (volute_export_failed_posixpath.png) Likely a Path passed where str/list expected; may be Linux-only, verify on Windows.
- UI-2 MED   FAN: unedited Reference shows "Edited since assessment" on first load; Reset clears it. Possibly tied to the 7->3 station Stock recipe bug. (fan_initial_load_edited_warning_and_framing.png)
- UI-3 MED   FAN: Reset clears the 3-D viewer to empty axes instead of showing the reference fan. (fan_reset_blank_viewer.png)
- UI-4 MED   FAN: "Preview (sec)" takes ~65 s per run (worker ~160% CPU, ~6 GB RAM); progress bar jumps back and forth, spinner looks stuck. CROR Preview ~70 s / Export ~40 s, stuck near 20%. (fan_preview_stuck_running.png, cror_disabled_cfd_refine_looks_enabled_slow_preview.png)
- UI-5 MED   PROP: 5" FPV prop reports 2087 g thrust / 743 W (implausible); polar starts "J=0.00 eta=-".
- UI-6 LOW   FAN: Export STL ~2 min, file only saved server-side (exports/design_100000_*.stl + .step), no browser download; "design_100000" is a confusing name for the stock reference.
- UI-7 LOW   FAN: after Randomize, previous "Saved ...design_100000...stl" message stays on screen. (fan_randomize_stale_export_msg.png)
- UI-8 LOW   FAN: slider tooltip and side label disagree (Chord root 18.0 vs 17.75 mm; 25.0 vs 25.12); tooltips overlap "Blades" label.
- UI-9 LOW   FAN: first-load 3-D view poorly framed under dense schematic arrows; U m/s colour bar reads 3.00/3.00/3.00 (zero range).
- UI-10 LOW  VOLUTE: Preview shows only an opaque casing box hiding the impeller; "RPM" and "Load Pa@50CFM" labels clipped by Outlet panel. (volute_initial_clipped_rpm_label.png)
- UI-11 LOW  MIXED/PROP/VOLUTE: sliders show no numeric values; viewer shows blurry leftover render before first Preview. (mixed_initial_no_slider_values_artifact_viewer.png, prop_initial_blurry_viewer_stop_looks_enabled.png)
- UI-12 LOW  MIXED: Preview renders flat unshaded silhouette. (mixed_preview_flat_unshaded.png)
- UI-13 LOW  PROP Stop and CROR CFD refine look enabled (solid red/orange) while disabled.
- UI-14 LOW  All tabs: tab hover tooltip covers neighbouring tab names after clicking.
- UI-15 LOW  Console 405 on POST /paraview/ at load.
