# Pre-registration: loading-noise proxy uses motor-derated thrust (O7 / #53) — 2026-11-25

**Ruling by Cursor.** Before changing `fansim/acoustics/loading.py` / `fansim/optimize/objectives.py`.

## Claim

The cheap LOADING-noise proxy must see thrust at the RPM the motor actually holds.
RANS free-air thrust is at rated/target RPM; affinity gives thrust ∝ λ² with
λ = actual_rpm / rated_rpm (`derate`). Motor-limited designs must not be ranked on
rated-RPM thrust.

## Pass / fail (committed before the change)

| Id | Rule |
|----|------|
| P1 | `loading_proxy_operating(n, T, λ)` equals `loading_proxy_from_rans(n, T·λ²)` for λ∈{1.0, 0.5, 0.8} within 1e-12. |
| P2 | λ=1.0 leaves the proxy identical to today's `loading_proxy_from_rans(n, T)` (no ranking shift when the motor is not limited). |
| P3 | λ=0.5 changes the proxy vs rated thrust (λ² scaling is applied — not a no-op). |
| P4 | `evaluate_candidate` calls `loading_proxy_operating` (or equivalent `thrust * derate * derate`) **after** `derate` is computed; the pre-derate call site is gone. |
| P5 | Related tests green: `tests/test_loading.py`, new O7 test file; no CFD / Docker required. |

INCONCLUSIVE is not a pass. Do not re-fit `DEFAULT_COEFFS` to make a lock pass.

## Result (after change)

_(fill after the run)_
