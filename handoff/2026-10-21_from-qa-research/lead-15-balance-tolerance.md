# Lead #15: ISO 21940-11 balance tolerance + four-run (no-phase) trim, 2026-10-21

**Verdict: worth it, proposed (effort S).** The formula checks out. For every realistic printed fan, ordinary print scatter is 2–6× over
the G 2.5 tolerance (and still 1.7–2.4× over G 6.3). A "this will need a trim" line plus a four-run trim calculator is cheap and
honest. The prototype solver reproduces two published worked examples. Proposal: `../proposals/lead-15-balance-tolerance.md`.

## Formula check
- ISO 21940-11:2016 free preview (iTeh sample, `proto/lead15/iso21940-11_preview.pdf`): §4.6 defines U_res ≤ U_per, e_per = U_per/m and e_per·Ω = const for
  a grade. The grade G is e_per·Ω in mm/s. The tables were not read and none are used.
- Derivation: e_per[µm] = 1000·G/Ω = 1000·G·60/(2π·n) = **9549.3·G/n**, so **U_per[g·mm] = m[kg]·9549.3·G/n**. This matches the BTI calculator
  page and the lead's formula. e_per doesn't depend on mass; U_per scales with mass.
- Fan grades from ISO 14694 come via Vibromera (a secondary source; the standard is paid and was not read): BV-3 = G 6.3 (typical default),
  BV-4 = G 2.5, BV-5 = G 1.0.
- Lead arithmetic: 15 g at 2000 rpm and G 2.5 gives 0.179 g·mm. That is correct, **but 15 g is too light**. A printed Stock is about 30–38 g (see below).

## Tolerances for representative fansim rotors (`proto/lead15/balance_tol.py`, `table.py` → `tolerance_table.csv`)
- Mass comes from `build_impeller_parts` volumes at PETG 1270 kg/m³. The motor cup (Ø37.25 × 13 mm, 14.2 cm³) is subtracted because the builder's hub is solid.
- The low/high range is blades solid + hub at 40 % infill / fully solid; the mid value is used. Props use the `approximate_prop_blade` geometry.
- The "Typical" columns are what a print realistically delivers: one blade 1 % heavy (at its centroid radius), or a 50 µm seat or bore offset of the whole rotor.

| Rotor | rpm | m (g) | e_per G2.5 / G6.3 (µm) | U_per G2.5 / G6.3 (g·mm) | blob at 0.9 R (mg) G2.5 / G6.3 | 1 % blade (g·mm) | 50 µm offset (g·mm) |
|---|---|---|---|---|---|---|---|
| Stock a12x25 | 2000 | 34.0 (30.2–37.7) | 11.9 / 30.1 | **0.41 / 1.02** | 8.3 / 20.8 | 2.44 | 1.70 |
| Stock a12x25 | 3900 | 34.0 | 6.1 / 15.4 | 0.21 / 0.52 | 4.2 / 10.7 | 2.44 | 1.70 |
| G_0502 (r16) | 2000 | 18.2 | 11.9 / 30.1 | 0.22 / 0.55 | 4.2 / 10.7 | 1.29 | 0.91 |
| S1_0534 (r16) | 2000 | 23.4 | 11.9 / 30.1 | 0.28 / 0.70 | 5.5 / 13.9 | 1.76 | 1.17 |
| prop 5×4.5×3 | 25 000 | 5.0 | 0.95 / 2.4 | 0.005 / 0.012 | 0.08 / 0.21 | 0.33 | 0.25 |
| prop 9×4.7×2 | 10 000 | 22.1 | 2.4 / 6.0 | 0.053 / 0.133 | 0.5 / 1.3 | 2.78 | 1.11 |

- **Fans:** typical print scatter is 2.4–6× over U_per, so a trim is needed. The e_per values (12–30 µm) are tighter than an FDM bore or motor-cup fit can hold,
  so balance has to be done **on the motor, assembled**. Balancing the loose part is meaningless.
- **Props:** ISO grades give sub-milligram blobs at 25k rpm, which is unrealistic for hobby balancing. For props, show G as information only and keep the existing practical
  "balance on a magnetic balancer" advice. Don't gate anything on it.

## Four-run solver (`balance_tol.py: four_run`)
- Model: V_i² = V0² + b² − 2·V0·b·cos(θ_i − ψ). It is linear in [1, cos θ, sin θ], solved by least squares for any ≥3 trial angles. The correction goes at ψ with
  mass TW·V0/b. This is the same as the graphical circles method, written as our own code from the published procedure.
- Synthetic exact recovery passes (angle sets 0/120/240 and 0/90/180).
- Published examples:
  - Reliabilityweb: we get 62.0 g at 40.1° against the published graphical 59 g at 42°. The residual rms is 0.38, which is the drawing error in the article.
  - Motionics: we get 2.367 g at 252.3° against the published 2.37 g at 252°.
- Monte Carlo on reading noise (median residual after one correction, as a share of the initial unbalance):
  - 2 % noise: 5–8 %;
  - **5 %: 13–19 % (p90 26–38 %)**;
  - 10 %: 26–37 %.
  Bigger trial weights help (aim for a trial that changes the reading by ≥30 %). Plan **1–2 rounds**.
- **Phone detectability:** at the Stock G2.5 limit the force is m·e·Ω² ≈ 0.034 kg × 11.9 µm × 209² ≈ 0.018 N. On a soft-mounted fan plus phone of about 0.33 kg,
  that is about 6 milli-g at 1× (33 Hz). Phone MEMS noise is about 150 µg/√Hz, roughly 50 µg in a 0.1 Hz bin, so the reading resolves comfortably. **But** it must be the 1× FFT amplitude
  (not overall RMS), with the phone rigidly taped to the fan frame in the same spot for all four runs.

## Caveats
- Single-plane (static) only. For a 25 mm thick, about 120 mm fan that's fine (aspect ratio < 0.5). Everett two-plane is not needed.
- The four-run method assumes linear response and steady speed. Motor speed must be identical across runs, which needs a fixed PWM duty or voltage.
- The mass model's hub-infill assumption moves m by ±11 %, so U_per moves by ±11 %. That doesn't change the conclusion.

## Licences
- Formulas and published shop procedure only. No ISO text or tables copied. All code is our own.

## Effort / gain
- **Effort S:** about ½ day for the helper and warning, and about 1 day with the CLI four-run calculator and tests.
- **Gain:** a real-world expectation set for users, and a working trim workflow with a phone only. No physics risk.
