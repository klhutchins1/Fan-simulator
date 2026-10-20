# Claude → QA bot, 2026-10-20: round 19 (do round 18 first if you haven't)

`fansim.bundle` here is master at the commit that added this folder.

## ▶ Then: round 19 (queued by Claude 2026-10-20; after round 18). Delivered as `handoff/2026-10-20_to-qa-19/`

Context: prop CFD rung B came back **B2 sectional** (CFD C_T −40 to −58 % at J 0.20–0.43). BEMT on the same generic section
is also −15 to −29 %, so the APC SF geometry (no published airfoil) can't validate CFD on its own. "Fixed" now needs a
prop with **known sections** (the results section of `docs/validation/audits/2026-10-17-prop-cfd-fix-prereg.md`).

| # | task | board |
|---|---|---|
| A | **A measured small prop with fully specified airfoil sections.** We need 5–12″ diameter, chord **and** twist **and** the named airfoil (or coordinates) per station, plus measured C_T and C_P at static and over J, under an open licence or public domain. Start with UIUC's own designs (Selig's group published geometry + airfoil for some props in the UIUC Propeller Database), NASA/TU Delft open props (e.g. TUD-XPROP), and any CC-BY paper with a printed or CNC prop. For each: URL, licence, geometry completeness, Re(0.75R) range, data format. Pick the best and say what we'd pre-register | R2.2 |
| B | **How good is BEMT on known sections?** For the best candidate from A, run fansim's BEMT (`fansim.propeller.bemt.analyze`, NeuralFoil and the default polars) against the measured C_T and C_P. Pre-register "agree" first (suggested: C_T ±15 %, C_P ±20 % at static and mid J). This tells us whether the APC SF deficit grows with J because of the generic section | R2.1 / R2.2 |

Notes to `docs/qa/notes/r19-*.md`, plus a "Round 19" section below.
