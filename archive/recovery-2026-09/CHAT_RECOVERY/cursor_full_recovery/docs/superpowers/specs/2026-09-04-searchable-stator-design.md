# Searchable stator stagger / n_vanes (stage 1)

**Date:** 2026-09-04  
**Status:** accepted  
**Approach:** When `--stator` is on, Optuna also samples **`stator_stagger_deg`** ∈ [35, 65] and **`stator_n_extra`** ∈ [1, 4] (`n_vanes = n_blades + extra`). Geometry / evaluate take optional kwargs; defaults remain today’s **50°** and **+2**. Not on `BladeParams`, not cockpit sliders, not searched camber/chord, not frame+stator stack.  
**Roadmap:** §2.2 remaining (searched n_vanes/stagger).

## Plain language

`--stator` already builds cambered NACA outlet vanes, but every trial gets the same 50° stagger and `n_blades + 2` count. Stage 1 lets NSGA try nearby stagger and vane offsets so a campaign can find whether more/less turning or a denser row helps hose CFM / efficiency — without inventing new geometry types.

## Approaches considered

| | Approach | Trade-off |
|---|---|---|
| **1 (chosen)** | Flag-gated Optuna DOFs + kwargs into stator build / evaluate; trial user attrs | Matches `--shroud`; keeps rotor `BladeParams` clean |
| **2** | Fields on `BladeParams` | YAML round-trip, but stator knobs on the rotor object even with frame CFD |
| **3** | Required `StatorParams` dataclass | Cleaner types; extra plumbing for stage 1 |

## Goal

### 1. Geometry (`fansim/cfd/stator.py`)

```text
STAGGER_DEG = 50.0          # default when kwargs omitted
STATOR_N_EXTRA_DEFAULT = 2  # default offset

n_stator_vanes(params, n_extra=None) -> int
  # int(params.n_blades) + int(n_extra if n_extra is not None else STATOR_N_EXTRA_DEFAULT)

build_stator_solid(params, rig, *, stagger_deg=None, n_vanes=None, n_extra=None) -> cq.Solid
export_stator_stl(..., same kwargs)
```

- `stagger_deg` defaults to `STAGGER_DEG`.
- Vane count: if `n_vanes` is set, use it; else `n_stator_vanes(params, n_extra)`.
- Axial band, chord, NACA section, hub barrel unchanged.
- Keep `STAGGER_DEG` / section constants exported for tests.

### 2. Search (`fansim/optimize/search_space.py`)

```text
STATOR_BOUNDS = {
  "stator_stagger_deg": (35.0, 65.0),
  "stator_n_extra": (1, 4),
}

suggest_stator(trial) -> dict
  # stagger_deg = suggest_float(...), n_extra = suggest_int(...),
  # n_vanes computed later from n_blades + n_extra
```

Call `suggest_stator` only when the study has `stator=True`. Do **not** add these keys to the search space when the flag is off (static Optuna space / resume safety: only suggest when the study was started with `--stator`).

### 3. Evaluate / study

- `evaluate_candidate(..., stator=False, stator_stagger_deg=None, stator_n_extra=None)`  
  When `stator` and kwargs are None → today’s defaults. When set → pass through to `export_stator_stl`.  
  Stamp `raw["stator_stagger_deg"]`, `raw["stator_n_extra"]`, `raw["stator_n_vanes"]` when stator is on.
- `run_study(..., stator=False)`: if stator, each trial calls `suggest_stator`, passes kwargs into `evaluate_candidate`, and sets user attrs:
  - `stator_stagger_deg`, `stator_n_extra`, `stator_n_vanes`
- JSON / catalog export of trials should include those attrs (same pattern as `shroud_thick_mm`). Replay / rebuild from trial params must restore them when re-evaluating a stator trial (merge into evaluate kwargs; not into `blade_from_flat`).

### 4. CLI / cockpit

- No new CLI flags. Existing `--stator` enables the DOFs.
- Cockpit: no new switches or sliders this cycle (Optimize already has Stator vanes). Optional later: hint on the label that stagger/extra are searched.

### 5. Docs

- Spec accepted; roadmap §2.2: searched stagger / n_vanes stage 1 done; remaining = BEM Euler credit, frame+stator stack.
- Update cambered-stator / stator-vanes specs’ “remaining” lines only via roadmap (no need to rewrite old specs).

## Honesty

- Searching stagger/count does not prove AMCA recovery; still need a CFD campaign vs frame.
- Fuse risk rises at extreme stagger; if a trial’s CadQuery fuse fails, mark infeasible (`stator failed:…`) as today — do not silently fall back to plates or fixed 50°.
- Comparing studies with vs without `--stator` mixes different stationary geometries; do not pool them as one Pareto.

## Tests (no Docker mesh)

- `build_stator_solid` with `stagger_deg=40` and `n_extra=3` → one solid; vane count = `n_blades + 3`.
- Defaults omit kwargs → still 50° path and `n_blades + 2` (existing tests stay green).
- `suggest_stator` / study wiring: when `stator=True`, trial params (or user attrs) include both keys in band; when `stator=False`, those keys are absent from suggestions.
- `evaluate_candidate` stamps raw stagger / n_extra / n_vanes when stator on (mock STL/CFD as existing stator tests do).
- No `★`.

## Non-goals

- Searched camber, thickness, chord, or spanwise twist
- Fields on `BladeParams` / recipe YAML for stator knobs
- Cockpit sliders for stagger / n_vanes
- Frame + stator stack / extra axial room
- BEM Euler / swirl-recovery credit
- Changing NACA section constants
- New CLI `--stator-stagger` / `--stator-n-extra` for one-shot eval (kwargs/API only; scripts can pass later)

## Success

With `--stator`, an NSGA study samples stagger in [35, 65] and vane offset in [1, 4], builds the matching OGV STL, and records the chosen values on each trial; without `--stator`, search and CFD match today.
