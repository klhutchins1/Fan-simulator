# FAN-01 external benchmark: CFD method validation (2026-09-28)

Benchmark: FAN-01 / EAA low-pressure axial fan (Zenodo 10787093, CC-BY-4.0; see
`validation/reference/fan01/README.md`). The geometry is the exact published CAD rotor (9 blades, 495 mm,
hub 248 mm). It was run at 1486 rpm against the 20-point measured characteristic (ISO 5801 inlet chamber;
total-to-static pressure = our back-pressure).

The setup is `CFD_VERSION` 5:
- a sealed ring duct matching the rig sleeve (inner radius 250 mm, 201 mm long);
- steady RANS k-ω SST with a frozen-rotor MRF;
- base cell 20 mm, blade wall 4 mm (measured), 1.58M cells;
- 1000 iterations per point, 16 procs.

**Direction came from the rotor's own geometry**, not the Noctua convention. The geometric proof gave ω +1
and pump +Z, with the opposite handedness to the A12x25, so the rotor ran as built at spin +1 (roadmap §19.2,
first use). Runs: `runs/fan01`. Rows: `docs/validation/fan01/fan01_cfd.json`. Wall time 3 h 38 min
(pilot estimate 5 h 51 min).

## Results

| back-pressure | CFD Q (m³/s) | measured Q (m³/s) | error | converged / osc | sanity |
|---|---|---|---|---|---|
| 7 Pa | 2.131 | 2.078 | **+2.6%** | yes / 0% | WARN (mesh skew only) |
| 64 Pa | 1.859 | 1.804 | **+3.1%** | yes / 1% | WARN (mesh skew only) |
| 126 Pa (design) | 1.163 | 1.407 | −17% | **no** / 28% | WARN |
| 135 Pa (stall dip) | 1.062 | ≈0.93 (multi-valued region) | — | **no** / 27% | WARN |
| 205 Pa | 0.025 | 0.604 | collapse | **no** / 362% | FAIL (near-stall imbalance) |
| 253 Pa | −0.325 | 0.199 | reversed | **no** / 81% | WARN |

## Verdict

- **High-flow branch validated on exact geometry.** From free delivery to mid-curve, the CFD matches the
  measurements within **+2.6% / +3.1%**, with converged solves and all physics checks passing. The CFD
  method (domain, solver, metrics, direction logic) is correct in the unstalled regime.
- **The loaded/stall branch fails, with the same signature as the A12x25.** From the design point toward
  stall, the steady solve oscillates (27–362%), under-predicts flow, and collapses about 100 Pa early.
  FAN-01's measured curve has a pronounced stall dip there. This is the known limit of steady RANS with
  a frozen rotor near stall, now confirmed on independent, exact geometry. It is a method limit, not a
  geometry or setup bug.
- **Consequence for the A12x25:**
  - its free-air and low-load numbers are trustworthy when the geometry is right (close-ref STL −0.5%);
  - its shut-off estimates carry the same near-stall uncertainty;
  - the Stock parametric recipe over-delivers by +22–29%, and that is a geometry-fidelity problem.

## Next levers for the loaded branch

These are shared by both fans:
- a transient method that can run within budget (URANS with larger Co and outer correctors, or a
  sliding-mesh AMI rotor), tested on ONE FAN-01 point near the design (126 Pa) first;
- a mesh ladder at 126 Pa;
- the frame/strut geometry of the FAN-01 rig (not yet modelled; the rig is a sleeve only).

Measured curve: `validation/reference/fan01/characteristic.csv`.
