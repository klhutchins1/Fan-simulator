# Release plan: Fan Simulator v0.1.0 on GitHub

Owner: Kimball. Written by Claude, 2026-10-17. Rules for every agent are in [`AGENTS.md`](../../AGENTS.md).
The backlog behind this is in [`docs/roadmap.md`](../roadmap.md). This board is the *ordered* subset that gets us to
a release.

**Definition of done for v0.1.0 (Kimball, 2026-10-17):**
- every surface we ship is validated against published data, with a pre-registered tolerance;
- anything not validated is either fixed, hidden, or labelled "experimental, not validated" in both the UI and the
  README;
- no rig measurements are needed for v0.1.0. They come in v0.1.1.

Status legend: `ready`, `blocked (<id>)`, `in progress (<agent>, <date>)`, `paused (<agent>)` + **Resume** note,
`needs Kimball`, `done <commit>`.

CPU: `day` = light, any time except 4–9 PM. `night` = heavy, a Scheduled Task between 9 PM and 3:30 PM.

---

## The path (milestones in order)

| milestone | what it means | gate |
|---|---|---|
| **M0 Trustworthy flow card** | the card's rows measure what they claim and are mesh-robust | R0.1–R0.4 done |
| **M1 Axial validated** | the Fan tab's numbers match two independent published fans, and the optimizer explores the right space | R1.1–R1.6 done |
| **M2 Every other tab decided** | each of propeller, CROR, mixed-flow and volute is validated against published data, or hidden / labelled | R2.x gates |
| **M3 Releasable repo** | anyone can install it from GitHub and run it; the repo is clean, licensed and CI-tested | R3.1–R3.9 done |
| **M4 Release candidate** | a clean-clone install and test pass on Linux (grok) and Windows (Kimball), plus release notes and the tag | R4.1–R4.4 done |

M3 does not depend on M1 or M2, so Cursor can run it in parallel from day one.

---

## M0: Trustworthy flow card

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

## M1: Axial validated

- **R1.1 Second published axial case: lt120 (roadmap 25.7)**. Pre-registered:
  `docs/validation/audits/2026-10-18-lt120-validation-prereg.md`.
  - **R1.1a reference build + freeze + script.** Lane: Cursor. CPU: day. Status: `done 6f25583`.
    - Landed: `reference_build=True` skips hang only (clip stays on). Freeze STL + cylinder-cut 9/9 PASS, r=23 N/M, direction CONCLUSIVE. `scripts/validate_lt120.py` resumes and writes `runs/lt120/summary.json`. Night job `lt120-r11a` is queued (8 h). grok r21 C pre-check: clip-off 9/9 PASS; freeze blockers (QA-60) are closed on this freeze.
    - grok r22 B (2026-10-29, `docs/qa/notes/r22-B-lt120-freeze-recut.md`): committed `lt120.stl` re-cut at b3d5543: r=23 N/M, 9/9 PASS (worst chord −2.26 %, stagger 0.06°, camber 0.0002), identical to r21 S; all 5 QA-60 sub-items closed → **QA-60 closed**. Note for R1.1b: the frozen (clip-on) reference is 2.0–2.3 % under the table chord from r 41.6 mm out. Also `scripts/validate_lt120.py` calls `build_case` without being in `AXIAL_SCRIPTS`/`EXEMPT` (orientation guard test fails, QA-62); fix before using the night result.
  - **R1.1b verdict.** Lane: Claude. Status: `done` 2026-10-30: **TRENDS**.
    - +8.1 % at 6.85 Pa (pass), +25.8 % at 13.71 Pa (fail); the meshes agree within 3 %. Results are in the lt120 prereg.
    - CFD over-predicts loaded flow on this fan. The leading suspect is the unreported tip gap; testing it would be a new
      pre-registration.
    - The release wording is in that file, for R3.8 / R1.10.
    - **Tip-gap follow-up (2026-10-30, `2026-10-30-lt120-tip-gap-prereg.md`): G3, not explained.**
      - At 1.0 mm the 13.71 Pa point got worse (+28.9 %). At 1.5 mm it flipped to −9.6 % but was INCONCLUSIVE.
      - The point sits on the curve's knee, where steady CFD is sensitive. The release wording is updated in that file.
      - Loaded-point fidelity near the knee goes to the roadmap, not v0.1.0.
      - grok r23 A (2026-10-31, `docs/qa/notes/r23-A-lt120-knee.md`): 13.71 Pa / 60 CFM is **at the knee** (robust, 100 % of 5000 MC draws). The CFD has no plateau (it stays steep through 17.14 Pa), so the shape does not agree. Tutar & Cam's own CFD (CC BY 4.0, Figs. 8/9) shows the plateau but also misses 13.71 Pa in flow (≈ 41 cfm). QA-64: the lt120 part of "near free air … within 8 %" is 6.85 Pa at +8.1/+9.5 %.
      - grok r23 B (2026-10-31, `docs/qa/notes/r23-B-near-knee-warning-spec.md`, proposal only): R23-KNEE (unconverged OR φ ≤ 0.6 OR P ≥ 0.6 × BEM shut-off) gets 6 hits, 1 miss (lt120 13.71, converged) and 0 false flags; **needs more data**. Draft: K1 warning now, φ and P/shutoff report-only.
      - grok r24 B (2026-11-01, `docs/qa/notes/r24-B-qa64-wording.md`): "near free air … within 8 %" fails on lt120 (P/Pmax 0.20; +8.1 %); **use "within 10 %", lt120 "at its lowest measured load (6.85 Pa)"** (all numbers ≤ 9.5 %; frozen 0.5 mm gap). QA-64.
      - grok r24 C (2026-11-01, `docs/qa/notes/r24-C-k1-visibility.md`): K1 is **not** shown for a converged=False score (only in reject text). QA-65 (MED); patch `docs/qa/patches/r24-C-k1-visible.patch`.
      - grok r25 C (2026-11-02, `docs/qa/notes/r25-C-qa64-strings.md`): both audit lines (`2026-10-18-…:89`, `2026-10-30-…:69`) still say "near free air … within 8 %" on 9d0118f; QA-64 open until R1.10.
- **R1.2 Loaded branch and shut-off honesty (19.6 / 1.5)**. Lane: Cursor (docs and UI). CPU: day. Status: `ready`.
  - Shut-off is 20–21 Pa against 22.9 published, and steady RANS does not converge at 15–20 Pa.
  - Make sure the UI and README never quote a number above the validated range. Add a test that the P–Q display
    stops at the last converged point.
  - **QA-65 (grok r24 C; Claude reviewed 2026-11-01): adopt.** Status: `done c10c06b`. An Assess score whose loaded point did not converge shows no
    warning. Apply `docs/qa/patches/r24-C-k1-visible.patch` (the caption reads "⚠ loaded point did not settle (CFD unconverged):
    loaded CFM is uncertain"), with a test that a `converged=False` result shows it and a converged one does not. This is the
    near-knee rule's K1. The rest of r23 B stays a roadmap proposal.
    Landed (2026-11-04, `c10c06b`): r24-C caption + reason on Assess; r25-B tests and Optimize trials carry `converged`.
    `test_score_caption` 11 passed.
  - grok r25 B (2026-11-02, `docs/qa/notes/r25-B-qa65-adopted-review.md`): 9d0118f is board-only, the patch is **not applied** (`git apply --check` still passes); behaviour OK (only `converged is False` warns). **Holes:** Optimize trials never carry `converged`, no test. Add-on `docs/qa/patches/r25-B-qa65-test-and-trials.patch`.
  - grok r25b (2026-11-02, `docs/qa/notes/r25b-master-0635a18-recheck.md`): **still not on master 0635a18**: `r24-C-k1-visible.patch` still applies; unpatched master shows no warning for `converged=False`. r25-B add-on still applies (score_caption 11 passed on scratch, 9 on master). QA-65 open (MED).
  - grok r26 (2026-11-04, `docs/qa/notes/r26-qa66-qa65-recheck.md`): on bd6abdd **QA-65 verified 3/3, closable** (r24-C and r25-B reverse-apply; only `converged is False` warns; trials carry `converged`). Optional test: `docs/qa/patches/r26-B-qa65-trial-test.patch`.
- **R1.3 Optimizer space under wrap (27.7)**. Lane: grok data (round 14 Task C), Cursor implements, Claude reviews.
  CPU: day for the bounds, night for any re-find campaign. Status: `blocked (R1.7, R1.8)`. grok r14 C delivered 2026-10-17
  (`docs/qa/notes/optimizer-space-wrap-r14.md`; proposed bounds give 4.3 % refused). The refused share depends on the hub
  (R1.7) and the hang check (R1.8), so re-measure after both.
  grok r17 C (2026-10-19, `docs/qa/notes/r17-C-hang-refusals.md`): r14 P0 bounds with R1.7 + R1.8 give 2.0 % refused (Wilson ≤ 4.3 %), so the bounds stand. R1.8 alone gives 7.7 %, R1.7 alone 0.3 %.
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
- **R1.9 Small QA fixes**. Lane: Cursor. CPU: day. Status: `ready`. One branch, one test each:
  - QA-39: sort postProcessing time dirs numerically (`_pp_file`, `sanity.py`, `timing.py`, the objectives copy);
  - QA-40: no noise text in Simple mode when there is no Stock reference;
  - QA-41: `watch_parent` must treat a zombie or exited launcher as gone (not `os.kill(pid, 0)` alone on Linux);
  - QA-42: the Preview weight line names the material and infill ("11 g PLA+, 20 % infill");
  - QA-45: undersized cup hub gives the plain "hub radius too small" message.
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
- **R1.10 Release claims fixes (grok r21 A; QA-55/56/57/58).** Lane: Cursor. CPU: day. Status: `in progress (Cursor, 2026-11-04)` (G3).
  - Groups G1–G5 with exact wording: `docs/validation/audits/2026-10-29-review-r21-claims-and-validation.md`. One branch per
    group, each with a grep or UI test.
  - Release gate: 0 overstated and 0 unsupported claims. grok re-audits the release candidate.
  - G1 landed (`bf2ee37`): Assess compares with scored Stock at the same hose/material/refine, or omits the line.
    Never vs the datasheet. Stock vs itself is +0 %. Fast chunks 692+514+702. QA-56.
  - G2 landed (`8d06672`): noise row never judged; README "Noise outputs are not validated"; no bare dB(A) on
    model outputs (design list "SWL est.", print sheet labelled, Optimize caption). Related tests 25 passed.
    Fast chunks not run (peak window). Carries out R0.4 and R1.6. QA-55. Merge after 21:00 chunks. G3 next.
  - Claude review of `r110-g2` (8d06672, 2026-11-04): **OK to merge**. The noise row is `na` (never ✓/⚠); the README and
    Expert text match the ruled wording; dB(A) stays only on published values; the export print sheet says "not dB(A);
    not validated".
- **R1.11 Surrogate-guided Optimize runs no CFD (UI-31, HIGH).** Lane: Cursor. CPU: day. Status: `done 5611332`.
  - Claude confirmed 2026-11-01: the cockpit never passes `--verify-cfd` (`scripts/run_optimization.py:111,159`), so its
    labels and "verify" come from `synthetic_label()` (`fansim/optimize/surrogate_search.py:309`), a test formula.
  - For v0.1.0: hide the Surrogate-guided switch, or wire it to `--verify-cfd` and refuse to run without Docker. It must
    never rank designs with `synthetic_label`. Add a test that the cockpit's argv cannot reach the stub path.
  - The other tooltip findings (UI-32 … UI-38) belong to M3 polish. UI-33 (Optimize ignores the Design sliders) needs one
    sentence in the Optimize help.
  - Landed: switch hidden; `cockpit_optimization_argv` never passes `--surrogate-guided` even if state is on; CLI refuses
    `--surrogate-guided` without `--verify-cfd` or `--stub-labels` and stamps stub output "synthetic labels, not CFD";
    dead `opt_surrogate_guided` tooltip dropped. QA-62: `validate_lt120.py` is on `AXIAL_SCRIPTS`. Fast chunks 679+506+705
    passed (OCCT teardown exit only).
  - Claude review of `r111-hide-surrogate` (a9ca242, 2026-11-01): **OK to merge** for the cockpit. Close-out items above
    are done (`23704f5`).
  - grok r24 A (2026-11-01): still open on 23831da (switch renders; argv has no `--verify-cfd`).
  - grok r25 A (2026-11-02, `docs/qa/notes/r25-A-r111-branch-check.md`): on unmerged 237a094 UI-31 and QA-62 **fixed on branch (pending merge)**; master 9d0118f still open. CLI behaviour test still guard-only (`docs/qa/patches/r25-A-r111-cli-behaviour-test.patch`); new **QA-66** (MED): `--verify-cfd` still trains on `synthetic_label` DoE, `run_surrogate_search.py` adds `--stub-labels` silently. Merge conflicts in this file only.
  - grok r25b (2026-11-02, `docs/qa/notes/r25b-master-0635a18-recheck.md`): on master 0635a18 UI-31 and QA-62 **verified**. **Not closable:** CLI behaviour test still guard-only (r25-A patch: 7 passed on scratch, master 5); **QA-66 still open 0/3** (`--verify-cfd` DoE = `synthetic_label`, `surrogate_search.py:458,484`; `run_surrogate_search.py:26-27` adds `--stub-labels`; "stamps stub output" is stdout only, `run_optimization.py:179-180`, nothing on disk).
  - Claude review 2026-11-02: **QA-66 confirmed** in code. The cockpit fix stands (UI-31 verified), but the CLI
    still ranks with synthetic labels: `run_surrogate_guided` labels the DoE with `label_fn or synthetic_label` even under
    `--verify-cfd`, and falls back to `stub_verify` silently when Docker fails. To close R1.11:
    - under `--verify-cfd`, label the DoE with CFD too (or train only on real catalog rows), and **refuse** instead of
      falling back to the stub;
    - `--stub-labels` (and `run_surrogate_search.py`, which adds it silently) writes "synthetic labels, not CFD" into
      `surrogate_guided.json` itself, not only stdout;
    - apply grok's `docs/qa/patches/r25-A-r111-cli-behaviour-test.patch` (a behaviour test, not a grep).
    - If that is too much for v0.1.0, ship the surrogate-guided CLI as "developer only, experimental" in `--help` and
      the README, with the refusal still in place.
  - Claude review of `r111-qa66` (6c0b10e, 2026-11-03): **OK to merge**; 17/17 in `test_surrogate_guided.py` +
    `test_r111_cockpit_surrogate.py`. It closes the three QA-66 holes. Two small follow-ups, not blockers:
    - `--verify-cfd` with no catalog, or fewer than 8 rows, ends with an empty result ("need ≥2 cfm_free labels") after the
      Docker check. Refuse up front: "needs a catalog with ≥ 8 CFD rows (--surrogate-db)".
    - `seed_from_catalog` fills `cfm_load` (0.55 × free, when missing) and `efficiency` (always 0.2 × free) with made-up
      priors. The ranks use `cfm_free` only, so they are real, but stamp those two predictions "prior, not CFD" in the JSON,
      or drop them.
  - Landed (QA-66, 2026-11-04, `5611332`): `--verify-cfd` trains on catalog + CFD verify (no synthetic DoE), refuses
    missing Docker and a catalog with < 8 rows; `run_surrogate_search.py` refuses an ungated stub; JSON stamps
    `synthetic labels, not CFD` and catalog load/efficiency `prior, not CFD`. r25-A CLI behaviour tests. Fast chunks
    679+512+707 (OCCT teardown only). Review follow-ups included.
  - grok r26 (2026-11-04, `docs/qa/notes/r26-qa66-qa65-recheck.md`): on bd6abdd **QA-66 verified 5/5; r25-A CLI test covered; R1.11 closable.** New **QA-68** (LOW): CLI catalog refusal is an uncaught traceback, not exit 2; `docs/qa/patches/r26-A-qa68-catch-refusal.patch`.
  - QA-68 done (Claude, 2026-11-04, merge of `r26-qa68`): grok's patch. The catalog/Docker refusal exits 2 with the
    message; its test failed first (uncaught RuntimeError). Fast chunks 692+515+702 passed (OCCT teardown exit only).
- **R1.5 Structural and flutter labels**. Lane: Cursor. CPU: day. Status: `ready`.
  - The beam models are unvalidated on real blades (audit-05).
  - Label the structural and flutter outputs "estimate, not validated" in Simple and Expert, plus the README.
    Add a test that the label is present.
  - grok r21 A (2026-10-25): not landed at 5063a65 (README:27/62, `fan_tab_ui.py:889/911`, `figures.py:394`). QA-59.
- **R1.6 Acoustics claims audit**. Lane: Cursor. CPU: day. Status: `done 8d06672`.
  - Grep the UI, export README and docs for any absolute dB(A) claim. Everything must say relative or ranking only
    (audit-06).
  - Add a test that greps the UI copy for "dB(A)" without the word "relative".
  - grok r21 A (2026-10-25, `docs/qa/notes/r21-A-release-claims-audit.md`): 15 overstated / 5 unsupported claims across README, cockpit, docs; noise ones in QA-55 (incl. `data.py:205` "dBA", flow-card hint row, README:59). Also QA-56: Assess "vs stock free 60 CFM" is vs the datasheet.
  - Landed (`8d06672`, via R1.10 G2): UI grep requires published/relative/measured/estimate/not validated next to
    dB(A)/dBA on model outputs; user-measured "Noise dB(A)" and datasheet "published" stay.

## M2: Every other tab decided

The same three steps for each tab:
1. grok finds published data and checks its licence;
2. Claude pre-registers the comparison and tolerance;
3. a night campaign runs it.

Pass ships the tab as validated. Fail means fix it, or ship it labelled "experimental", or hide it, and that choice is
Kimball's.

- **R2.1 Propeller BEMT**: validated against UIUC (C_T PASS; SF static C_P −21 % is a known fail).
  - 2026-10-20: on APC SF, BEMT's C_T error grows with J (−13 % static, −15 / −20 / −29 % at J 0.20 / 0.30 / 0.43), most likely
    from the generic section. The release claim must say "±15 % at static; worse toward zero-thrust J on props with unknown
    sections" until grok r19 B shows the known-section number.
  - Lane: Cursor labels the C_P limit; Claude confirms the claims list. Status: `ready`.
  - **Claude confirmed 2026-10-29** (`docs/validation/audits/2026-10-29-review-r21-claims-and-validation.md`): grok r21 A stands. The fixes are grouped G1–G5 there; G1 (the Assess message compares with the datasheet) goes first.
- **R2.2 Propeller CFD: fix it** (Kimball 2026-10-17). FAIL, −44 % C_T against UIUC (audit-08).
  - Pre-registered diagnostic ladder: `docs/validation/audits/2026-10-17-prop-cfd-fix-prereg.md`. Read its rules
    before running anything; each rung's result picks the next rung.
  - **R2.2a 2-D section case (rung A).** Lane: Cursor. CPU: day (minutes per run; not 4–9 PM). Status: `done` (2026-10-20; verdict report to Claude).
  - **R2.2a′ rung A0: verify the 2-D setup on NACA 0012 at Re 6×10⁶ against Ladson.** Lane: Cursor. CPU: day (minutes). Status: `done 3fe5c60` (2026-10-26, `r22a-rung-a0`). Snappy **FAIL** (layers 0 %, y+ ~1100). Wake-cut C-grid **FAIL** with the wall resolved: C_d(0°) −2.4 % (inside ±20 %), C_l(5°) −14 %, C_l(10°) −44 % (need ±5 %). y+ mean 0.27 / 0.25 / 0.22. Table in the ladder prereg. Recorded, not re-tuned. (grok r20 B: C_d(0°) 0.00808, C_l(5°) 0.537, C_l(10°) 1.063; `docs/qa/r20/r20-B-ladson-naca0012-reference.csv`).
    - Work: `scripts/prop_section_2d.py` hard-codes the section (`naca4(0.04, 0.4, 0.06)`) and `RE`. Add `--section` (NACA 4-digit code), `--re`, `--alphas`, `--models` and `--tu`, keeping the defaults equal to today's rung A.
    - Then run `--section 0012 --re 6e6 --alphas 0 5 10 --models kOmegaSST`. Tripped data means fully turbulent, so use a normal freestream Tu of about 0.1 %, not the Ncrit-9 value.
    - Report the achieved y+ (max and mean on the airfoil), layer coverage % and surface cells. Write the result into `2026-10-17-prop-cfd-fix-prereg.md` and judge it against the rulings doc §1. Don't re-tune.
    - grok r22 C (2026-10-29, `docs/qa/notes/r22-C-a0b-alpha-bookkeeping.md`, code reading only): U, liftDir and dragDir all use the same α once (geometry not rotated); `coefficient.dat` Cd/Cl columns read correctly. No setup bug, so it does not explain the C_l −14 %/−44 %. Code-visible candidates: convergence (`residualControl {}`, last-20 % mean), 48 uniform cells per surface at the LE, 8c far field, fixed +x wake blocks.
    - Pre-registered in `docs/validation/audits/2026-10-20-rulings-r18-r19-rungA.md` §1. Same script, with only the section, Re and α changed.
    - Report the achieved y+ (max and mean), layer coverage % and surface cell count.
    - Pass: C_l ±5 % at 5° and 10°, C_d ±20 % at 0°.
  - **R2.2a″ rung A0c: last A0 attempt for v0.1.0.** Lane: Cursor. CPU: day (minutes; not 4–9 PM). Status: `ready`.
    - **Claude ruling 2026-11-06** (`docs/validation/audits/2026-11-06-ruling-rung-a0-cgrid.md`): the C-grid result is **INVALID as a judge of SST, not a FAIL of it**.
      - 0° and 5° are not converged (C_l(0°) swings −0.19…+0.22 in the tail).
      - The LE is about 2 cells across (48 uniform tangential cells; LE radius 1.6 mm).
      - There is a 3.7× cell jump foil→wake at the TE, normal growth is about 1.25, and the far field is at 8c.
    - Work: make the C-grid parameters CLI options (keep today's values as defaults), then run 0012 / Re 6e6 / SST / α 0 5 10 on a grid that meets the ruling's **grid-quality gate**:
      - ≥ 128 clustered cells per surface, LE and TE cells ≤ 0.1 % c, every adjacent-cell ratio ≤ 1.2;
      - normal growth ≤ 1.15, y+ max ≤ 1;
      - far field and wake ≥ 50c;
      - converged: C_l tail peak-to-peak ≤ 1 % (≤ 0.005 abs at 0°), |C_l(0°)| ≤ 0.01, iters up to 10 000;
      - one 2×-refined run at 10° that changes C_l ≤ 2 %.
    - Report the gate table and then the numbers. Pass windows are unchanged.
    - Outcomes (fixed): gate met + PASS → re-run rung A unchanged on this mesher and judge A1/A2. Anything else → the ladder closes for v0.1.0 (prop CFD stays "direction and bookkeeping only"), and the result is reported to Kimball.
  - **QA-51: the NeuralFoil prop backend doesn't converge on the TUD prop.** Lane: Cursor. Status: `ready`. Until fixed, the backend appears only in Expert, labelled "experimental".
    - Landed: `scripts/prop_section_2d.py`, fast-suite case build + y+ ≤ 1, 2-D SST vs SST-LM at Re 8×10⁴. At α 4° SST C_l is −19 % vs the grok r17 reference and SST-LM is −24 % (neither A1 nor A2). Table in the ladder prereg. R2.2c stays blocked until Claude rules.
    - New `scripts/prop_section_2d.py`: a 2-D OpenFOAM case of the prop builder's generic section (6 % thick,
      camber 0.04) at Re 8×10⁴, y+ ≤ 1, α 0–8°, with `kOmegaSST` and `kOmegaSSTLM`.
    - Compare with NeuralFoil at the same Re, and write `runs/prop_section_2d/summary.json` plus a table in the
      prereg doc.
    - Test: grid y+ ≤ 1 and the case builds (no solve) in the fast suite.
    - grok r17 A (2026-10-19, `docs/qa/notes/r17-A-reference-polars.md`, `docs/qa/r17/`): the reference at Re 8e4, α 4° is CERTAIN, C_l 0.855 [0.847, 0.863] and C_d 0.0201 (NeuralFoil + XFOIL, Ncrit 9). On the NASA E387 anchor the tools read about 8 % high at 1e5; Re 6e4 is UNUSABLE.
    - grok r20 B (2026-10-21, `docs/qa/notes/r20-B-ladson-naca0012-reference.md`): the rung A0 reference is Ladson TM-4074 (public domain), Re 6e6, M 0.15, tripped: C_d(0°) 0.00808 ± 0.0002, C_l(5°) 0.537, C_l(10°) 1.063. The bands are inside the ±5 % / ±20 % windows.
  - **R2.2b Advance-ratio sweep (rung B).** Status: `done` 2026-10-20. **B2 sectional:** CFD C_T −40 / −45 / −58 % at J
    0.20 / 0.30 / 0.43. BEMT on the same geometry is also −15 … −29 %, so the generic section is a shared limit, and
    "fixed" was amended (results section of the ladder prereg). Next: rung A (R2.2a) confirms the turbulence model, then
    rung C. Validation needs a prop with known sections (grok r19 A).
    - grok r20 C (2026-10-21, `docs/qa/r20/r20-C-tud-build-details.csv`): for the TUD prop, hub r 12.5 mm, flat boss, no spinner. The root transition from r 12.5 to about 29 mm is unspecified. The tip is square-cut. The rig is an upward open jet with a 50 mm nacelle of unstated length. The rotor-to-nozzle distance is stated as 0.5 m and also as 0.72 m.
    - Add `--j` to `scripts/audit_prop_cfd.py`: freestream U = J·n·D, at J 0.3 / 0.5 / 0.7, 6000 rpm, compared with
      kt1035/1036.
    - Launch as a Scheduled Task after 9 PM (AGENTS.md rule 2).
  - **R2.2c 3-D transition (rung C)** and **R2.2d domain size (rung D)**: `blocked (R2.2a″ A0c)`.
    - Claude ruled A, B and A0 (2026-10-20, 2026-11-06). C or D are unblocked only if A0c passes and the re-run of rung A then gives A1 or A2.
- **R2.3 CROR**: direction proof only.
  - Lane: grok data hunt for small counter-rotating fan or prop P–Q / thrust data. Status: `done (grok r15 hunt, 2026-10-17)`; see `docs/qa/notes/r15-data-hunt-cror-mixed-centrifugal.md`.
- **R2.3 CROR against Shigemitsu 2018** (CC BY 4.0, 40 mm). Pre-registered:
  `docs/validation/audits/2026-10-18-cror-centrifugal-validation-prereg.md`.
  - **R2.3a geometry freeze + case script.** Lane: Cursor. CPU: day for the build. Status: `ready`.
    - **Amended 2026-10-19 (§2):** S1 withdrawn (it was CFD vs CFD), replaced by S1′. Table 1 stagger is **from the rotation plane**. Camber NACA 4 % at 40 %; axial gap 4.9 mm. Now `ready` (grok r17 B delivered the data).
    - grok r17 B delivered 2026-10-19: `docs/qa/r17/r17-B-shigemitsu2018-digitised.csv` + `docs/qa/notes/r17-B-digitised-cror-centrifugal.md` (CC BY 4.0 confirmed). Only total P–Q is measured; the per-rotor data and η are CFD (QA-47). Stagger convention and camber are missing, so Claude rules before the freeze.
    - Follow step 0 exactly; fill missing values only by the stated rules.
    - Commit `validation/reference/cror_shigemitsu2018/geometry.json` + STL (that commit is the freeze), then
      `scripts/validate_cror_shigemitsu.py`.
  - **R2.3b runs.** Lane: night. Status: `blocked (R2.3a)`. Add the job to `night/queue.json`.
- **R2.4 Mixed-flow**: no published comparison.
  - grok r15: no small CC-licensed mixed-flow data. The 85 mm Treder rig is cite-only.
  - **Kimball 2026-10-17: label it experimental.** Lane: Cursor. CPU: day. Status: `ready`.
    - The Mixed tab title and its Assess/Optimize results say "Experimental: not validated against published data".
    - Same in the README feature list, and in exported READMEs for mixed-flow parts.
    - Test: the label appears on the tab and in the export README.
  - Lane: grok data hunt for mixed-flow fan curves at small diameter. Status: `done (grok r15 hunt, 2026-10-17)`; same note.
- **R2.5 Volute / centrifugal**: CFD is unconverged (17–23 % oscillation), a ±20 % proxy.
  - Lane: grok data hunt for a small centrifugal blower curve. Claude decides converge-or-label. Status: hunt `done (grok r15,
    2026-10-17)`, same note; converge-or-label still with Claude.
- **R2.5 Volute/centrifugal against EPJ WoC 180:02023** (60 mm). Pre-registered: same document.
  - **R2.5a convergence fix.** Lane: Cursor. CPU: day for short tests, night for full runs. Status: `ready`.
    - Get the existing volute case to ≤ 5 % peak-to-peak ΔP over the last 20 % of iterations (step 1).
    - Judge it **only** on convergence, never against the paper.
  - **R2.5b geometry freeze + case script.** Lane: Cursor. Status: `ready`.
    - **Amended 2026-10-19 (§3):** A1 at 0.4 / 0.7 / 1.0 × Q_max,meas; outlet-tube static pressure; log-spiral volute; gap t 0.5 mm. Now `ready` (grok r17 B delivered the data).
    - grok r17 B delivered 2026-10-19: `docs/qa/r17/r17-B-epj2018-02023-digitised.csv` (CC BY 4.0 confirmed; plastic wheel at 6000/9000/11000). No curve reaches free delivery (QA-48), so A1 needs restating. b2 = 3.86 mm, d1/d2 ≈ 0.5, no blade angles, no scaled volute drawing.
    - Step 0, then `validation/reference/volute_epj2018/geometry.json` and `scripts/validate_volute_epj.py`.
  - **R2.5c runs.** Lane: night. Status: `blocked (R2.5a, R2.5b)`.
- **R2.6 Centrifugal (no tab) and wind turbine (scaffold)**: excluded from v0.1.0.
  - Lane: Cursor makes sure neither is reachable from the cockpit or the README quickstart. Status: `ready`.

## M3: Releasable repo (parallel, mostly Cursor)

- **R3.1 Release export hygiene**. Lane: Cursor. CPU: day. Status: `ready`.
  - grok r20 E: the leak check is waiting for R3.1 to land (not run).
  - Extend `RELEASE_EXCLUDE` and `scripts/export_release.py` to drop `archive/`, `memory/`, `handoff/`,
    `docs/qa/screenshots`, `*.bak`, chat-recovery dumps and any `C:\Users\…` / `E:\…` paths.
  - Test: an export of master contains none of them, and the grep for user paths is empty.
- **R3.2 Packaging**. Lane: Cursor. CPU: day. Status: `ready`.
  - `pyproject.toml`: licence, authors, URLs, readme, classifiers, and a `[project.scripts]` entry point
    `fansim-cockpit = …` (wrapping `scripts/cockpit.py`).
  - Test: `uv build` works, and the installed entry point starts the server with `--help`.
- **R3.3 Install guide**. Lane: Cursor. CPU: day. Status: `done` (2026-10-20).
  - **QA-53 fixes (Cursor, small):** `done` on `r22a-rung-a0` (`5705d0e`): clone placeholder → "the GitHub URL"; cockpit URL `http://127.0.0.1:8080`; Assess "typically 30–40 min"; Linux Docker Engine link. Docker-not-installed row waits for R3.4.
    - `git clone <this-repo>` → the real URL, or "the GitHub URL" until the repo exists;
    - the port: the cockpit prints **8080**, not 9001;
    - Assess time "30–40 min", not "several minutes".
    - "Docker not running" troubleshooting comes with R3.4.
  - Landed: README **Install** for Windows and Linux (uv, Docker Desktop / Engine, `docker pull opencfd/openfoam-default:2406`, first Assess, WSL2 / Docker-not-running). Grok r15 can follow it word for word.
  - A README install section for Windows and Linux: uv, Docker Desktop / Engine, `docker pull opencfd/openfoam-default:2406`,
    the first Assess, and troubleshooting (WSL2 memory, Docker not running).
  - Test: grok round 15 follows it on a clean Linux box. r15: NOT RUN (no guide yet); `docs/qa/notes/r15-install-dry-run.md`.
  - grok r20 D (2026-10-21, `docs/qa/notes/r20-D-install-guide-dry-run.md`): the clean-Linux dry run WORKS (install, cockpit HTTP 200, UI test 6/6; Docker would-run). README fixes are needed (QA-53): port 8080 not 9001, Assess 30–40 min, the clone URL, a Linux Docker link, and a 'Docker not installed' row.
  - grok r22 A (2026-10-29): QA-53 verified at b3d5543 (cockpit prints http://127.0.0.1:8080/ = README:137; README:138 "30–40 min"; README:107 "the GitHub URL", interim). Docker-not-installed row still absent (R3.4).
- **R3.4 Docker/OpenFOAM readiness badge and first-run check (21.2g)**. Lane: Cursor. CPU: day. Status: `ready`.
  - The cockpit shows "CFD ready / Docker not running / image missing" with the fix in plain words.
- **R3.5 GitHub Actions CI**. Lane: Cursor. CPU: none (cloud). Status: `ready`.
  - Port `.github/workflows/ci.yml` for GitHub: ubuntu fast suite in 3 chunks, plus a Windows job for the fast
    geometry and export subset.
  - Widen ruff to the default rule set on changed files only.
- **R3.5b `pytest_chunks.py --all` stops after a green chunk on Windows**. Lane: Cursor. CPU: day. Status: `in progress (Claude, 2026-11-07)`.
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
- **R3.6 CHANGELOG, CONTRIBUTING, issue templates**. Lane: Cursor. CPU: day. Status: `ready`.
  - CONTRIBUTING points to `AGENTS.md`'s rules (pre-registration, tests first).
- **R3.7 Cockpit UI regression tests (29.2)**. Lane: Cursor writes, grok proposes cases. CPU: day. Status: `ready`.
  - Headless "we say X, we do Y" tests (`tests/test_ui_says_what_it_does.py`), at least one per tab that ships.
- **R3.8 Validation page**. Lane: Cursor drafts, Claude checks the numbers. CPU: day. Status: `blocked (M1, M2)`.
  - **Claude reviewed grok r21 B 2026-10-29: approved as the base.** Apply M1–M9 (M3: name the rig for 58.3 vs 59.8; M5: the link is `2026-10-12-cylinder-sections.md`). See the review doc. grok checks the final page.
  - `docs/VALIDATION.md`: per surface, what it was validated against, the tolerance, the result and the known limits.
    Every number links to its audit.
  - grok r21 B (2026-10-25): draft from the audits in `docs/qa/notes/r21-B-validation-draft.md` (13 surfaces + Known limits, 9 mismatches listed) for Cursor to adapt and Claude to check.
- **R3.9 Large files**. Lane: Cursor. CPU: day. Status: `ready`.
  - Decide per file between Git LFS, a release asset, or out of the export: `validation/reference/fan01/*.stl`
    (11 MB), `cad_model.zip` and `a12x25_impeller.stl`. Keep the CC-BY attribution in `THIRD_PARTY.md`.

## M4: Release candidate

- **R4.1 Clean-clone install and test on Linux**. Lane: grok. Status: `blocked (M3)`.
  - From the release export: follow README install, run the fast suite and one headless cockpit start.
- **R4.2 Windows install and one Assess**. Lane: Kimball, with Claude or Cursor on standby. CPU: night for the Assess.
  Status: `blocked (M3)`.
- **R4.3 Release notes v0.1.0**. Lane: Cursor drafts, Claude checks the claims. Status: `blocked (R3.8)`.
- **R4.4 Tag, publish and create the GitHub repo from the export**. Lane: Kimball. Status: `blocked (R4.1–R4.3)`.

---

## Budget notes

- **Claude** (runs out early in the week): R0.1, the R0.2 decision, R0.4, the R1.1 pre-registration, R1.4, the R2.x
  pre-registrations and the R3.8 number check. Everything else is Cursor or grok.
- **Cursor**: all of M3, the implementation halves of M0 and M1, and any labels.
- **grok**: round 14 (queued), then round 15 = the R2.3–R2.5 data hunts plus R3.3 install-guide dry run.
- **Night**: R1.1 lt120 campaign, R2.x campaigns, any optimizer re-find (R1.3).

---

## After v0.1.0 (parked; not release work)

- **grok lead 15: balance tolerance** (ISO 21940-11 + a phone four-run trim helper): `docs/qa/notes/balance-tolerance-proposal.md`.
- **grok lead 16: tap-test calibration** of `FDM_E_K` (phone f1 tap test): `docs/qa/notes/tap-test-calibration-proposal.md`.
  This needs printed parts, so it fits v0.1.1 (rig measurements) alongside 5.1/5.2.

