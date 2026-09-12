# Cockpit Optimize geometry stamps (stage 1)

**Date:** 2026-09-04  
**Status:** accepted  
**Approach:** Four optional switches on the fan Optimize card that pass existing CLI flags: `--stator`, `--sickle`, `--stepped-inlet`, `--notched-tips`. Extend `optimization_argv`. Default all **off**. Not new physics. Not Assess.  
**Roadmap:** §8.3 leftover wiring; closes cockpit gaps called out on §2.2 / §2.3 / §2.6.

## Goal

1. **`optimization_argv(..., stator=False, sickle=False, stepped_inlet=False, notched_tips=False)`** — append each flag when True.
2. **Cockpit** — four switches under the existing Optimize card (after GP). Labels match CLI help, short.
3. **Tests** — argv includes/omits each flag; `app.py` contains the four labels / `opt_stator` etc.

## Non-goals

- Searching `le_skew` / vane count
- Cockpit geometry preview of stamps
- Changing CLI defaults
