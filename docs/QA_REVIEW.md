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
- **Re-test 2026-10-09:** `master` @ `961f9534674c375bbc0a730a34979d859a1be05d` (commit date 2026-10-08 21:56 MDT), cloned from `fansim_master.bundle`; `uv sync --extra dev`; Linux, no Docker/OpenFOAM/CFD. Code items re-run with the original repros (`qa/retest_code.py`); UI items checked headlessly (curl, wslink websocket client, code + regression tests). "needs browser pass" = fix claimed in a commit, not yet confirmed by clicking.
- **Re-test 2026-10-09 (2):** branch `qa-fixes-2026-10-09` @ `d781894` (from `fansim_2026-10-09.bundle`; forks from 961f953; `station-mapping-23-35` not tested). Bundle `master` is `6b7f3bf`, not the `6f31514` named in the brief: 6f31514 is an ancestor of master (6 docs-only commits on top, docs/handoff + one `.gitignore` line) and is NOT an ancestor of the branch. Fix tests: 59 passed, 1 skipped, 1 xfailed (`test_ws_guard`, `test_tip_trim`, `test_build_progress`, `test_prop_polar`, `test_blade_validation`, `audit/test_prop_bemt_audit`, `test_volute_export_rows`). The full fast suite was not re-run on the branch. Websocket checks: `handoff/2026-10-09_from-qa/ws/`, run on 961f953 and d781894 side by side. Browser steps still to do: `docs/qa/browser_checklist_2026-10-09.md`.

## Tracker
| ID | Sev | Area | Summary | Status |
|---|---|---|---|---|
| QA-1 | HIGH | Geometry/Stock | 7-station Stock A12x25 recipe cut to 3 stations by `blade_to_flat`/`stock_blade_flat` | verified `20aed3e` |
| QA-2 | MED | Geometry | No validation for axial/mixed-flow inputs (hub>tip, neg chord, 0 blades, NaN) | verified `e5ed908` (validation at build; `BladeParams` itself still accepts bad values) |
| QA-3 | MED | BEM | Free delivery falls back to sweep max when pressure never > 0 (0 blades = 129 CFM) | verified `e5ed908` |
| QA-4 | MED | BEM/polars | AoA clamped to table edges; paddles/reversed blades score as good fans | not yet fixed: patch not applied on d781894 (`fan_bem.py` unchanged). QA clone with `docs/qa/patches/axial-force-pressure.diff` passes pre-registered rules a, b, b2, d (Stock 59.8 CFM / 22.08 Pa; paddle 14.0 CFM, η 0.009; reversed −22.5 / −19.2 Pa; top-5 66.7–68.5 CFM; default `euler` byte-identical); rule c pending tonight's `cfd_designs.csv`. Criteria sha256 `17e1e9c4…f7e2` |
| QA-5 | MED | Audit/tests | `motor_side()` returns None with 5 mm centre bore (2 failing tests) | verified `e5ed908` |
| QA-6 | LOW | CI | Ruff F811 in `fansim/cockpit/fan_viz.py:46` fails "Ruff critical" | verified `5f5b29b` |
| QA-7 | LOW/MED | Tests | `audit_archetype_direction_cfd.py` not registered with rotor-orientation guard | verified `97b9258` |
| QA-8 | LOW | Math | `camber_from_turning_rad` ~2x circular-arc camber | verified `e5ed908` |
| QA-9 | LOW | Math | Two different "solidity" definitions; docstring mismatch | verified `e5ed908`/`ca1f8c9` (by design, docstrings explain both) |
| QA-10 | LOW | Docs | README quickstart test command needs `--extra dev` | verified `5f5b29b` |
| UI-1 | HIGH | Volute | Export STLs fails: `TypeError: object of type 'PosixPath' has no len()` (verify on Windows) | verified in browser 2026-10-09 (Volute Export STLs succeeded, `ca1f8c9`) |
| UI-2 | MED | Fan | Unedited Reference shows "Edited since assessment" on load | verified in browser 2026-10-09 (`1e344ec`) |
| UI-3 | MED | Fan | Reset leaves 3-D viewer empty | verified in browser 2026-10-09 (`d4e9010`) |
| UI-4 | MED | Fan/CROR | Preview ~65-70 s, progress bar jumps/looks stuck | fixed (pending QA) `0354b3c`: bar determinate from the first frame ('starting build process' → 'stage k/5'), never decreases, no sweep; worker reports stage 1 before loading the CAD kernel. The 66 s was the motor-cup path: `preview_motor_cup` defaulted ON (switch in the Assess & print panel) — now OFF, Preview ~15 s on Windows |
| UI-5 | MED | Prop | 5" FPV prop reports 2087 g / 743 W (implausible) | verified `ad1c716`, incl. browser B5: Prop tab shows η 25%/35%/44% at J 0.16/0.24/0.31; static 2087 g / 743 W (plausible vs APC). Follow-up CT0 creep → QA-12 |
| UI-6 | LOW | Fan | Export only saved server-side, ~2 min, `design_100000` name | verified in browser B6: download link works (5.0 MB STL downloaded), file in repo/exports; export still ~75 s. docs/qa/screenshots/2026-10-09/B6_PASS_export_link.png |
| UI-7 | LOW | Fan | Stale "Saved..." message after Randomize | verified in browser 2026-10-09 (`c6fb753`) |
| UI-8 | LOW | Fan | Slider tooltip vs side label disagree; tooltip overlaps label | verified in browser B2 `c4da19c`: Chord root tooltip 17.75 = label 17.75 mm (minor: aria value reports 18; tooltip slightly overlaps end of label text). docs/qa/screenshots/2026-10-09/B2_PASS_chord_root_tooltip.png |
| UI-9 | LOW | Fan | Poor first-load framing; colour bar zero range | fixed (pending QA) `0354b3c`: viewer card was a fixed 400 px, so a wide (zoomed-out) column gave a ~2.8:1 canvas and a height-limited fan; all tabs now 3:2, ≥ 400 px, ≤ 75vh (1131×754 at a 1970-px window) |
| UI-10 | LOW | Volute | Casing hides impeller; clipped labels | verified in browser 2026-10-09 (`8e975bf`) |
| UI-11 | LOW | Mixed/Prop/Volute | No slider values; leftover blurry render | verified in browser 2026-10-09 (viewers clean before Preview) |
| UI-12 | LOW | Mixed | Flat unshaded preview | verified in browser 2026-10-09 (`8e975bf`) |
| UI-13 | LOW | Prop/CROR | Disabled buttons look enabled | verified in browser B4: Prop Stop grey/disabled when idle. docs/qa/screenshots/2026-10-09/B4_PASS_prop_stop_disabled.png |
| UI-14 | LOW | All | Tab tooltip covers neighbouring tabs | verified in browser 2026-10-09 (`b4524ab`) |
| UI-15 | LOW | All | Console 405 on POST /paraview/ | verified `ea418f3` (by design: documented benign; POST /paraview/ still 405) |
| QA-11 | LOW | Geometry | `blade_solidity(BladeParams(n_blades=0))` raises ZeroDivisionError (build-time validation now blocks it, direct API call doesn't) | verified `c4da19c`: `blade_solidity(BladeParams(n_blades=0))` → {hub, mid, tip} all 0.0 |
| UI-16 | HIGH | Server | One connected-but-stalled client (frozen/sleeping tab) freezes ALL websocket sessions; new sessions never get `wslink.hello` reply, HTTP stays 200 | verified `94a7365` (Linux): 1 SIGSTOPped client + 200 image pushes. Fresh sessions always connect (0.25–0.38 s during the pushes, was a 15 s timeout every time); 200/200 pushes complete (was stuck at 76); the stalled client is dropped about 15 s later with one warning; no restart needed |
| UI-17 | LOW | Server | A non-upgrade GET `/ws` logs `KeyError` in wslink `onClose` and leaks a `connections` entry; abrupt disconnects log `Cannot write to closing transport` tracebacks on Linux | verified `94a7365`: 20× `curl /ws` gives 0 KeyErrors and `connections` back to 0 (961f953: +20 KeyErrors, 20 leaked entries). The 'Cannot write to closing transport' log noise is also gone in this run (0 vs 15 on 961f953) |
| UI-18 | LOW | Server | Remote-view image-push observers are never removed when a client disconnects (observerCount only grows; views keep rendering/pushing with no clients) | verified `c4da19c`: `observerCount` stays at `{}` after 30 aborted observer sessions and after 506 stress cycles (961f953: 30, growing to 538) |
| UI-19 | LOW | Fan | Export download dir is `Path("exports").resolve()`, i.e. relative to the launch CWD, not the repo/run dir | verified `94a7365` + browser B6 (file lands in repo/exports) |
| UI-20 | LOW | Fan | After Randomize, Design dropdown still says '◆ Reference · Noctua A12x25 (published)' though geometry changed | fixed (pending QA) `0354b3c`: the selected value itself now reads '✎ Edited copy of ◆ Reference …' (label: '✎ Edited copy (not saved) — based on:') |
| UI-21 | LOW | Mixed | CFD refine button solid orange with 'top N = 0', looks enabled (not clicked) | verified in browser B8: CFD refine on Mixed/Prop is pale tonal disabled (not clicked). docs/qa/screenshots/2026-10-09/B8_PASS_mixed_cfd_refine_tonal.png |
| UI-22 | LOW | Mixed | Preview timer may lag ('Running Preview… 0:01' ~6 s after click) | verified / not reproduced on Linux branch d781894 (B9): '0:00' 0.13 s after click, ticks ~1 s, done ~3.9 s |
| QA-12 | LOW | Prop/BEMT | Static CT0 creeps up ~60% from 4k to 30k rpm (measured: flat). Diagnosis `docs/qa/notes/prop-ct0-rpm-creep.md`: ~44% from the analytic fallback below Re 4e4 (`fansim/propeller/polars.py:151`), ~44% from real table Re effects, ~15% from Mach. No patch yet | open (new 2026-10-09) |
| UI-23 | LOW | All | Browser console `TypeError: n[i[e]] is not a function` in `assets/index-*.js` from `invokeConnectionClose`, twice, on page reload (B10) | open (new 2026-10-09) |

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
6. **[verified fixed `cd136fe`, 2026-10-09: `random_prop_flat(fpv_5inch)` seed 12345 ×8 all trim, max radius ≤ R + 0.046 mm (tol 0.1), all valid]** **`_trim_blade_to_tip_cylinder` can still return an untrimmed blade** if all 4 intersect retries come back empty (`blade.py:1080-1084`), even though the comment says that is what it avoids. This did not happen in my 23 builds.
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


## Re-test 2026-10-09 (master @ 961f953)

**Tracker:** 11 verified (QA-1,2,3,5,6,7,8,9,10, UI-1, UI-15), 0 reopened, 5 not yet fixed (QA-4; UI-4, UI-5, UI-6, UI-11 partly fixed), 9 need a browser pass (UI-2, 3, 7, 8, 9, 10, 12, 13, 14). New: QA-11, UI-16..UI-19.

**Needs a real browser click-through:** UI-2, UI-3, UI-7, UI-8, UI-9, UI-10, UI-12, UI-13, UI-14; also the remaining parts of UI-4 (progress bar), UI-6 (click Export → download link) and UI-11 (leftover render), and a Volute Export click for UI-1.

**Fast suite, Linux, one process (§23.9):** `pytest -m "not docker and not slow"` → 1555 passed, 18 skipped, 22 deselected, 1 xfailed, 0 failed, in 21 min 40 s. No OOM kill (dmesg unchanged). Peak RSS 8.2 GB (sampled every 2 s, `qa/fullsuite_rss.log`), reached about 60–65% of the way through the run (sampler t≈850–885 s); RSS drops between files (down to ~0.7 GB at times), so the `malloc_trim` fixture in `tests/conftest.py` works. Note that the peak is HIGHER than the earlier OOM points (5.4–6.3 GB anon-rss): this run finished only because nothing else was using the box. On a 16 GB box with a browser/cockpit open, a single-process run could still OOM; it is one file (or a few) that peaks, not accumulation. Windows comparison: 1565 passed / 2.47 GB.

**Reconnect stress (UI-16..18):** cockpit from the repo on 127.0.0.1:8080 with an empty run dir; client `qa/ws_stress.py` does the browser handshake (WS `/ws` → `wslink.hello` with secret → `trame.state.get` → `trame.lifecycle.update client_connected` → `viewport.image.push.observer.add`), then closes cleanly / closes without `client_exited` / aborts the TCP connection (no close frame) / sends RST, plus groups of 3–6 overlapping sessions.
- 506 cycles, 0 errors; a fresh session got the full state (422 keys, 0.02 s) after every batch of 25. Server RSS 800→895 MB then flat, threads 19→36 then flat, fds 14 flat, asyncio tasks back to 2 between batches. **Open/close churn alone does not break it.**
- **What breaks it (UI-16):** one client that completes the handshake + image observer and then stops reading (`qa/ws_stall.py`, SIGSTOP; same as a frozen/sleeping browser tab or a dropped Wi-Fi link). After ~76 image pushes the server's send to that client blocks and **no new session can complete `wslink.hello` (probe timed out at 15 s every time for 150 s; HTTP `/index.html` still 200 in 5 ms)**. The 30 s heartbeat fires (`No PONG received after 15.0 seconds` in the log) but does not release it; only killing the stalled client recovers (next probe 0.03 s). Same with 1 or 3 stalled clients. Task census during the hang: `sendWrappedMessage` tasks piling up (6) waiting.
- **Likely code:** `wslink/protocol.py` `sendWrappedMessage` (~l.425–431): every send to every client is `await ws.send_bytes(chunk)` inside one global `async with self.attachment_atomic` lock, with no timeout, so one client whose TCP buffer is full blocks all replies (including the `wslink.hello` reply to new clients). The heartbeat timeout is handled as a message (`wslink is not expecting text message: > No PONG…`) in `handleWsRequest`'s loop rather than aborting the transport, so the blocked drain never wakes. The image pushes come from `vtkmodules/web/protocols.py` `pushRender` → publish to all authenticated clients. Upstream (wslink 2.5.7 / aiohttp 3.14.3), triggered by the cockpit's remote views. Possible fixes (not done): per-client send timeout/abort, close stalled clients on heartbeat failure, or a lower `WSLINK_HEART_BEAT` plus abort.
- **UI-17:** 20 plain `curl /ws` → 20 `KeyError` tracebacks: `handleWsRequest` registers `connections[client_id]` before `prepare()`; when `prepare()` fails, `onClose` hits `del self.unchunkers[client_id]` → KeyError, so `del self.connections[client_id]` never runs (entry leaks, "No more connections" logic never sees an empty dict). Abrupt disconnects produce 46 `Cannot write to closing transport` tracebacks per ~500 cycles; `_quiet_connection_reset` in `app.py` only filters the loop exception handler, not wslink's logger.
- **UI-18:** (correction 2026-10-09: the live code is `trame_vtk/modules/vtk/protocols/publish_image_delivery.py` `add_render_observer`/`tracking_views`, same logic.) `addRenderObserver` increments `trackingViews[...]["observerCount"]`; there is no `onClose` hook, so tabs that vanish without `observer.remove` are never subtracted and the observers are never removed.


## Re-test 2026-10-09 (2): branch `qa-fixes-2026-10-09` @ d781894

**Result:** 7 verified (UI-5, UI-16, UI-17, UI-18, UI-19, QA-11, suspicious #6 / §23.32). 0 reopened. 7 need a browser pass (UI-4, 8, 9, 13, 20, 21, 22). QA-4 is still open (patch not applied). New: QA-12 (CT0 rpm creep, LOW).

**Websocket checks** (`handoff/2026-10-09_from-qa/ws/ws_suite.sh`, same launcher and run on both builds, empty run dir, Linux):

| check | 961f953 | d781894 |
|---|---|---|
| A: 20× plain GET `/ws` | +20 `KeyError`, `connections` 0→20 (leaked) | +0, `connections` 0 |
| B: 30 observer sessions aborted (no close frame) | `observerCount` 30 | `{}` (released) |
| C: 1 frozen client + 200 image pushes | pushes stuck at 76; every fresh-session probe timed out (15 s) for 65 s+; healthy only 5 s after the frozen client was killed | 200/200 pushes in ~16 s; probes 0.25–0.38 s all along; frozen client dropped after ~15 s (`not reading for 15 s` warning, once); with 1500 pushes, fds 16→15 between t=16 and t=21 s |
| D: 506 cycles (clean / no-exit / abort / RST / 3–6 concurrent) | 0 errors, probes OK, observerCount → 538 | 0 errors, probes OK, observerCount `{}`; 41 s vs 21 s (each new session re-adds its observer and triggers a first render) |
| server after D | RSS 909 MB, 36 threads, 14 fds | RSS 952 MB, 36 threads, 14 fds |
| log counts | KeyError 20, closing-transport 15, No PONG 1 | 0, 0, 0 |

Observation (not filed): server RSS rose by about 60–100 MB during the stall test (903→966, and 952→1009 with 1500 pushes) and did not drop after the client was dropped. That looks like allocator retention, not growth: it stayed flat over the next 70 cycles.
