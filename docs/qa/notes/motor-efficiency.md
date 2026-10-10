# Motor efficiency for the score derate (Task C, round 6)

Status: done (research only, no patch). Sources are linked and summarised, and only numbers are quoted (with citations).

## Plain-language verdict
- **Proposed motor efficiency (electrical in → shaft out, driver IC included): η_m = 0.50, plausible range 0.40–0.65.**
- 0.40 is the pessimistic end of that range, not a typical value.
- The bigger issue is the input-power figure the derate uses. It uses Noctua's *maximum* rating (0.14 A, 1.68 W). Two independent measurements show a real NF-A12x25 at full speed draws 1.0–1.5 W. TechPowerUp says the 0.14 A figure includes start-up boost.
- Effect on the score: with η_m = 0.50 and the current 1.68 W input, the 5–7 % derate on the three audited designs goes away.
- If the input is instead set to the measured steady draw (1.50 W), the derate shrinks to about 1–3 %.
- Either way, 0.40 × 1.68 W overstates the penalty. Confidence in the exact number is low, because no source measured the shaft torque of this motor directly.

## Facts found (all numbers cited)
| # | Source | What it gives | Terms |
|---|---|---|---|
| S1 | Noctua NF-A12x25 PWM spec page, https://www.noctua.at/en/products/nf-a12x25-pwm/specifications | 2000 rpm max; input power max 1.68 W, typical 1.2 W; current max 0.14 A, typical 0.1 A; single-phase, 4-pole, 4-slot motor, driver IC NE-FD1 | Manufacturer page; numbers cited only |
| S2 | Cybenetics test report, Noctua NF-A12x25 (issued 2023-04-27), https://www.cybenetics.com/evaluations/fans/4/de/pdf/ | At 100 % PWM, eight P–Q points: 1978–2132 rpm, 0.110–0.125 A, **1.32–1.50 W** (highest draw at shut-off, lowest at free air) | Commercial test report, no open licence; numbers cited only |
| S3 | TechPowerUp review, https://www.techpowerup.com/review/noctua-nf-a12x25-pwm/3.html | Measured max operating current about 0.087 A (≈1.0 W at 12 V). States that the 0.14 A rating covers start-up boost | Review site; numbers cited only |
| S4 | MDPI *Machines* 2023, 11(11), 1003, https://www.mdpi.com/2075-1702/11/11/1003 | Single-phase external-rotor BLDC motor designed for a cooling fan (~2 W class). Reported efficiencies fall in the 62–69 % range. I did not check which rows are prototype measurements and which are analysis | CC BY 4.0 |
| S5 | "Design Constraints of Small Single-Phase Permanent Magnet Brushless DC Drives for Fan Applications" (IEEE; PDF copy at logosfoundation.org) | Qualitative: single-phase fan drives trade efficiency for cost and are less efficient than three-phase | IEEE copyright; citation only |
| S6 | Tezara thesis record 438732, "Performance characterization and optimization of an axial flow fan for electronic enclosures", https://tezara.org/theses/438732 | Abstract states that the overall efficiency of an axial fan (air power / electrical power) is typically 15–40 % | Abstract only; citation only |

## Derivation (my arithmetic, from S2)
- Overall static efficiency of the real fan at 100 % PWM is air power / electrical power. Units: 1 CFM = 1/2118.88 m³/s and 1 mmAq = 9.80665 Pa.
  - It peaks at **≈13.4 %** (31.51 CFM, 1.36 mmAq, 1.48 W) and is 13.3 % at 40.08 CFM.
- Overall efficiency = η_aero × η_m.
  - If the real impeller's aerodynamic static efficiency at that point is 0.25–0.35 (assumed, not measured), then η_m ≈ 0.38–0.54.
  - S4 gives an upper bound of about 0.62–0.69 for a purpose-designed motor, before driver-IC losses.
- I combine these as a central value of 0.50 with a range of 0.40–0.65.
- Consistency check: for the CFD Stock replica (0.775 W shaft at 2000 rpm) to run on the real 1.50 W draw, it needs η_m ≥ 0.52. This is a model statement, not a measurement.

## Effect on the derate
λ = min(1, (budget / shaft)^(1/3)). Shaft powers are taken from the round-4 scored-vs-raw audit: Stock 0.775 W and the two other audited designs at 0.811 and 0.825 W.

| input W | η_m | budget W | λ Stock | λ 0.811 | λ 0.825 |
|---|---|---|---|---|---|
| 1.68 (current) | 0.40 (current) | 0.672 | 0.954 | 0.939 | 0.934 |
| 1.68 | **0.50** | 0.840 | 1.000 | 1.000 | 1.000 |
| 1.68 | 0.65 | 1.092 | 1.000 | 1.000 | 1.000 |
| 1.50 (S2 measured) | 0.40 | 0.600 | 0.918 | 0.904 | 0.899 |
| 1.50 | **0.50** | 0.750 | 0.989 | 0.974 | 0.969 |
| 1.50 | 0.65 | 0.975 | 1.000 | 1.000 | 1.000 |

- The first row reproduces the round-4 implied derates (0.954 / 0.939 / 0.934), which confirms the formula.
- Break-even η_m with 1.68 W input: 0.46 for Stock, 0.48 for the 0.811 W design and 0.49 for the 0.825 W design. Any η_m above about 0.5 removes the derate for all three designs.

## Recommendation (no patch)
1. Use η_m = 0.50 and report the 0.40–0.65 band as a sensitivity: score at both ends and flag any ranking flips.
2. Pick the input power on purpose:
   - 1.68 W means "what the motor is rated to supply";
   - 1.50 W means "what a real NF-A12x25 draws at 2000 rpm under load" (S2).
   - Make it a named constant with these citations.
3. The derate stays a soft guess until someone measures shaft torque, for example by spinning the motor with the impeller removed and with a calibrated load.
