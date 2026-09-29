# Audit #2: CFD method validation (2026-09-27 … 2026-09-28)

Question: is the fan CFD math and setup right, or is something fundamentally off? This audit covers the
sanity checks, three domain fixes, a factor A/B, an external benchmark (FAN-01) and a transient pilot.

## Plain-language verdict

**The CFD method is sound in the unstalled range and validated against measurements on two fans.**
- **A12x25:** the complete setup with the close-ref STL gives free air **59.8 vs 60.1 CFM (−0.5%)**.
- **FAN-01:** the external benchmark, run on its exact published geometry, is **within +2.6% / +3.1%**
  from free delivery to mid-curve.

The remaining problems are specific and known:
1. **Near stall**, steady RANS with a frozen-rotor MRF can't follow the unsteady flow: it oscillates and
   collapses early. This is confirmed on both fans. It is a method limit, not a bug, and transient CFD
   isn't affordable on this PC (about 32 h per point).
2. **The Stock parametric blade recipe**, which the optimizer uses, over-delivers airflow by **+22–29%**.
   That is a geometry-fidelity problem.

No part of the audit points to wrong equations. Every bug found was in the setup around the solver.

## 1. Sanity checks (new, `fansim/cfd/sanity.py`, unit `cfd.sanity_checks`)

Ten checks run on every fan CFD result: mass balance, energy, power sign, thrust direction, inlet
bookkeeping, mesh quality, y+, tip Mach, converged, and duct shape. The optimizer flags a failing design
and never rejects it (user decision). `scripts/cfd_sanity.py` checks any existing case, inferring
metadata for legacy cases.

On real runs:
- Mass balance, energy, power sign and thrust direction **PASS on every converged forward-flow solve**.
- Inlet bookkeeping matches within 0.2–0.4% once the area is right.
- The checks correctly flag the near-stall points (mass-balance FAIL at 20 Pa).
- **The checks caught three setup/bookkeeping bugs:** the square-tunnel corners, the ring inlet area, and
  false positives on reversed flow.

## 2. Domain fixes (setup bugs found)

| version | domain | Stock free air | problem |
|---|---|---|---|
| v3 | square slip-wall tunnel | 58.7 (−2%) | open corners let air bypass the tips; the "match" was error cancellation |
| v4 | full-length noSlip round duct | 39.6 (−34%) | ~0.7 m of pipe friction, not free air; ~5× slower |
| **v5** | **sealed 25 mm frame ring + slip box walls** | 80.4 (+34%), no frame | tip gap real; no pipe friction |

Also fixed:
- the optimizer's MRF zone clipped the blade ends and its frame overlapped the blades (Audit #1b);
- the CROR hub overhung its MRF zones;
- the plenum and stepped-inlet casings left open bypass corners, now sealed by `check_casing_seals`.

## 3. Factor A/B (v5, ring + frame, free air)

| geometry | layers | CFM | vs 60.1 |
|---|---|---|---|
| Stock recipe | no | 73.1 | +22% |
| Stock recipe | yes | 77.4 | +29% |
| **close-ref STL** | no | 58.4 | −3% |
| **close-ref STL** | yes | **59.8** | **−0.5%** |

Geometry dominates; prism layers change the result by only 2–6%, and bring y+ to about 2 (resolved).

## 4. A12x25 full P–Q, complete setup, close-ref STL

The result is 59.8 / 52.5 / 41.0 / 26.8 / 2.2 CFM at 0 / 5 / 10 / 15 / 20 Pa.
- The points up to 10 Pa are converged and all physics checks pass.
- 15 and 20 Pa are unconverged near stall.
- The zero crossing is at ≈20–21 Pa vs 22.9 published, inside ±5 Pa, but it rests on the unconverged points.
- The formal proxy gives 28.0 Pa (FAIL by 0.1 Pa).

## 5. External benchmark FAN-01

The case is the exact CAD from Zenodo 10787093 (CC-BY-4.0). Full detail is in
`docs/validation/fan01/fan01_report.md`.

| back-pressure | CFD vs measured |
|---|---|
| 7 Pa | +2.6% (converged) |
| 64 Pa | +3.1% (converged) |
| 126 Pa (design) | −17% (unconverged) |
| 135–253 Pa | collapse (stall) |

The direction came from the rotor's own geometry. FAN-01 has the opposite handedness to the A12x25, was run
as built at spin +1, and all power and thrust signs were physical (roadmap §19.2, first use).

## 6. Transient (URANS) pilots

| fan | settings | time step | cost |
|---|---|---|---|
| A12x25 | maxCo 1.5 | ~3.4 µs | ~3 days per point |
| FAN-01 | maxCo 5, 3 outer correctors | 18 µs, but 10.6 s per step | ~32 h per point |

It is not viable on this machine. The options are recorded in roadmap §19.6.

## Units and ledger

The changes to `build_case` (ring duct, case_meta, function objects) and to the sanity checks move the
audited units to CHANGED. Their unit checks pass. `cfd.flow_direction_convention` keeps its 2026-09-26 CFD
evidence (v3 domain) until the v5 re-proof (roadmap §19.9, queued). The units are re-recorded after that
run completes.

## Not checked

- Transient near-stall behaviour.
- A mesh ladder at loaded points (v5).
- The Stock recipe loaded P–Q in the complete setup (queued).
- BEM, BEMT, acoustics and structural models (roadmap §19.5+).

## Queued long run (2026-09-28)

1. The Stock direction matrix in the v5 domain (§19.9).
2. The Stock recipe loaded P–Q in the complete setup (the §19.7 baseline).

## Addendum: long run 2026-09-28 (19:11–23:12, 3 h 58 min vs est. 5.5 h)

**Direction re-proof in the v5 ring domain (roadmap §19.9): PASS.** The designed rotation delivers 76.5 CFM
against 46.4 CFM for the reversed rotation (+65%). All runs converged. Convention verdict PASS
(production = flipped, spin −1). The ring domain nearly removes the duct-end BC bias (1–3 CFM, vs 14–18 in
the v3 square tunnel). Evidence: `direction_cfd_stock.json`, copy `direction_cfd_stock_v5.json`.

**Stock recipe loaded P–Q, complete setup (roadmap §19.7 baseline).** 0 / 5 / 10 / 15 / 20 Pa give
77.4 / 46.7 / 11.2 / −23.7 / −41.9 CFM (loaded points unconverged, 6–12% oscillation), so the shut-off is
about 11–12 Pa. The close-ref STL gives 59.8 / 52.5 / 41.0 / 26.8 / 2.2 (shut-off ≈ 20–21 Pa). The Stock
recipe is wrong at both ends: too much free air and too little pressure. This is the target for §19.7.

**Ledger:** after roadmap §19.2 (direction derived from geometry) and the v5 domain changes, the units were
re-verified by their checks (256 tests including slow) and re-recorded. 9/9 PROVEN.
