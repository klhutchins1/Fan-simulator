# QA round 21 pre-registration (grok, QA bot)

Written 2026-10-25 MDT, before any round-21 data. Brief: `handoff/2026-10-25_to-qa-21/CLAUDE_TO_QA.md` (repo-r21,
master 5063a65 = 5063a6595d52c96f7f3df3d6a26d248ebd439f7b, fresh clone of `fansim_master_r21.bundle`).

**Repo state recorded before any data:**
- `rg reference_build fansim` finds nothing: master has **no** `reference_build=True` path (lt120 prereg, work
  item 1). The only way to skip the hang check is `clip_below_hub=False`, which also skips the hub-face clip
  (`clip_blade_below`) and the clip correction (`correct_clipped_sections`). This is noted now as a candidate freeze
  item; it is not a result.
- `docs/qa/benchmarks/lt120/built_vs_table.json` exists (my round-7 file, planar era). Its values are not read before
  C is done; it is context only.

**Seen before writing this (format/method only):**
- the lt120 prereg, `geometry.json` / `source.md` / `fansim_params.json` inputs (table values are inputs, not results);
- the builder code paths and tolerances: `tests/test_hub_hang.py:155-157` and audit
  `2026-10-12-cylinder-sections.md` V1 ("chord within 3 % of the slider; camber within 0.005 and stagger within 1.5°
  of the same section read from a wrapped no-lean reference"). That audit's line 67 quotes an older lt120 worst
  camber/stagger; I saw it while finding the rule.
- file names in `fansim/cockpit/`, `docs/`, `docs/validation/audits/`. No claim text was read.

## A. Release claims audit (R1.5, R1.6, R2.x, R4.3)

**Scope (fixed now):**
1. `README.md`.
2. Cockpit copy: every `fansim/cockpit/*copy*.py`, plus user-visible strings (tab titles, help/tooltip text, results
   captions) in `fansim/cockpit/*.py` (incl. `score_caption.py`, `labels.py`, `flow_reference.py`, tab files).
3. The export README template (whatever code writes the README inside an export zip; located by `rg -i readme`).
4. User-facing `docs/` pages: top-level `docs/*.md` a user would open (e.g. how-scores-are-computed, known-issues,
   design-rules, a12x25-reference) and any `docs/` page linked from the README. **Out of scope:** `docs/qa/`,
   `docs/validation/audits/`, `docs/release/`, `docs/plans/`, `docs/superpowers/`, `docs/roadmap.md`,
   `handoff/`, `archive/` (internal records; they are the evidence, not the claims).

**What counts as a claim:** a sentence a user reads that states or implies how well a number or output matches
reality: a %/dB/dB(A)/Pa/CFM/N/g/W accuracy figure, "validated", "accurate", "matches", "within", "agrees",
"predicts", "measured", "reliable", "real", "trust", "confidence", or a ranking/ordering claim. Pure descriptions of
what a feature does are not claims. Collection: a fixed keyword grep (the words above, plus `dB`, `±`, `%`,
`flutter`, `structural`, `stress`, `safety`, `CFD`, `mixed`, `volute`, `prop`, `print`) over the scope, then read
every hit in context. Each claim gets file:line, exact wording.

**Evidence:** an audit file under `docs/validation/` (audits or summaries) or a QA note, with the number.

**Verdict rules:**
- **supported as worded**: an audit number matches the wording (within its rounding), for the same conditions and
  scope, and any needed qualifier is present.
- **overstated**: evidence exists but the wording claims more: a tighter number, wider scope (other fans, archetypes,
  printed parts), drops a condition, or says validated/accurate where the audit says trends, INCONCLUSIVE, relative
  only, or not run.
- **unsupported**: no audit evidence found after searching audits + QA notes by keyword, or the evidence contradicts.
- **needs a label**: the number/behaviour is supported but a required qualifier is missing (relative vs absolute,
  model vs CFD, CFD vs printed fan, Stock ~5 % recipe gap, single fan only).
- Special flags (always called out in the note): absolute dB(A); structural/flutter/stress; prop CFD; mixed-flow;
  volute; anything implying a *printed* fan will perform as predicted.
- **Pass/fail for the round:** A "passes" (release-ready copy) only if 0 overstated and 0 unsupported claims. Any
  overstated/unsupported claim gets a QA item (one item per theme, not per line).

## B. VALIDATION.md draft (R3.8)
Written from `docs/validation/**` and QA notes, not the board. A board number is a **mismatch** if it differs from
the audit's number beyond the audit's printed rounding, or cites a different condition. Recompute where a summary
JSON/CSV allows it in < 1 min; otherwise re-read. Mismatches are listed, not fixed. Board R1.4 Stock-gap wording is
quoted verbatim.

## C. lt120 reference build pre-check (R1.1a; no CFD)
**Build (primary, P):** `p = replace(load_blade_params("docs/qa/benchmarks/lt120/fansim_params.json"),
section_wrap="cylinder", clip_below_hub=False)`; `build_impeller(p)` (the shipping path: validate → blade with
chord realisation → hang refusal [skipped by the flag] → hub → fuse); export STL. Nothing else is changed.
**Secondary (report-only, S):** the literal "shipping build minus only the hang check": `clip_below_hub=True`,
`build_blade_solid(p)` (chord realisation + clip correction) then `clip_blade_below` at the hub face, bypassing only
`validate_blade_params`'s hang test and `_refuse_if_built_hang_past_limit` (scratch script; no source edits).
Blade-only S solid cut the same way.

**Cut:** `measure_sections(stl, [r/60 for r in table radii], tip_radius_mm=60)` at the 10 table radii
(23.0 … 56.5 mm). Report chord, stagger, camber, n_blades, omega_sign.

**Per-radius gate (the builder's own tolerance):**
- chord: |chord_meas / chord_table − 1| ≤ 3 %;
- camber: |camber_meas − camber_ref| ≤ 0.005;
- stagger: |stagger_meas − stagger_ref| ≤ 1.5°;
- where `*_ref` is the table station's section, wrapped at r, no lean/sweep, read by the same estimator
  (`_measure_loop`, as `tests/test_hub_hang.py::_analytic`).
- A radius **PASS** = all three within; **FAIL** = any outside; **N/M** = no blade section can be cut there
  (e.g. inside the 25 mm hub). N/M is not a pass and is listed as a freeze item.
- Report-only: raw camber vs table (0.04) and raw stagger vs table setting angle; the estimator bias (ref − table).

**Freeze blockers (each reported yes/no):** any radius FAIL or N/M; no `reference_build` path; P ≠ S beyond the gate at
any radius (which build is "the reference" is then a decision); impeller not one watertight solid with 7 blades;
direction proof not CONCLUSIVE; designed and built hang values; `validation/reference/lt120/` absent.
**C passes** if all 9–10 measurable radii PASS on P and no blocker other than the known missing path.

## D. R3.1 export leak check: waiting (R3.1 not landed). Not run.

Timing with `time.monotonic`; long jobs with `setsid nohup`; no CFD/Docker/OpenFOAM/Assess/Sweep.
