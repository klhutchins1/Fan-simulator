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
- **R0.4 Noise hint review (27.3c)**. Lane: Claude ruled, Cursor implements. CPU: day. Status: `ready` (ruling below).
  - **Ruling (Claude 2026-10-17):** stop *judging* the hint.
    - At fixed rpm and tip radius, L = 55 log U_tip + 10 log CFM differs between designs only through CFM. So
      "louder" just restates "moves more air", which is the standard fan-law result at equal pressure, and it can never
      show a design that is quieter for the same flow.
    - There is no validated design-sensitive noise estimate yet (FW-H needs transient CFD, roadmap 1.4).
    - Change: the noise row is never ✓/⚠/better. Expert shows the hint number with "scales with tip speed and airflow
      only; not a comparison of how quiet the design is". The README claims no noise comparison for v0.1.0.
    - Test: a design with more CFM gets no ⚠ on noise.
  - Cursor's tip-speed + CFM hint (`fansim/acoustics/tip_loading.py`) only varies with CFM, because rpm and tip
    radius are fixed for a12x25. As written, a fan that moves more air reads "louder".
  - Decide: keep it as Expert-only information, or replace it with a loading-based estimate. Test the candidates
    on the 15 runs.

## M1: Axial validated

- **R1.1 Second published axial case: lt120 (roadmap 25.7)**. Pre-registered:
  `docs/validation/audits/2026-10-18-lt120-validation-prereg.md`.
  - **R1.1a reference build + freeze + script.** Lane: Cursor. CPU: day. Status: `ready`.
    - `reference_build=True` skips only the print-hang check, with a test proving that.
    - Wrapped build from `docs/qa/benchmarks/lt120/geometry.json`, a cylinder-cut check against the table, and the
      freeze commit.
    - `scripts/validate_lt120.py` runs fixed back-pressure points at 6.85 / 13.71 / 14.69 / 17.14 Pa on meshes 5.8 and
      6.2 mm, resumes finished points, and writes `runs/lt120/summary.json`.
    - Then add the night job (about 6 h).
  - **R1.1b verdict.** Lane: Claude. Status: `blocked (R1.1a + night run)`.
- **R1.2 Loaded branch and shut-off honesty (19.6 / 1.5)**. Lane: Cursor (docs and UI). CPU: day. Status: `ready`.
  - Shut-off is 20–21 Pa against 22.9 published, and steady RANS does not converge at 15–20 Pa.
  - Make sure the UI and README never quote a number above the validated range. Add a test that the P–Q display
    stops at the last converged point.
- **R1.3 Optimizer space under wrap (27.7)**. Lane: grok data (round 14 Task C), Cursor implements, Claude reviews.
  CPU: day for the bounds, night for any re-find campaign. Status: `blocked (R1.7, R1.8)`. grok r14 C delivered 2026-10-17
  (`docs/qa/notes/optimizer-space-wrap-r14.md`; proposed bounds give 4.3 % refused). The refused share depends on the hub
  (R1.7) and the hang check (R1.8), so re-measure after both.
  grok r17 C (2026-10-19, `docs/qa/notes/r17-C-hang-refusals.md`): r14 P0 bounds with R1.7 + R1.8 give 2.0 % refused (Wilson ≤ 4.3 %), so the bounds stand. R1.8 alone gives 7.7 %, R1.7 alone 0.3 %.
- **R1.7 QA-44: the optimizer scores a different hub than Export prints**. Lane: Cursor. CPU: day. Status: `ready`.
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
  - **AMENDED 2026-10-19 (QA-46, `docs/validation/audits/2026-10-19-prereg-amendments-r17.md` §1): two stages.**
    - Stage 1, 1.75× designed, is a search prefilter (≤ 3 % false refusals).
    - Stage 2 measures the **built** solid's hang wherever the blade is built (Assess CFD build, Preview, Export) and
      refuses when it is > 2 mm.
    - Acceptance for stage 2: it matches grok's built values within 0.05 mm on 10 designs incl. S2_0269 (grok r18 A
      supplies them).
    - The single-factor acceptance below is recorded as FAIL (1/123), not re-tuned.
  Lane: Cursor (the rule is fixed below). CPU: day. Status: `ready` (Kimball 2026-10-17: **2 mm is for the printed blade**).
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
- **R1.4 Stock recipe gap**. Lane: Claude. CPU: day. Status: `ready`.
  - Stock v3 is 55.7 CFM against 58.3 for the reference STL (−4.5 %).
  - Either close the gap or state it in the UI and README as the recipe's known limit. Decide with Kimball.
- **R1.5 Structural and flutter labels**. Lane: Cursor. CPU: day. Status: `ready`.
  - The beam models are unvalidated on real blades (audit-05).
  - Label the structural and flutter outputs "estimate, not validated" in Simple and Expert, plus the README.
    Add a test that the label is present.
- **R1.6 Acoustics claims audit**. Lane: Cursor. CPU: day. Status: `ready`.
  - Grep the UI, export README and docs for any absolute dB(A) claim. Everything must say relative or ranking only
    (audit-06).
  - Add a test that greps the UI copy for "dB(A)" without the word "relative".

## M2: Every other tab decided

The same three steps for each tab:
1. grok finds published data and checks its licence;
2. Claude pre-registers the comparison and tolerance;
3. a night campaign runs it.

Pass ships the tab as validated. Fail means fix it, or ship it labelled "experimental", or hide it, and that choice is
Kimball's.

- **R2.1 Propeller BEMT**: validated against UIUC (C_T PASS; SF static C_P −21 % is a known fail).
  - Lane: Cursor labels the C_P limit; Claude confirms the claims list. Status: `ready`.
- **R2.2 Propeller CFD: fix it** (Kimball 2026-10-17). FAIL, −44 % C_T against UIUC (audit-08).
  - Pre-registered diagnostic ladder: `docs/validation/audits/2026-10-17-prop-cfd-fix-prereg.md`. Read its rules
    before running anything; each rung's result picks the next rung.
  - **R2.2a 2-D section case (rung A).** Lane: Cursor. CPU: day (minutes per run; not 4–9 PM). Status: `ready`.
    - New `scripts/prop_section_2d.py`: a 2-D OpenFOAM case of the prop builder's generic section (6 % thick,
      camber 0.04) at Re 8×10⁴, y+ ≤ 1, α 0–8°, with `kOmegaSST` and `kOmegaSSTLM`.
    - Compare with NeuralFoil at the same Re, and write `runs/prop_section_2d/summary.json` plus a table in the
      prereg doc.
    - Test: grid y+ ≤ 1 and the case builds (no solve) in the fast suite.
    - grok r17 A (2026-10-19, `docs/qa/notes/r17-A-reference-polars.md`, `docs/qa/r17/`): the reference at Re 8e4, α 4° is CERTAIN, C_l 0.855 [0.847, 0.863] and C_d 0.0201 (NeuralFoil + XFOIL, Ncrit 9). On the NASA E387 anchor the tools read about 8 % high at 1e5; Re 6e4 is UNUSABLE.
  - **R2.2b Advance-ratio sweep (rung B).** Status: `done` 2026-10-20. **B2 sectional:** CFD C_T −40 / −45 / −58 % at J
    0.20 / 0.30 / 0.43. BEMT on the same geometry is also −15 … −29 %, so the generic section is a shared limit, and
    "fixed" was amended (results section of the ladder prereg). Next: rung A (R2.2a) confirms the turbulence model, then
    rung C. Validation needs a prop with known sections (grok r19 A).
    - Add `--j` to `scripts/audit_prop_cfd.py`: freestream U = J·n·D, at J 0.3 / 0.5 / 0.7, 6000 rpm, compared with
      kt1035/1036.
    - Launch as a Scheduled Task after 9 PM (AGENTS.md rule 2).
  - **R2.2c 3-D transition (rung C)** and **R2.2d domain size (rung D)**: `blocked` on Claude's ruling from A and B.
    - Claude: read R2.2a and R2.2b's results against the prereg rules, record the ruling there, and unblock C or D.
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
  - Extend `RELEASE_EXCLUDE` and `scripts/export_release.py` to drop `archive/`, `memory/`, `handoff/`,
    `docs/qa/screenshots`, `*.bak`, chat-recovery dumps and any `C:\Users\…` / `E:\…` paths.
  - Test: an export of master contains none of them, and the grep for user paths is empty.
- **R3.2 Packaging**. Lane: Cursor. CPU: day. Status: `ready`.
  - `pyproject.toml`: licence, authors, URLs, readme, classifiers, and a `[project.scripts]` entry point
    `fansim-cockpit = …` (wrapping `scripts/cockpit.py`).
  - Test: `uv build` works, and the installed entry point starts the server with `--help`.
- **R3.3 Install guide**. Lane: Cursor. CPU: day. Status: `ready`.
  - A README install section for Windows and Linux: uv, Docker Desktop / Engine, `docker pull opencfd/openfoam-default:2406`,
    the first Assess, and troubleshooting (WSL2 memory, Docker not running).
  - Test: grok round 15 follows it on a clean Linux box. r15: NOT RUN (no guide yet); `docs/qa/notes/r15-install-dry-run.md`.
- **R3.4 Docker/OpenFOAM readiness badge and first-run check (21.2g)**. Lane: Cursor. CPU: day. Status: `ready`.
  - The cockpit shows "CFD ready / Docker not running / image missing" with the fix in plain words.
- **R3.5 GitHub Actions CI**. Lane: Cursor. CPU: none (cloud). Status: `ready`.
  - Port `.github/workflows/ci.yml` for GitHub: ubuntu fast suite in 3 chunks, plus a Windows job for the fast
    geometry and export subset.
  - Widen ruff to the default rule set on changed files only.
- **R3.5b `pytest_chunks.py --all` stops after a green chunk on Windows**. Lane: Cursor. CPU: day. Status: `ready`.
  - On 2026-10-17, chunk 1 printed "658 passed" and then pytest exited 127, the known OCCT teardown crash
    (`docs/validation/suite_baseline_2026-09-14.md`). `--all` returned and chunks 2–3 never ran.
  - Fix: run every chunk, then print one summary line per chunk.
  - A chunk whose pytest summary line says "N passed, 0 failed" but whose exit is non-zero is reported as
    "passed (teardown exit <rc>)", not as a failure. Any real failure still fails the run.
  - Test with a fake pytest command.
- **R3.6 CHANGELOG, CONTRIBUTING, issue templates**. Lane: Cursor. CPU: day. Status: `ready`.
  - CONTRIBUTING points to `AGENTS.md`'s rules (pre-registration, tests first).
- **R3.7 Cockpit UI regression tests (29.2)**. Lane: Cursor writes, grok proposes cases. CPU: day. Status: `ready`.
  - Headless "we say X, we do Y" tests (`tests/test_ui_says_what_it_does.py`), at least one per tab that ships.
- **R3.8 Validation page**. Lane: Cursor drafts, Claude checks the numbers. CPU: day. Status: `blocked (M1, M2)`.
  - `docs/VALIDATION.md`: per surface, what it was validated against, the tolerance, the result and the known limits.
    Every number links to its audit.
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
