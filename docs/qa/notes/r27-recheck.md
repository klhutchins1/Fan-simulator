# Round 27 (grok, 2026-11-09): current-master re-check on 9869116

**Build:** `master_9869116.bundle` sha256 `0f8e06e0682f8c433f2e7a3e58d161e9f14d3c67df6025c7d6a21d6913621d92` (verified), fresh clone
`/workspace/fansim/repo-r27` at `986911657cf0874d35ab6ef5c1427d2acbc0616a`; brief `handoff/2026-11-09_to-qa-27/CLAUDE_TO_QA.md` (identical in bundle
and brief zip). Linux, Python 3.12, `uv sync --frozen --extra dev`. No Docker / CFD / OpenFOAM; no Assess, Sweep, Optimize, Export or Randomize
click. No edits or commits in the clone (`git status` clean at the end). Code proposals are patches only.
**Prereg:** `ef58906` on branch `prereg/r27` in `/workspace/fansim/qa/prereg_r6` (separate worktree `qa/prereg_wt_r27`; shared copy left on
`prereg/research-lead30`), committed before any diff, grep, test or render. Copy: `handoff/2026-11-09_from-qa-27/prereg/`.
**Evidence types:** behavioural = test or probe executed; rendered = headless cockpit (empty run, port 8827, 1366×768); static = grep / diff / code.

## Summary

| item | verdict | evidence |
|---|---|---|
| A QA-57 (Volute Assess label) | **still open (partly fixed, unchanged since G3)** | static + rendered |
| B UI-39 (Sweep steps) | **still open** | static + behavioural + rendered |
| B UI-40 (Optimize Trials) | **still open** | static + behavioural + rendered |
| C QA-70 (Expert noise-hint row) | **still open** | static + behavioural |
| D G4 (R1.10) | **verified for its listed files** (D1–D9 pass), with 2 new leftovers outside its list | static + behavioural + rendered + red check |
| D QA-58 | **verified for G4's list**; leftovers filed as QA-71 / QA-72 | as G4 |
| D QA-69 | **verified** (design-rules.md and the generator label say "Noise estimate (min)") | static + test + red check |
| UI-41 / UI-42 (not in the brief) | **still open** (code unchanged) | static (diff only) |
| New | **QA-71** (MED), **QA-72** (LOW) | behavioural + static |

`git diff --stat 41e2dc9 9869116` over `volute_tab.py`, `fan_assess.py`, `fan_optimize.py`, `fan_flow_report.py`, `fan_editor.py`, `fan_viz.py`,
`fan_widgets.py` and their tests is empty. In `fansim/cockpit/` only `fan_copy.py`, `fan_tab_ui.py` (the Assess intro line) and `figures.py`
changed, all G4. `git apply --check` on master: the three earlier patches (`g3-QA57-volute-assess-label`, `ui-hunt-1-UI39-UI40-steps-trials`,
`ui-hunt-1-QA70-noise-hint-row`) still apply, so **none is landed**.

## A. QA-57: still open
- Static (`volute_tab.py`, unchanged): only Optimize lines carry the label (:164, :590). The Assess copy (:159 "Assess runs radial MRF…",
  :163 "Assess: free+load CFD in the radial MRF domain (OpenFOAM Docker).") and the result readout (:417 "Domain: radial MRF stage 1 (…)") do not.
- Rendered (Volute Design and Results, Expert): the label shows on 2 lines, both about Optimize; the 2 Assess lines have no label.
  Screens `r27_volute_{design,results}_expert_1366.png`.
- Patch `docs/qa/patches/g3-QA57-volute-assess-label.patch` (from G3) still applies; on scratch it passes with the other patches (below). Mixed: not re-tested.

## B. UI-39 / UI-40: still open
- Static: `fan_assess.py:448` `steps = max(2, int(state.sweep_steps))` and `fan_optimize.py:129-133` (fallback 8, `max(2, min(40, trials))`) unchanged;
  `fan_tab_ui.py` labels are still "steps" and "Trials".
- Behavioural (ui-hunt-1 `seed_probe.py` re-run, output identical to ui-hunt-1): steps "" and "1e9" → ValueError (silent; no message);
  "100" → 100 runs; "-5" → 2. Trials "" → 8, "-5" → 2, "100" / "1e9" → 40 (silent clamp).
- Rendered: labels read "steps" / "Trials" with no range; typing 1e9, 100, −5 or "" stores the text in state with no error state and no min/max
  attribute on either input. Run not clicked.
- The ui-hunt-1 patch only labels the fields and adds min/max; it **does not meet the brief's "refuse instead of silent clamp"** for Trials.
  New patch `docs/qa/patches/r27-UI39-UI40-refuse-run-counts.patch` supersedes it: `fansim/cockpit/input_checks.py` (whole number in 2–12 /
  2–40, else `⚠ … Nothing was started.`), `on_sweep` and `on_optimize_fan` refuse before any task starts (message to `assess_msg` / `opt_msg`),
  labels "steps (2–12)" / "Trials (2–40)" with min/max/step, test `tests/test_ui39_ui40_run_counts.py` (23 tests). On scratch: 67 passed with
  `test_simple_mode_copy.py` and `test_optimization_argv.py`; red check (helper + tests only, handlers unpatched): 1 failed / 22 passed.

## C. QA-70: still open
- Static: `fan_flow_report.py` unchanged since 41e2dc9.
- Behavioural (ui-hunt-1 `flowcard_hint_probe.py`, I/O faked): hint-only run (tip speed + CFM, no SWL) → rows `direction, push, spin, dead`
  (no `noise`); hint + SWL → `noise` present. Patch `ui-hunt-1-QA70-noise-hint-row.patch` still applies and passes on scratch. G2 not re-tested.

## D. G4 (+ QA-58, QA-69): verified for its list; two leftovers
G4 is on master (`5c79aaa`, `d3c78d8`, merge `a56dcb0`).
- D1 `figures.py:398` "CFD's static-pressure ceiling is a little below the datasheet's (about 10 %)"; no "~2×". **pass**
- D2 `fan_tab_ui.py:494` "Assess runs two CFD solves (free air and a loaded point), about 20–40 min". Rendered in Simple (the intro alert is
  Simple-only); "one CFD solve" not on the page in either mode. **pass**
- D3 `fan_copy.py`: no "~0.6×"; "ranking only; coarse; can't separate close designs". **pass**
- D4 `design-rules.md:43` and `adversarial-review.md:237` say "screening mesh, GCI ≈ 21 %; ranks designs, ±1 % run to run on Stock". **pass**
  (but see QA-72: the generator still writes the old caveat)
- D5 "more blades raise airflow" gone from `design-rules.md`. **pass**
- D6 `a12x25-reference.md:24` "validated on a close-reference STL of the A12x25: 59.8 vs 60.1 CFM"; "every gap … closed" gone; the historical
  block lists what is still open (near-stall points, Stock recipe gap). **pass**
- D7 README "Known limits" (line 67 summary + list at :202) has all six items, incl. "the Stock recipe reads about 5 % less airflow than the real
  A12x25". **pass**
- D8 QA-69: `design-rules.md:10` and `extract_design_rules.py:106` say "Noise estimate (min)"; no "Noise dB(A) (min)". **pass**
- D9 `tests/test_r110_g4_stale_numbers.py` 8/8 pass; **red check**: restoring the 41e2dc9 copies of the 8 G4 files in scratch → 8 failed.
- Rendered: no "~2×", "0.6×", "3–5", "one CFD solve" or "dB(A)" in the Fan tab text (Simple, Expert, Expert with all panels expanded).
- Targeted suite on master: `test_r110_g4_stale_numbers`, `test_r110_g3_mixed_volute_copy`, `test_r110_g2_noise_copy`, `test_flow_verdicts`,
  `test_simple_mode_copy`, `test_design_dropdown` → **64 passed**.

Repo-wide grep (outside QA files) found stale numbers G4's file list missed:
- **QA-71 (MED, new): the Assess "rejected — stalls at this hose" message still says "CFD under-predicts static ~2×"**
  (`fansim/optimize/objectives.py:154`, docstring :137). Behavioural: `_operating_point_reason` for a stalled probe returns
  "… (CFD static ceiling is below the hose; CFD under-predicts static ~2×). Try a lighter hose."; `fan_assess.py:211/273` shows it as
  `assess_msg`. It contradicts G4's new "about 10 %" copy on the same tab. Not rendered (needs an Assess).
- **QA-72 (LOW, new): other stale G4 numbers outside its list.** `scripts/extract_design_rules.py:139` still writes the caveat
  "CFD is screening fidelity (~3–5% discretization)", so regenerating `docs/design-rules.md` would undo G4's line 43 (the generator's read-out
  text also differs from the hand-edited doc). `scripts/run_optimization.py --help` for `--bem-prescreen` prints "BEM≈0.6× CFD" (behavioural:
  `--help` output). Docstrings: `fansim/fan_bem.py:16` "~0.6×", `extract_design_rules.py:6` "relative noise dB(A)".
  Left alone as correct or not stale: `objectives.py:81` (warns against a 3–5 % bar), `fan_spec.py:282` (~2x RPM), roadmap/perf notes
  (speed-ups), `bibliography.md:87` (historical study).
- Patch `docs/qa/patches/r27-QA71-QA72-g4-leftovers.patch` (objectives message + docstring → "a little below the datasheet's, about 10 %";
  CLI help → "ranking only, coarse"; generator caveat → G4 wording; two docstrings) + `tests/test_r27_g4_leftovers.py` (3 tests).
  Scratch: 32 passed with `test_objectives_reason.py`, `test_r110_g4_stale_numbers.py`, `test_optimization_argv.py`; red check (tests only): 3 failed.

## All open patches together
On a scratch clone of 9869116: `g3-QA57-volute-assess-label` + `ui-hunt-1-QA70-noise-hint-row` + `r27-UI39-UI40-refuse-run-counts` +
`r27-QA71-QA72-g4-leftovers` apply together (11 files) → **113 passed** over the 10 affected test files.
(`ui-hunt-1-UI39-UI40-steps-trials.patch` is superseded by the r27 patch; do not apply both.)

## UI-41 / UI-42 (asked by Kimball, not in the brief)
Static only: `fan_widgets.py` and the Seed / Scale fields in `fan_tab_ui.py` are unchanged since 41e2dc9. **Still open.** Not re-rendered.

## Not done / not claimed
- QA-71's text was not rendered (it only shows after a CFD Assess); the stall message is checked through the pure function.
- G2 and G3 C22/C24/C25 not re-proved (per brief). R3.1 export leak still waits on R3.1. Research leads 23–30 stay parked. G5 queued, not tested.
  R3.5b and the merge-gate counts (701/519/706, 717/555/653) are board claims, not re-run here.
- Console: one `POST /paraview/ 405` at load (documented harmless in README); no page errors.
