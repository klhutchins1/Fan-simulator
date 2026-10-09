# Fan Optimize in the cockpit (stage 1)

**Date:** 2026-09-03  
**Status:** accepted  
**Approach:** Do not reimplement NSGA-II. Build the same argv `scripts/run_optimization.py` already understands, spawn it as a subprocess, stream the log. Reuse the Assess Application picker + refine-op switch. A testable `optimization_argv` helper is the core. Not BEM-only search. Not prop Optimize.  
**Roadmap:** §8.3 stage 1. Guided camber/blades and the tip cap stay inside `suggest_params` (no extra widget).

## Plain language

Prop Optimize is instant BEMT. Fan search is the CLI: hours of OpenFOAM. The cockpit has no fan Optimize button, so `--preset`, `--bem-prescreen`, `--surrogate-prescreen`, `--shroud`, `--refine-op` stay invisible. Stage 1 is a card that runs that CLI with the flags already on the Assess card, plus shroud / BEM / GP toggles. New run folder. Cancel kills the process.

## Problem

```text
prop tab  → Optimize → run_prop_study in-process (~1 s)
fan tab   → Assess one design; optimizer is CLI-only
```

## Goal

1. **Card** on the fan Design tab, under Assess & sweep: **Optimize (NSGA-II, CFD)**.

```text
Trials [8]
[ ] Search a tip ring (--shroud)
[ ] BEM skip below 32 CFM  (off = floor 0)
[ ] Catalog GP skip below 40 CFM free  (off = floor 0)
[Optimize]  [Cancel]
```

Application hose and refine-op come from the **existing** Assess widgets (do not duplicate). `--fan-model` is `state.fan_model`. `--mountable` is **on**. `--space guided`. **No** `--features`. Trials default **8**, clamp 2–40.

2. **Helper** (no Trame, no Docker):

```text
optimization_argv(
    *, trials, out, fan_model, preset, refine_op,
    shroud, bem_floor, gp_floor, space="guided", mountable=True,
) -> list[str]
```

- `sys.executable`, `-m` is **not** used; invoke `scripts/run_optimization.py` the same way the repo already does (`[sys.executable, str(repo/"scripts/run_optimization.py"), ...]`).
- `preset=="legacy"` → omit `--preset` (CLI 1 Pa).
- `bem_floor==0` → omit `--bem-prescreen`. Else `--bem-prescreen {floor}`.
- Same for `--surrogate-prescreen`.
- `refine_op` / `shroud` / `mountable` → flags when True.
- Always `--space guided` unless tests pass another space.
- Always `--trials`, `--out`, `--fan-model`.

3. **Run folder:** `runs/cockpit_opt_{YYYYMMDD-HHMMSS}/` — **do not** write into the opened `--run` (that study stays intact).

4. **Spawn:** async, same busy lock as Assess (`assess_busy`). Disable Assess/sweep/Optimize while a study runs. Stream the last ~20 log lines into `opt_msg` (reuse assess_msg if simpler). **Cancel** terminates the subprocess (Windows: `taskkill /T` or `Popen.terminate` on the process group). On success, `load_designs(out)` and merge into the plot with `trial += 20000` so IDs do not collide with the opened study; `extra["source_run"]` = folder name. Do not auto-rebuild `catalog.db`.

5. Caption on merged rows: existing `score_caption` if extra has hose stamps from the study; else skip.

## Non-goals

- In-process `run_study` (OCP crash would kill the cockpit)
- `--features` / tip-round / bio search
- OPEN space picker, `--loadcap`, `--noise`, `--winglet` as extra switches (winglet still follows shroud policy inside `suggest_params` when `--shroud`)
- Resuming the opened run’s Optuna sqlite
- Live per-trial plot updates (refresh when the process **exits**)
- Changing CLI defaults

## Tests (no Docker, no Trame, no CFD)

- `optimization_argv` legacy omits `--preset`; `case` includes `--preset case`
- `refine_op=True` includes `--refine-op`; False omits it
- `shroud=True` includes `--shroud`
- `bem_floor=0` omits `--bem-prescreen`; `32` includes `--bem-prescreen 32`
- `gp_floor=0` omits `--surrogate-prescreen`
- always `--space guided`, `--mountable`, `--fan-model a12x25` when passed
- argv starts with `sys.executable` and ends with a path containing `run_optimization.py`
- `app.py` contains `Optimize (NSGA-II, CFD)` and `optimization_argv`

## Files

| Path | Responsibility |
|---|---|
| `fansim/optimize/cli_argv.py` (or `presets.py`) | `optimization_argv` |
| `fansim/cockpit/app.py` | card, spawn, cancel, merge `load_designs` |
| `tests/test_optimization_argv.py` | argv cases |
| `tests/test_cockpit_view.py` | card copy |
| `docs/roadmap.md` | §8.3 stage 1 done; remaining = live plot / resume |

Do not add Python dependencies. Do not commit `catalog/catalog.db`.
