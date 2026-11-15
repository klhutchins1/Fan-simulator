# Round 27 for grok (Cursor, 2026-11-09)

Thank you for the 2026-11-08/09 packs (QA-68, G2, ui-hunt-1, G3, leads 23–30). Those are recorded on master. This round is a **current-master re-check**, not a new claims audit of G2/G3.

**Build:** master at the commit that added this folder. No Docker, CFD, OpenFOAM, Assess, Sweep or Optimize run. Pre-register A and B before data.

## Tasks

| # | task | board |
|---|---|---|
| A | **QA-57 closeout.** Volute Assess copy and result readout must carry "ranking only, unvalidated (CFD not yet converged)". Mixed side is already verified — do not re-prove C22/C24/C25. If `docs/qa/patches/g3-QA57-volute-assess-label.patch` is applied, red-check it. | QA-57 |
| B | **UI-39 and UI-40.** Sweep steps: refuse empty / non-int / outside 2–12 with a visible message; never queue a huge CFD sweep. Optimize Trials: label "2–40"; refuse out-of-range instead of silent clamp. Do not click Run. | UI-39, UI-40 |
| C | **QA-70.** Expert noise-hint row still shows when a run has the tip-speed+CFM hint but no turbulence SWL. G2 claims stay verified / not re-tested. | QA-70 |
| D | **G4 if it is on this master.** Stale ~2× / ~0.6× / ~3–5 % gone; Assess "two CFD solves … 20–40 min"; README Known limits still has R1.4's "about 5 % less airflow than the real A12x25". QA-69 (`design-rules.md` "Noise dB(A) (min)") is G4's. If G4 is not merged, say so and skip. | R1.10 G4 |

Notes to `docs/qa/notes/r27-*.md`, plus a "Round 27" section in `docs/QA_REVIEW.md`.

Research leads 23–30 stay **parked** (Cursor will pick patches later). R3.1 export leak still waits on R3.1.
