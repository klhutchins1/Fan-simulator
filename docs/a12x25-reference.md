# NF-A12x25 Reference Data (validation ground truth)

Published manufacturer specs for the **Noctua NF-A12x25 PWM** — the target our CFD must
eventually reproduce (within a stated tolerance) before any absolute-performance claim.
Sources: [Noctua specs](https://noctua.at/en/nf-a12x25-pwm/specification),
[PCPartPicker](https://pcpartpicker.com/product/zxx2FT/noctua-nf-a12x25-pwm-601-cfm-120mm-fan-nf-a12x25-pwm).

| Quantity | Published value | SI |
|---|---|---|
| Max rotational speed | 2000 RPM | 209.4 rad/s |
| Speed range (PWM) | 450–2000 RPM | — |
| **Max airflow** (free delivery) | **60.1 CFM** | 102.1 m³/h = 0.02836 m³/s |
| **Max static pressure** (shut-off) | **2.34 mmH₂O** | **22.9 Pa** |
| **Max acoustic noise** | **22.6 dB(A)** | (18.8 dB(A) min) |
| Input power (max) | ~1.68 W | — |
| Tip clearance | **0.5 mm** | Sterrox LCP + MIM hub |
| Blade count | 9 | — |

## Acceptance budgets (geometry vs CFD)

Two **separate** gates apply before absolute-performance claims; they must not be merged into one pass/fail:

1. **Geometry fidelity** — blade count, tip/hub radii, axial depth, LE sickle character, and **0.5 mm** tip clearance vs the **110 mm** frame ID (vs trusted STL when available, else the parametric envelope).
2. **CFD fidelity** — vs this table at 2000 RPM: interim **±10%** on free-air (**60.1 CFM**) and **±5 Pa** on shut-off (**22.9 Pa**), until further validation on more fans tightens them (the CFD v5 setup — sealed ring + four-bar frame + prism layers — is validated on Stock: 59.8 vs 60.1 CFM; `docs/validation/a12x25_pq_report.md`).

Full criteria, numeric bands (e.g. tip radius **54.0–54.5 mm**, hub **20–23 mm**, **9** blades), and the rule that geometry pass **does not** imply CFD pass (and vice versa): [validation/a12x25_geometry_acceptance.md](validation/a12x25_geometry_acceptance.md).

## Historical: the reality check that drove the validation work (2026-09)

*Kept for context. Every gap below has since been closed by the validated CFD v5 setup (sealed
ring + four-bar frame + prism layers, resolved 0.5 mm tip gap, grid study); see
`docs/validation/a12x25_pq_report.md` and `docs/validation/audits/2026-09-28-audit-02-cfd-method-validation.md`.*

Our parametric Stock / approximate recipes historically under-resolved tip leakage and frame losses;
published free-air is **60.1 CFM** at 2000 RPM. Closing the gap requires a trusted impeller mesh
(see `validation/reference/a12x25_impeller.stl`), resolved tip gap (**0.5 mm**), and honest duct/frame
physics — not datasheet-tuning of BEM alone:
- **Slip duct walls** remove all duct friction (real ducts/frames add loss).
- **No fan frame / motor struts / venturi inlet** — the real fan has flow-blocking structure.
- **No resolved tip-leakage** (0.5 mm gap, ~1 mesh cell) — a dominant real loss.
- **Fully-turbulent SST at transitional Re**, coarse mesh (grid convergence pending).
- Geometry mismatch: parametric planform vs close-reference STL (blade count must be **9**).

## Validation plan (review §6.1)

1. Prefer the **close-reference STL** under `validation/reference/a12x25_impeller.stl` (user-provided;
   not OEM CAD) over envelope-only parametric builds for absolute CFD claims.
2. Run the full **P–Q curve** at 2000 RPM and compare to (60.1 CFM free-air, 22.9 Pa
   shut-off). Report the error.
3. Add the missing physics in priority of impact: resolved tip gap → frame struts/venturi →
   no-slip walls → grid convergence → transition model — and watch the error shrink.
4. Only once free-air CFM and shut-off pressure land within a documented tolerance do
   absolute numbers (and any "beats stock" claim) become defensible. Relative rankings on a
   controlled printed baseline remain valid before then.

## Noise target
22.6 dB(A) max is the number the noise tier (FluidX3D LBM: Curle dipole → BPF tone + relative dB(A)) must eventually reproduce. Today it ranks designs relatively; it is not yet calibrated to absolute dB(A).
