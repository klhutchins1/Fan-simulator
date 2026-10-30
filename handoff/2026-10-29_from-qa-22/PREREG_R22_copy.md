# QA round 22 pre-registration (grok, QA bot)

Written 2026-10-29 MDT, before any round-22 data. Brief: `handoff/2026-10-29_to-qa-22/CLAUDE_TO_QA.md` (repo-r22,
master b3d5543 = b3d5543dc3fb035e83a0949f40062587425d28ac, fresh clone of `handoff_in/master_b3d5543.bundle`; the
brief's `fansim.bundle` is not on the box, Kimball named this bundle instead).

**Seen before writing this (context/spec only, no results):**
- the brief; my r21 prereg (956b8ff) and r21 C note (my own r21 P/S numbers are the comparison baseline for B);
- QA_REVIEW.md tracker rows for QA-40, QA-42, QA-53, UI-26, UI-27, UI-29 (their repro text);
- RELEASE_PLAN.md R1.1a "Landed" line (Cursor states `reference_build=True` skips hang only, clip stays on, 9/9
  PASS, r=23 N/M, "freeze blockers (QA-60) are closed"), R1.4 wording + test, R2.2a′ A0 result line
  (C_d(0°) −2.4 %, C_l(5°) −14 %, C_l(10°) −44 %), R3.3 QA-53 fix line ("the GitHub URL", 8080, "30–40 min");
- the file names in `validation/reference/lt120/` (`geometry_freeze.json`, `lt120.stl`, `params.json`); not opened;
- that `scripts/prop_section_2d.py` exists; not opened.

## A. UI and bug pass (status vocabulary and rules)

Cockpit started headless from repo-r22 on **:8080** (`scripts/cockpit.py`, as the README says), driven with Playwright +
system Chrome (`qa/pwvenv`) in a fresh context, plus curl and code reading of the served code. Fast pytest
(`-m "not docker and not slow"`) once, counts recorded. No Assess/Sweep/CFD clicked.

**Status words (only these three):**
- **verified**: the item's own repro, run on b3d5543, no longer shows the problem, by the rule below.
- **still open**: the repro still shows the problem (any one sub-check failing keeps the item open).
- **not re-tested**: no decisive headless check exists or it could not be run this round (reason stated).

**Per-item rules:**
- **QA-53** (three sub-checks, all must pass for verified): (a) port: the URL in the README equals the URL the
  cockpit prints/binds when started as the README says (expect 8080); (b) Assess time: README says 30–40 min
  (matching the cockpit's own text); (c) clone URL: no `<this-repo>` placeholder; a real URL **or** the board's interim
  wording "the GitHub URL" counts as pass (interim is noted). The "Docker not installed" row is R3.4 and is reported, not
  gated.
- **R1.4 phrase**: "about 5 % less airflow than the real A12x25" (case-insensitive; normal space / no-break space /
  no space before % all accepted) must appear in **both** the README and the Stock Expert text the cockpit renders (or,
  if rendering can't be reached headlessly, the string in the source the Stock Expert caption uses). Both → verified;
  either missing → still open. Simple mode must show nothing extra (reported).
- **UI-26**: verified if none of the four quoted jargon strings is rendered on the Fan tab first view (Simple and
  Expert) and none is in the cockpit source unchanged; still open if any is.
- **UI-27** (1366×768, Fan tab first view, no scroll): verified if the 3-D viewer's bounding box bottom ≤ 768 px and
  the design picker and the Actions (Preview button) are visible above the fold; still open otherwise.
- **UI-29** (1920×1080, first view): verified if the controls column is ≥ 25 % of the viewport width, body text
  computed font-size ≥ 14 px, and the 'Start here' text ≥ 14 px and not a grey caption; still open if any fails.
- **QA-40**: verified if, for a run with SWL but no Stock reference (r14 case s3), the Simple-mode flow card does not
  show "No Stock comparison for noise." (direct call of the card builder with s3-like inputs, or the r14 harness);
  still open if it does.
- **QA-42**: verified if the Preview "fits … g" line names the material (and infill) so PLA+ and PETG are
  distinguishable (direct call of the line builder with both materials, or the rendered line); still open if not.
- **New bugs**: anything that crashes, contradicts README/board text, or regresses an earlier verified item gets a new
  ID after the current highest (QA-61…, UI-31…), with repro.

## B. lt120 freeze re-cut (R1.1a, QA-60; no CFD)

**Input:** the committed `validation/reference/lt120/lt120.stl`, unchanged (sha256 recorded; compared with any hash
in `geometry_freeze.json`). Rebuild only if the STL is missing (then reported as a deviation).
**Cut:** `measure_sections(stl, [r/60 for r in table radii], tip_radius_mm=60)` at the 10 table radii (23.0 … 56.5 mm),
exactly as r21 C. Report chord, stagger, camber, n_blades, omega_sign.

**Per-radius gate (unchanged from r21 C):** chord |meas/table − 1| ≤ 3 %; camber |meas − ref| ≤ 0.005; stagger
|meas − ref| ≤ 1.5°; `*_ref` = table station wrapped at r, no lean/sweep, read by `_measure_loop` (as
`tests/test_hub_hang.py::_analytic`). PASS = all three; FAIL = any outside; N/M = no section cut (0 blades).
**B passes** if r = 23.0 is N/M **and** 9/9 radii 26.7–56.5 PASS. r = 23.0 being cuttable is a FAIL of the
expectation.

**Compare with r21 S** (clip on, hang checks bypassed; `qa_r21/c/out` data): per radius Δchord %, Δstagger, Δcamber.
"Matches r21 S" if |Δchord| ≤ 0.5 %, |Δstagger| ≤ 0.1° and |Δcamber| ≤ 0.001 at every cut radius. Also against r21 P
(report-only). Also report: watertight / bodies, rmax, n_blades, direction (if `prove_direction` runs on the STL in
< 5 min).

**QA-60 sub-items** (each closed / open, by reading the freeze files and `fansim` code, no edits):
1. `reference_build` exists and skips only the hang checks (clip behaviour stated);
2. r = 23 is recorded in the freeze as embedded / not cuttable (or the table remapped);
3. `validation/reference/lt120/` present with STL + `geometry_freeze.json`;
4. the 56.5 → 60 mm tip extrapolation is recorded;
5. which build (clip on vs clip off) is the reference is stated.
**QA-60 verdict:** **closed** if B passes and sub-items 1, 3 and 5 are closed and 2 is closed (4 may be open: then
closed with a LOW follow-up); **contradicted** if any cut radius 26.7–56.5 FAILs, r = 23 cuts, or the freeze/board
text states something the files/code show is false (e.g. clip state); **still open** otherwise (listing sub-items).

## C. A0b bookkeeping, `scripts/prop_section_2d.py` (code reading only; no solve, no OpenFOAM, no case write)

For α = 0, 5, 10° (the A0 run `--section 0012 --re 6e6 --alphas 0 5 10`) record from the code path, with file:line:
1. inflow U: vector formula and where α enters (U rotated, or geometry rotated, or both);
2. `liftDir` and `dragDir` written into the forces / forceCoeffs function object (formula and the numeric vector at
   each α, evaluated by hand/arithmetic only);
3. the α each of them uses, and the α the airfoil geometry is at (if it is rotated).
Report-only: `magUInf`, `lRef`, `Aref`, `CofR`, `pitchAxis`, rho, and the patch list.

**Rules:**
- **consistent** (no setup bug in this bookkeeping) if, at every α: dragDir ∥ the freestream as seen by the airfoil
  chord frame, liftDir ⟂ dragDir in the flow plane and on the suction-positive side, and the effective angle between
  the chord line and U equals the nominal α (applied once) to within 0.01°.
- **setup bug** if any of: liftDir/dragDir use an α different from U's (incl. 0 when U is rotated); α applied twice
  (geometry and U both rotated the same sense) or not at all; liftDir not ⟂ dragDir; a sign error that flips α.
- **Explains the A0 FAIL** if a found bug, applied to the Ladson reference (C_d 0.00808 at 0°, C_l 0.537 at 5°, 1.063
  at 10°, and C_d at 5°/10° taken from Ladson-level values), predicts C_l low at 5° and 10°, more so at 10°, with C_d(0°)
  unchanged, and the predicted deficits are within a factor 2 of the reported −14 % and −44 %. **Partly** if the
  sign/trend matches but the size is off by more than 2×. **Does not explain** if no bug, or the predicted error has the
  wrong sign/trend. If the bookkeeping is consistent, the note lists the code-visible alternatives (report-only).

## D. R3.1 export leak check: waiting (R3.1 not landed). Not run.

Timing with `time.monotonic`; long jobs with `setsid nohup`; logs trimmed (tail/grep). No CFD/Docker/OpenFOAM/
Assess/Sweep; nothing committed to repo-r22; no fansim source edits; no outside STLs.
