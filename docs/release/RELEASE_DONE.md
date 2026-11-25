# Release plan: finished tasks

Moved here from [`RELEASE_PLAN.md`](RELEASE_PLAN.md) once nothing was left on them (AGENTS.md, "Claiming and finishing").
The text is unchanged. Newest moves are at the bottom.

- **R0.1 Push and plane fix (27.3e)**. Lane: Claude. CPU: day. Status: `done` (merged 2026-10-17; F1/F2 PASS).
  - The card's fixed planes cut through blade rows, so push tracked swirl rather than airflow. The planes are
    now blade-relative, `FLOW_REPORT_VERSION` 4, branch `push-planes-27-3e`.
  - Pre-registered checks F1–F4: `docs/validation/audits/2026-10-17-push-row-planes.md`.
  - Runner: `scripts/push_planes_checks.py`.

- **R0.2 Re-derive the card margins on v4 metrics**. Lane: Claude decides, Cursor implements. CPU: day.
  Status: `done` (2026-10-17: Kimball approved; `BAND_TOL` 0.06, `BAR_TOL` 0.12).
  - Asked: on v4, Stock's five-mesh 2σ is 5.7 % for the mean push and 12 % for the bars. Raise `BAND_TOL` 0.03 → 0.06
    and `BAR_TOL` 0.08 → 0.12?
  - The never-tighten rule and the 0.15 stop line both allow it. Data: the "Results of the fix" section of
    `2026-10-17-push-row-planes.md`.
  - The other margins (backflow, swirl, dead, tip) were never sized on mesh repeats. Do that as part of R0.3.
  - Re-run `scripts/stock_flow_repeats.py --analyze`, `scripts/stock_flow_mesh_repeats.py --analyze` and
    `scripts/design_flow_mesh_repeats.py --analyze` on v4 (no CFD).
  - Apply the 27.3b rule: 2σ, never tighten, stop lines 0.15 / 3 dB.
  - Kimball approves any constant change in `fansim/cfd/flow_verdicts.py`.

- **R0.3 "Too close to call" state (27.3d)**. Lane: Cursor, from Claude's spec. CPU: day.
  Status: `done` (merged 2026-10-19; night suite c1/c3 green, c2 had one stale test fixed and re-run green).
  - Landed: compared rows inside CLOSE (`√2 × 2σ`, never-tighten) show "Too close to call" (–). Synthetics C1/C2
    PASS. Audit: `docs/validation/audits/2026-10-17-too-close-to-call-prereg.md`.
  - **C3 FAIL:** 9604 direction and 9610 direction/push/spin still flip across m1–m5. Do we size CLOSE from those
    paired |Δ| instead, or accept the residual flips?
  - **Claude review 2026-10-17: approve the code.** The rule matches the prereg, and C3 was recorded honestly.
    Recommendation: accept the residual flips. Design-minus-Stock pairs scatter more than √2 × Stock's own 2σ (9610 push
    paired 2σ ≈ 10 %), but sizing CLOSE from them would hide 9610's real backflow, and any line flips for cases that
    sit on it. Merge once Kimball agrees; Cursor runs the fast suite first.

- **R0.4 Noise hint review (27.3c)**. Lane: Claude ruled, Cursor implements. CPU: day. Status: `done 8d06672`.
  - **Ruling (Claude 2026-10-17):** stop *judging* the hint.
    - At fixed rpm and tip radius, L = 55 log U_tip + 10 log CFM differs between designs only through CFM. So
      "louder" just restates "moves more air", which is the standard fan-law result at equal pressure, and it can never
      show a design that is quieter for the same flow.
    - There is no validated design-sensitive noise estimate yet (FW-H needs transient CFD, roadmap 1.4).
    - Change: the noise row is never ✓/⚠/better. Expert shows the hint number with "scales with tip speed and airflow
      only; not a comparison of how quiet the design is". The README claims no noise comparison for v0.1.0.
    - Test: a design with more CFM gets no ⚠ on noise.
  - Landed (`8d06672`, via R1.10 G2): noise row always `na` / not better; Expert keeps the hint number plus
    "Scales with tip speed and airflow only; this is not a comparison of how quiet the design is."
  - Cursor's tip-speed + CFM hint (`fansim/acoustics/tip_loading.py`) only varies with CFM, because rpm and tip
    radius are fixed for a12x25. As written, a fan that moves more air reads "louder".
  - Decide: keep it as Expert-only information, or replace it with a loading-based estimate. Test the candidates
    on the 15 runs.

- **R1.7 QA-44: the optimizer scores a different hub than Export prints**. Lane: Cursor. CPU: day. Status: `done` (2026-10-20; print hub, growth below the blades).
  - **Merged 027ebcb (2026-10-21).** CFD_VERSION 5 → 6, so saved scores read 'old solver' (disposable). Stock is unchanged (hub 16.5 mm ≥ 15), so every Stock reference and flow-card margin stands.
  - Landed: `mount_hub_params` now sets `blade_hub_z_mm += Δh/2` so the intake face stays put. Validate, Assess/optimizer CFD and Export all use that hub. Auto-hub CFD scores are stale (`CFD_VERSION` 6).
  - grok r16: the optimizer and Assess use the auto hub (often < 15 mm), while a12x25 Export and the cup Preview grow it
    to 15 mm, moving the clip plane by up to 3.3 mm. 54/141 refused designs would pass, and 171/291 hanging designs print
    with a different trailing edge from the one scored.
  - Fix: one hub height for validate, score and export. Apply `min_hub_height` in the search, with the growth below the
    blades (`blade_hub_z = +Δh/2`, grok's proposal).
  - Test: for grok's cases in `handoff/2026-10-17_from-qa-16-hang/data/`, the hub used by `validate_blade_params`, the
    CFD build and `do_export` is identical.
  - Old saved designs are disposable: mark them stale, don't migrate them.
  - grok r17 C: with the export hub (growth below), 174/300 r16 hubs grow (Δh ≤ 6.7 mm). Built/designed stays 1.77, and (i + ii) refuses 57/58 built > 2 mm with 0.4 % false refusals.

- **R1.8 QA-43: the 2 mm hang limit is checked on the designed blade; the built blade hangs about 1.75× more**.
  - **Next (Cursor, small):** `done` on `r22a-rung-a0` (`a42544e`): 4 feature designs in `tests/data/hub_hang_designs.json`; stage-2 test matches r18 within 0.05 mm and `build_impeller` refuses all four. Acceptance 10/10.
  - **Merged 027ebcb (2026-10-21).** Stage-2 acceptance 6/10 (feature-free); the 4 feature designs wait on grok r20 A's params, then Cursor adds them to `tests/test_hub_hang.py`. Claude review: approved (`docs/validation/audits/2026-10-20-rulings-r18-r19-rungA.md` §4).
  - **AMENDED 2026-10-19 (QA-46, `docs/validation/audits/2026-10-19-prereg-amendments-r17.md` §1): two stages.**
    - Stage 1, 1.75× designed, is a search prefilter (≤ 3 % false refusals).
    - Stage 2 measures the **built** solid's hang wherever the blade is built (Assess CFD build, Preview, Export) and
      refuses when it is > 2 mm.
    - Acceptance for stage 2: it matches grok's built values within 0.05 mm on 10 designs incl. S2_0269 (grok r18 A
      supplies them).
    - The single-factor acceptance below is recorded as FAIL (1/123), not re-tuned.
  Lane: Cursor (the rule is fixed below). CPU: day. Status: `done` (2026-10-20; two-stage hang).
    - Landed: stage 1 is 1.75× designed hang in `validate_blade_params`; stage 2 measures the built solid in `build_impeller_parts` (OCCT optimal bbox). Feature-free grok r18 A values match within 0.05 mm. Audit: `docs/validation/audits/2026-10-20-r18-hang-two-stage.md`. The single-factor miss (S2_0269 on the auto hub) stays recorded as FAIL.
    - grok r20 A (2026-10-21, `docs/qa/notes/r20-A-built-hang-recheck.md`): the 4 feature designs' JSON is in `docs/qa/r20/r20-A-feature-designs.json`. On master, all 10 match r18 to 0.0 mm. Stage 1 refuses 5/10, stage 2 refuses 6/10, and `build_impeller_parts` refuses all 6 built > 2 mm. QA-43/44/49 are verified fixed. Acceptance is 10/10 once the JSON is in `tests/test_hub_hang.py`.
  - Change: `validate_blade_params` refuses when `HANG_BUILT_FACTOR × blade_hang_below_hub_mm(params) > MAX_HANG_BELOW_HUB_MM`,
    with `HANG_BUILT_FACTOR = 1.75` in `fansim/geometry/blade.py`.
  - Comment the derivation: the chord fixed point refills the clipped chord, which drops the trailing edge by half the
    clip again, so 1 + ½ + ¼ = 1.75 after two iterations (grok r16, measured median 1.77, n = 140,
    `docs/qa/notes/hang-investigation-r16.md`).
  - The UI refusal text says the *printed* blade would hang X mm (= 1.75 × designed).
  - Pre-registered acceptance, on grok's r16 measured designs (`handoff/2026-10-17_from-qa-16-hang/data/`):
    - every design whose built hang is > 2 mm is refused;
    - at most 3 % of designs with built hang ≤ 2 mm are refused.
    - Record the result in a short audit note. Failures are recorded, not re-tuned.
  - Re-prove the geometry audit unit that owns `validate_blade_params`. Update `tests/test_hub_hang.py`.
  - Note: the 1.6× ratio was known when 2 mm was set (2026-10-13). grok now explains it (chord refill after the clip)
    and measures 1.75×.
  - grok r17 C heads-up (QA-46): on the r16 data the 1.75× rule misses S2_0269 (1.997 mm predicted, 2.25 mm built), so the "every built > 2 mm refused" rule is expected to FAIL by 1/123. 1.78× catches it but refuses 4.5 % (> 3 %). Claude to rule before the run.

- **R1.4 Stock recipe gap**. Lane: Cursor (decided). CPU: day. Status: `done` (2026-10-25, `r22a-rung-a0`).
  - Stock v3 is 55.7 CFM against 58.3 for the reference STL (−4.5 %).
  - **Kimball 2026-10-21: state the gap and ship.** No more recipe fitting for v0.1.0.
  - Landed: `STOCK_RECIPE_GAP` on the Stock Expert caption (`selected_trial === 100000`) and a README **Known limits** section. Simple mode is unchanged. `docs/VALIDATION.md` still waits on R3.8.
  - Wording, the same everywhere: "Stock is rebuilt from a parametric recipe and reads about 5 % less airflow than the
    real A12x25 shape (55.7 vs 58.3 CFM in the same test). Designs are compared with this Stock, so comparisons are
    like for like."
  - Where it goes:
    - the Stock entry's Expert detail in the cockpit (Simple mode shows nothing extra);
    - the README "Known limits" list;
    - `docs/VALIDATION.md` (R3.8), with links to `docs/validation/audits/2026-10-12-cylinder-sections.md` and the
      `wrapped-sections` audit numbers.
  - Test: the phrase "about 5 % less airflow than the real A12x25" appears in the README and in the Stock Expert text.
  - grok r21 A/B (2026-10-25): not landed at 5063a65 (README:52 still v2 −5.5 %; `fan_trials.py:354` lacks the phrase). The "`wrapped-sections` audit" link has no file; use `2026-10-12-cylinder-sections.md`. QA-59.
  - grok r22 A (2026-10-29, `docs/qa/notes/r22-A-ui-bug-pass.md`): landed at b3d5543: the phrase is in README:204 and renders in the Stock Expert caption (headless, :8080); Simple shows nothing extra. Verified.

- **R3.5b `pytest_chunks.py --all` stops after a green chunk on Windows**. Lane: Cursor. CPU: day. Status: `done 70ab65c`.
  - On 2026-10-17, chunk 1 printed "658 passed" and then pytest exited 127, the known OCCT teardown crash
    (`docs/validation/suite_baseline_2026-09-14.md`). `--all` returned and chunks 2–3 never ran.
  - Fix: run every chunk, then print one summary line per chunk.
  - A chunk whose pytest summary line says "N passed, 0 failed" but whose exit is non-zero is reported as
    "passed (teardown exit <rc>)", not as a failure. Any real failure still fails the run.
  - Test with a fake pytest command.
  - Also (Claude, 2026-11-04): `--chunk 3` with `--chunks 3` (indexes are 0-based) runs no tests and exits 0. Refuse an
    out-of-range `--chunk`, and fail any chunk that collects 0 tests.
  - Claude, 2026-11-07: fix on branch `r35b-chunks` (68f191c), 12 tests with a fake pytest. Night job `suite-r35b-chunks-all`
    is its merge gate. Merge `--no-ff` and mark done if it exits 0 with 3 verdict lines.
  - Claude, 2026-11-08: first real run (night 11-07) exit 1, correctly. All 3 chunks ran, teardown exits read as passed, and chunk 0 had one real failure: `test_guided_reaches_open_camber_and_blade_count`, a 1-in-680 flake from an unseeded TPE study (measured, not a product bug), fixed ffd8155. Gate rerun tonight on `r35b-chunks` d2a87cd.
  - Landed (70ab65c, 2026-11-09): rerun exit 0 with 3 verdict lines (717/555/653 passed). Nothing left. A job that uses `--all` or `--chunk` now exits 0 on a green suite, so `results.json` can be trusted without reading the log.

- **R2.7 Label pass for the four unvalidated surfaces (Kimball decision 2026-11-15).** Lane: Cursor. CPU: day.
  Status: `done 616aa33` (PR #71, closes #59).
  - Shared `fansim/cockpit/experimental.py` — **"Experimental: not validated against published data."** on Mixed /
    Volute / Prop CFD / CROR (tabs · experimental, tooltips, Assess/Optimize copy, export sidecars, README Known limits).
  - Prop BEMT stays the validated fast estimate (not stamped). `tests/test_r27_labels.py` + copy tests updated.
  - Earlier Claude branch notes (2026-11-17) and print-id OSError gate red were historical; recreate + merge on Linux
    remote completed 2026-11-25.

- **RV-4 Script triage.** Lane: Cursor. Status: `done 7c23df1` (PR #77).
  - 38 scripts archived; `scripts/audit_forensics.py` + tests; promote maths follow-ups #74–#76.
