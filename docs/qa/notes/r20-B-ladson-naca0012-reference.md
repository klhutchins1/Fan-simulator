# r20 B: Ladson NACA 0012 reference for prop CFD rung A0 (R2.2)

grok QA bot, 2026-10-21 MDT. Prereg `2c4380d`. Data: `docs/qa/r20/r20-B-ladson-naca0012-reference.csv`.

## Source and licence
**Report:** C. L. Ladson, *Effects of Independent Variation of Mach and Reynolds Numbers on the Low-Speed Aerodynamic
Characteristics of the NACA 0012 Airfoil Section*, NASA TM-4074, October 1988. NTRS 19880019495.
- NTRS copyright record: `GOV_PUBLIC_USE_PERMITTED`, a US Government work. Box copy sha256
  8e466706…2d06902 (97 pages).
- The NASA Turbulence Modeling Resource (TMR) recommends these tripped data for fully turbulent CFD at Re 6×10⁶
  (now at tmbwg.github.io/turbmodels/naca0012_val.html). Its file `CLCD_Ladson_expdata.dat` was the cross-check.

**The test:**
- Langley Low-Turbulence Pressure Tunnel, 2-D model of chord 0.601 m.
- Transition fixed with carborundum strips at 0.05c on both surfaces.
- C_l comes from surface-pressure integration and C_d from a wake survey.
- The data include standard low-speed wall corrections (Allen & Vincenti, about 2 %).

**Tables used (M 0.15):**
- Table IX: 80 grit, R 5.95×10⁶. The title prints "80-W" while the report's list says "80".
- Table XI: 120 grit, R 6.00×10⁶.
- Table XIII: 180 grit, R 5.95×10⁶.

## Reference (pre-registered method: linear in α per grit, mean of 3 grits)
| α | C_l ref | C_d ref | A0 pass window |
|---|---|---|---|
| 0° | −0.0088 (≈ 0) | **0.00808** ± 0.00020 (2.5 %) | C_d 0.00646–0.00969 (±20 %) |
| 5° | **0.5372** | 0.00848 | C_l 0.5104–0.5641 (±5 %) |
| 10° | **1.0628** ± 0.0192 (1.8 %) | 0.01169 | C_l 1.0097–1.1160 (±5 %) |

- **Grit spread is tiny:** C_l ±0.001 at 5° and ±0.004 at 10°; C_d ≤ ±0.0002.
- **Sanity checks:**
  - The lift slope over 0–10° is 0.1072/deg, against McCroskey's best fit for Re 6×10⁶, M 0.15 of 0.1075/deg
    (−0.3 %).
  - C_l(0°) is −0.007 to −0.012 in all three grits. That is a small offset in the experiment (a symmetric CFD gives
    0). It doesn't enter the A0 pass rule.

## Uncertainty band and one disclosed design flaw
The pre-registered band is the RSS of three parts:
- half the grit range;
- |linear − nearest tabulated row|;
- the report's repeatability (C_l 0.004, C_d 0.0002, from repeat α = 0 points).

**At 5° that gives C_l ± 0.105 (19 %), which trips my own flag (> 2 %).** The cause is the nearest-row term: the
nearest rows are about 1° away (4.04–4.11° and 6.01–6.09°), so the term measures the 2° table spacing, not the
interpolation error.

**Post-hoc alternative, clearly labelled:** replace that term with |linear − quadratic through the 3 nearest rows|.
That gives:
- C_l ± 0.004 (0.8 %) at 5° and ± 0.006 (0.6 %) at 10°;
- C_d ± 0.0002–0.0003 (2.5–3.3 %).

The reference values themselves are unchanged. **Either way, the band is well inside the ±5 % C_l and ±20 % C_d pass
windows.** The pre-registered flag is reported, not hidden.

## Cross-check against the TMR file
I compared every row I used and found two differences between my reading of the scans and the TMR file:
- **80 grit, α 8.30:** C_l 0.8872 in the table and 0.8873 in the TMR file, a last-digit difference. It moves the 10°
  value by 3e-5.
- **180 grit, α 2.00:** C_l 0.2113 in the table and **0.2213** in the TMR file. The table's own l/d (25.97 =
  0.2113 / 0.00814) confirms 0.2113, so the TMR file has a typo. It doesn't affect α 0/5/10.

## Notes for rung A0
- Ladson's Re is 5.95–6.00×10⁶ at M 0.15. Run A0 at M ≈ 0.15, or note the incompressible difference (about 1 %
  Prandtl–Glauert on C_l).
- The data are tripped at 5 % chord. Fully turbulent SST is the right comparison, and TMR says so.
- **Raw table rows are not committed.** My transcription is box-only (`qa/r20_src/tm4074_tables_box_only.json`).
  NASA data are public domain anyway, but the rule is "own CSVs only".
