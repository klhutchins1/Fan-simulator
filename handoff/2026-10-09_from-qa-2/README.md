# QA → Claude, round 3 (2026-10-09). Requests (1), (4), (5), (6)

Compute ran in the QA clone (`research/repo_research`, e48a32d, with the axial-force patch applied, since it is **not** on master).
Nothing was committed to repo-r3. Patches are proposals only. No CFD, Docker or OpenFOAM was used, and :8080 was not touched.

## Pre-registration (hashed and committed before running)
QA clone branch `prereg/round3`, commit `5913a74eef5211ca6fe22c63ac6e6a856fb1aeb7` (2026-10-09 14:04 MDT):
- `docs/qa/notes/axial-force-top5-vs-stock-criteria.md`: sha256 `66db00187d4a008135a6a807f24ff9c3466de6c0ee8b668c01311c7b05bdf75e`
- `docs/qa/notes/prop-lowre-blend-criteria.md`: sha256 `e91b280457a17f50f9e0b9c9a3e5375ebbba9ff6026e5899665abcfa2d426844`

Existing criteria, unchanged on e48a32d:
- `axial-force-retune-criteria.md`: `17e1e9c4…f7e2`
- `prop-ct0-rpm-creep-criteria.md`: `428c808e…700cea4`
- the eval script `handoff/2026-10-09_from-qa/eval_rank_vs_cfd.py`: `6377ee0b…`, identical to the pre-registered copy.

## (1) Rule (c): PASS
Run exactly as pre-registered on `cfd_designs.csv` (n = 16, `cfd_free_cfm`).

| | Spearman ρ vs CFD | top-3 overlap |
|---|---|---|
| axial | **0.809** | 2/3 |
| euler | 0.827 | 2/3 |

The pass bar was ρ_new ≥ 0.6 and ≥ ρ_base − 0.10 = 0.727, so it **PASSES**.
- CFD top 3: t9016, t9005, bem_9505.
- axial top 3: t9016, bem_9505, bem_9504.
- euler top 3: t9016, bem_9505, bem_9502.

Secondary checks (not part of the verdict):
- ρ without t9012: 0.769 axial vs 0.790 euler.
- load CFM (n = 13): 0.691 vs 0.724.

**In plain language:** axial mode ranks free airflow about as well as the old model, slightly worse. What it gains is removing the old exploits, not better ranking.

CSV notes:
- 3 blank `cfd_load_cfm` rows (not used by the verdict).
- `stock_thin` gets BEM scores identical to Stock, because the BEM ignores thickness, while CFD differs (54.8 vs 58.1).

Output: `results/rule_c.json`.

### All 5 BEM-screen picks above Stock in axial mode? FAIL (pre-registered)
Screen score in axial mode (Stock = 1):

| design | score |
|---|---|
| 9501 | 1.056 |
| 9502 | 0.968 |
| 9503 | 0.971 |
| 9504 | 0.986 |
| 9505 | 0.965 |

Only 1 of 5 is above Stock. Euler puts 0 of 5 above (0.954–0.978).

The airflow terms are close. The miss comes from **efficiency**: the BEM gives Stock 29.4 % at the operating point, while CFD gives Stock 17.9 % against 26–29 % for the five designs. So the BEM over-rates Stock's efficiency. Output: `results/top5_vs_stock.json`.

## (4) QA-12 blended low-Re prop polar: FAIL
Details: `docs/qa/notes/prop-lowre-polar-blend.md`. Patch (record only, do not merge): `docs/qa/patches/prop-lowre-polar-blend.diff` (passes `git apply --check` on e48a32d).

| rule | baseline | with blend | result |
|---|---|---|---|
| R1 creep | +62.5 % | +62.3 % | fail (expected) |
| R2 GWS CT0 | −8.4 % | −4.8 % | pass |
| R3 spread | 0.160 | 0.196 | **fail** |
| R4 J-rms | 0.0080 | 0.0100 | **fail** |
| R5 tests | | 42 + 4 pass | pass |
| R6 jump | 66 % | 0 % | pass |

The jump at the table edge was real, but it is not what causes the creep. The analytic low-Re polar itself is the problem.

## (5) Noise leads (notes only)
- **#1 rotor–strut, Tyler–Sofrin:** worth it (S). With 9 blades and 4 struts, the blade-pass tone escapes as an m = ±1 "side-shake" pattern at 1× and 3× BPF. Never pick B as a multiple of V. The uneven-spacing metric should be strut-aware. See `docs/qa/notes/noise-lead-1-rotor-strut.md` and `results/tyler_sofrin.md`.
- **#2 ECMA-418-1 + MoSQITo:** worth it (S) as a readout. MoSQITo 1.2.1 is Apache-2.0 but has a hidden matplotlib import. In a demo, PR = 19.9 dB but TNR = 2.9 dB on the same tone, so validate first. CFD traces are too short for these metrics; feed it a synthetic spectrum. See `docs/qa/notes/noise-lead-2-ecma418.md`.

## (6) Axial-force BEM screen, max_camber ≤ 0.10 → `screen_r3/`
Setup: same `bem_screen.py` guards, score, 8 Pa "case" load and 2000 rpm. Sobol 4096 + TPE 2500, seed 0, about 12 min on 1 core at nice 19. The post-hoc stalled-span guard is also applied.

Results:
- 2079 of 6596 designs are feasible. 1993 of the feasible designs beat Stock in axial mode.
- Shortlist: 30 diverse designs (RMS-normalised distance ≥ 0.12), trial ids 9601–9630.
- Cockpit runs: `bem_screen_r3_top5` / `bem_screen_r3_reserve`. Load check: 30/30 via `_load_assessed_designs`, 32/32 YAMLs.
- References included: Stock and previous #4/bem_9504.

| rank | id | B | camber | free CFM | load CFM | η op | score | Euler score |
|---|---|---|---|---|---|---|---|---|
| ref | Stock | 9 | (0.097 yaml) | 56.8 | 48.3 | 29.4 % | 1.000 | 1.000 |
| ref | prev #4 bem_9504 | 10 | 0.028 | 58.8 | 48.6 | 26.9 % | 0.986 (rank 1997/2079) | 0.962 |
| **1** | T06592 | 11 | 0.030 | 66.3 | 59.2 | 46.4 % | 1.325 | 0.952 |
| **2** | T05252 | 11 | 0.024 | 63.4 | 57.2 | 42.2 % | 1.246 | 0.934 |
| **3** | T04536 | 11 | 0.026 | 59.8 | 54.6 | 38.0 % | 1.158 | 0.899 |
| **4** | S03681 | 10 | 0.067 | 60.5 | 53.2 | 32.0 % | 1.085 | 0.941 |
| **5** | S01272 | 11 | 0.004 | 58.4 | 52.5 | 31.9 % | 1.067 | 0.908 |

**Caveats. Read before spending CFD on these:**
1. **The two models disagree completely.** Euler scores all 400 of the top axial-mode designs *below* Stock (`hedge_top400.json`). The top picks gain about 10 CFM and double their efficiency purely from the pressure model.
2. **Rule (c) only checked free-CFM ranking** on designs from the old search region. The new leaders sit at the box edges (11 blades = max, chord_mid = max, camber_pos = max, tip = max), which the 16 CFD designs never covered.
3. **Efficiency is not trustworthy.** The BEM gives 38–46 % against 18–29 % in CFD, and BEM efficiency barely tracks CFD (ρ ≈ 0.3).

So the CFD top 5 is effectively **a test of the axial model in a new region**: worth running, but don't expect the BEM gains to show up.

Widening camber to 0.10 changed almost nothing:
- Of 1638 trials with camber > 0.06, only 64 were feasible. Most failed loadcap_solidity, flutter or envelope_fit.
- Only #4 of the top 5 has camber above 0.06, and 9 of the 30 on the shortlist do.
- Above about 0.0625, the BEM switches to the S1223 high-lift tables, and every camber from 0.07 to 0.10 reads the same table. So high-camber rankings are coarse.

## Status lines for docs/QA_REVIEW.md (owner: other worker)
- QA-4 (axial-force): rule (c) **PASS**, n = 16, ρ 0.809 axial vs 0.827 euler, top-3 2/3 both. Pre-registered "all 5 screen picks > Stock in axial": **FAIL** (1/5), driven by BEM over-rating Stock's efficiency (29.4 % vs CFD 17.9 %). The axial patch is still not on master.
- QA-12 (prop CT0 creep): pre-registered smooth low-Re blend **FAIL**. It removes the jump at Re 4e4 (66 % → 0 %) but creep is unchanged (+62 %) and GWS R3/R4 get worse. Record-only patch is `docs/qa/patches/prop-lowre-polar-blend.diff`. Root cause is the analytic low-Re polar level, not the switch.
- Noise leads #1 and #2: worth-it/proposed (S). Notes are in docs/qa/notes/noise-lead-*.md.
- Screen r3 (axial, camber ≤ 0.10): 30-design shortlist in handoff/2026-10-09_from-qa-2/screen_r3. The top 5 are all axial-only winners (Euler < Stock), so treat their CFD as validation of the axial model.

## Files
- `scripts/`: top5_vs_stock.py, blend_eval.py, tyler_sofrin.py, ecma_tnr_demo.py, screen_r3.py, postprocess_r3.py, screen_r3_check.py, screen_r3_hedge.py.
- `results/`: rule_c.json, top5_vs_stock.json, blend_baseline.json, blend_blend.json, tyler_sofrin.md, ecma_tnr_demo.out.
- `screen_r3/`: shortlist.csv, screen_summary.json, stock_baseline.json, top5_euler_vs_axial.json, hedge_top400.json, screen_run.log, all_designs.jsonl.gz, designs/ (30 + 2 refs), cockpit_import/, quick_cfd_jobs/.

---

# QA → Claude, round 3: requests (3) and (2)-prep (second QA worker)

Run in `/workspace/fansim/repo-r3`, master `e48a32d`, Linux. Nothing was committed.

- **(3) Linux fast suite, one process:** see `memory/README.md`.
  - 1573 passed, 18 skipped, 1 xfailed, 0 failed, in 20 min 44 s. No OOM.
  - **Peak 8.19 GB, held by one test:** `tests/test_mount_gauge.py::test_gauge_accepts_carved_stock_export`. It reaches 7.7 GB even when run alone, in the in-process OCCT fuse of the motor-cup hub + 9 blades (`fuse_impeller`). `MALLOC_ARENA_MAX=2` only takes it to 6.4 GB.
  - Next highest: CROR setup audit 6.45 GB, test_cror 6.40 GB, notched tips 4.22 GB, isolated build 3.53 GB.
- **(2) prep:**
  - The cockpit is running from repo-r3 on 127.0.0.1:8080 with an empty run dir; a fresh session connects.
  - Browser checklist for UI-4/9/20 (+UI-23): `docs/qa/browser_checklist_2026-10-09_r3.md`.
  - Headless pre-checks on master:
    - `preview_motor_cup` = False on load.
    - The served template has the 3:2 viewer style and the `✎ Edited copy of` selection slot.
- **Websocket regression on master (`ws_regression_e48a32d.log`):**
  - UI-16: a frozen client doesn't block anyone (probes 0.33–0.39 s, 200/200 pushes).
  - UI-17: 0 KeyErrors.
  - UI-18: observers `{}`.
  - 506 cycles, 0 errors.
  - `FANSIM_WS_GUARD=0` really turns the guard off: 20 KeyErrors and 20 leaked connections, i.e. the old behaviour.
