# Cockpit UI cohesion — Approach 1 (approved 2026-09-08)

**Status:** Approved verbally (“sounds good”); implementing now.  
**Scope:** Layout / information architecture only. No new physics or Approach 3 features.

## Problem

Wiring audit: most cockpit features are already hooked up. Browser review scored consistency ~4/10 — Fan mirrored the other tabs (viz left / controls right), action order differed per tab, Fan Design buried Preview/Assess under a long slider farm, and Mixed put the scatter above the 3D view.

## Approach 1 (this pass)

1. **Shell:** Controls **left**, viz **right** on every top tab (Fan flipped to match Prop / Mixed / Volute / CROR).
2. **Top tabs:** Order Fan → Mixed → Volute → Prop → CROR (ducted family, then open-rotor). Short labels; tooltips keep full titles.
3. **Shared action strip:** `Preview/Analyze → Assess → Export → Optimize → CFD refine` with dependency-aware disables:
   - No geometry / no design → disable Export (and Assess where it exists).
   - No Pareto / optimize front → disable CFD refine.
   - Top-N ≤ 0 → disable CFD refine.
4. **Viz stack:** readout → **3D** → plot. Mixed fixed (plot was above 3D). CROR: 3D if cheap, else a clear “proxy-only / no mesh yet” empty state.
5. **Fan Design:** Pin **Preview + Assess** (and the shared strip) above the fold; collapse Optimize flag farm into **Advanced search**; move Leeway / Manage fan models / Measurements under **Library**.
6. **Hub chrome:** Show Fit envelope / Scale-to-hub only on Fan **Design** when a design is loaded. Keep Library’s own Scale for library selection (different handler) — no duplicate on Design chrome when browsing Library.
7. **Deferred (Approach 3):** CROR resume, Prop CFD polar polish, full Lab panel for FW-H/LBM — caption cleanup only if trivial.

## Non-goals

- New design system (keep Vuetify3 / trame patterns).
- Extracting the whole `app.py` into modules (optional tiny helpers for busy/disable expressions only).
- Catalog DB changes.

## Verification

- Source-shape tests in `tests/test_cockpit_view.py` (layout order, labels, Library hosts leeway/measurements).
- Smoke: Fan left-controls/right-viz; Assess/Preview high on Design.
- CadQuery `ACCESS_VIOLATION` on pytest teardown is expected / known.
