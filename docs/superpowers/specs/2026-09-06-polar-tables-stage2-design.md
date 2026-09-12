# Low-Re polar tables stage 2 (thickness + Selig families)

**Date:** 2026-09-06  
**Status:** implemented  
**Approach:** Extend vendored polars so BEM/BEMT match on **camber + thickness**, and add **e387**, **sd7032**, and **s1223** families (three Re tags each) alongside existing NACA *12. Same CSV contract and log-Re / linear-α interp. Not full LSAT ingest, not CFD geometry change, not Optuna airfoil-name DOF.  
**Roadmap:** §1.6 / §7.2 stage 2.

## Goal

1. `_FAMILIES`: `(name, design_camber, design_thickness)` — nearest by  
   `abs(c−c*) + 0.5*abs(t−t*)` (thickness weight 0.5 so camber still dominates mild mismatches).
2. `cl_cd_table(alpha, camber, re, thickness=0.12)`; `_cl_cd` / fan BEM pass station thickness.
3. CSVs: `e387`, `sd7032`, `s1223` × `re4e4|re8e4|re1.6e5` under `fansim/data/polars/`.
4. README + bibliography note; tests for family pick by thickness and table hit.

## Non-goals

Network scrape; changing NACA loft geometry; NSGA airfoil catalog.

## Done when

Unit tests green; fan BEM with thick vs thin stations selects different families when camber matches.

