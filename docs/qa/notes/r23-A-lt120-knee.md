# r23 A: is 13.71 Pa / 60 CFM on lt120's knee? (no CFD)

QA bot, 2026-10-31. Master **3b92eea**. Prereg **0006f9b** (`prereg_r6`, branch `prereg/round23`,
`qa_r23/PREREG_R23.md` §A, committed 12:19 MDT before any data). Script: `handoff/2026-10-31_from-qa-23/scripts/a_knee.py`.
Data: `handoff/2026-10-31_from-qa-23/data/a_knee.json`. Run time 0.4 s. No CFD, no source edits.

## Verdict: **at the knee** (robust: 100 % of 5000 Monte Carlo draws)

The 13.71 Pa / 60 CFM point sits at the high-flow end of a measured plateau (40–60 CFM). The CFD does not
reproduce that plateau: it stays on a steep branch through 17.14 Pa, so the CFD shape **does not agree**.

## Measured slopes (`docs/qa/benchmarks/lt120/curve.csv`, 2000 rpm, static)

| segment (CFM) | ΔP (Pa) | slope (Pa/CFM) | slope (Pa per m³/s) | ÷ s_steep | class |
|---|---|---|---|---|---|
| 8 → 32 | 34.01 → 17.14 | −0.703 | −1490 | 1.00 | steep |
| 32 → 40 | 17.14 → 14.69 | −0.307 | −650 | 0.44 | flat |
| 40 → 60 | 14.69 → 13.71 | **−0.049** | −104 | 0.07 | flat |
| 60 → 84 | 13.71 → 6.85 | −0.286 | −606 | 0.41 | flat |

- Both segments next to 60 CFM are *flat*, and none are *rising*, so by the pre-registered definitions the point is **at the
  knee**, not past it. The 5 points do not resolve a stall dip (no rising segment).
- The 40–60 CFM slope is 5.8× flatter than the 60–84 CFM slope. 60 CFM is where the curve stops being flat on the way to
  free air.
- **Uncertainty:** Q ±3 %, ΔP ±0.5 Pa, uniform. `source.md` says the rig uncertainty is unknown, so the prereg default
  was used. Over 5000 draws (seed 23), 100 % gave "at the knee".
- Knee location (slope crosses 0.5·s_steep): **34 CFM** (MC p5–p95 31–39 CFM). That marks the low-flow end of the
  plateau. s_steep is set by the near-shutoff segment, so all later segments count as "flat".
  - Exploratory: with s_steep taken from 32–84 CFM only, the classes are steep / flat / steep, which is still "at the knee".
- PCHIP derivative (report-only): −0.082 Pa/CFM at 60 CFM and −0.415 Pa/CFM at 84 CFM. At 60 CFM the curve is about 5× flatter.
  - Practical consequence: near 13.71 Pa, 1 Pa of pressure error is worth about 12 CFM (≈ 20 %) of flow.

## CFD shape (numbers from the 2026-10-18 and 2026-10-30 lt120 audits)

| CFD series | points (CFM @ Pa) | slope 6.85–13.71 (Pa/CFM) | CFD ÷ measured | class at 13.71 | error at 13.71 / 6.85 |
|---|---|---|---|---|---|
| 0.5 mm, 5.8 mm mesh | 65.0@17.14, 72.4@14.69, 74.7@13.71, 89.6@6.85 | −0.460 | **1.61** | on the steep branch | +24.5 % / +6.7 % |
| 0.5 mm, 6.2 mm mesh | 65.5@17.14 (INCONCL.), 73.7, 76.2, 92.0 | −0.434 | 1.52 | on the steep branch | +27.0 % / +9.5 % |
| 1.0 mm gap | 77.3@13.71, 94.9@6.85 | −0.390 | 1.36 | n/a (1 segment) | +28.8 % / +13.0 % |
| 1.5 mm gap | 54.2@13.71 (INCONCL.), 89.3@6.85 | −0.195 | 0.68 | n/a (1 segment) | −9.7 % / +6.3 % |

- Neither CFD series has a free-air point. The prereg's "free → 6.85 → 13.71" shape is therefore built from the loaded
  points only (deviation; see the handoff README).
- The CFD is **steeper** than the measurement on 6.85–13.71 Pa (ratio 1.5–1.6, not < 0.5). Every CFD segment from 65 to 90 CFM
  is steep. There is no plateau, so 13.71 Pa lands at 75 CFM instead of 60.
- **CFD shape agrees: NO.** The CFD class is "on the steep branch"; the measured class is "at the knee".
- Only the unconverged 1.5 mm point falls onto the plateau region (54 CFM). That fits Claude's knee-bistability reading,
  but it is one INCONCLUSIVE point.

## Tutar & Cam 2025 (their own CFD)

- **Citation:** Tutar, M.; Cam, J.B. "Computational Design of an Energy-Efficient Small Axial-Flow Fan Using Staggered Blades
  with Winglets", Int. J. Turbomach. Propuls. Power 2025, 10(1), 1, https://doi.org/10.3390/ijtpp10010001.
- **Licence:** CC BY 4.0, verified on the PDF's first page ("Creative Commons Attribution (CC BY) license … /by/4.0/").
  It is not NC/ND. Even so, only figure numbers and approximate read-offs are cited here; no data was copied into the repo.
- **What they did:** Fluent MRF RANS with a velocity inlet. Flow is *prescribed* at the 5 measured flows (8/32/40/60/84 cfm)
  and the static pressure is computed. There are 4 meshes (Fig. 8) and 3 turbulence models (Fig. 9). The text gives
  numbers only as a mean pressure deviation of 2.0 % (M3) and 1.5 % (M4) over 60–80 cfm. Table 3 holds efficiencies at
  60 cfm, not P–Q values.
- **Do they report this fan near 6.85 and 13.71 Pa?** Yes, in **Figs. 8 and 9** (graphs only). Approximate read-off,
  ±0.5 Pa (QA digitisation, `a/digitize_tc.py` in scratch):
  - RNG k–ε, 3 M cells: ≈ 6.1 Pa at 84 cfm, ≈ 12.7 Pa at 60 cfm, ≈ 13.8 Pa at 40 cfm.
  - 3.77 M cells: ≈ 6.0, 12.7 and 13.9 Pa at the same flows.
- **Their own description:** 40–60 cfm is a "stall range". There, "the decrease rate of the pressure rise becomes
  significantly retarded … up to a local peak point signifying the end of the stall regime"; above 60 cfm is the
  "pre-stall regime". The authors themselves place 60 cfm at the edge of the flat stall range, which agrees with A.
- **Prereg outcome:**
  - **6.85 Pa: matched.** Read as flow at that pressure, ≈ 81 cfm (−3.5 %).
  - **13.71 Pa: did not match.** On their RNG curve, 13.71 Pa is crossed at ≈ 41 cfm (38–50 cfm with ±0.5 Pa read
    error), i.e. −15 % to −36 % against 60 cfm.
  - In their own pressure-at-prescribed-flow terms, they are only about −7 % low at 60 cfm. The miss in flow terms is the
    plateau effect itself: a small pressure error becomes a large flow error. Tutar & Cam's own CFD shows the plateau that
    ours lacks, but it sits about 1 Pa low, so even a CFD that has the right shape cannot pin the flow at 13.71 Pa.
- Side note: they cite Lin & Tsai as "Int. J. Adv. Eng. Innov. Technol. 2010, 225, 885–895". The repo's `source.md`
  citation (Proc. IMechE C 225(4), doi:10.1243/09544062JMES2231) is the correct one; the volume and pages match.

## Release-text check (feeds QA-64)

- 6.85 Pa is about 20 % of the measured near-shut-off pressure (34 Pa) and lies on the stable branch. It is not free air,
  and the dataset has no free-air point.
- The +8.1 % is the mean of the two meshes; the 6.2 mm mesh alone is +9.5 %.
- So the proposed wording "validated near free air on three published fans, within 8 %" slightly overstates lt120. See QA-64.
