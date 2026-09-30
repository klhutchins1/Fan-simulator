# CST section variables — Stage 1 investigate (§20.2 remainder)

**Date:** 2026-09-30  
**Status:** approved (Stage 1 only)  
**Approach:** Literature + fit to our polar/BEMT stack. **No optimizer DOFs, no UI knobs.**  
**Roadmap:** §20.2 remaining after NeuralFoil opt-in / RMS re-register.

## Plain language

Class-Shape Transformation (CST) parameterizes an airfoil thickness + camber with a small
coefficient vector instead of a named NACA / Selig table. Tools like NeuralFoil / AeroSandbox
can evaluate CST sections directly. Stage 1 answers whether we should expose CST as Prop
optimizer / Design variables **now**.

## What we already have

| Piece | Role |
|-------|------|
| UIUC **table** polar (default) | Discrete families; Re interp; Audit #3 regression |
| NeuralFoil **NACA4** opt-in | `naca4_name(camber, t/c)` → Cl/Cd; stall/α band shipped |
| `BladeParams` stations | chord, stagger, thickness, max_camber, camber_pos |

CST would replace (or sit beside) `max_camber` / `thickness` / family tables with a coefficient
vector per station or a single mid-span section.

## Analysis path

- **BEMT:** usable if each station still yields Cl/Cd vs α (NeuralFoil accepts CST / custom
  coordinates). Ranking-only, same as today.
- **Table backend:** CST does **not** map cleanly onto vendored UIUC CSVs → NeuralFoil (or
  XFOIL) required when CST is active.
- **Default policy:** table remains default; CST would be opt-in alongside NeuralFoil, never
  forced.

## Printability / geometry

CST changes the **section curve**, not topology. Same loft / FDM gates as open Prop. Risk is
thin TE / LE from aggressive coefficients — reuse existing thickness / printability gates.

## Go / no-go

**No-go for Stage 2 right now.**

Reasons:

1. SF static **C_P** and aspirational **0.015** C_T(J) RMS are still open on the **table** path —
   more section freedom before those clear invites datasheet-fitting noise.
2. NeuralFoil opt-in just landed; CST needs a polar backend contract (which backend, how Design
   edits coefficients, how Stock/UIUC regression stays frozen).
3. Optimizer DOF count jumps (typically 6–12 CST coeffs × stations) — needs a search-space
   design and surrogate story (§20.5) before NSGA on raw CST.

**Revisit Stage 2 when:** SF C_P is claimed or explicitly abandoned; NeuralFoil (or CST-native)
backend has a frozen contract test; and a short Optuna bound proposal exists.

## Stage 2 (parked) sketch

Only if greenlit later:

1. `SectionCST` dataclass + `section_neuralfoil_cst(...)`  
2. Prop Design: advanced panel (coeffs) defaulting off  
3. Optimize: optional `--cst` bounds; force NeuralFoil backend  
4. Keep UIUC table path untouched for Audit #3

## Non-goals

- Proven 360° α — DONE via NF ±25° + Viterna–Corrigan (see `neuralfoil_polars.py`)  
- Making NeuralFoil or CST the default  
- Fan axial BEM CST (axial uses plate/NACA families differently)
