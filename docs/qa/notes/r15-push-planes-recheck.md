# Round 15, Task D (board R0.1): re-check of the 27.3e plane fix

Master 9562574, synthetic only (no CFD). Prereg: `prereg/round15` commit 336211b (`qa_r15/PREREG_R15.md`,
sha256 6fa2b69d…b4b). Script: `handoff/2026-10-17_from-qa-15/scripts/d_planes.py` → `data/d_planes.json`
(plus a report-only `d_planes_nr59.py` variant).

## Results against the pre-registered rules

| rule | result | detail |
|---|---|---|
| D1 hand derivation | **PASS** | h = max(0.04 r_tip, 2 mm). Centres LE − 0.1 r_tip − h and TE + 0.1 r_tip + h. The code matches to 0 m (≤ 1e-12) for r_tip 54.5 mm with a 9604-like row (−16.4…+4.2 mm → slabs at −23.99 / +11.79 mm, h 2.18 mm) and a Stock-like row, and for r_tip 30 mm (h floor 2 mm). Gap to the blade = 0.1 r_tip exactly on both sides. With no blade extent, the legacy z_fan ± 0.18 r_tip is returned. |
| D2 mm→m + hub exclusion | **PASS** | Synthetic STL in mm (hub r 21.5, fillet ring 21.5–22.0, blade 22.6–54.5): with hub_r = 0.0215 m, blade_z_extent = (−0.0079, +0.0082) m (STL float32 rounding only). The ×1e-3 and the r > hub + 1 mm cut are right. Report: with hub_r = 0.018625 (spanwise default when there is no meta) or 0, the hub/fillet is counted as blade (LE −9.5 mm). Code read: `build_case` always writes `hub_radius_m` from the rig, and the fan rig takes `params.hub_radius`, so the default is not reachable from the fan tab. |
| D3a push outside the row is swirl-independent | **FAIL as registered (my grid), PASS on a tie-free grid** | With blade_z given, the mean push is 13.4004 Pa at S = 0 and drifts to 13.4102 at S = 1.5 (+0.07 %, limit 1e-9). Cause: my 60-cell radial grid puts cell centres exactly on r = 54.5 mm, and `np.hypot` rounding keeps only 46/48 of that ring, so my zero-mean swirl tilt isn't zero-mean on the code's annulus. With 59 radial cells (no ties) all four S give exactly ρ(P_b + ½u_z²) = 13.4004 Pa. Not a code defect. |
| D3b push inside the row tracks swirl | **FAIL as registered (direction), effect confirmed** | With the legacy planes the inlet slab sits inside the row, and push falls with swirl: 13.40 → 9.17 → 5.16 → 1.36 Pa (S = 0 → 1.5, −90 %). I had predicted it would *rise*. The registered direction was wrong; the dependence is large and monotonic. This is exactly the audit's 9604 symptom (inlet slab inside the row → "pushes less" on the better fan). |
| D3c swirl row still reports swirl | **PASS** | swirl_frac 0 → 0.16 → 0.43 → 0.63 under both plane choices. |
| D3d hub/tip exclusion | **PASS** | Garbage p/U at r < hub and r > tip change no metric (max diff 0). |
| D4 spanwise shares the planes | **PASS (code read)** | `spanwise.py:385-386` calls `slab_centres(... blade_z=_blade_z(case_dir, hub_r))`, the same function and extent. |

**Verdict:** the plane placement, units and hub exclusion are correct. Push measured outside the blade row
doesn't depend on swirl; measured inside, it moves strongly with swirl. Two of my registered predictions failed
because of my own setup (a grid tie, and the wrong sign for an inlet slab inside the row), not the code. Both are
recorded as failures, not re-tuned.

## Doc notes (no new QA item)
- `flow_report.py` module docstring (line 3) still says the slabs "match spanwise (z_fan ± 0.18 r_tip)". Since
  v4 that is only the fallback.
- The audit proposal's "an assertion in `compute_metrics`" that no slab overlaps the blade was not added. F2 is
  a unit test (`test_slab_centres_sit_outside_the_blade_row`) on one extent only. It's harmless while
  `slab_centres` is the only source of centres.
- The audit's pre-registration says "all 25 cases". The F2 result line counts 20 (Stock 5 + 5, 9604 5, 9610 5).
- The audit's F3 paragraph says "Proposed `BAND_TOL` (set by the bars) 0.12", then "mean 0.06, bars 0.12". The
  baked line is BAND_TOL 0.06 / BAR_TOL 0.12. The first sentence reads as if BAND_TOL were 0.12.
- My round-14 Task F margins were derived on the **v3** table the queue gave. Under v4, Claude measured more mesh
  scatter (2σ 5.7 % vs 2.9 %), so F's mean/bar proposals are v3-only and must be re-derived on v4 fields.
