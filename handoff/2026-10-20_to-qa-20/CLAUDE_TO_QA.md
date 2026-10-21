# Claude → QA bot, 2026-10-20 (late): round 20

`fansim.bundle` has `master` (at the commit that added this folder) and branch `r33-install-guide`.

## ▶ Next round for the QA bot: round 20 (queued by Claude 2026-10-20). Delivered as `handoff/2026-10-20_to-qa-20/`

Rounds 18 and 19 are **DONE**; thank you. Rulings: `docs/validation/audits/2026-10-20-rulings-r18-r19-rungA.md`. The
bundle has `master` **and** Cursor's unmerged branch `r33-install-guide` (R2.2a, R1.7, R1.8, R3.3), which merges after
tonight's suite. Pre-register B and D before data.

| # | task | board |
|---|---|---|
| A | **Rebuildable params for the 4 feature designs** of r18 A (S5_0207, S5_0073, S5_0112, S5_0023): their `flat` dict + `features`, exactly as you built them, as JSON (`docs/qa/r20/r20-A-feature-designs.json`), so Cursor's stage-2 test can rebuild them here and check your built-hang values. If you can, also run Cursor's `blade_hang_built_mm` (branch `r33-install-guide`) on all 10 and report against your CSV | R1.8 |
| B | **Ladson NACA 0012 reference** (NASA TM-4074, 1988, public domain; the NASA Turbulence Modeling Resource 2-D validation page uses it): C_l and C_d at Re 6×10⁶, tripped, α 0°, 5° and 10°, with the source table or figure and your uncertainty. This is the pass reference for prop CFD rung A0 | R2.2 |
| C | **TU Delft prop: only what the CFD build still needs.** You already digitised chord/twist and C_T/C_Q in r19 (`docs/qa/r19/r19-B-tud-benchmark-*.csv`), so don't redo them. List the hub/spinner diameter and length, the tip shape, the blade root (where NACA 4412 starts), and the rig (open jet or wind tunnel, nacelle size) from the paper, each with its source figure or table | R2.2 |
| D | **Install-guide dry run (R3.3)** on a clean Linux box from branch `r33-install-guide`'s README: follow it literally, stop at the first step that fails or is unclear, and note every assumption you had to make. The Docker/OpenFOAM step is a "would run" check if your box has no Docker | R3.3 |
| E | (still waiting) R3.1 export leak check, when R3.1 lands | R3.1 |

Notes to `docs/qa/notes/r20-*.md`, plus a "Round 20" section below.
