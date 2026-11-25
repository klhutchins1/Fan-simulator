# Long-form review and maths tracking plan (2026-11-24)

Asked for by Kimball; written by Claude. Board tasks RV-0 to RV-5 in `docs/release/RELEASE_PLAN.md` point here.
Why the audit drifted and CI went red is recorded in
`docs/validation/audits/2026-11-24-audit-drift-forensics.md`.

## The problem in one paragraph

The project aims for correct maths first, but two of its three safety nets are off and the third is coarse.
The physics audit ledger drifted (5 CHANGED, 3 AFFECTED) and nothing fails on it. CI has never run pytest on
GitHub. Most numeric tests are wide bands (`tests/test_fan_bem.py:15` accepts Stock free delivery from 50 to 80 CFM),
so a 30 % change in the BEM would pass. Since 10-15, 229 commits touched `handoff/` 647 times and `docs/` 337 times,
but `fansim/cfd`, `optimize`, `geometry` and `propeller` about 30 times in all. The process now costs more than the
maths it protects.

## RV-0 Make the safety nets real (day CPU, 1–2 days)

See section 6 of the forensics file. Done when CI is green on master, `gate.py` and CI run the same checks, and
`audit_status.py` reads 33/33 PROVEN plus `latest_pp_file` registered.

## RV-1 Maths snapshot: CI fails when a number moves (day CPU)

- `tests/data/physics_snapshot.json`: a fixed set of designs and operating points with their outputs.
  - Designs: Stock v3, lt120 reference, UIUC GWS 5×4.3, plus a few edge cases (`tests/data/*_flat.json`).
  - Outputs: every BEM P–Q point, free delivery, shut-off, peak η; BEMT C_T / C_P / η over J; centrifugal and
    mixed-flow BEM; structural (stress, deflection, flutter, balance); acoustics proxies.
- `tests/test_physics_snapshot.py` compares at a tight tolerance. Regenerate with
  `scripts/physics_snapshot.py --write`.
- **Rule:** a commit that changes the snapshot names, in its message, the audit file that explains the change.
  Enforce it with a CI check on the diff.
- This is a regression pin, not a validation, so it judges no model. The tolerance (proposed: rel 1e-6 for pure
  maths, 1e-3 for anything through scipy root-finding) still goes in a short pre-registration before the first write,
  because it decides what counts as a change.
- The measured Stock comparison in the forensics file (section 3) is the first row of this.

## RV-2 Validation scoreboard: published-data numbers generated, not typed (day CPU)

- A test recomputes every published-data comparison the release claims: a12x25 vs Noctua, lt120 vs Tutar & Cam
  (TRENDS: +8.1 % at 6.85 Pa, +25.8 % at 13.71 Pa), and BEMT vs UIUC. It reads frozen CFD results and committed
  reference data.
- It writes `docs/validation/scoreboard.md`. R3.8 and the README quote that file.
- Commit one small, real OpenFOAM `postProcessing` set each for Stock and lt120 (results only, no mesh). CI can then
  test `parse_fan_metrics`, the flow report and the flow sign without Docker.

## RV-3 Long-form code review, module by module

Order (highest accuracy risk first):

1. `fansim/optimize/objectives.py` (`evaluate_candidate`, 486 lines)
2. `fansim/fan_bem.py`
3. `fansim/cfd/metrics.py`, `flow_report.py`, `flow_verdicts.py`
4. `fansim/geometry/blade.py`, `airfoil.py`
5. `fansim/propeller/bemt.py`, `polars.py`
6. `fansim/optimize/search_space.py`
7. `fansim/structural/*`, `fansim/acoustics/*`
8. the cockpit, last

Checklist for each module:

- Every equation has a cited source; units and signs are consistent.
- No failure is swallowed silently. A failure is either stamped into the result or raised.
- Every physical constant comes from `fansim/physics/air.py` or `fansim/cfd/metrics.py`.
- A numeric test exists (RV-1 snapshot or a direct test), not only a band or a source grep.
- Every public function is in the audit ledger or exempt.
- No function over about 150 lines without a reason.

Findings become GitHub issues labelled `math` (changes a number) or `review` (code health), kept apart from Cursor's
`ux` issues. grok's best use is independent re-derivation of the equations in steps 1–5.

Already found (2026-11-24; to file as issues):

- `objectives.py:316`: an exception in the BEM pre-screen is silently `pass`ed and the design goes on to CFD with no
  stamp. The surrogate pre-screen (line 339) stamps its error, so the two are inconsistent.
- `objectives.py:460`: a sanity-check crash becomes `[]`, which reads the same as "no warnings".
- The CFM factor is defined twice more: `optimize/meanline.py:20` and a literal `2118.882` at `multi_point.py:132`.
  `test_cfm_factor_is_single_source` checks only `fan_bem`.
- `tests/test_math_consistency.py:39` passes if a comment exists in the source. About 26 tests grep source files
  instead of testing behaviour.
- `tests/test_fan_bem.py:15`: Stock free CFM band 50–80. Pin it (RV-1).
- 252 `except Exception` blocks in `fansim/`: 25 in `fan_viz.py`, 18 in `midplane.py`, 14 in `objectives.py`.
- mypy covers 3 files (`pyproject.toml` `[tool.mypy] files`).

## RV-4 Script triage (128 scripts)

- 19 are referenced nowhere: `compare_sections`, `dedup_designs`, `design_uneven_spacing`, `_fit_a12x25_slices`,
  `overnight_wrapup`, `run_cror_optimization`, `run_feature_minmax`, `run_feature_study`, `run_spacing_study`,
  `run_stall_study`, `run_stator_vs_frame`, `run_tip_noise`, `run_tip_study`, `run_winglet_study`, `score_all_noise`,
  `screen_r3_cfd`, `_split_fan_tab_ui`, `test_reproducibility`, `what_helps`.
- 68 have no test.
- Sort each script into one of three groups:
  - **promote:** it produces a validation verdict, so its maths moves into `fansim/` with a test and a ledger unit
    (for example `prop_section_2d.py`, 1,676 lines; `fan_noise_curle.py` and `fan_noise_cv.py`, which rewrite the
    Curle sum that `acoustics.curle_dipole` already proves);
  - **keep:** an operational tool such as `gate.py`, `night_queue.py` or `stray_work.py`;
  - **archive:** move to `archive/scripts/` with a one-line reason.
- Rule from here on: no code that produces a verdict lives only in `scripts/`.
- Add the forensics script used on 2026-11-24 as `scripts/audit_forensics.py`, with a test. It names the first
  commit that changed each part of a drifted unit.

## RV-5 Speed and code health

- Fast suite about 45 min: profile with `pytest --durations=50`. Fused builds take about 13 s each, so use
  session-scoped fixtures and move repeat builds to `slow`.
- Split `evaluate_candidate` into stages (guards → pre-screens → geometry → CFD → scoring), each testable on its own.
- Break up the cockpit's long `bind`/`render` functions (`fan_tab_ui.py:44` is 1,540 lines) only when UX work
  touches them.
- Widen mypy one module at a time, starting with `fan_bem.py` and `cfd/metrics.py`.

## Process

- Until RV-0 to RV-2 are done: no new grok rounds or handoff bundles beyond re-derivations for RV-3.
- On the Windows PC: finish W1 (`scripts\stray_work.py` must list nothing) and push the missing grok handoffs,
  `research/` and the leads 23–48 pre-registrations.
