# Task 4.2 Report — Performance baselines and speedups

**Status:** DONE  
**Date:** 2026-09-14

## Deliverables

| Item | Path | Notes |
|------|------|-------|
| Baseline doc | `docs/validation/perf_baseline.md` | Stock `a12x25_reference.yaml` timings; ranked hotspots; Phase 3 honesty stamp |
| Speedups | `fansim/propeller/polars.py`, `fansim/fan_bem.py` | BEM screening path only (~14% faster `pq_curve`; outputs unchanged) |
| Commit | (this task) | Message: `Add perf baselines and first screening-path speedups.` |

## Measurements (summary)

- `build_impeller`: ~13.1 s (fused STL — dominates eval vs BEM).
- `build_impeller_preview`: ~5.0 s (preview tier).
- `pq_curve`: 15.9 ms → 13.7 ms median after caches + geometry hoist; free 65 CFM / shutoff 36.4 Pa unchanged.

## Verification

- `uv run python -m pytest tests/test_fan_bem.py -q` — 4 passed.

## Concerns / deferrals

- Fused geometry build not shortened this cycle (needs explicit screening-resolution policy; would not address Phase 3 −32% free-air gap anyway).
- Windows OCCT teardown non-zero exit after successful timing scripts — expected noise.

## Out of scope (honored)

- No push.
- `CHAT_RECOVERY/` untouched.
- No Docker CFD campaign.
