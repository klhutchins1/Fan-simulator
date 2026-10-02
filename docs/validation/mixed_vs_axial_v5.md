# Mixed-flow vs axial, CFD v5 (2026-10-02)

Replaces the 2026-09-05 campaign, which solved the mixed-flow rotor backwards (Audit #7) in the v4
full-length tube (−34 % pipe friction, Audit #2) on a non-adaptive mesh. Its "axial wins"
conclusion is withdrawn.

## Setup (identical for both)

- Domain: CFD v5, sealed 25 mm frame ring plus four-bar frame. Mesh: wall-sized surface refinement
  (`MeshResolution.for_blade`, floor `OPTIMIZER_SURF_MAX_FLOOR`). Base cell 5 mm. 1000 iterations,
  16 procs.
- Rotation: 2000 rpm, each rotor turning its designed way (axial and mixed-flow flipped copies at
  spin −1).
- Hose: "case", 8 Pa at 50 CFM (ΔP = kQ²), inside the axial fan's validated unstalled range. Print
  penalty on. Motor derate applied.
- Axial: Stock A12x25 recipe (the validated axial design). Mixed-flow: default `MixedFlowParams`
  (9 blades, 35° stagger).

## Result

| | free air | at the case hose | efficiency | converged | sanity |
|---|---|---|---|---|---|
| axial (Stock) | 54.4 CFM | **44.3 CFM** (ΔP 7.0 Pa) | 23.9 % | yes (osc 0.4 %) | physics PASS (y+ WARN) |
| mixed-flow (default) | **67.0 CFM** | **44.3 CFM** (ΔP 7.0 Pa) | 22.7 % | yes (osc 2.6 %) | physics PASS (1 skew face WARN) |

**At the case hose they tie** (44.3 vs 44.3 CFM; efficiency −1.3 points for mixed-flow). The
mixed-flow moves more air at free delivery (+23 %), but its curve is steeper, so at 8 Pa it lands
on the same operating point. The mixed-flow is also motor-limited (1975 rpm, 99 %).

## How far to trust it

- **Direction and setup:** proven for both (Audits #1 and #7).
- **Method:** the CFD method is validated against measurements on two **axial** fans (A12x25
  within −0.5 % of free air, FAN-01 within +3 % from free delivery to mid-curve). There is no
  measured mixed-flow fan to validate against, so the mixed-flow absolute numbers carry the method's
  axial-validated accuracy at best. Treat the tie as "comparable", not as a ranking.
- **Not tested here:** higher hoses (heatsink 20 Pa, radiator 35 Pa). Steady RANS is not
  trustworthy near the axial fan's stall (~20 Pa, roadmap §19.6), so a high-Pa comparison would
  need care.

Raw: `runs/campaign_mixed_vs_axial_v5/summary.json`. Command:
`uv run python scripts/run_mixed_vs_axial.py --preset case --out runs/campaign_mixed_vs_axial_v5`.
Wall time 1 h 40 min (pilot estimate ~2 h 20 min with margin).
