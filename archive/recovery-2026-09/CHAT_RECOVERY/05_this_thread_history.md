# This-thread history (agent chat after fan-tab / opt work)

## Git commits remembered (local master; push status unknown)

1. **`b360dde`** — Fan tab extract, `fansim.isolated_job`, wind-turbine scaffold, roadmap mojibake scrub
2. **`a110f76`** — §12 leftovers: Ruff F401 trim on Fan binders, `Design` → `fansim/optimize/design.py`, lazy PyVista plotters, `_UnimplementedArchetype` (alias `_StubArchetype` kept), north-star print sheet

## Fan tab extract

Spec: `docs/superpowers/specs/2026-09-11-fan-tab-extract-design.md`

Modules: `fan_session`, `fan_copy`, `fan_widgets`, `fan_models`, `fan_assess`,
`fan_optimize`, `fan_viz`, `fan_ui`, `fan_tab`

API: `setup_fan_tab` / `render_fan_tab` (render re-exported from `fan_ui`)

Post-extract bug fixed in session: missing `fan_ui` imports `assess_load`, `scatter_figure`, `published_scatter_point` (may have been uncommitted when drive died).

## Wind turbine

- Scaffold under `fansim/wind_turbine/`, registered lazily
- Honesty: BEM-lite only; full HAWT parked (`wt-later`, roadmap §9.5)
- Spec: `docs/superpowers/specs/2026-09-11-wind-turbine-scaffold-design.md`

## North star (§5.1)

- Print-ready stock STL name remembered:
  `exports/north_star_a12x25_stock_20260911-163616.stl` (gitignored `*.stl`)
- Sheet `.md` was committed; `docs/validation/north-star-staged.md` updated
- Hardware measure still open

## Optimization campaign `opt_cfm_compact_3h` (2026-09-11)

```bash
uv run --extra optim python scripts/run_optimization.py \
  --trials 55 --preset case --guided --bem-prescreen 35 --mountable \
  --iters 800 --procs 8 \
  --out runs/opt_cfm_compact_3h --study-name cfm_compact
```

- Wall ~7030 s (~2.0 h); 55 trials; **5 feasible**
- Pareto winner **trial 35**: free 47.1 / load **33.0** CFM / eff **20.8%**
- Weaker than prior `opt_run1` (~66 CFM load on trial_0002) due to mountable + PETG vibration + BEM floor

### Prior run `opt_run1` tops (cfm_load)

| Trial | load | free | eff |
|-------|------|------|-----|
| 0002 | 65.9 | 75.9 | 20.5% |
| 0015 | 63.8 | 76.0 | 18.0% |
| 0003 | 51.8 | 73.1 | 10.3% |

Other run dirs seen: `cockpit_opt_20260911-121024`, `opt_realframe2`, `opt_guided`

## Viz note (assess design_9101)

Huge yellow velocity glyphs were tip `|U|` spikes (~24 m/s vs median ~3); CFM from outlet `sum(phi)` was fine (~38 CFM). Optional fix: clamp glyph length at p95.

## User goal at interruption

Chase **good CFM with low volume** (interpreted as compact A12x25 envelope, not quiet unless `--noise`).
