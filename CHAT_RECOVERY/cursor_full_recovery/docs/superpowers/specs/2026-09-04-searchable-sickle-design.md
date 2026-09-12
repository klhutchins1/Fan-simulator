# Searchable sickle tip `le_skew` (stage 1)

**Date:** 2026-09-04  
**Status:** accepted  
**Approach:** When `--sickle` is on, Optuna samples **`sickle_mm` ∈ [4, 12]** and stamps `apply_sickle(params, tip_mm)` (hub 0 / mid 40% / tip). Without the flag, behavior unchanged. Not mid-fraction search, not cockpit LE editor, not LBM.  
**Roadmap:** §2.3 remaining (search `le_skew`).

## Plain language

`--sickle` already builds a scimitar LE, but every trial gets the same 8 mm tip offset. Stage 1 lets NSGA try milder or stronger tip sickles in a band around that default so a campaign can see whether planform sweep helps hose CFM / noise proxies.

## Approaches considered

| | Approach | Trade-off |
|---|---|---|
| **1 (chosen)** | Flag-gated Optuna `sickle_mm` + existing `apply_sickle` | Matches stator / shroud pattern |
| **2** | Always-on guided `le_skew_tip` | Pollutes non-sickle studies |
| **3** | Independent mid/tip fractions | Breaks the simple recipe |

## Goal

### 1. Search (`fansim/optimize/search_space.py`)

```text
SICKLE_BOUNDS = (4.0, 12.0)   # tip le_skew mm

suggest_sickle(trial) -> float
  # trial.suggest_float("sickle_mm", *SICKLE_BOUNDS)
```

Call only when `run_study(..., sickle=True)`.

### 2. Study

```text
if sickle:
    tip_mm = suggest_sickle(trial)
    apply_sickle(params, tip_mm)
    sickle_mm = tip_mm
else:
    sickle_mm = 0.0
trial.set_user_attr("sickle_mm", sickle_mm)
```

Remove the fixed `SICKLE_DEFAULT_MM` stamp for NSGA trials (keep the constant for docs / non-search callers / `blade_from_flat` when a flat dict has no value but needs a default elsewhere).

Pareto / JSON export already can carry `sickle_mm` via user attrs; include in `pareto_summary` if not already present.

### 3. Rebuild

`blade_from_flat` already applies `sickle_mm` from the flat dict when > 0. Ensure study export / `with_shroud_attr`-style merge includes `sickle_mm` from user attrs when replaying (same honesty as shroud).

### 4. Cockpit / CLI

- No new CLI flags. Existing `--sickle` enables the DOF.
- Cockpit Optimize switch unchanged (no tip-mm slider this cycle).

### 5. Docs

- Spec accepted; roadmap §2.3: searched tip sickle done; remaining LBM compare / photographed AAO.

## Honesty

- Still LE-only θ rake, not a digitised Noctua planform.
- Stronger sickle can tighten the tip-radius cap via `open_tip_rmax_mm` — that is intended.
- Do not claim quieter BPF without an LBM campaign.

## Tests (no Docker)

- `suggest_sickle` values in [4, 12]; key present on trial.params.
- Without calling `suggest_sickle`, `suggest_params` does not add `sickle_mm`.
- `apply_sickle` with tip=4 and tip=12 still one solid; tip `le_skew` matches tip_mm.
- Study wiring unit test optional: monkeypatch `suggest_sickle` / `apply_sickle` if needed; prefer search_space + apply tests.
- No `★`.

## Non-goals

- Searching mid fraction or hub LE
- Cockpit Design-tab LE curve for `le_skew`
- Changing `SICKLE_DEFAULT_MM` meaning for non-NSGA scripts
- LBM `--sickle` vs default campaign

## Success

With `--sickle`, NSGA samples tip sickle in [4, 12] mm and stamps the 0/0.4/1 recipe; without `--sickle`, trials stay unsickled.
