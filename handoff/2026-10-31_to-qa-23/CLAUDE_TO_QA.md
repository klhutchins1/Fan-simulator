# Claude → QA bot, 2026-10-31: round 23

`fansim.bundle` here is master at the commit that added this folder. Clone it fresh.

## ▶ Next round for the QA bot: round 23 (queued by Claude 2026-10-31 for Kimball). Delivered as `handoff/2026-10-31_to-qa-23/`

Round 22 is **DONE** (results below); thank you. Build: master at the commit that added the folder. Pre-register A and B
before data. No CFD.

Context: lt120 is **TRENDS** (`docs/validation/audits/2026-10-18-lt120-validation-prereg.md`): CFD +8 % at 6.85 Pa, +26 % at
13.71 Pa. The tip-gap follow-up (`2026-10-30-lt120-tip-gap-prereg.md`) came back **G3, not explained**:
- at 1.0 mm the error got worse (+28.9 %);
- at 1.5 mm it flipped to −9.6 % but was INCONCLUSIVE.

Claude's reading is that 13.71 Pa sits on the **knee** of the curve, where steady CFD is sensitive. Please test that reading
independently.

| # | task | board |
|---|---|---|
| A | **Is 13.71 Pa on lt120's knee?** From the measured curve (`docs/qa/benchmarks/lt120/curve.csv`, 5 points) and the CFD points (`runs` numbers in both audit files): estimate the measured slope dΔP/dQ between neighbouring points, and where the curve flattens or turns (the stall dip). Say whether 13.71 Pa / 60 CFM is on the steep stable branch, at the knee, or past it, with the uncertainty that only 5 points allow. Compare with the CFD curve's shape. Also check Tutar & Cam 2025's own CFD of this fan, if the paper reports it at these points: did *they* match 13.71 Pa? Pre-register what "on the knee" means before computing | R1.1b follow-up |
| B | **Draft spec: a "near the knee" warning for a design's loaded point** (roadmap item "Loaded-point fidelity near the knee"). Using only what Assess already has (the free-air solve, the loaded probe, and the 2-point fan line in `fansim/optimize/system_curve.py`), propose a cheap rule that flags when a design's loaded operating point is likely near its knee. Test it on the cases we have: A12x25 Stock (5/10 Pa held; 15/20 Pa didn't converge), lt120 (6.85 good, 13.71 bad), FAN-01. Give its hit / miss on those, and the false-flag risk. Proposal only; no source edits | roadmap |
| C | (still waiting) R3.1 export leak check, when R3.1 lands. Also re-run the r21 A claims audit once R1.10 lands | R3.1, R1.10 |

Notes to `docs/qa/notes/r23-*.md`, plus a "Round 23" section below.
