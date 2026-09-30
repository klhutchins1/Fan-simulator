# Audit #5: structural models vs closed-form solutions (2026-09-29)

Question: do `fansim/structural/` (deflection, stress, flutter, balance), the tip-deflection factor in
`fansim/optimize/print_penalty.py`, and the FDM checks in `fansim/manufacturability/` solve their own
equations correctly, with consistent units and defensible material data?

## Plain-language verdict

- **structural.deflection: PASS** (verification). Uniform-load tip deflection equals q L^4 / (8 E I) to 1e-9
  (tolerance 2%) on 3 materials x 3 prismatic sections; an independent Hermite FE agrees to < 0.1%. Units are
  consistent (mm geometry, Pa load, GPa E, mm result). Material E / yield / density / HDT sit inside datasheet ranges.
- **structural.centrifugal: PASS.** sigma = rho w^2 (R^2 - r^2)/2 matches the closed form and a numerical integral of
  rho w^2 r dr to < 1e-6 (3 rpm/radius/material cases). Output is MPa; SF = 0.6 x yield / sigma; independent of section.
- **structural.flutter: PASS** as a *resonance gate*. f1 = (1.875^2/2pi) sqrt(EI/(rho A L^4)) matches the closed form to
  1e-9 and a Hermite FE eigenvalue to < 1% (tolerance 1%). It is not aeroelastic flutter (the docstring says so).
- **structural.balance: PASS after one bug fix.** Sums, F = U w^2, couple, counterweight, equal and generated uneven
  spacings all exact. Bug found and fixed (below).
- **Absent (closed 2026-09-30 / §19.17):** tip point-load δ = P L³/(3EI) and root bending
  σ = M c / I now exist (`tip_deflection_point_load_mm`, `root_bending_stress`); `RESIN` is in
  `MATERIALS`.
- **Not validated against reality:** the models are verified against textbook beam theory, not against a printed blade
  or FEA. The Stock v2 blade is a wide tapered plate (aspect ratio < 1.5), where Euler-Bernoulli beam theory is out
  of its regime. Verification here does not show the numbers are right for the real blade (19.18).

## Pre-registered tolerances (fixed before running any check)

| unit | quantity | tolerance |
|---|---|---|
| deflection | uniform-load tip delta vs q L^4/(8EI), prismatic beam | rel err <= 2% |
| deflection | FE harness vs PL^3/(3EI) and q L^4/(8EI) | <= 0.1% (harness check only) |
| centrifugal | sigma vs rho w^2 (R^2-r^2)/2 and vs integral of rho w^2 r dr | rel err <= 1e-6 |
| flutter | f1 vs closed form; f1 vs Hermite FE (40 elements) | rel err <= 1% |
| balance | residual after generation / counterweight | <= 1e-8 normalized; exact sums to 1e-9 |
| materials | E, yield, density, HDT vs datasheet ranges | inside the range listed in the test |
| units | mm vs m, Pa vs MPa | hand SI anchor to 1e-9 |

Tolerances were not changed after seeing data.

## 1. Inventory: what the code claims

- `deflection.py`: blade = uniform rectangular cantilever of tip-station chord x (thickness x chord), span = tip - hub;
  hose pressure loads it as q = dP x chord; delta = q L^4/(8EI); E knocked down by `FDM_E_K` = 0.70 (non-resin).
  Gate: delta < leftover tip gap.
- `stress.py`: root stress of a uniform rotating bar, sigma = rho w^2 (R^2 - r^2)/2 with r = hub radius; allowable =
  yield x `LAYER_ADHESION_K` 0.60; required SF 3.
- `flutter.py`: f1 of a uniform cantilever using the mid-span (nearest r/R = 0.5) chord and thickness, same E knockdown;
  gate f1 >= 1.2 x blade-pass frequency (n_blades x rpm/60).
- `balance.py`: static unbalance sum m r e^{i theta}, couple sum m r z e^{i theta}, F = U w^2, counterweight, and
  generated balanced uneven spacings (pair method for even N, Newton projection otherwise).
- `print_penalty.py`: printed CFM = CFD x 0.95 x k_fsi, k_fsi = max(0.90, 1 - 0.5 delta/gap), eta x 0.92-0.96. These
  are **empirical constants with no source**; only their bounds and monotonicity are testable here.
- `manufacturability/fdm_rules.py`: section wall = thickness fraction x chord (mm), body >= 2 x nozzle, tip >= 1 x
  nozzle. Checked for units and threshold. `mount_gauge`, `print_export`, `printability_score` are geometry / heuristics
  outside this audit.

## 2. Verification results (`tests/audit/test_structural_audit.py`)

| check | result |
|---|---|
| Uniform-load delta, 9 cases (PETG/PLA/ABS) | PASS, rel err 0 (< 1e-9); FE within 1e-3 |
| Scaling: linear in load, L^4 in span, 1/8 for 2x thickness; absolute SI anchor | PASS |
| Centrifugal vs closed form and vs integral, 2000 to 30000 rpm | PASS, < 1e-6 |
| Centrifugal independent of chord/thickness; ok flag flips with rpm | PASS |
| lambda = 1.875104 solves cos(l) cosh(l) = -1 | PASS |
| f1 closed form and Hermite FE, 9 cases | PASS, closed form exact, FE < 1% |
| BPF, margin, `max_blades_for_margin` | PASS |
| Balance: phasor sum, exact values, F = U w^2, couple, counterweight | PASS |
| Uneven spacing balanced (N = 4..9) | PASS |
| Uneven spacing with per-blade masses | **FAIL before fix, PASS after** |
| Print penalty k_fsi in [0.90, 1], monotone; FDM wall in mm | PASS |

Stock v2 (9 blades, 2000 rpm, PETG, 10 Pa): tip deflection 0.0008 mm; centrifugal 0.070 MPa (SF 429); f1 387 Hz,
BPF 300 Hz, **margin 1.29 vs the 1.2 gate**: Stock passes the resonance gate narrowly.

## 3. Bugs

1. `balance.balanced_uneven_spacing` sorted the angles before returning. With per-blade `masses`/`radii` the balance
   is solved for a specific mass-to-angle pairing, so sorting broke it (normalized unbalance 0.021 instead of ~1e-14
   for a 5-blade case; the docstring promised `is_balanced(result)`). Fixed: keep blade order when masses/radii are
   given, sort otherwise. No production caller passes masses today (latent).
2. Dead code: `_fdm_e_factor` has a RESIN branch but `MATERIALS` has no resin, and an unused `mat` variable. Not changed.

## 4. Material data vs datasheets (sources in the test)

| material | code E / yield / rho / HDT | datasheet class | verdict |
|---|---|---|---|
| PLA | 3.5 GPa / 50 MPa / 1240 / 55 C | NatureWorks Ingeo 3D850: E ~3.5, yield ~60, 1240 | inside; yield at the low (printed) end |
| PLA+ | 3.0 / 45 / 1240 / 60 | vendor dependent | inside a wide range; unsourced |
| PETG | 2.1 / 50 / 1270 / 70 | Eastman Amphora AM: E 2.0-2.2, yield ~50, 1270, HDT ~70 | inside |
| ABS | 2.0 / 40 / 1040 / 95 | ASTM D638 generic: E 1.8-2.6, yield 33-45, 1040-1060 | inside |
| TPU | 0.02 / 25 / 1210 / 60 | NinjaFlex / TPU 85A-95A: E 0.01-0.1, 1120-1220 | inside; wide-spread family |

The materials docstring says "representative FDM-part properties", so the values are moulded-class numbers and then
knocked down again (E x 0.7, yield x 0.6). Stacking both may double-count for PLA; harmless because none of the gates binds
for Stock.

## 5. Claims check

- `flutter.py` name overstates ("flutter") but its docstring is honest ("not flutter derivatives"). Stationary f1
  ignores centrifugal stiffening (conservative) and added air mass (non-conservative, small in air).
- `docs/bibliography.md` says balance is "code (future): fansim/structural/balance.py". The module exists and is
  tested. Corrected.
- `stress.py` says "independent of cross-section": true, verified.
- `deflection.py`: "same order-of-magnitude class as the flutter gate" is a fair description. Loading the full hose dP as
  a uniform line load normal to the chord is a conservative assumption, not a computed aerodynamic load.

## 6. Verdicts

| unit | verdict |
|---|---|
| structural.deflection | PASS (verification only) |
| structural.centrifugal | PASS |
| structural.flutter | PASS (resonance gate) |
| structural.balance | PASS (after fix) |

Ledger: the four units are recorded PASS. The physics-vs-reality gap is tracked in roadmap 19.17 / 19.18.

### Addendum 2026-09-30 (§19.17 / §19.18)

- **19.17 closed:** `root_bending_stress` (σ = M c / I) and `tip_deflection_point_load_mm`
  (δ = P L³ / 3EI) live; `RESIN` in `MATERIALS`; unused `mat` lookup removed.
- **19.18 partial:** `beam_aspect_ratio` / `BEAM_ASPECT_MIN = 1.5`. Stock tip aspect ≈ 0.98,
  mid ≈ 1.31 → `beam_regime_ok=False` with WARN reason on `deflection_report` /
  `flutter_report` (gate `ok` unchanged). Print-penalty constants documented against
  bibliography Sim→print refs + FSI design note; still provisional pending §5 hardware.
  Absolute δ / f1 trust still needs shell FEA or a printed-blade tap test.
