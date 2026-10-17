# Flow-card noise that survives a mesh change (roadmap 27.3c) — pre-registration

Written 2026-10-16, **before** scoring the three candidates. Does not re-solve CFD.
HEAD is master after `2b200d0` (round 14 queued). Inputs for candidate 1 and 3 are the **already
published** 27.3b table (`docs/validation/audits/2026-10-15-stock-flow-mesh-repeats-prereg.md`).

## Why

Proudman SWL on the Assess mesh moved −13.7 to +22.2 dB on the same Stock fan (27.3b). Kimball
stopped judging that row. This ticket asks for an estimate whose 2σ on those five meshes is ≤ 1 dB.

## Candidates (evaluate in this order; first that passes wins)

1. **Tip speed + airflow** (Ffowcs Williams / Lighthill dipole scaling). No turbulence field.
   ```
   L = 55 log10(U_tip / 1 m/s) + 10 log10(Q_free / 1 CFM)
   U_tip = RPM × 2π/60 × tip_radius
   ```
   55 is the middle of the 50–60 dipole exponent. The 10 log10 Q term is the volume/mass-flow
   scale. Relative ranking only; not dB(A).
   On m1–m5: U_tip is Stock v3 spec (2000 rpm, tip 54.5 mm) — identical. Q_free is the published
   free-air CFM of each mesh run.
2. **Proudman restricted to the wake**, downstream of the blades, away from wall-resolved cells.
   Needs the m1–m5 OpenFOAM fields. If those cases are not on disk, **skip** (do not re-run CFD).
3. **Existing BEM** `relative_fan_noise` (`fansim.optimize.multi_point`) on Stock v3 at 2000 rpm.
   Same geometry every time, so σ is exactly 0 if it is a pure function of the sliders.

## Pass rule (fixed now)

Let σ be the **sample** standard deviation (n−1) of the five L values.

- Pass the candidate if `2σ ≤ 1.0 dB`.
- If it passes, bake `HINT_MARGIN_DB = max(0.5, ceil_1dp(2σ))` (same floor/rounding as 27.3).
- The Expert noise row uses this estimate vs Stock. It stays Expert-only and never enters the
  Simple overall line. Proudman stays in the Expert numbers table, labelled mesh-dependent, and
  is still not judged.

## After baking

Judge m2–m5 against m1 on the hint: every noise row not ⚠. A failure is recorded, not re-widened.

## Results

Candidate 2 skipped: `runs/stock_flow_mesh_repeats/m{1..5}` is not on disk; no new CFD.

| candidate | 2σ (dB) | pass? |
|---|---|---|
| 1. tip speed + CFM | **0.069** | **PASS** |
| 2. wake Proudman | — | skipped (no fields) |
| 3. BEM `relative_fan_noise` | 0 (pure function of Stock sliders) | would pass; not used |

Winner: **candidate 1**. U_tip = 11.41 m/s (2000 rpm × 54.5 mm). L = 55 log10 U + 10 log10 Q:

| run | Q_free CFM | L (dB-ish) | vs m1 |
|---|---|---|---|
| m1 | 53.31 | 75.428 | — |
| m2 | 53.04 | 75.406 | −0.022 |
| m3 | 53.58 | 75.450 | +0.022 |
| m4 | 52.45 | 75.358 | −0.071 |
| m5 | 53.13 | 75.413 | −0.015 |

`HINT_MARGIN_DB = 0.5` (floor). After-bake: every |Δ| ≪ 0.5 → no ⚠. **PASS.**
