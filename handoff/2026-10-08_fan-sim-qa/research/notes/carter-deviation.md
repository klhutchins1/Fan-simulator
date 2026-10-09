# Lead #6: Carter's-rule deviation instead of the constant SLIP = 0.71 (investigated 2026-10-08)

**Verdict: promising, but blocked.** It noticeably reshuffles the ranking, so it must be proven against the Audit-4 CFD designs, which are on Kimball's PC. It also makes the paddle exploit worse.

## Source
- Carter's rule (1950): deviation δ = m·θ/√σ, where m = 0.23·(2a/c)² + β2/500 (β2 is the exit blade angle from axial, in degrees). For a NACA-4 line, θ = atan(2m/p) + atan(2m/(1−p)).
- I used the open-access van der Spuy & von Backström write-up for context. I did not need the Wallis book.

## Prototype
Code: `proto/bem_variants.py` (`carter=True`).
- Each element's slip = SLIP × (1 − δ/(θ + incidence)), divided by Stock's mass-averaged value of that factor (0.782).
- This keeps Stock near its current calibration, so only the *relative* effect between designs changes.

| case | base: free / shut-off / peak η | Carter |
|---|---|---|
| Stock (7-station) | 58.2 / 38.9 / 0.536 | 56.3 / 38.8 / 0.528 |
| top 5 / S03681 | 61.3–64.3 / 40.1–41.6 / ~0.54 | 60.1–63.6 / 42.4–43.9 / **0.58–0.59** |
| paddle 89° | 62.5 / 38.9 / 0.549 | **66.9 / 42.8 / 0.635** (worse exploit) |
| reversed −45° | 7.6 / 38.0 / 0.528 | 7.6 / 27.1 / 0.376 |
| 0 blades | none | none |

**Against the references:**
- Stock free 56.3 is closer to CFD Stock v2 (56.5) but further from the datasheet (60.1).
- Shut-off doesn't move, still about 39 Pa.

**Re-ranking the 517 guarded screen designs:**
- ρ = 0.946 against the current ranking. Only **19 of the top 30 stay**.
- **331 designs now beat Stock** (best +6 %), compared with 0 today. Dense 10–11-blade designs gain.
- So a re-screen would change the shortlist, but only Audit #4 can say whether the change is right.

## Effort vs gain
- Effort: S to code; M including Audit #4 (needs the CFD-scored designs in `runs/` on his PC).
- Gain: possibly better mid-pack ranking, which is what Audit-4 flagged (ρ 0.54 without t9012). Unproven.
- Risk: it rewards high stagger and solidity, including the paddle, until the QA-4 accounting fix exists.

## Status
**blocked.** Needs Audit-4's 7 CFD designs. I did not write a patch.
