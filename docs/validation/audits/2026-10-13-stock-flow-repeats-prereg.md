# Stock flow-card repeats (roadmap 27.3) — pre-registration

Written 2026-10-13, **before** any of the five Assess solves. Thresholds in
`fansim/cfd/flow_verdicts.py` are **not** changed until these runs finish and the rule below is
applied.

HEAD at writing: `a09905a`. Working tree also has 27.1 / 27.5 / 27.8 (fuse guard, captions,
hang-limit UX). Those do not change the solver, mesh, or Stock YAML.
`config/problems/a12x25_reference.yaml` stays `section_wrap: cylinder` (Stock v3).

## Why

`BAND_TOL` (±15 %) and `NOISE_MARGIN_DB` (+2.8 dB) came from one pair of Stock runs that was **not**
a pure repeat (hub-clip vs pre-clip, audit `2026-10-10-flow-report-checks` F2). Roadmap 27.3: run
Stock 3–5 times on the same setup and set each tolerance at about 2σ.

## Setup (fixed)

Five independent cockpit Assess solves of Stock v3, same knobs as
`scripts/cylinder_sections_cfd.py` / `scripts/screen_rank_audit.py` `run_full`:

| knob | value |
|---|---|
| geometry | `stock_blade_flat("a12x25")` → `a12x25_reference.yaml` |
| spec | `a12x25` |
| hose | `"case"` (`assess_load`) |
| procs | 8 |
| base_cell | 0.006 m |
| iters | 500 |
| material | PETG |
| refine_op | False |
| parallel_mesh | True |

Each repeat is a **new** case directory `runs/stock_flow_repeats/r{1..5}/`. Do not reuse
`runs/screen_rank_audit/*` or the V5 Stock v3 case. Skip-done is only `_eval_result.json` already
in that repeat's own directory. Runner: `scripts/stock_flow_repeats.py`. Launch: Windows Scheduled
Task `fansim-27.3-stock-repeats` (not a shell background job).

Flow metrics: `load_or_compute_metrics` at `FLOW_REPORT_VERSION` 3 (area-weighted mean push).
The report uses the **loaded** field (Assess writes free air first, case hose last).

n must be 5 OK solves. A failed eval is not replaced; stop and report.

## Rule (fixed now — apply only after n = 5)

Let σ be the **sample** standard deviation (denominator n−1).

- `x_i` = `mean_dp0_pa` of repeat i
- `b_{i,k}` = `band_dp0_pa[k]`, k = 0..4
- `n_i` = `noise_swl_db` of repeat i (skip the noise rule if any repeat is missing noise)

Relative 2σ of a series `v` is `2 σ(v) / |mean(v)|` when `|mean(v)| > 1 Pa`; otherwise that series
is ignored (a near-zero band would blow up).

```
BAND_TOL         = max(0.02, ceil_2dp(max of 2σ_rel(mean_dp0) and 2σ_rel of kept bands))
NOISE_MARGIN_DB  = max(0.5,  ceil_1dp(2 σ(noise_swl_db)))
```

Floors are display precision: the card prints percents and one decimal dB. Rounding is always
**up**, so the baked value still covers 2σ.

Do not change backflow / swirl / dead / tip-ratio margins from this campaign (F2 said those rows
were stable). Per-band labels keep using the same `BAND_TOL` as the mean-push verdict; they stay a
picture (27.3 option b).

## After baking (not judged until the constants are in the file)

Using the new constants, judge r2..r5 against r1: every push row "about as hard as Stock", every
band "similar", every noise row not ⚠. If that fails, do not widen again in this ticket; record
FAIL and ask Kimball.

## Results (n = 5, applied 2026-10-14)

Five OK Assess solves. Proposed from the rule: **BAND_TOL = 0.03**, **NOISE_MARGIN_DB = 0.5**.
Baked into `fansim/cfd/flow_verdicts.py` (was 0.15 / 2.8 dB from the non-repeat F2 pair).

| repeat | mean_dp0_pa | noise_swl_db | CFM free / load |
|---|---|---|---|
| r1 | 12.711 | 20.780 | 53.281 / 43.369 |
| r2 | 12.886 | 20.560 | 53.321 / 43.356 |
| r3 | 12.880 | 20.531 | 53.306 / 43.362 |
| r4 | 12.919 | 20.659 | 53.287 / 43.391 |
| r5 | 12.741 | 20.738 | 53.268 / 43.364 |

2σ_rel of mean_dp0 = 0.0147; of hub band (k=0) = 0.0271 → ceil_2dp **0.03**.
2σ of noise = 0.217 dB → floor **0.5**.

### After-bake vs r1 (registered check)

Mean push: all r2–r5 "about as hard" (**PASS**). Noise: none ⚠ (**PASS**).
Bands: 19/20 similar; **r4 hub bar 8.519 vs r1 8.267 Pa = +3.05 %** labelled "stronger"
(**FAIL**). Per the rule: do not widen again. Kimball chose to bake 0.03 / 0.5 anyway
(option b: the mean is the verdict; bars stay a picture). Recorded, not re-opened.

Cases under `runs/stock_flow_repeats/r{1..5}/` (gitignored). Summary
`runs/stock_flow_repeats/summary.json`.

## Out of scope

Validation-rig CFD (5 mm / 1000 iters / frame). Optimizer campaign. Stock YAML / loft edits.
§28. 27.2b.
