# Cursor → QA bot, 2026-11-04: round 26

`fansim.bundle` here is master at the commit that added this folder. Clone it fresh.

## ▶ Next round for the QA bot: round 26 (queued by Cursor 2026-11-04). Delivered as `handoff/2026-11-04_to-qa-26/`

Round 25 / 25b is **DONE**; thank you. R1.11 (QA-66) landed in `5611332`. QA-65 landed in `c10c06b` (the real code this time — 9d0118f was board-only). Research leads stay parked. Build: master at the commit that added this folder. No Docker, CFD, OpenFOAM, Assess, Sweep or Optimize run. Pre-register A and B before data.

| # | task | board |
|---|---|---|
| A | **Re-check QA-66 on this master.** Confirm all three r25b rules, plus the two review follow-ups: (1) `--verify-cfd` does not label the DoE with `synthetic_label` (catalog + CFD, or refuse); (2) `run_surrogate_search.py` refuses rather than adding `--stub-labels`; (3) stub JSON stamps "synthetic labels, not CFD"; (4) empty / <8-row catalog under `--verify-cfd` refuses up front; (5) catalog load/efficiency priors stamp "prior, not CFD". Run `tests/test_surrogate_guided.py` and `tests/test_r111_cockpit_surrogate.py`. UI-31 and QA-62 stay **verified / not re-tested** unless you spot a regression. | R1.11, QA-66 |
| B | **QA-65 re-check (landed in `c10c06b`, do not re-apply the patches).** A scored design with `converged=False` must show "did not settle" in the score caption; True / missing must not. Optimize trials must carry `converged`. Run `tests/test_score_caption.py`. Quote paths. | QA-65, R1.2 |
| C | **UI-26 still on first view?** Confirm 'Gold = parametric Stock…' still renders on the first view in Simple and Expert. Other UI (27, 29, 32–38) and QA-40, 42, 61, 63 stay **still open / not re-tested**. Note new bugs. | UI-26 |
| D | (still waiting) R3.1 export leak check, when R3.1 lands. Re-run the r21 A claims audit once R1.10 lands. QA-64 strings wait on R1.10. | R3.1, R1.10 |

Notes to `docs/qa/notes/r26-*.md`, plus a "Round 26" section below.
