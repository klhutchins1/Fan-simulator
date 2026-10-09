# FDM layer-adhesion knockdown in the structural gate

**Date:** 2026-09-03  
**Status:** accepted  
**Approach:** Keep the uniform-bar centrifugal formula. Score safety factor against `yield * 0.60` (layer adhesion), not in-plane yield. No FEA, no flutter this cycle.  
**Roadmap:** §1.3 stage 1. Not §7.6 sim→print flow penalty, not first-mode / flutter.

## Plain language

FDM blades fail between layers, not along them. The structural gate today uses datasheet (in-plane) yield, so a blade that would delaminate still looks fine. Knock the allowable stress to 60% — the middle of the 50–70% band in the roadmap — and leave the centrifugal formula alone. At 2000 RPM on a 120 mm fan the gate still almost never binds; it binds on the high-RPM / long-span pathologies it was meant to catch, a bit earlier.

## Problem

`centrifugal_root_stress`:

```text
sigma = rho * omega² * (r_tip² - r_hub²) / 2
sf    = yield_strength_mpa / sigma
ok    = sf >= 3
```

`MATERIALS[…].yield_strength_mpa` is an in-plane FDM-part number. Inter-layer strength is typically 50–70% of that. The gate is isotropic.

## Goal

1. Default knockdown `LAYER_ADHESION_K = 0.60`. Allowable = `yield_strength_mpa * K`.
2. Safety factor uses allowable, not in-plane yield. `CentrifugalReport.yield_mpa` becomes the **allowable** (so existing `ok` / `reason` stay consistent). Stamp `in_plane_yield_mpa` and `adhesion_k` on the report.
3. Same `min_safety_factor = 3.0`. Same formula for `sigma_root`. Same materials table (do not rewrite PETG 50 MPa to 30).
4. `K = 1.0` is an explicit argument for a later resin path; default is 0.60. No CLI flag — the optimizer / Assess / `evaluate_candidate` inherit the default.
5. Existing 2000 RPM PETG case stays `ok` with `sigma_root_mpa < 1`.

## Non-goals

- Flutter / first-mode / Campbell diagram
- FEA, anisotropy tensor, print-orientation as a search DOF
- Sim→print flow/roughness penalty (§7.6)
- Changing `MATERIALS` in-plane numbers
- Infill-aware weight (§2.4)

## Tests

`tests/test_optimize.py` (or a thin `tests/test_stress.py`):

- Default PETG 2000 RPM: still `ok`, sigma < 1 MPa (existing test)
- `adhesion_k=0.60` SF is `0.60` times the `adhesion_k=1.0` SF on the same blade (sigma unchanged)
- A high-RPM blade that passes at `K=1` fails at default `K=0.60` (construct via `BladeParams.rpm`, not Docker)
- Reason mentions layer-adhesion when not `ok`
- `adhesion_k` and `in_plane_yield_mpa` on the report

No Docker. No new dependencies.

## Files

| Path | Responsibility |
|---|---|
| `fansim/structural/stress.py` | `LAYER_ADHESION_K`, knockdown, extra report fields |
| `tests/test_optimize.py` or `tests/test_stress.py` | SF ratio + fail-closed case |
| `docs/roadmap.md` | §1.3 stage 1 done; flutter still open |
