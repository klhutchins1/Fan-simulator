# Cursor → QA bot, 2026-11-01: round 24

`fansim.bundle` here is master at the commit that added this folder. Clone it fresh.

## ▶ Next round for the QA bot: round 24 (queued by Cursor 2026-11-01). Delivered as `handoff/2026-11-01_to-qa-24/`

Round 23 is **DONE**; thank you. 13.71 Pa / 60 CFM is at the knee. The near-knee warning draft needs more data.
Research leads stay parked. Build: master at the commit that added this folder. No Docker, CFD, OpenFOAM, Assess,
Sweep or Optimize run. Pre-register B before data.

| # | task | board |
|---|---|---|
| A | **Remaining UI and bugs on this master.** Re-check: UI-26, UI-27, UI-29, QA-40, QA-42, QA-61, QA-62, QA-63, and tooltip items UI-32 … UI-38. UI-31 (Surrogate-guided ranks with `synthetic_label`) is still on this master; Cursor is hiding it on `r111-hide-surrogate` — report **still open / verified / not re-tested** on the bundle you were given, not that branch. Note new bugs. | UI, QA-61…64 |
| B | **QA-64 wording check (no CFD).** Independently compare "Fan CFD: validated near free air on three published fans (within 8 %)" with the A12x25, FAN-01 and lt120 audit numbers. Verdict: **supported as worded / overstated / needs grok's proposed wording** ("within 10 %", and for lt120 "at its lowest measured load (6.85 Pa)"). Quote the three numbers and the files they come from. | QA-64, R1.10 |
| C | **Does Assess already show K1?** r23 B: only "loaded probe did not converge" caught the known bad points. In the cockpit results / flow card / Assess copy, is that failure already visible to the user? Quote the path. Proposal only; no source edits. | roadmap knee |
| D | (still waiting) R3.1 export leak check, when R3.1 lands. Re-run the r21 A claims audit once R1.10 lands | R3.1, R1.10 |

Notes to `docs/qa/notes/r24-*.md`, plus a "Round 24" section below.
