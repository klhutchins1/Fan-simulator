# Cockpit tab layout unification

**Date:** 2026-09-24  
**Status:** working note (no review gate)  
**Approach:** Fan shell — Design / Results / Library on every tab. Shared helper first on Prop, then Mixed / Volute / CROR, then Fan reorder.

## Locked chrome

- Split: left 5 / right 7.
- Left sub-tabs: Design | Results | Library (`{prefix}_subtab`).
- Right: readout → 3-D at 400 px → airflow only on Results when the tab has it.
- Design action row slots (skip empty): Preview → score (Assess|Analyze) → Export → Optimize → Stop → Randomize.
- Optimize card order: trials → tab-specific fields → resume → CFD refine (if any).
- Results: previous-runs picker + scatter (+ pareto list when useful).
- Library: previous runs + that archetype’s exports (STL / PyThrust / print). Fan keeps its catalog Library.

## Landings

1. `fansim/cockpit/tab_shell.py` + Prop
2. Mixed, Volute, CROR
3. Fan Actions / Optimize reorder to match
