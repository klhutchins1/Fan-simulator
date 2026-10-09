# First-bending vs BPF gate (stage 1)

**Date:** 2026-09-03  
**Status:** accepted  
**Approach:** Cantilever first-bending frequency from mid-span chord × thickness as a rectangle, compared to blade-passing frequency. Cheap gate after centrifugal stress. Not FEA, not flutter derivatives, not FSI.  
**Roadmap:** §1.3 remaining.

## Plain language

The structural gate only checks centrifugal root stress. A printed blade can still sit near a resonance. Stage 1 estimates the first bending frequency of a cantilever bar and rejects when it is too close to BPF (n_blades × RPM / 60). Default PETG A12-class blades stay well above; TPU or extreme RPM/span can fail.

## Goal

```text
first_bending_hz(params, material) -> float
  L = (tip - hub) mm
  mid station: c, t = thickness * c
  I = c t³ / 12, μ = ρ c t
  f1 = 1.875² / (2π) * sqrt(EI / (μ L⁴))

flutter_report(...) -> ok if f1 >= 1.2 * BPF
BPF = n_blades * rpm / 60
```

`evaluate_candidate` calls it after `centrifugal_root_stress`. Fail → `_infeasible("resonance: ...")` like overstress.

## Tests

- Default `BladeParams()` PETG at 2000 RPM: `ok`.
- Same geometry TPU at 30 000 RPM: not `ok`.
- `f1` scales ~sqrt(E): PETG/TPU ratio ≈ sqrt(2.1/0.02).

## Non-goals

- FEA, unsteady aeroelastic coefficients, stall flutter
- Cockpit display
- Changing print infill stiffness
