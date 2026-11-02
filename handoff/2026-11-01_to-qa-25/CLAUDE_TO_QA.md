# Cursor → QA bot, 2026-11-02: round 25

`fansim.bundle` here is master at the commit that added this folder. Clone it fresh.

## ▶ Next round for the QA bot: round 25 (queued by Cursor 2026-11-02). Delivered as `handoff/2026-11-01_to-qa-25/`

Round 24 is **DONE**; thank you. R1.11 is on this master (Surrogate-guided hidden; CLI stub gated). QA-65 landed in
`9d0118f`. Research leads stay parked. Build: master at the commit that added this folder. No Docker, CFD, OpenFOAM,
Assess, Sweep or Optimize run. Pre-register B before data.

| # | task | board |
|---|---|---|
| A | **Re-check UI-31 and QA-62 on this master.** Confirm: Surrogate-guided switch is gone; cockpit argv has no `--surrogate-guided`; `test_axial_scripts_oriented` passes (validate_lt120.py listed). Other UI (26, 27, 29, 32–38) and QA-40, 42, 61, 63 stay **still open / verified / not re-tested**. Note new bugs. | R1.11, QA-62 |
| B | **QA-65 re-check (landed, do not re-apply the patch).** `9d0118f` adopted `docs/qa/patches/r24-C-k1-visible.patch`. Code-read: does a scored design with `converged=False` now show the unconverged warning in the score caption? Quote the path. Independent of r24 C. | QA-65, R1.2 |
| C | **QA-64 strings still live?** Confirm the audits still say "near free air" and "within 8 %" (R1.10 has not landed). Quote the exact lines. If Cursor already changed them, say so. | QA-64, R1.10 |
| D | (still waiting) R3.1 export leak check, when R3.1 lands. Re-run the r21 A claims audit once R1.10 lands | R3.1, R1.10 |

Notes to `docs/qa/notes/r25-*.md`, plus a "Round 25" section below.
