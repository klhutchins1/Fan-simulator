# Sim→print performance knockdown (stage 1)

**Date:** 2026-09-03  
**Status:** accepted  
**Approach:** After derate / system-curve / optional `--refine-op`, multiply reported `cfm_free`, `cfm_load`, and efficiency by fixed print factors. Smooth-wall RANS stays what it is; the objectives become “printed.”  
**Roadmap:** §7.6 stage 1. Not wall-function ks, not FSI deflection, not thickness-as-robustness, not layer-adhesion (already §1.3).

## Plain language

The optimizer ranks a smooth-wall RANS fan. You will print layer lines and a slightly flexible blade. Stage 1 does not model roughness in OpenFOAM. It knocks the **reported** flow and efficiency so NSGA-II prefers designs that still look good after a boring, published-size print penalty.

BEM and the catalog GP stay un-penalized (they screen physics / smooth-wall `cfm_free`). Historical catalog rows are not rewritten (`print_k` absent = smooth-wall).

## Problem

`evaluate_candidate` returns derated, hose-intersected RANS numbers. Nothing accounts for FDM roughness or running deflection. Roadmap §7.6: use published metal-vs-printed impeller deltas as a knockdown, not a new mesh.

## Goal

1. Constants (order-of-magnitude; not a fit to one paper this cycle):

```text
PRINT_K_CFM = 0.95    # printed free/load CFM / smooth-wall CFM
PRINT_K_ETA = 0.92    # printed efficiency / smooth-wall efficiency
```

2. Apply **once**, after the algebraic (and optional refine-op) `cfm_free` / `cfm_load` / `efficiency` exist:

```text
raw["cfm_free_cfd"] = cfm_free          # smooth-wall, derated
raw["cfm_load_cfd"] = cfm_load
raw["efficiency_cfd"] = efficiency
cfm_free  *= PRINT_K_CFM
cfm_load  *= PRINT_K_CFM
efficiency *= PRINT_K_ETA
raw["print_k_cfm"] = PRINT_K_CFM
raw["print_k_eta"] = PRINT_K_ETA
```

3. Default **on** for `evaluate_candidate` (this tool prints blades). `print_penalty: bool = True`. `False` is the explicit “smooth-wall / resin” escape, same idea as `adhesion_k=1.0`. No new optimizer CLI flag this cycle — Assess inherits on.
4. Do **not** apply to `--bem-prescreen` or `--surrogate-prescreen`.
5. Do **not** backfill `catalog/catalog.db`. Old rows have no `print_k_*`.

## Non-goals

- OpenFOAM wall `ks` / roughness height
- FSI / endplate deflection (the 2309.13195 paper’s lesson, not our constant)
- Thickness-dependent robustness lever
- Recalibrating 0.95 / 0.92 from a scraped table this cycle
- Motor-derate or hose algebra changes

## Tests (no Docker)

Helper `apply_print_penalty(cfm_free, cfm_load, efficiency) -> tuple` plus stamps:

- Default factors: 100 / 80 / 40 → 95 / 76 / 36.8
- `print_penalty=False` is identity
- A thin `evaluate_candidate` path is not required if the helper is the only transform; existing gate tests never reach it
- `print_k_cfm` / `print_k_eta` in the returned dict when on

## Files

| Path | Responsibility |
|---|---|
| `fansim/optimize/print_penalty.py` | constants + `apply_print_penalty` |
| `fansim/optimize/objectives.py` | apply before `ObjectiveResult`; stamp raw |
| `tests/test_print_penalty.py` | math + off switch |
| `docs/roadmap.md` | §7.6 stage 1 |

Do not add Python dependencies. Do not commit `catalog/catalog.db`.
