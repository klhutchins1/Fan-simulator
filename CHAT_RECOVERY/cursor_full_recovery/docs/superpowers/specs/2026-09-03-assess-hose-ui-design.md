# Assess hose picker + provenance

**Date:** 2026-09-03  
**Status:** accepted  
**Approach:** Assess already runs circular-duct + print-penalty `evaluate_candidate`. Wire the same `resolve_load` presets the CLI uses, pass `load_pa` through the isolated worker, and print hose / duct / print-k / curve k on the result. Not a new scorer. Not refine-op. Not fan Optimize.  
**Roadmap:** §8.1. Not §8.2 (`--refine-op` switch). Not §8.3 (fan Optimize / BEM / GP).

## Plain language

Clicking Assess still scores load CFM on a **1 Pa @ 50 CFM** hose and never says so. Case / heatsink / radiator presets exist for the optimizer. Put that picker on the Assess card and show what the numbers actually mean (which hose, circular vs square, printed knockdown, curve k).

## Problem

```text
evaluate_candidate_isolated(...)   # no load_pa
_eval_worker → evaluate_candidate(..., load_pa=1.0)   # function default
assess_msg = "free … load … eff …"   # no hose / duct / print-k
```

`extra` already stores `duct` and `curve_provenance` (`k`, `dp_op_pa`, `q_ref_cfm`). The UI does not show them. Sweep uses the same `_assess` path, so it is also stuck at 1 Pa.

## Goal

1. **Picker** on the Assess card, above **Assess this design**:

```text
Application  [ 1 Pa (legacy) | Case 8 Pa | Heatsink 20 Pa | Radiator 35 Pa ]
```

State: `assess_preset: str = "legacy"`. Items from a helper (not hardcoded twice). Changing the picker after a scored design is selected marks `edited_stale` with a hose-changed note (load CFM is for the previous application).

2. **`load_pa` plumbing** — same `resolve_load` as CLI:

```text
legacy     → resolve_load()              → 1.0 Pa, name None
case       → resolve_load(preset="case") → 8.0
heatsink   → 20.0
radiator   → 35.0
```

No free-form Pa box this slice (`--load-pa` stays CLI).

3. **`evaluate_candidate_isolated(..., load_pa=)`** puts `load_pa` on the job JSON. `_eval_worker` passes it into `evaluate_candidate`. Default **1.0** so existing callers stay bit-identical. Sweep uses the current picker (same `_blocking_eval`).

4. **Stamp extra** (in addition to today’s `duct` + `curve_provenance`):

```text
extra["load_pa"] = load_pa
extra["preset"]  = assess_preset          # "legacy" | "case" | …
# from result.raw when present:
extra["print_k_cfm"] / extra["print_k_eta"]
```

Print penalty stays **on** (no off switch). Circular duct stays **on** (no square toggle).

5. **Caption** on `assess_msg` (and `info_lines` when selecting a scored design):

```text
hose: case 8 Pa @ 50 CFM · circular duct · printed ×0.95 / ×0.92
```

Helper so tests don’t boot Trame:

```text
assess_load(preset: str) -> (load_pa, label)     # wraps resolve_load
score_caption(extra: dict) -> str                # hose / duct / print-k; omit missing keys
```

If `duct` or print-k is absent (old catalog rows), skip that clause — don’t invent “circular”.

6. Prop tab unchanged. No CLI change. No catalog rewrite.

## Non-goals

- §8.2 refine-op switch
- §8.3 fan Optimize / `--bem-prescreen` / `--surrogate-prescreen` / `--shroud`
- Custom Pa text field
- Print-penalty or circular-duct toggles
- Changing `PRESETS` Pa values
- GP / BEM UI

## Tests (no Docker, no Trame, no CFD)

- `assess_load("legacy")` → 1.0; `"case"` → 8; `"heatsink"` → 20; `"radiator"` → 35; unknown key raises
- `score_caption` with full extra lists hose + circular + printed ×0.95; empty extra does not claim circular
- Isolated job dict includes `load_pa` when passed (helper or worker: monkeypatch `evaluate_candidate`, assert kwargs)
- `app.py` contains the Application select / `assess_preset` (same style as other cockpit copy tests)
- Existing `test_presets.py` still passes

## Files

| Path | Responsibility |
|---|---|
| `fansim/optimize/presets.py` | `assess_load` + picker items |
| `fansim/cockpit/score_caption.py` (or `placement.py`) | `score_caption` |
| `fansim/optimize/isolated_eval.py` | pass `load_pa` in the job |
| `fansim/optimize/_eval_worker.py` | `evaluate_candidate(..., load_pa=)` |
| `fansim/cockpit/app.py` | picker, stale-on-change, `_blocking_eval`, extra stamps, caption |
| `tests/test_presets.py` / `tests/test_score_caption.py` | load + caption |
| `tests/test_cockpit_view.py` | Application string |
| `docs/roadmap.md` | §8.1 done |

Do not add Python dependencies. Do not commit `catalog/catalog.db`.
