# Round 28 for grok (Cursor, 2026-11-09)

Kimball asked that this session also test the new print-part ID glyphs (roadmap §28.3).

**Build:** `fansim_master.bundle` in this folder is **master including the commit that adds this brief**. No Docker, CFD, OpenFOAM, Assess, Sweep or Optimize run. Write `docs/qa/rounds/r28.md` (do not edit `docs/QA_REVIEW.md` or the board). Pre-register E before data. Do not CFD the hub recess. Do not re-prove G2/G3 claims C22/C24/C25.

Round 27 (`handoff/2026-11-09_to-qa-27/`) was queued on older master. If you have not started 27, do A–D here (this master has G4) **and** E. If 27 is already in progress, skip A–D and only do E.

## Tasks

| # | task | board |
|---|---|---|
| A | **QA-57 closeout.** Volute Assess copy and result readout must carry "ranking only, unvalidated (CFD not yet converged)". Mixed side verified — do not re-prove C22/C24/C25. Skip if already in r27. | QA-57 |
| B | **UI-39 and UI-40.** Sweep steps: refuse empty / non-int / outside 2–12 with a visible message; never queue a huge CFD sweep. Optimize Trials: label "2–40"; refuse out-of-range instead of silent clamp. Do not click Run. Skip if already in r27. | UI-39, UI-40 |
| C | **QA-70.** Expert noise-hint row still shows when a run has the tip-speed+CFM hint but no turbulence SWL. G2 claims stay verified / not re-tested. Skip if already in r27. | QA-70 |
| D | **G4.** Stale ~2× / ~0.6× / ~3–5 % gone; Assess "two CFD solves … 20–40 min"; README Known limits still has R1.4's "about 5 % less airflow than the real A12x25". QA-69 (`design-rules.md` "Noise dB(A) (min)") is G4's. Skip if already in r27. | R1.10 G4 |
| E | **28.3 recessed hub glyphs (new).** See below. | roadmap §28.3 |

## Task E — 28.3 glyphs

Mark-spec: `docs/qa/notes/print-id-mark-spec-r10.md`. Code: `fansim/manufacturability/print_id_mark.py` (`engrave_print_id`), wired from `export_print_ready(..., print_id=)`. Layout constants in `print_id.py`. Cursor's disk tests: `tests/test_print_id.py`, `tests/test_print_id_glyphs.py`.

Pre-register before you cut a print-ready impeller. Suggested PASS/FAIL (you may tighten, not loosen):

- **PASS** if all of: the two pytest files above are green; a print-ready Stock A12x25 impeller exported with a known 5-char print-id is 1 B-rep solid, watertight, 1 body; ΔV vs the unmarked sibling is a shallow recess (order 10 mm³, not a through-cut); the recess sits on +Z in r 11.5–14.7 mm; cup gauge K7 is unchanged (floor ~13 mm above the motor face, 20 grips); README no longer says "No glyphs on the part yet".
- **FAIL** if the marked STL splits, leaks, or the cup/grips change.
- **INCONCLUSIVE** if CAD/OCCT dies before a verdict. Do not re-tune the glyphs to chase a pass.

Do not CFD the pocket. Research leads 23–30 stay parked.
