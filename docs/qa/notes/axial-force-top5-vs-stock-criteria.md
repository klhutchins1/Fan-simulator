# Does axial-force mode put all five BEM-screen top-5 designs above Stock? (PRE-REGISTERED)

Written 2026-10-09, round 3. Written BEFORE running anything on `cfd_designs.csv` and before
opening its CFD columns. To pick the rows I read only the header, `design_id`, `geometry` and
`flat`.

## Disclosure
When I wrote this I already knew, from Claude's round-3 note, that under CFD all five of
bem_9501–9505 beat Stock, and that bem_9504 is CFD's best. That fact is about CFD, not about what
the BEM predicts. I have not computed the axial-force screen score for these designs on e48a32d.

On 2026-10-08/09 I did see their free-CFM-only numbers in axial mode, with the default 0.5 mm
gap: 66.7–68.5 against Stock's 59.8. That is a different metric from the primary one below.

## Designs
- The top 5 are `bem_9501` through `bem_9505` in `cfd_designs.csv`. I checked that their `flat`
  values are identical to QA screen designs 01_S00948, 02_T06567, 03_T06478, 04_T06559 and
  05_T05663.
- Stock is the `geometry=stock` row: `config/problems/a12x25_reference.yaml`, 7 stations.

## Primary criterion (decides the verdict)
- The metric is the QA screen's scalar score, `bem_screen.scalar_score`. It is the equal-weight
  mean of three ratios to Stock: derated, print-penalised free CFM; hose-point (8 Pa @ 50 CFM)
  CFM; and operating-point efficiency.
- Every number comes from `bem_screen.evaluate()`, the same 2000 rpm, "case" load and
  leftover-to-frame tip gap as the original screen. `pq_curve` and `operating_point` run with
  `pressure_model="axial_force"`. The patch constants are AX_SLIP 0.65, AX_K_FRICTION 1.9 and
  CD_90 1.8.
- Stock is scored through the same path, so Stock = 1.000 by construction.
- **PASS:** all five designs score strictly > 1.000.
- **FAIL:** any of the five scores ≤ 1.000, or fails to produce a score (no system-curve
  intersection).
- Feasibility guard flags are reported but do not decide the verdict.

## Reported, not deciding the verdict
- The same score under today's Euler model (Claude reports that Euler put all five below Stock).
- Each of the three objectives on its own, under both models.
- The BEM order of the five, and whether bem_9504 comes first.
- Plain free CFM from `pq_curve`, default gap, both models.
