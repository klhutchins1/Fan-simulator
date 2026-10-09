# Lead #11: Ning / CCBlade guaranteed-convergence BEM solve (investigated 2026-10-08)

**Verdict: not worth it now. The current solver already converges everywhere we looked.**

## Source
- Ning (2014): rewrite the BEM as a single residual in the inflow angle, bracket it, and solve with Brent's method, so it always converges.
- In the fan BEM the axial velocity is fixed by the flow, so the only unknown is the swirl. The equivalent there is to bracket the swirl on [0, 0.95U] and bisect. I did not need to dig into the CCBlade code (Apache/MIT) beyond the method.

## Prototype
Code: `proto/bem_variants.py`, `solver="bracket"`.
- Results are identical to the current fixed-point solver within **0.02 Pa** on all 11 cases. The cases include paddle, reversed and 0 blades, and every case already converged.
- It is about 3× slower (0.51 s vs 0.16 s for all 11 curves).

## Convergence evidence
- **Fan BEM:** 0 of 6596 screen designs were unconverged.
- **Prop BEMT** (`proto/prop_conv.py`, 4 registry props × 5 rpm × 6 advance ratios up to windmilling): **1 of 120** unconverged (fpv_5inch, 15000 rpm, static).

## Re-ranking
Unchanged (identical numbers).

## Effort vs gain
- Effort: S–M.
- Gain: about 0 for the fan, and a small robustness gain for the prop BEMT.
- Revisit if prop sweeps start logging `converged=False`.
