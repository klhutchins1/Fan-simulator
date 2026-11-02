# QA r24 A: remaining UI items and bugs on master 23831da (grok, 2026-11-01 MST)

**Setup**
- Prereg: `prereg_r6` `prereg/round24` **88c4e79**, committed 12:21 MST before any data.
- Build: fresh clone of `master_23831da.bundle`; HEAD 23831da.
- Cockpit: run headless on :8080 with `scripts/cockpit.py --run <empty dir>`. Driven by Playwright with system Chrome, plus pure-function calls.
- Nothing was clicked except Preview. No Assess, Sweep, Optimize, CFD or Docker.
- **Code delta:** `git diff 3b92eea 23831da -- fansim scripts docs/control_images README.md` is empty. Since b3d5543 (r22), only `scripts/validate_lt120.py` and two lt120 tests changed. So nothing below could have been fixed in code. The checks were still re-run, as pre-registered.
- Scripts and raw JSON: `handoff/2026-11-01_from-qa-24/{scripts,data}/`.

| ID | Sev | r24 status | evidence (rule from PREREG_R24) |
|---|---|---|---|
| UI-26 | MED | **still open** | 'Gold = parametric Stock' renders on the first view in Simple and Expert at both sizes. The hose line shows in Expert. (`a_ui.json`) |
| UI-27 | MED | **still open** | 1366×768: viewer bottom at 957 px (limit 768). The picker (y 512 / 300) and Preview (y 602 / 482) are above the fold. 1920×1080: viewer bottom at 1172 px. |
| UI-29 | LOW | **still open** | Controls column 793/1920 = 41 % (pass). Body text 16 px (pass). 'Start here' is 12 px, `text-caption text-medium-emphasis`, rgba(0,0,0,0.6) (fail). |
| QA-40 | LOW | **still open** | r14 flow-card harness: s3 (SWL, no Stock) still shows the noise row in Simple; s1, s2 and s4 pass. (`a_flowcard.json`) |
| QA-42 | LOW | **still open** | The rendered Preview line reads "✓ fits Noctua NF-A12x25 (dia 109 mm, depth 16 mm, 11 g)" for both PLA+ and PETG, with no material named. |
| QA-61 | LOW | **still open** | Two ranges remain. "~15–30 min" at `fan_tab_ui.py:494,594,896`, `fan_core.py:84` and `fan_assess.py:482`; the Actions button renders "Assess (~15–30 min)". "30–40 min" at README:138, `fan_assess.py:332` and `run_settings.py:3`. |
| QA-62 | MED | **still open** | `pytest tests/test_axial_scripts_oriented.py` fails: "validate_lt120.py: add to AXIAL_SCRIPTS or EXEMPT". |
| QA-63 | LOW | **still open** | `pytest tests/test_fuse_memory.py` fails: `fuse_remaining_estimate_gb(18084)` = 1.934 is not less than `fuse_peak_estimate_gb(18084)` = 1.925. |
| UI-31 | HIGH | **still open** (on this bundle, not `r111-hide-surrogate`) | (a) The "Surrogate-guided (DoE→NSGA on GP→verify top-k)" switch renders in Expert and is enabled (`fan_tab_ui.py:1071`). Its tooltip still says "verify top-k (stub by def…". (b) `optimization_argv(surrogate_guided=True, …)` gives `['--surrogate-guided']` with no `--verify-cfd`. `run_surrogate_guided` defaults to `label_fn or synthetic_label` and `stub_verify` (`surrogate_search.py:442,458,471-477`). |
| UI-32 | MED | **still open** | `fan_copy._load_control_images()` returns 54 keys, all `e_*` (glob `e_*.png`, `fan_copy.py:14`); 0 `opt_*`/`assess_*`. Hovering Boost, NN, Surrogate-guided and Catalog GP skip shows text with 0 `<img>`. |
| UI-33 | MED | **still open** | The rendered Optimize panel text has none of the pre-registered phrases. The panel reads: "Multi-objective CFD search. Reuses Application hose + Honesty above. Defaults: 8 trials…" (`fan_tab_ui.py:1015-1018`). |
| UI-34 | MED | **still open** | The Boost and NN switches are enabled with GP skip and Surrogate-guided both off. Their tooltips name only "With Catalog GP skip on". `optimization_argv(gp_boost=True, gp_nn=True, gp_floor=0, surrogate_guided=False)` emits no `--surrogate-*` flag (`cli_argv.py:160-173`). |
| UI-35 | MED | **still open, 13/13** | `range_check.py` on repo-r24 finds 20 min/max mismatches, including all 13 listed models (camber root/mid/tip, hub_radius, skew mid/tip, winglet sweep/lean, tip_notch_depth, thick_mm, le_thick, te_thick, shroud_height). `data/range_check_r24.json` |
| UI-36 | MED | **still open, 0/8** | Hovered in Expert: Fan model (hub), Hub profile, Application, Print material, Sweep, Allow intake overbuild, Fit hub to the motor and Preview. None shows a tooltip. Report-only: the source inventory is identical to the tooltip audit (293/293 rows, same status), so 49 Fan-tab settings still have no tooltip. |
| UI-37 | LOW | **still open** | Proxy-tab inventory (Prop / Mixed / Volute / Prop+CROR panels): 1 of 100 rows has a tooltip (1 %, rule ≥ 90 %). The audit counted 1 of 109 including the CROR rows. |
| UI-38 | LOW | **still open** (one sub-check now passes) | (1) **Passes:** the Expert caption under Print material says "Used by Assess and Optimize. Pick PLA+ here before Optimize…" (`fan_tab_ui.py:926`). Honesty says "Also applied when you press Optimize" (`:947`). This text was already present at 3b92eea, so the audit's first clause was **overstated**: the Application caption does not mention Optimize, but the material caption does. (2) **Fails:** picking a design still silently overwrites preset, refine and roughness (`fan_trials.py:103-105`) with no message. |

**Fast suite** (`-m "not docker and not slow"`, one process, 25 min 35 s): **1883 passed, 4 failed**, 21 skipped, 23 deselected, 1 xfailed.
- The 4 failures are the same as in r22:
  - QA-62: `test_axial_scripts_oriented`;
  - QA-63: `test_fuse_memory`;
  - QA-41: 2 × `test_worker_parent_watch` (the zombie/parent-watch behaviour on this box).
- 1883 passed against 1880 in r22: 3 more, from the new `tests/test_lt120_tipgap_cli.py`.

**New bugs:** QA-65 (MED), from task C: a converged=False Assess score loses its UNCONVERGED note. See `r24-C-k1-visibility.md`. No new UI IDs.
