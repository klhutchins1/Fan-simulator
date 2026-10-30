# r21 C: lt120 reference-build pre-check (R1.1a, no CFD)

QA bot, 2026-10-25. Master **5063a65**. Prereg **956b8ff** (`prereg_r6`, branch `prereg/round21`,
`qa_r21/PREREG_R21.md` §C, committed before any data). Script: `handoff/2026-10-25_from-qa-21/scripts/c_lt120.py`
(scratch, outside the repo; no source edits). Data: `handoff/2026-10-25_from-qa-21/data/r21-C-lt120-cut-check.csv` and
`handoff/2026-10-25_from-qa-21/data/c_lt120.json`. Wall time 163 s (`time.monotonic`).

## Verdict: cut check PASS on P (9/9 measurable radii); C as pre-registered: **NOT PASS** (freeze blockers below)

The wrapped build reproduces the table at every radius that can be cut, with a large margin. C does not pass
formally because the pre-registered rule counts the r = 23.0 mm station (N/M, inside the hub) as a blocker, and
`validation/reference/lt120/` does not exist yet. Both are decisions for Cursor and Claude, not builder faults.

## Exactly how the builder was called

```python
base = load_blade_params("docs/qa/benchmarks/lt120/fansim_params.json")
P  = dataclasses.replace(base, section_wrap="cylinder", clip_below_hub=False)   # primary
Pc = dataclasses.replace(base, section_wrap="cylinder")                          # clip on (as the json ships)
validate_blade_params(Pc)        # -> refused (recorded only)
validate_blade_params(P)         # -> accepted
imp = build_impeller(P)          # shipping path; export STL
measure_sections(stl, [r/60 for r in table radii], tip_radius_mm=60)
```

- P: `clip_below_hub=False` turns off the hang check **and** the hub-face clip and the clip correction
  (`correct_clipped_sections`). Chord realisation (`prepare_loft_chords`) still runs.
- S (report-only): `build_impeller(Pc)` with clip on, with `validate_blade_params` patched to run the original check on a
  clip-off copy and `_refuse_if_built_hang_past_limit` set to a no-op. So it is the shipping build minus only the hang
  checks. **Deviation from the prereg:** S was built and cut as the full impeller, not blade-only. That makes no
  difference to the cut at r ≥ 26.7 mm, which is outside the hub.
- Reference reading `*_ref`: the table station, wrapped at r, with no lean or sweep, read by `_measure_loop` (as
  `tests/test_hub_hang.py::_analytic`).
- Gate (the builder's own, `tests/test_hub_hang.py:155-157`): chord within 3 % of the table; camber within ±0.005 and
  stagger within ±1.5° of `_ref`.

## Per-radius result, P (primary)

| r mm | blades | chord meas / table | err | stagger meas / ref (table) | err | camber meas / ref | err | verdict |
|---|---|---|---|---|---|---|---|---|
| 23.0 | 0 | — / 18.6 | — | — (39.9) | — | — | — | **N/M** (inside 25 mm hub) |
| 26.7 | 7 | 21.18 / 21.2 | −0.09 % | 40.19 / 40.19 (39.7) | +0.00° | 0.0292 / 0.0294 | −0.0002 | PASS |
| 30.4 | 7 | 23.59 / 23.6 | −0.06 % | 39.97 / 39.97 (39.5) | +0.00° | 0.0299 / 0.0299 | +0.0000 | PASS |
| 34.2 | 7 | 26.21 / 26.2 | +0.03 % | 39.74 / 39.76 (39.3) | −0.01° | 0.0307 / 0.0307 | +0.0000 | PASS |
| 37.9 | 7 | 28.88 / 28.9 | −0.07 % | 39.35 / 39.35 (38.9) | +0.01° | 0.0307 / 0.0307 | −0.0001 | PASS |
| 41.6 | 7 | 31.59 / 31.6 | −0.03 % | 39.03 / 39.04 (38.6) | −0.01° | 0.0309 / 0.0315 | −0.0006 | PASS |
| 45.3 | 7 | 34.19 / 34.2 | −0.03 % | 38.63 / 38.64 (38.2) | −0.01° | 0.0318 / 0.0317 | +0.0001 | PASS |
| 49.1 | 7 | 36.57 / 36.6 | −0.09 % | 38.12 / 38.14 (37.7) | −0.02° | 0.0321 / 0.0321 | +0.0000 | PASS |
| 52.8 | 7 | 39.06 / 39.1 | −0.10 % | 37.41 / 37.44 (37.0) | −0.03° | 0.0322 / 0.0321 | +0.0001 | PASS |
| 56.5 | 7 | 41.56 / 41.6 | −0.11 % | 36.50 / 36.44 (36.0) | +0.06° | 0.0321 / 0.0321 | −0.0001 | PASS |

The worst errors are 0.11 % chord (gate 3 %), 0.06° stagger (gate 1.5°) and 0.0006 camber (gate 0.005).
`omega_sign` is +1 at every radius.

**Estimator bias (report-only, ref − table):**
- camber reads −0.0079 to −0.0106 below the table's 0.04: the wrapped section read by the estimator gives about 0.030;
- stagger reads +0.44° to +0.49° above the table setting angle.

Both biases are the same on the built blade and on `_ref`, so they come from the estimator, not the build. Any
claim of "matches the table's camber 0.04 / setting angle" must be made against `_ref`, not the raw readout.

**Against the old `built_vs_table.json`** (pre-chord-realisation build): chord was −3 % to −13 % short outboard, with
stagger drifting to −0.75°. Chord realisation closes that gap to ≤ 0.11 %.

## S (report-only): clip on, hang checks bypassed

- 9/9 measurable radii PASS, and r 23.0 is N/M.
- S is **materially shorter in chord outboard**: P/S chord +0.8 % at 34.2 mm, rising to +2.2 % at 56.5 mm. S chord
  error vs the table is −2.26 % at worst, inside the 3 % gate but using most of it. The hub-face clip trims the outer
  trailing edges, because the blade hangs 8.6 mm below the face before the clip. The clip correction restores camber and
  stagger, but not chord.
- One watertight solid, 1 body, rmax 60.0 mm, direction CONCLUSIVE (ω +1).

P differs from S by less than the gate at every radius, so the "P ≠ S beyond gate" blocker is **no**. But they are
different blades (≈2 % chord outboard, and the trailing edge is cut flat at the hub face). The prereg says "which
is the reference" must be stated. P is the one that matches the paper's table.

## Freeze blockers (each yes/no, as pre-registered)

| blocker | status | detail |
|---|---|---|
| any radius FAIL | **no** | 0 FAIL on P or S |
| any radius N/M | **yes** | r 23.0 mm: the table's first station sits at r0 = hub 25 − root_embed 2 = 23 mm, inside the hub. `source.md` notes the table radii (23.0–56.5) do not match the stated annulus (25–60). Proposal: freeze with r 23.0 recorded as "embedded root station, not cuttable", or remap the table onto 25–60 (a geometry decision for Claude). |
| no `reference_build` path | **yes (known)** | master 5063a65 has no `reference_build`. `clip_below_hub=False` is the only route, and it also drops the clip and the clip correction, not "only the hang check" as R1.1a specifies. |
| P ≠ S beyond the gate | no | max 2.2 % chord; within the 3 % gate (see above) |
| one watertight solid, 7 blades | no (OK) | P: 1 solid, watertight, 1 body, 7 blades at every cut radius, rmax 60.0 mm, volume 45 931 mm³ |
| direction proof | no (OK) | CONCLUSIVE, ω_sign +1 (P and S) |
| hang values | reported | designed hang 4.76 mm; P built hang 4.82 mm against the clip-on hub face (built/designed 1.01); with clip on, `validate_blade_params` refuses: "the printed blade would hang 8.3 mm below the hub (limit 2 mm)" (1.75 × 4.76); S unclipped built hang 8.59 mm |
| `validation/reference/lt120/` absent | **yes** | not on master (only `docs/qa/benchmarks/lt120/`) |

Other observations (not blockers):
- P blades overhang the hub's axial faces from r ≈ 30.7 mm outward, 4.8 mm below and 4.5 mm above (hub z −7.47 to
  +7.96 mm). No blade material sits at r < 25 mm outside the hub, so there are no exposed roots. Whatever the CFD rig
  puts behind the hub (spinner, motor face or nothing) has to be frozen with it. The paper's hub length is not reported.
- From 56.5 mm out to the 60 mm tip the builder holds or extrapolates the last table station (r_frac 0.905 → 1.0). That
  extrapolation must be recorded in the freeze.
- S's hub top sits at z +16.2 mm, against +12.4 mm on P: the clip-on build moves the hub. This is report-only.

## Proposals (code ideas only; not done)

1. Add `reference_build=True` (R1.1a): skip `validate_blade_params`' hang test and `_refuse_if_built_hang_past_limit`
   only, and decide explicitly whether the hub-face clip applies. For lt120, "no motor face" argues for clip **off**,
   which is P.
2. Freeze P's STL in `validation/reference/lt120/` with its params, the table→r mapping (r 23 embedded) and the
   tip extrapolation stated in `geometry.json`.
3. Add a test that cuts the frozen STL at the 9 cuttable radii against `_ref` using the gate above.
