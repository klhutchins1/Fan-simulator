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

## Work outside the repo: rescue task (Claude, 2026-11-15; for Cursor and Kimball)

- **W1 Get every stranded piece into the repo.** Lane: Cursor (the work is Cursor's; Claude was not allowed to commit
  another agent's work, AGENTS.md rule 6). CPU: none. Status: `ready`. Do it before new work.
  - Rules for this from now on: AGENTS.md "Where work lives". Check: `scripts/stray_work.py` must list nothing.
  - **`T:/Projects/fansim-merge-master`, branch `stock-outline`:** 17 commits not on GitHub (outline prereg attempts,
    grok session notes, a "four grok sessions every day" rule), still active on 2026-11-15 (uncommitted
    `airfoil.py`, `blade.py`, `outline_z.py`, `outline_le_face.py`, new tests). Commit, push, add a board task. Edits
    to the 11-06 A0 ruling and the print prereg after their data need dated amendments instead (rule 1).
  - **`T:/Projects/fansim-a0c-wake`, branch `r22a-wake-aspect`:** about 500 uncommitted lines in
    `scripts/prop_section_2d.py` and its test since 2026-11-13; the branch has no commits and no remote. This is the fix
    the held A0c night job (`r22a-a0c-gate`) waits for.
  - **Main checkout `T:/Projects/Fan Simulator`:** on branch `r111-hide-surrogate` instead of master, with about 414
    untracked files and 325 uncommitted lines in the board and `QA_REVIEW.md`:
    - grok handoffs `handoff/2026-11-01…11-15_from-qa-*` (about 250 files) and 61 files under `docs/qa/`;
    - `research/` (leads tracker and prototypes for leads 23–48, 2.6 MB incl. STL/3MF/WAV made from our code; the
      only licence file is an Apache-2.0 wheel licence) and `qa_research_leads*/PREREG_*.md`;
    - `HANDOFF_TO_CURSOR.md` (11-09 "DO FIRST" QA list incl. QA-73 HIGH) and about 20 `.bak` copies (now gitignored).
    - **The leads 23–48 pre-registrations are not valid yet.** Each `PREREG_COMMIT.txt` names a commit in grok's own
      sandbox (e.g. a114efd); none of them exists in this repo. Commit them, and judge those leads as
      not-pre-registered unless grok's bundle proves the dates.
    - Then put the checkout back on clean `master` (AGENTS.md "Where work lives" 2).
  - **`T:/Projects/fansim-p1-glyphs`:** 23 untracked files (older copies of the research/handoff files above, plus
    `docs/qa/patches/{export-fit-coupon,layer-dropout,manifold-fuse}.patch` and `scripts/export_print_session_1.py`).
    Keep what the main-checkout copy lacks, then remove the worktree.
  - **`T:/Projects/fansim-r110-g2-merge`:** detached, one merge commit 48c1571 on no branch. Push as a branch or drop.
  - Next grok round: its `CLAUDE_TO_QA.md` must ask for the return as a `from-qa.bundle` (AGENTS.md "Where work
    lives" 6).
  - About 44 loose October debug scripts and logs sit in `T:/Projects` itself (`dbg_*.py`, `*.log`). They are outside
    any repo; Kimball can delete them.
- Cleaned up 2026-11-15 with Kimball's yes: 24 merged, clean worktrees and 19 `tmpcache_*` folders (branches kept).
  `fansim-r283-print-id` is empty but locked by a running program; delete it after a reboot.

## The path (milestones in order)

| milestone | what it means | gate |
|---|---|---|
| **M0 Trustworthy flow card** | the card's rows measure what they claim and are mesh-robust | R0.1–R0.4 done |
| **M1 Axial validated** | the Fan tab's numbers match two independent published fans, and the optimizer explores the right space | R1.1–R1.6 done |
| **M2 Every other tab decided** | each of propeller, CROR, mixed-flow and volute is validated against published data, or hidden / labelled | R2.x gates |
| **M3 Releasable repo** | anyone can install it from GitHub and run it; the repo is clean, licensed and CI-tested | R3.1–R3.9 done |
| **M4 Release candidate** | a clean-clone install and test pass on Linux (grok) and Windows (Kimball), plus release notes and the tag | R4.1–R4.4 done |

### Decision (Kimball, 2026-11-15): ship v0.1.0 with four surfaces labelled, not validated

**Propeller CFD, volute, mixed-flow and CROR ship as "Experimental: not validated against published data".** Their
validation moves to v0.1.1. This is the "hidden or labelled" branch of the definition of done above; it needs no new
pre-registration, and no result in any of the four is re-judged. What is validated stays as it is: the axial Fan tab
(M0, M1) and the propeller **BEMT** fast estimate (R2.1, UIUC C_T PASS).

Why: since 2026-10-17 the night queue ran CFD on 3 of about 30 nights, and each validation try on these four ended
FAIL or not-converged (prop CFD −44 %, A0c diverged, volute relaxation sweep none/none). The pre-registered rules
already allowed stopping; this makes it the plan.

**Frozen for v0.1.0 (no more work, no night jobs):** R2.2a″ A0c and R2.2c/d, R2.3a/b (CROR vs Shigemitsu), R2.4,
R2.5a transient, R2.5b/c (volute vs EPJ). Their data, preregs and branches stay as they are for v0.1.1. Uncommitted
work for them (`fansim-a0c-wake`) is still committed and pushed under W1, so it is not lost, but it no longer blocks
anything.

**Release path from here (this is the whole list; add to it only with a reason):**
1. **R1.3** optimizer bounds under wrap. Last open M1 task.
2. **R2.7** label pass (below). Closes M2.
3. **R3.8** validation page: what is validated, against what, with which tolerance; the four labelled surfaces listed
   as not validated.
4. **R4.1** clean-clone install and test on Linux (grok), plus Kimball's Windows install.
5. **R4.3** release notes v0.1.0.
6. **R4.4** tag and publish.

Night CPU is now for gate suites and any R1.3 re-find campaign only.

- **UX-1 Simple/Expert cockpit polish (GitHub #1–#20).** Lane: Cursor. CPU: day (UI copy + unit tests; not 4–9 PM heavy). Status: `in progress (Cursor, 2026-11-24)`.
  - Opened from a live Linux cockpit walk + three review agents (2026-11-24). Issues: https://github.com/klhutchins1/Fan-simulator/issues?q=is%3Aissue+label%3Aux
  - Branch `cursor/ux-simple-mode-2026-11-24`: issues #1–#20 addressed in code (tests for High + related copy). Gate when ready: `scripts/gate.py cursor/ux-simple-mode-2026-11-24` (not during 4–9 PM).

M3 does not depend on M1 or M2, so Cursor can run it in parallel from day one.

## Work order (Claude review 2026-11-09; Kimball approved). SUPERSEDED 2026-11-15 by the decision above: steps 2 and 3 are frozen

Why: from 2026-10-17 to 2026-11-08 the night queue ran on 7 nights, and 13 of its 16 jobs were test suites, not CFD.
The tasks that unblock CFD validation sat `ready` behind wording fixes. So accuracy work goes first (AGENTS.md rule 9).

1. **Finish R1.10 as one batch.** G5 plus R1.2, R1.5 and R1.9 on one branch with one gate. No more one-branch-per-group.
2. **R2.2a″ A0c** (minutes of day CPU). It decides whether propeller CFD rungs C and D run or the tab is labelled.
3. **R2.5a** volute convergence fix, then **R2.3a** and **R2.5b** geometry freezes. Each one ends by adding a CFD job to
   `night/queue.json` (R2.3b, R2.5c): that is the point of doing them first.
4. **R1.3** optimizer bounds under wrap (now `ready`).
5. **M3 packaging** (R3.1, R3.2, R3.4–R3.9) fills any time the steps above are waiting on a night run.
   **P1** (engraved print-id, section below) goes ahead of M3: it is the only code blocking Kimball's first print.
6. grok: after round 27, one re-derivation or bug-hunt round per CFD result, and the full claims audit at the release
   candidate. No routine re-check rounds.

Merge gates run the same day with `scripts/gate.py <branch>` (lands with branch `process-tools`); nights are for CFD.

---

## Print session 1 (Kimball 2026-11-09; runs beside the release work)

Goal: print Stock v3 once and learn what works: fit, shape, the engraved ID and the test routine. Kimball has a
laser tach and a phone. No airflow meter. Rules and pass/fail are pre-registered in
`docs/validation/audits/2026-11-09-first-print-tach-phone-prereg.md` (T1–T6). Only Stock v3 is printed; no
optimizer candidate. This does not change the v0.1.0 definition of done.

- **P1 Engraved print-id on the hub (roadmap 28.3).** Lane: Cursor. CPU: day (a few geometry builds; not 4–9 PM).
  Status: `done 2bfde35`. Grok r28 ingested; QA-73 HIGH (mirror), QA-74 depth, QA-75 6=G, QA-76 one-cut, QA-78 skip-copy,
  QA-79 hub-face. Merge gate 750/521/683. Still open: QA-77 lands. Prints: H7MQ8 Stock T1–T6 (PLA+, 0.6 mm, **27.41 g**,
  T3 FAIL → P6); E0MWW t9002 extra. Live mark: cap 5.0 mm, stroke 0.9 mm, band r 11.5–16.5.
  - Follow `docs/qa/notes/print-id-mark-spec-r10.md` (P6 addendum): +Z hub top, strokes engraved 0.5 mm deep, cap height 5.0 mm,
    stroke width 0.9 mm, band r 11.5–16.5 mm, 5 characters (the 4-character code plus its check digit), read along
    the arc.
  - Draw the Crockford characters from line segments defined in code (no system font), fuse them, and make **one**
    cut on the mounted print solid. Export only: the scored and CFD geometry never carries the mark.
  - If the flat ring on a design is too narrow, skip the cut and keep the Sharpie line in the README; say so.
  - Tests: after the cut there is 1 watertight solid; removed volume is within 10 % of stroke area × 0.5 mm; the
    mount gauge reads the same as before the cut; every one of the 32 characters has a segment definition; the
    engraved code equals the code in the README and `*_print_fit.json`.
  - Also put the predicted weight (material, infill) in the export README, as Preview shows it (check T2).
  - README states: "ID engraving removes about 2 % of the hub face; its effect on airflow was not simulated."
- **P2 Recording tool.** Lane: Claude. Status: `done f60d234` (merged 2026-11-13; night gate green 2026-11-09): branch `print-session-prep`
  (`bd6b12e`), `scripts/analyze_fan_recording.py` + `validation/recording.py`, 12 tests. Gate: night job
  `suite-print-session-prep-all`. Merge if green.
- **P3 Export the print.** Lane: Cursor. Status: `done` 2026-11-09. H7MQ8 Stock v3
  (`exports/H7MQ8_a12x25_stock_reference_20261109-220053.stl`); E0MWW t9002 extra. Material PLA+, 0.6 mm nozzle.
- **P4 The session.** Lane: Kimball. Status: `in progress (Kimball, 2026-11-11)`. T2 27.41 g record-only; T3 FAIL → P6.
  T1 FAIL: H7MQ8 pad tips 36.55 mm in the file (caliper 36.21 mm) will not seat. Still open: T4 tach/phone, T5 12 V rpm, T6 bag. Keep WAV/photos in `validation/prints/H7MQ8/`.
- **P4a Hub opening.** Lane: Cursor. Status: `done 0beb057`. Branch `hub-opening-3725` (0beb057 is on master; checked 2026-11-16).
  Pad tips back on the 37.25 mm circle (the 2026-08-31 opening and the reference STL). `cavity_dia_mm` stays 37.25. Protrude 0.7 → 0.35, equal to the clearance. Wrap, loft, and Stock YAML untouched. Layout tests passed. Fit coupon, no blades: `exports/hub_fit_37.25mm_20261111-215225.stl` (also copied beside the other prints). 6 mm ring, pad tips 37.25 mm, 1.96 cm³. Kimball 2026-11-12: that ring fits the motor better than H7MQ8 and E0MWW; he will sand those two. Selecting A12x25 uses this pad circle (37.25 mm). The class default no longer sticks the pads in 0.7 mm. T1 stays open until a full impeller with this opening is on the frame.
- **N1 Night runner visibility (Claude, 2026-11-16): `done` (merge of `night-visibility`, gate 707/654/729).** On 11-15 a queued job
  did not run: the runner fell back to a week-old local master without saying so. Now `runs/night/<date>/runner.log` records the
  master it followed and why ("FETCH FAILED" if the fetch failed), and `morning_check` reports "APPLY FAILED/SKIPPED" in
  STATUS.md. Read `runner.log` first if a queued job did not run. Cause of the failed fetch is still unconfirmed.
- **P5 Write up.** Lane: Claude or Cursor. Status: `blocked (P4)`. Fill the Results table in the pre-registration
  (nothing above it is edited) and put each failed check on this board as its own task.
- **P6 Enlarge print-id glyphs (T3 FAIL / QA-80).** Lane: Cursor. CPU: day. Status: `done 2bfde35` (code); T3 coupon **needs Kimball**.
  H7MQ8 (Stock v3, PLA+, 0.6 mm nozzle, 27.41 g): 3.2 mm cap / 0.6 mm stroke is too small to read at arm's length.
  Raise cap and stroke a little. Proposal: cap **5.0 mm**, stroke **0.9 mm**, advance **3.6 mm**, band r **11.5–16.5**
  (`print_id.py` + r10 mark-spec). Depth stays 0.5 mm. Keep ≥1 mm from the bore and rim. Widen the cell with the
  stroke so QA-77 lands do not get worse.
  Tests first: glyphs still distinct; 1 watertight solid; K7 cup unchanged. Prove T3 on a **hub-face coupon**, not a
  full impeller (prereg T3-fail path).
  Balance: extra recess ~0.02 g at r ~14 mm. Even if the mark were fully one-sided that is ~0.3 g·mm, under ordinary
  blade print scatter (lead 15: 1.7–2.4 g·mm).
  - Landed `2bfde35`: constants 5.0 / 0.9 / 3.6; sheet "about 2 %"; coupon script `scripts/export_id_coupon.py`.
    Glyph tests 25 passed. **needs Kimball:** print `exports/H7MQ8_id_coupon_20261111-190250.stl`, marked face on the bed, no supports, and try T3 again.
- Later, not blocking: roadmap 28.4 (Record measurement by `print_id`); a vane anemometer (about $25) for session 2.

---

## M0: Trustworthy flow card

- R0.1 Push and plane fix: done (merged 2026-10-17; F1/F2 PASS). Detail: [`RELEASE_DONE.md`](RELEASE_DONE.md).
- R0.2 Card margins on v4 metrics: done (2026-10-17; `BAND_TOL` 0.06, `BAR_TOL` 0.12). Detail: [`RELEASE_DONE.md`](RELEASE_DONE.md).
- R0.3 "Too close to call" state: done (merged 2026-10-19; C3 FAIL recorded, residual flips accepted). Detail: [`RELEASE_DONE.md`](RELEASE_DONE.md).
- R0.4 Noise hint never judged: done `8d06672`. Detail: [`RELEASE_DONE.md`](RELEASE_DONE.md).

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
- **R1.2 Loaded branch and shut-off honesty (19.6 / 1.5)**. Lane: Cursor (docs and UI). CPU: day. Status: `done 1c2cf12` (shipped in the R1.10 batch, merged 2026-11-13).
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
  CPU: day for the bounds, night for any re-find campaign. Status: `ready` (Claude 2026-11-09: R1.7 and R1.8 are both done, and grok r17 C re-measured 2.0 % refused with both, so the block is gone). grok r14 C delivered 2026-10-17
  (`docs/qa/notes/optimizer-space-wrap-r14.md`; proposed bounds give 4.3 % refused). The refused share depends on the hub
  (R1.7) and the hang check (R1.8), so re-measure after both.
  grok r17 C (2026-10-19, `docs/qa/notes/r17-C-hang-refusals.md`): r14 P0 bounds with R1.7 + R1.8 give 2.0 % refused (Wilson ≤ 4.3 %), so the bounds stand. R1.8 alone gives 7.7 %, R1.7 alone 0.3 %.
  - **Start here (Claude, 2026-11-17):** no acceptance rule for the bounds is pre-registered. The "≤ 3 % false refusals" in
    `2026-10-19-prereg-amendments-r17.md` is the hang check's rule, not the optimizer space's. Before applying the r14 P0
    bounds, commit a dated prereg (ruling by Cursor) saying what refused share, and what coverage of the old space, the
    bounds must meet. Then apply them with a test.
- R1.7 One hub for score and export (QA-44): done `027ebcb`. Detail: [`RELEASE_DONE.md`](RELEASE_DONE.md).
- R1.8 Two-stage hang check (QA-43): done `027ebcb`, acceptance 10/10 `a42544e`. Detail: [`RELEASE_DONE.md`](RELEASE_DONE.md).
- **R1.9 Small QA fixes**. Lane: Cursor. CPU: day. Status: `done 1c2cf12` (shipped in the R1.10 batch, merged 2026-11-13). One branch, one test each:
  - QA-39: sort postProcessing time dirs numerically (`_pp_file`, `sanity.py`, `timing.py`, the objectives copy);
  - QA-40: no noise text in Simple mode when there is no Stock reference;
  - QA-41: `watch_parent` must treat a zombie or exited launcher as gone (not `os.kill(pid, 0)` alone on Linux);
  - QA-42: the Preview weight line names the material and infill ("11 g PLA+, 20 % infill");
  - QA-45: undersized cup hub gives the plain "hub radius too small" message.
- R1.4 Stock recipe gap stated (about 5 % low): done 2026-10-25. Detail: [`RELEASE_DONE.md`](RELEASE_DONE.md).
- **R1.10 Release claims fixes (grok r21 A; QA-55/56/57/58).** Lane: Cursor. CPU: day. Status: `done 1c2cf12` (batch: G5 + R1.2 + R1.5 + R1.9; merged 2026-11-13).
  - 2026-11-13 (Claude): night gate `suite-r110-batch-all` was green on 957a483 (2026-11-09). Master had moved (the r110-g3 merge), so the merge conflicted in one docstring of `tests/test_r110_g3_mixed_volute_copy.py` (master's wording kept). Re-gate on `claude/r110-batch-merge`: the first run was RED on `test_catalog.py::test_classify_puts_small_blade_on_a12x25`, which had been red on master since a6b77c9 (the pad-tip fix raised the A12x25 minimum hub radius to 21.075 mm, and the fixture had 21.0). The fixture now uses Stock's 21.5 mm hub (781310f). Second gate green: 705/655/716 at f716dc0.
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
  - Claude, 2026-11-08: G2 merged to master 3fca917 (night gate: 717/544/653 passed, 0 failed). G3 reviewed OK, wording matches the 10-29 audit; merged onto master as `r110-g3-merge` dd13be7 (board conflict only, 36 related tests pass).
  - G3 landed (`5945620`): Mixed tab "Experimental: not validated against published data"; Assess "runs MRF CFD
    (not validated against published data)"; Volute "ranking only, unvalidated (CFD not yet converged)". Related tests
    38 passed. QA-57 / R2.4. Merge gate 2026-11-08: 668/568/683 passed (OCCT teardown only). Merged to master `41e2dc9`.
  - G4 landed (`5c79aaa`): drop stale ~2× / ~0.6× / ~3–5 %; Assess "two CFD solves … 20–40 min"; README Known limits list (R1.4 phrase kept). QA-69: LBM ranking is "Noise estimate (min)", not dB(A). Merge gate 2026-11-09: 701/519/706 passed (OCCT teardown only). G5 next.
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
- **R1.5 Structural and flutter labels**. Lane: Cursor. CPU: day. Status: `done 1c2cf12` (shipped in the R1.10 batch, merged 2026-11-13).
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
- **R2.2 Propeller CFD: fix it** (Kimball 2026-10-17). **Frozen for v0.1.0 (Kimball 2026-11-15): ships labelled; see the decision at the top.** FAIL, −44 % C_T against UIUC (audit-08).
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
  - **R2.2a″ rung A0c: last A0 attempt for v0.1.0.** Lane: Cursor. CPU: day (minutes; not 4–9 PM). Status: `in progress (Cursor, 2026-11-12)`.
    - 2026-11-12: C-grid counts, far field, wake length and LE/TE clustering are CLI flags; defaults stay 48/60/32, 8c and the old grading. A build-only gate mesh meets the geometric items. Night job `r22a-a0c-gate` is queued (0012, Re 6e6, SST, Tu 0.001, α 0 5 10, iters 10000, then 2× at 10°). The solve has not been started.
    - 2026-11-13 (Claude): the night run of 2026-11-12 failed in 71 s ("OpenFOAM image not available": Docker was not up at 23:30; no solves). The 3 base angles are now running on day CPU as the one-shot Scheduled Task `fansim-a0c-day` into `T:/Projects/Fan Simulator/runs/prop_section_a0c` (about 2 h per angle, 10 000 iterations; it stops itself before 15:30). Night job `r22a-a0c-gate` now writes to the same absolute folder: tonight it skips the solved angles and runs only the 2×-refined 10° grid (about 8 h). Docker Desktop must be running at 23:30.
    - 2026-11-13 11:55 (Claude): the day run **diverged**. At 0° simpleFoam stopped with a floating-point exception at iteration 48 (forces about 1e13, symGaussSeidel in the U solve), so no angle solved. Log: `runs/prop_section_a0c/kOmegaSST_a0.0/logs/simpleFoam.log`. The day task was removed, and night job `r22a-a0c-gate` is set to `hold`. Cursor is already working on it (worktree `fansim-a0c-wake`, branch `r22a-wake-aspect`, uncommitted, not touched). Re-queue the job when that fix lands.
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
  - **QA-51: the NeuralFoil prop backend doesn't converge on the TUD prop.** Lane: Cursor. Status: `done b8559f1`. Until fixed, the backend appears only in Expert, labelled "experimental".
    - Landed (`b8559f1`): Simple mode does not offer NeuralFoil. Expert title is "NeuralFoil (experimental, needs --extra neuralfoil)". Polar math unchanged. Left: the backend still does not converge on the TUD prop.
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
  - **R2.2c 3-D transition (rung C)** and **R2.2d domain size (rung D)**: `frozen for v0.1.0` (Kimball 2026-11-15).
    - Claude ruled A, B and A0 (2026-10-20, 2026-11-06). C or D are unblocked only if A0c passes and the re-run of rung A then gives A1 or A2.
- **R2.3 CROR**: direction proof only.
  - Lane: grok data hunt for small counter-rotating fan or prop P–Q / thrust data. Status: `done (grok r15 hunt, 2026-10-17)`; see `docs/qa/notes/r15-data-hunt-cror-mixed-centrifugal.md`.
- **R2.3 CROR against Shigemitsu 2018** (CC BY 4.0, 40 mm). **Frozen for v0.1.0 (Kimball 2026-11-15): ships labelled.** Pre-registered:
  `docs/validation/audits/2026-10-18-cror-centrifugal-validation-prereg.md`.
  - **R2.3a geometry freeze + case script.** Lane: Cursor. CPU: day for the build. Status: `frozen for v0.1.0`.
    - **Amended 2026-10-19 (§2):** S1 withdrawn (it was CFD vs CFD), replaced by S1′. Table 1 stagger is **from the rotation plane**. Camber NACA 4 % at 40 %; axial gap 4.9 mm. Now `ready` (grok r17 B delivered the data).
    - grok r17 B delivered 2026-10-19: `docs/qa/r17/r17-B-shigemitsu2018-digitised.csv` + `docs/qa/notes/r17-B-digitised-cror-centrifugal.md` (CC BY 4.0 confirmed). Only total P–Q is measured; the per-rotor data and η are CFD (QA-47). Stagger convention and camber are missing, so Claude rules before the freeze.
    - Follow step 0 exactly; fill missing values only by the stated rules.
    - Commit `validation/reference/cror_shigemitsu2018/geometry.json` + STL (that commit is the freeze), then
      `scripts/validate_cror_shigemitsu.py`.
  - **R2.3b runs.** Lane: night. Status: `frozen for v0.1.0`. Add the job to `night/queue.json`.
- **R2.4 Mixed-flow**: no published comparison.
  - grok r15: no small CC-licensed mixed-flow data. The 85 mm Treder rig is cite-only.
  - **Kimball 2026-10-17: label it experimental.** Lane: Cursor. CPU: day. Status: `done 5945620`.
    - The Mixed tab title and its Assess/Optimize results say "Experimental: not validated against published data".
    - Same in the README feature list, and in exported READMEs for mixed-flow parts.
    - Test: the label appears on the tab and in the export README.
    - Landed (`5945620`, via R1.10 G3): tab "Mixed · experimental"; export sidecar `.md`; README Known limits.
  - Lane: grok data hunt for mixed-flow fan curves at small diameter. Status: `done (grok r15 hunt, 2026-10-17)`; same note.
- **R2.5 Volute / centrifugal**: CFD is unconverged (17–23 % oscillation), a ±20 % proxy.
  - Lane: grok data hunt for a small centrifugal blower curve. Claude decides converge-or-label. Status: hunt `done (grok r15,
    2026-10-17)`, same note; converge-or-label still with Claude.
- **R2.5 Volute/centrifugal against EPJ WoC 180:02023** (60 mm). **Frozen for v0.1.0 (Kimball 2026-11-15): ships labelled; the transient prereg is v0.1.1 work.** Pre-registered: same document.
  - **R2.5a convergence fix.** Lane: Cursor. CPU: day for short tests, night for full runs. Status: `frozen for v0.1.0` (Kimball 2026-11-15; relaxation sweep none/none, transient is v0.1.1 work).
    - 2026-11-15 (Claude): sweep run and merged (`7efee56`, gate green 707/652/726). **No relaxation variant passes on either mesh** (fine V0 22 %/18 %, V1 40 %/69 %, V2 killed/7.2 %); more damping makes it worse. Results in the prereg. Next: a pre-registration for transient averaging (pimpleFoam, frozen rotor). Until then the volute stays a labelled ±20 % proxy. **Trap:** every 50 Pa run shows a reversed 800–1550 CFM flow (≈ shut-off at 3000 rpm, outlet backflow), so the transient prereg needs a reachable load point and a backflow check first.
    - 2026-11-13 (Claude): pre-registered sweep `docs/validation/audits/2026-11-13-volute-convergence-sweep-prereg.md` covers coarse/fine mesh × relaxation V0/V1/V2 × free/50 Pa, 3000 iterations, judged on step 1 only. Branch `claude/r25a-volute-conv` (93a79cc) adds `build_volute_case(relax=...)` (default unchanged) and `scripts/volute_convergence_sweep.py`; its related tests pass and the gate is not run yet. Night job `r25a-volute-conv-sweep` is queued for tonight, about 3 h. Results: `T:/Projects/Fan Simulator/runs/volute_conv_r25a/summary.json` (`choice` per mesh). Existing data shows that the 17–23 % swing is the fine mesh and the reversed rotor; the coarse designed run was already 3.4 %.
    - Get the existing volute case to ≤ 5 % peak-to-peak ΔP over the last 20 % of iterations (step 1).
    - Judge it **only** on convergence, never against the paper.
  - **R2.5b geometry freeze + case script.** Lane: Cursor. Status: `frozen for v0.1.0`.
    - **Amended 2026-10-19 (§3):** A1 at 0.4 / 0.7 / 1.0 × Q_max,meas; outlet-tube static pressure; log-spiral volute; gap t 0.5 mm. Now `ready` (grok r17 B delivered the data).
    - grok r17 B delivered 2026-10-19: `docs/qa/r17/r17-B-epj2018-02023-digitised.csv` (CC BY 4.0 confirmed; plastic wheel at 6000/9000/11000). No curve reaches free delivery (QA-48), so A1 needs restating. b2 = 3.86 mm, d1/d2 ≈ 0.5, no blade angles, no scaled volute drawing.
    - Step 0, then `validation/reference/volute_epj2018/geometry.json` and `scripts/validate_volute_epj.py`.
  - **R2.5c runs.** Lane: night. Status: `frozen for v0.1.0`.
- **R2.7 Label pass for the four unvalidated surfaces (Kimball decision 2026-11-15).** Lane: Cursor. CPU: day.
  Status: `in progress (Cursor, 2026-11-19)`. One branch, one gate. Branch `r27-labels-fix` (from `claude/r27-labels`).
  - 2026-11-17 (Claude): landed on the branch (`111b559`), not merged yet. Also labels the CROR and Volute point inspectors (as Mixed's) and keeps the CROR README sidecar out of the export list. The label is on every tab tooltip (Prop
    tooltip says the optional CFD check is experimental), next to every Assess / Optimize / CFD-refine result, and in
    new CROR and Volute export README sidecars. Volute's "ranking only, unvalidated" is now the standard words. Labelled
    completion messages lose their ✓ (existing rule in `test_ui_says_what_it_does`). README Known limits has one
    labelled line per surface. Tabs renamed "Volute · experimental" and "CROR · experimental" (Kimball 2026-11-17), as Mixed. `tests/test_r27_labels.py`
    + 4 older copy tests moved to the new wording: 80 passed.
  - 2026-11-17 night gate RED: `test_export_hint_uses_the_fit_hub_setting_from_the_click` hit OSError 22 on a print-id
    whose check digit was `*` (`5YEE*…`), illegal in a Windows path. Not an R2.7 label bug. Cursor 2026-11-19:
    `issue_print_id` skips filename-unsafe check digits; master merged into the branch; focused tests 36 passed.
  - **Resume:** re-queue `suite-r27-labels-all` on `r27-labels-fix` (merge on green). If STATUS.md says merged, set
    this to `done <merge commit>` and R3.8 to `blocked (R1.3)`.
  - The same words everywhere: **"Experimental: not validated against published data."** In Simple and Expert, on the
    tab (tooltip or name, as Mixed already does), next to every Assess/Optimize number, and in the export README/sidecar.
  - Where it stands (Claude, 2026-11-15): Mixed is done (`5945620`). Volute says "ranking only, unvalidated" (change it
    to the standard words). Propeller CFD has only a note in the Assess text (`prop_tab.py:1393`); the BEMT fast estimate
    is validated and must **not** get the label. **CROR has no label in the UI at all.**
  - README "Known limits": one line per surface with the standard words; also drop "nothing printed or measured yet"
    (print session 1 happened; nothing is *validated* by it).
  - Test first: one test that each of the four tabs shows the exact string in Simple and Expert, and that the Fan tab
    and the prop BEMT result do not.
- **R2.6 Centrifugal (no tab) and wind turbine (scaffold)**: excluded from v0.1.0.
  - Lane: Cursor makes sure neither is reachable from the cockpit or the README quickstart. Status: `done 1d5e8b9`.
  - Landed: no centrifugal-only or wind-turbine control, tab, menu, or README quickstart link. `tests/test_r26_hide_scaffolds.py` locks that. Mixed and Volute stay. The wind_turbine package stays in the repo.

## M3: Releasable repo (parallel, mostly Cursor)

- **R3.1 Release export hygiene**. Lane: Cursor. CPU: day. Status: `done ac4024f`.
  - Landed: the public export drops archive, memory, handoff, screenshots, bak files, and chat-recovery dumps, and the product docs still ship with user-home and E: prefixes redacted.
  - grok r20 E: the leak check is still not run.
  - Extend `RELEASE_EXCLUDE` and `scripts/export_release.py` to drop `archive/`, `memory/`, `handoff/`,
    `docs/qa/screenshots`, `*.bak`, chat-recovery dumps, and any user-home or E: drive prefix (either slash).
  - Test: an export of master contains none of them, and the grep for user paths is empty.
  - Ruling (Cursor, 2026-11-11): named large files stay in git and out of the public export. No Git LFS. CC-BY attribution in `THIRD_PARTY.md` stays. Tracked: `validation/reference/fan01/fan01_rotor.stl` (the only `fan01/*.stl`), `validation/reference/fan01/cad_model.zip`, `validation/reference/a12x25_impeller.stl`.
- **R3.2 Packaging**. Lane: Cursor. CPU: day. Status: `done 26ccf29`.
  Landed: MIT metadata, author Kimball with no email, the Gitea repository URL, and `fansim-cockpit` via `fansim/cockpit_entry.py`; the wheel is the installed artifact.
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
- **R3.4 Docker/OpenFOAM readiness badge and first-run check (21.2g)**. Lane: Cursor. CPU: day. Status: `done 540829e`.
  - The cockpit shows "CFD ready / Docker not running / image missing" with the fix in plain words.
  - Landed: Simple mode shows one of four lines (CFD ready, start Docker Desktop, pull the OpenFOAM image, or install Docker); Kimball still signs off the wording.
- **R3.5 GitHub Actions CI**. Lane: Cursor. CPU: none (cloud). Status: `done 8c34965`.
  - Port `.github/workflows/ci.yml` for GitHub: ubuntu fast suite in 3 chunks, plus a Windows job for the fast
    geometry and export subset.
  - Widen ruff to the default rule set on changed files only.
  - Landed: Windows job `windows-geometry` runs `test_export_release.py`, `test_geometry.py`, `test_stl_sanitize.py`, and `test_span_interp.py` with `-m "not docker and not slow"`, judged by `pytest_chunks.judge()` so an OCCT teardown after a green summary counts as a pass; ruff's default rules stay on changed `.py` only, the whole-tree gate stays F811,F821, and the Ubuntu fast suite is unchanged.
- R3.5b Chunk runner runs every chunk: done `70ab65c`. Detail: [`RELEASE_DONE.md`](RELEASE_DONE.md).
- **R3.6 CHANGELOG, CONTRIBUTING, issue templates**. Lane: Cursor. CPU: day. Status: `done 2311d26`.
  - CONTRIBUTING points to `AGENTS.md`'s rules (pre-registration, tests first).
  - Landed CONTRIBUTING, an Unreleased CHANGELOG, two issue templates, and one README contributing link; the print-id coupon has not passed.
- **R3.7 Cockpit UI regression tests (29.2)**. Lane: Cursor writes, grok proposes cases. CPU: day. Status: `done 2b98425`.
  - Headless "we say X, we do Y" tests (`tests/test_ui_says_what_it_does.py`), at least one per tab that ships.
  - Landed one headless say/do test per shipping tab (Fan, Prop, Mixed, Volute, CROR); handlers are read with inspect.getsource, not run, and no production copy changed.
- **R3.8 Validation page**. Lane: Cursor drafts, Claude checks the numbers. CPU: day. Status: `blocked (R1.3, R2.7)`.
  - **Claude reviewed grok r21 B 2026-10-29: approved as the base.** Apply M1–M9 (M3: name the rig for 58.3 vs 59.8; M5: the link is `2026-10-12-cylinder-sections.md`). See the review doc. grok checks the final page.
  - `docs/VALIDATION.md`: per surface, what it was validated against, the tolerance, the result and the known limits.
    Every number links to its audit.
  - grok r21 B (2026-10-25): draft from the audits in `docs/qa/notes/r21-B-validation-draft.md` (13 surfaces + Known limits, 9 mismatches listed) for Cursor to adapt and Claude to check.
- **R3.9 Large files**. Lane: Cursor. CPU: day. Status: `done ac4024f`.
  - Landed: `fan01_rotor.stl`, `cad_model.zip`, and `a12x25_impeller.stl` stay in git and out of the public export, with no Git LFS, and the CC-BY attribution stays in `THIRD_PARTY.md`.
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

## Unparked by Kimball 2026-11-09: print-part ID (roadmap §28)

- **28.3 Recessed hub glyphs**. Lane: Cursor. CPU: day. Status: `done 2bfde35` (QA-73 un-mirror; P6 5 mm cap). First cut was `11f97d6`.

## After v0.1.0 (parked; not release work)

- **grok lead 15: balance tolerance** (ISO 21940-11 + a phone four-run trim helper): `docs/qa/notes/balance-tolerance-proposal.md`.
- **grok lead 16: tap-test calibration** of `FDM_E_K` (phone f1 tap test): `docs/qa/notes/tap-test-calibration-proposal.md`.
  This needs printed parts, so it fits v0.1.1 (rig measurements) alongside 5.1/5.2.

