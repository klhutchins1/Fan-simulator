# Audit #4: axial-fan BEM pre-screen vs validated CFD (2026-09-29)

Question: does `fansim/fan_bem.py` solve its equations right, and does it do the one job it claims
(RANKING-ONLY screening of fan designs against CFD)?

## Plain-language verdict

- **Verification: PASS.** Air power never exceeds shaft power, the pressure rise crosses zero at the reported
  free-delivery flow, the P-Q curve falls monotonically past its peak, constants match the single source.
  One gap found and fixed: the swirl iteration had no convergence flag (see Bugs).
- **Validation (a) absolute, Stock v2: PASS.** BEM 58.0 CFM vs CFD 56.5 (+2.7%); flow order 0 > 5 > 10 Pa correct.
- **Validation (b) ranking: INCONCLUSIVE.** Only **3** designs exist (Stock v1, Stock v2, one re-scored
  optimizer design); the rule needs >= 5. The 3-point Spearman is 1.0 but carries no weight.
- **Validation (c) v1 above v2: PASS**, but the margin is small: BEM 61.9 vs 58.0 (+6.7%); CFD 77.4 vs 56.5 (+37%).
- **Overall: INCONCLUSIVE.** Unit `fan.bem_prescreen` is registered and **not** recorded in the ledger (stays NEW).
  To close it: about 2 more re-scored designs (each ~40 min of CFD).

## Pre-registered tolerances (fixed before any BEM-vs-CFD comparison)

| id | criterion | rule |
|---|---|---|
| a | Stock v2 free-air | BEM within +-25% of CFD (56.5 CFM); flow at 0 > 5 > 10 Pa (slope sign, order) |
| b | ranking | Spearman rho >= 0.6 between BEM and CFD free-air CFM over all designs; n < 5 -> INCONCLUSIVE |
| c | Stock v1 vs v2 | BEM free-air(v1) > free-air(v2), as CFD (77.4 > 56.5) |

Verification bounds: static air power <= shaft power (and Q*dP_total <= shaft power, ideal-actuator limit);
dP_static = 0 at reported free delivery; monotone P-Q from the peak on; iteration flagged if not converged.
Tolerances were not changed after seeing data.

CFD reference (CFD v5, ring + frame + layers, converged; `a12x25_pq_report.md`): Stock v2 56.5 / 49.8 / 40.2 CFM at
0 / 5 / 10 Pa; Stock v1 77.4 CFM at 0 Pa (its 5 / 10 Pa points are unconverged and not used). The close-ref STL has
no recipe and is unusable. Re-scored design `opt_run1_t9000`: CFD 51.72 CFM at 2000 rpm, converged, **optimizer
default mesh, not the complete setup** (so only loosely comparable to the Stock points). `opt_run1_t9001` was
infeasible in CFD and is excluded. Data: `bem_vs_cfd_audit4.json` (script `scripts/audit_bem_vs_cfd.py`).

## 1. Inventory: what the code claims

- Blade element + Euler: 20 annular elements hub to tip. Per element, a damped fixed-point iteration (cap 50)
  balances blade lift/drag against swirl momentum; dP0 = rho U dVtheta, integrated mass-weighted.
- Polar: `propeller.bemt._cl_cd` (Re-aware thin cambered-airfoil, shared with the prop BEMT).
- Losses, all **empirical buckets** tuned to Stock: SLIP 0.71 (deviation), K_TIP_LEAK 9.0 x gap/chord on
  r/R > 0.65, K_FRICTION 1.7 dynamic head; swirl KE lost unless `stator=True`. No Prandtl tip loss (ducted).
- `pq_curve`: 22 flows from 2% to 100% of 0.6 U_tip A; free delivery = interpolated zero crossing; shut-off =
  Q->0 linear intercept via `analyze.fan_curve.shut_off_pa`; peak efficiency.
- Docstring scope: RANKING-ONLY, do not quote BEM CFM as absolute.

## 2. Verification (`tests/audit/test_fan_bem_audit.py`)

| check | result |
|---|---|
| units: CFM = m3/s x CFM_PER_M3S; 0 < dP_total <= 0.95 rho U_tip^2; dP_static <= dP_total | PASS |
| Q*dP_total and Q*dP_static <= shaft power, efficiency in [0,1]; v1 and v2, 1000/2000/3500 rpm, all 22 points | PASS (to the 0.01 W output rounding) |
| dP_static = 0 at free delivery; sweep brackets it | PASS (\|dP\| < 1.5 Pa when re-evaluated at the interpolated flow) |
| monotone P-Q from the peak to the end, v1 and v2 | PASS |
| iteration converged at every point up to free delivery | PASS once the flag existed. Non-converged elements occur only past free delivery (v2 at 93-114 CFM, dP < -31 Pa, windmill region), never in a reported result |
| `CFM_PER_M3S` is the `fansim.cfd.metrics` object; `RHO_AIR` 1.2 equals it; `NU_AIR` equals `physics.air` | PASS. `RHO_AIR` and `NU_AIR` are local copies (already on the KNOWN_COPIES list), values agree |

## 3. Validation

| design | mesh | CFD CFM | BEM CFM | error |
|---|---|---|---|---|
| Stock v2 | complete | 56.5 | 58.0 | +2.7% |
| Stock v1 | complete | 77.4 | 61.9 | -20.0% |
| opt_run1_t9000 | optimizer default | 51.72 | 57.6 | +11.4% |

(a) v2 loaded points, BEM vs CFD flow: 5 Pa 52.6 vs 49.8 (+5.6%); 10 Pa 46.4 vs 40.2 (+15%). Slope sign and
ordering correct; BEM P-Q is too flat at load. **PASS.**
(b) n = 3 < 5, **INCONCLUSIVE** (Spearman 1.0, not judged).
(c) BEM v1 61.9 > v2 58.0. **PASS**, at a 6.7% spread vs 37% in CFD. BEM barely separates the two recipes and puts
v1 20% under CFD: it cannot resolve differences smaller than about 10%.

## 4. Claims check

- Docstring: "typically under-ranks CFD (~0.6x)" is **stale**: BEM is +2.7% (v2), -20% (v1), +11% (opt).
- Header comment says the buckets were calibrated to "~60 CFM free, ~23 Pa shut-off, ~25-35% eff". The model
  gives Stock v2 shut-off 40.6 Pa (datasheet 22.9, CFD loaded branch 9.5) and peak efficiency 0.53. Free-air agrees
  only because it is calibrated; shut-off and efficiency are not reproduced.
- `docs/bibliography.md` said the code has "the Prandtl finite-blade tip-loss". It does not (ducted; the source and
  `test_math_consistency` say so). Corrected. The "ranking Spearman ~0.62" figure is not reproducible from stored
  data here; this audit could only build 3 points.
- The bibliography cites Winterberg/FAN2018, Denton, Storer & Cumpsty for the loss buckets; the constants are
  fitted, not taken from those correlations.

## Bugs found

1. **No convergence flag** on the per-element swirl iteration (silently used the last iterate after 50 tries).
   Fixed: `FanPoint.converged`, `FanCurve.converged`, `N_ITER_MAX`. No number changes.
2. Docstring and bibliography inaccuracies above (fixed: docstring scope note, Prandtl claim).

No equation bugs.

## Not checked

- Ranking on >= 5 designs (blocked on CFD re-scores). Optimizer-default-mesh scores add mesh noise (roadmap 19.14).
- Loaded-branch accuracy for v1 (CFD unconverged); stalled branch; stator mode; shut-off vs CFD (no converged
  CFD); efficiency vs CFD; other rpm; the polar itself (see Audit #3, 19.15).
