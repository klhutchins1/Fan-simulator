# CFD sanity checks — baseline on existing cases (2026-09-27)

Tool: `uv run python scripts/cfd_sanity.py <case_dir>` (module `fansim/cfd/sanity.py`; audit unit
`cfd.sanity_checks`). Optimizer policy: **flag, never reject** (`sanity_status` + reason text).

Legacy cases have no `case_meta.json` / `inletFlow` / `yPlus` outputs, so metadata is inferred from
`MRFProperties`, `blockMeshDict` and the triSurface STLs; mass balance and y+ SKIP until new runs.
Each case directory keeps only its **last** solve.

| case (last solve) | notable results |
|---|---|
| `runs/validate_a12x25_dirfix` (20 Pa, reversed flow) | forward-flow checks SKIP; **duct_shape WARN: square tunnel**; mesh WARN (1 highly skew face); not converged (shift 3.3%) |
| `runs/loaded_ladder/plenum` (15 Pa, reversed) | round duct; mesh OK; not converged (osc 23%) |
| `runs/loaded_ladder/frame` (15 Pa, reversed) | round duct; mesh OK; not converged (osc 352%) |
| `runs/audit_direction/stock/flipped` (spin +1, reversed) | **duct_shape WARN: square tunnel**; converged |
| `runs/loaded_ladder/urans` (0 Pa forward, stopped early) | energy η_total 0.005 PASS; **power sign PASS**; **thrust direction PASS**; **inlet bookkeeping 0.4% PASS**; mesh WARN (skew) |

## Findings

1. **Square tunnel in the default domain.** Without a casing the CFD domain is a square box of
   half-width = duct radius; the corners (~21% of the cross-section) are open around the blade tips, so
   the nominal 0.5 mm tip gap exists only at four points. This affects the optimizer default and the
   2026-09-26 P–Q. The plenum rungs (round bore) are not affected. Follow-up: decide whether the default
   should use a round casing (changes CFM → needs a `CFD_VERSION` bump and re-validation).
2. **Bookkeeping validated on a forward-flow case:** the inlet static pressure matches the flow/area
   prediction to 0.4%, and the power and thrust signs are physical — the direction fix and area
   accounting are consistent.
3. **Mesh:** one highly skewed face in each blade mesh (skewness ~4.3); tolerated (WARN), watch it.
4. Mass balance and y+ will populate on the next CFD run (new function objects).
