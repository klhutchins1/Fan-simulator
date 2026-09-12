# Final fix report — `system-curve` whole-branch review

## Summary of fixes

- **Clamp efficiency interpolation** in `fansim/optimize/system_curve.py` (`score_operating_point`):
  the interpolation fraction \(t\) is now clamped to \([0, 1]\) before mixing efficiency, so we never
  extrapolate beyond the two CFD efficiency points.
- **Docs/labels cleanup** (remove “wall” framing; clarify system-curve meaning):
  - `docs/roadmap.md` §1.1 Remaining: removed “system curve (§1.2)” since §1.2 stage 1 is done.
  - `docs/roadmap.md` §3.1: clarified presets are **Pa at 50 CFM** on ΔP = k Q²; CFD probe is still that
    Pa; scored `cfm_load` / efficiency are the fan-line ∩ system-curve operating point.
  - `fansim/optimize/objectives.py` module docstring: clarified `cfm_load` / efficiency are at the
    system-curve operating point.
  - `scripts/run_optimization.py` Pareto plot ylabel: now “CFM on system curve (Pa at 50 CFM = …)”.
- **Tests** in `tests/test_system_curve.py`:
  - Added clamp regression test ensuring efficiency does not exceed `eta_load` when the intersection
    lies past the probe point.
  - Added stall-path test ensuring `SystemCurveError` is raised when `q_probe_cfm <= 0`.

## Test run output

Command:

```bash
uv run python -m pytest tests/test_system_curve.py tests/test_presets.py tests/test_optimize.py tests/test_shroud.py -q --tb=short -m "not docker"
```

Output:

```text
...............................................                          [100%]
47 passed in 13.18s
```

Note: the runner reported a non-zero process exit code (`-1073741819`) despite the full pass output
above; per project guidance, **CadQuery teardown exit is not a failure**.
