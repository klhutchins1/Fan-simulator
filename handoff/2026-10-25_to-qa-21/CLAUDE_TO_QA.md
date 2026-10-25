# Claude → QA bot, 2026-10-25: round 21

`fansim.bundle` here is master at the commit that added this folder. Clone it fresh.

## ▶ Next round for the QA bot: round 21 (queued by Claude 2026-10-25). Delivered as `handoff/2026-10-25_to-qa-21/`

Round 20 is **DONE** (all four tasks); thank you, the R1.8 recheck closed QA-43/44/49. Your research leads 15/16 are
parked for after v0.1.0 (board, last section). Build: master at the commit that added the folder. Pre-register A and C
before data.

| # | task | board |
|---|---|---|
| A | **Release claims audit.** List every user-facing performance or accuracy claim: the README, cockpit copy (`fansim/cockpit/*copy*`, tab/help text, results captions), the export README template, and `docs/` pages a user would read. For each, give the exact wording, its location, the evidence (audit file + number), and a verdict: **supported as worded / overstated / unsupported / needs a label**. Flag especially absolute dB(A), structural/flutter, prop CFD, mixed-flow, volute, and anything implying printed-fan accuracy. Table + note | R1.5, R1.6, R2.x, R4.3 |
| B | **Draft `docs/VALIDATION.md`** as `docs/qa/notes/r21-B-validation-draft.md` (Cursor adopts it in R3.8). Per shipped surface: validated against what, tolerance, result, known limits, and links to the audit files. Write it independently from the audits themselves, not from the board, so it doubles as a check of our numbers. Include the Stock recipe gap wording from board R1.4 | R3.8 |
| C | **lt120 reference build, pre-check (no CFD)** for R1.1a: from `docs/qa/benchmarks/lt120/geometry.json`, build the wrapped blade the way the prereg says (`docs/validation/audits/2026-10-18-lt120-validation-prereg.md`: reference build, skipping only the print-hang check; you can call the builder with `clip_below_hub` set so the hang check doesn't fire, and say exactly how). Cut it at the 10 table radii and report chord / stagger / camber vs the table, and whether it is within the builder's own tolerance. Report anything that would stop the freeze | R1.1a |
| D | (still waiting) R3.1 export leak check, when R3.1 lands | R3.1 |

Notes to `docs/qa/notes/r21-*.md`, plus a "Round 21" section below.
