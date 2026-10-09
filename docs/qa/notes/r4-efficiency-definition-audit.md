# Round 4, request 2: is the BEM's 29.4 % for Stock the same quantity as the CFD's 17.9 %?

Pre-registration: `r4-prereg-axial-crosscheck-eff-audit.md` (sha256 `1252f73f…acaf`, committed `e4db298b`).
Script: `handoff/2026-10-09_from-qa-3/scripts/eff_audit.py`; output in `results/eff_audit.json`. No CFD was run.

**Verdict: the same quantity (pre-registered rule: the definition part is ≤ 1 pp; measured −0.66 pp).**
The gap is mostly real model error: the BEM over-predicts Stock's pressure under load. One scoring step (linear η interpolation)
also pulls Stock's CFD number down by an estimated 3–4 pp.

## The formulas, traced in code
| | BEM (screen, `bem_screen.evaluate`) | CFD Assess (`objectives.evaluate_candidate`) |
|---|---|---|
| pressure | `dp_static` = static rise (axial-force or Euler minus swirl KE minus friction) | `(p_out − p_in)·ρ`, area-averaged **static** pressure at the outlet and inlet patches (`cfd/metrics.py`) |
| power | shaft power = Σ ṁ·U·vθ (blade tangential force only) | shaft power = \|M_z\|·ω on the `impeller` patch (blades **plus hub**) |
| η at one flow | Q·max(dp_static, 0) / P_shaft | Q·Δp_static / P_shaft |
| electrical? | no (motor efficiency 0.40 only sets the derate budget) | no (same) |
| operating point | fan line through the BEM free point (0 Pa) and the 8 Pa probe ∩ ΔP = kQ² (8 Pa @ 50 CFM), at **rated** rpm; η = `operating_point` evaluated **at that flow** | the same line, but flows ×λ, the probe at 8λ² Pa and the free point at the measured residual p_free·λ²; η = **linear interpolation in flow** between η_free and η_probe, clamped to η_probe past the probe |
| motor derate λ | min(1, (0.672 W / max shaft)^⅓); η unchanged | same formula, CFD torque |
| print knockdown | η × k_eta (0.92 → 0.96 by tip t/c) | same |
| cockpit shows | — | the scored `efficiency` objective, labelled just "η" |

Both are **static-pressure, shaft-power, aerodynamic** efficiencies at the hose operating point, after the same print knockdown.

## Reproduced by hand (Stock, tip t/c 0.0727, so k_eta = 0.92 + (0.0727 − 0.04)/0.06 × 0.04 = **0.9418**)
**BEM, axial mode:**
- free 59.80 CFM, probe at 8 Pa 51.21 CFM.
- Line ∩ hose gives op 50.90 CFM.
- η at op (pre-print) = **31.20 %**; × 0.9418 = **29.38 %**, matching the screen's 29.4.
- BEM shaft power is 0.61–0.64 W, under the 0.672 W budget, so λ = 1.
- Run through the CFD procedure instead: η_free 0.60 %, η_probe 30.50 %, t = 1.04 (clamped), so 30.50 % × 0.9418 = **28.72 %**.
  **Definition part: −0.66 pp.**
- Euler mode, same steps: direct 25.71 % → CFD procedure 25.11 % (−0.60 pp).

**CFD:**
- scored 17.888 / 0.9418 = **18.99 %** at the operating point, before print.
- The raw η, torque and p_free are **not** in `cfd_designs.csv` or the top-5 audit doc. I backed them out from the scored columns (see request 3):
  - λ = 0.9537, i.e. the CFD Stock is motor-limited to 1,907 rpm. That implies a rated shaft power of 0.672 / 0.9537³ = **0.775 W**.
  - p_free = 1.74 Pa.
  - The op sits at **t = 0.755** between free and probe.
- So 18.99 % = η_free + 0.755·(η_probe − η_free).
  - η_free = 1.74 Pa × 0.02586 m³/s / P_free. Assuming the free point is the 0.775 W maximum gives η_free ≈ 5.8 %, so **η_probe ≈ 23.3 %**.
  - That puts the probe shaft power at 0.1576 W of air power / 0.233 = 0.68 W. That is plausible.
  - The other assumption (probe = maximum) needs a 0.30 W free shaft, which isn't plausible.

## Where the 11.5 pp (scored) goes (axial mode; Euler in brackets)
| step | pp |
|---|---|
| BEM direct → BEM by the CFD procedure (**definition**) | −0.66 (−0.60) |
| BEM by the CFD procedure → CFD scored (**model + CFD-side procedure**) | −10.83 (−7.22) |
| … of which: linear-η interpolation pulls CFD Stock from its probe η (est. 23.3 % raw = 21.9 scored) to 17.9 | ≈ −4 (estimate, depends on the inferred values) |
| … of which: genuine BEM vs CFD physics | ≈ −6.8 (≈ −3.2) |

**Physics, at the CFD's own probe flow (41.75 CFM, rated rpm):**
- Pressure: CFD measures **8.0 Pa**; the BEM predicts **14.7 Pa** in axial mode (+83 %) and 12.0 Pa in Euler (+50 %).
- Shaft power: BEM 0.64 W vs CFD ≈ 0.68 W (inferred). At free flow it is BEM 0.61 W vs CFD up to 0.775 W.

**In plain language:** the BEM thinks Stock pushes much harder against the hose than the CFD says, and needs a bit less power to do it. That's model error, mostly the pressure.

## Two things to flag
1. **Linear η interpolation penalises fans whose operating point falls between free and probe** (Stock, t = 0.755).
   - η(Q) is curved, peaking between those points, so a straight line under-states it. Designs whose op is at or past the probe get the full probe η: t9005 has t = 1.33 and bem_9504 has t = 1.16.
   - So part of the "1.5× efficiency vs Stock" in the top-5 audit is scoring procedure, not physics.
   - Turning on `refine_op` (a third CFD at the operating point) would remove this.
2. **The CFD says Stock can't hold 2000 rpm:** it needs 0.775 W of shaft power against a 0.672 W budget (12 V × 0.14 A × **assumed** motor efficiency 0.40), so the motor derate cuts its speed.
   - The real NF-A12x25 does run at 2000 rpm. Either the CFD torque is high, or the motor efficiency assumption is low; 0.46 would suffice.
   - This cuts Stock's scored CFM by 4.6 %. It doesn't change η.
