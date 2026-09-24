# Dense near-shut-off P–Q (A12x25 Stock + STL)

**Date:** 2026-09-24  
**Status:** accepted  
**Approach:** Densify the existing OpenFOAM pressure-BC P–Q sweep near stall on **both** parametric Stock and close-reference STL, with `MeshResolution.for_blade` and longer iters. Stamp shut-off from **converged** rows only via `fansim.analyze.fan_curve.shut_off_pa` (honest Q→0 when the sweep reaches near-zero flow) plus a last-two-converged proxy when it does not. Do **not** add blocked-outlet / mass-flow BCs (Approach B) or LBM (Approach C).  
**Roadmap:** §1.5 remainder (absolute shut-off / denser near-stall branch).

## Plain language

Today’s shut-off numbers are linear proxies from the last two converged back-pressure points; near-stall solves often diverge. This campaign re-runs Stock and the close-ref STL with a denser Pa ladder so we either get a converged Q≈0 intercept or document clearly that RANS still cannot sit there.

## Goal

1. Runner stamps a `shutoff` block on `validation.json` from converged `pq_rows` (map `back_pa` → `static_pa`).
2. CLI preset `--near-shutoff` sets the dense backs list + recommended iters.
3. Run Stock + STL campaigns (tip 0.5 mm, `for_blade` mesh).
4. Commit summaries + update `docs/validation/a12x25_pq_report.md` and roadmap §1.5.

## Non-goals

- Closing free-air ±10% vs 60.1 CFM (screening levers exhausted; Phase 5 / new fidelity).
- Blocked-outlet OpenFOAM BC, AMI, FW-H, datasheet claims.
- Replacing LBM `evaluate_shutoff`.

## Success criteria

| Check | Pass |
|-------|------|
| Interim shut-off (±5 Pa vs 22.9) | Prefer true `shut_off_pa` when `min(converged CFM) ≤ 5`; else last-two proxy with explicit note |
| Free-air | Record only; interim fail expected |
| Both geometries | Same backs / mesh recipe / iters |

## Backs (default `--near-shutoff`)

`0,5,10,12,14,15,16,17,18,20,22,24,26` Pa  

Mesh: `base_cell=0.006` (match §9/§11), `for_blade` via existing `_mesh`. Iters: **1200**. Procs: **8**.

## Outputs

- `runs/validate_a12x25_near_shutoff_stock/` (local)
- `runs/validate_a12x25_near_shutoff_stl/` (local)
- `docs/validation/a12x25_near_shutoff_stock_summary.json`
- `docs/validation/a12x25_near_shutoff_stl_summary.json`
- Report §12 + roadmap §1.5 note
