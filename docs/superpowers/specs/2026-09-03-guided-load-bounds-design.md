# Re-open guided camber and blade count

**Date:** 2026-09-03  
**Status:** accepted  
**Approach:** Widen `GUIDED` / `GUIDED_LC` camber and blade-count to match `OPEN`. Scoring is already on the system curve; the free-air “keep camber low / fewer blades” box is now the thing blocking load CFM. Not preset-dependent bounds. Not 13 blades this cycle.  
**Roadmap:** §3.2. Not §3.3 tip-cap, not stator, not rewriting `docs/design-rules.md` correlations.

## Plain language

`--space guided` still searches like a free-air fan: camber 0–0.02 and 5–8 blades. Those numbers came from a free-delivery study where extra camber and extra blades hurt flow and noise. The optimizer now ranks **hose CFM** (case 8 Pa / heatsink 20 Pa / radiator 35 Pa). Under back-pressure, more camber and more blades are how axial fans make static pressure. Guided search cannot reach them.

`OPEN` already allows camber 0–0.06 and 5–11 blades. Point guided at the same box. Default CLI space stays `open` if neither `--guided` nor `--space` is set.

## Problem

```text
GUIDED     n_blades (5, 8)    max_camber (0.0, 0.02)
GUIDED_LC  n_blades (7, 11)   max_camber (0.0, 0.02)
OPEN       n_blades (5, 11)   max_camber (0.0, 0.06)
```

Cockpit sliders already match OPEN. Design-rules table still says “keep camber low / fewer blades” from the old free-air Spearman — that file is historical; this spec does not rewrite it.

## Goal

1. New bounds (only these four numbers):

```text
GUIDED     n_blades (5, 11)   max_camber (0.0, 0.06)
GUIDED_LC  n_blades (7, 11)   max_camber (0.0, 0.06)   # blade count already 7–11
```

2. Comments next to those keys: free-air study kept them tight; hose scoring needs the OPEN range.
3. `suggest_params` / `blade_from_flat` / CLI `--space` unchanged except they read the new tuples.
4. No new flag. `--preset radiator` still only sets `load_pa`.

## Non-goals

- 12–13 blades (print/tone/weight; OPEN max stays 11)
- Per-preset search spaces
- Changing stagger/chord/lean in GUIDED
- Changing OPEN, EXTENDED, cockpit sliders
- Re-fitting `docs/design-rules.md`
- Re-running an optimization in this slice

## Tests

Sample 30 `space="guided"` trials:

- `n_blades` in 5..11
- `max_camber` in 0..0.06
- at least one trial with `n_blades >= 9`
- at least one trial with `max_camber > 0.02`

Sample 20 `space="guided_lc"` trials: `max_camber` in 0..0.06 and at least one `> 0.02`. `n_blades` still 7..11.

Existing `test_suggest_params_within_bounds` (OPEN 5–11) stays.

## Files

| Path | Responsibility |
|---|---|
| `fansim/optimize/search_space.py` | GUIDED / GUIDED_LC tuples + comments |
| `tests/test_search_space.py` | guided / guided_lc bound samples (new file if none exists) |
| `docs/roadmap.md` | §3.2 done |

Do not add Python dependencies. Do not commit `catalog/catalog.db`.
