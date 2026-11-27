# Pre-registration: physically signed loading-noise proxy (#122) — 2026-11-26

**Ruling by Cursor.** Written before changing `fansim/acoustics/loading.py` (`AGENTS.md` rule 1).

## Problem

`fansim.acoustics.loading.DEFAULT_COEFFS = (2.263, -74.4, 35.55)` was fit by unconstrained OLS to
only 7 `opt_noise` Pareto finalists where blade count $B$ and per-blade thrust $T/B$ were strongly
collinear. Because $c_1 = -74.4 < 0$:

1. **Perverse thrust sign:** higher per-blade loading $T/B$ *reduces* the predicted loading-noise
   score (high-thrust designs can even score negative dB).
2. **Inverted motor-derate scaling (O7 / `#53`):** `loading_proxy_operating(7, 0.07, 0.5)` returns
   `51.21 dB` at half RPM vs `50.65 dB` at rated RPM (**+0.56 dB louder** at half speed), inverting
   dipole aeroacoustics ($W \propto B (T/B)^2 \Omega^2$).
3. **Audit claim contradiction:** `fansim/audit/registry.yaml` unit `acoustics.loading` claims
   *"Fan loading-noise ranking proxy increases with blade count and thrust/blade; operating RPM
   scales thrust by λ² (RANKING-ONLY)"*, which `c1 = -74.4` directly violates.

## Ruling

Because the 7-point `runs/opt_noise` LBM directory is absent from the repository and unconstrained
$n = 7$ OLS cannot separate collinear $B$ and $T/B$ without physical sign constraints, adopt a
physically signed default coefficient tuple while keeping the linear API and adding constrained
recalibration support:

- **`DEFAULT_COEFFS = (2.263, 100.0, 34.0)`:**
  - Keeps the empirical blade-count slope $c_0 = 2.263\text{ dB/blade}$ (the robust signal in the
    7-point LBM data, Spearman $\rho = 0.86$).
  - Replaces the confounded negative $c_1 = -74.4$ with a physically positive loading slope
    $c_1 = +100.0\text{ dB/N}$ (sub-dominant to $c_0$ over typical 120 mm PC-fan spreads
    $\Delta(T/B) \sim 0.005\text{–}0.015\text{ N}$ while strictly penalizing higher blade loading
    and strictly lowering predicted noise when motor-derated).
  - Sets $c_2 = 34.0$ so the nominal `(B = 7, T/B = 0.01 N)` center (`50.84 dB`) stays aligned
    with the existing ~50 dB LBM-band-equivalent ranking scale used by `multi_point.py`.
- **`calibrate(..., non_negative: bool = False)`:**
  - Adds optional `non_negative=True` bounded least squares ($c_0 \ge 0, c_1 \ge 0$, free $c_2$)
    so future LBM recalibrations cannot reintroduce an unphysical negative slope.
- **RV-1 physics snapshot (`tests/data/physics_snapshot.json`):**
  - Regenerated with `--reason` pointing to this file; only `loading_proxy_7_0.05N` and
    `loading_proxy_9_0.03N` move; all other 14 snapshot cases remain bit-for-bit unchanged.

## Pass / fail rules (fixed before edits)

| Id | Rule |
|---|---|
| P1 | `DEFAULT_COEFFS` satisfies $c_0 > 0$ and $c_1 > 0$. |
| P2 | `loading_noise_proxy(B, tpb)` strictly increases with both `n_blades` and `thrust_per_blade_n` (and stays $> 0$ for all `B >= 1`, `tpb >= 0`). |
| P3 | `loading_proxy_operating(7, 0.07, 0.5) < loading_proxy_from_rans(7, 0.07)` (motor derating strictly reduces predicted noise), while preserving O7 P1–P4 (`loading_proxy_operating(n, T, λ) == loading_proxy_from_rans(n, T * λ²)`). |
| P4 | `calibrate(nb, tpb, y, non_negative=True)` guarantees $c_0 \ge 0$ and $c_1 \ge 0$ even on confounded synthetic data whose unconstrained OLS fit has $c_1 < 0$; default `non_negative=False` remains exact OLS. |
| P5 | `tests/data/physics_snapshot.json` diff touches only `loading_proxy_7_0.05N` and `loading_proxy_9_0.03N`; `acoustics.loading` re-proven and `scripts/audit_status.py --strict` exits 0 (`PROVEN=34 CHANGED=0`). |

## Result

P1–P5 **PASS**. Updated `fansim/acoustics/loading.py` (`DEFAULT_COEFFS = (2.263, 100.0, 34.0)`
and `calibrate(..., non_negative=True)`), regenerated `tests/data/physics_snapshot.json` (moving
only `loading_proxy_7_0.05N` and `loading_proxy_9_0.03N`), and re-proved `acoustics.loading` in
`docs/validation/audits/ledger.json` (`scripts/audit_status.py --strict`: `PROVEN=34 CHANGED=0`).
