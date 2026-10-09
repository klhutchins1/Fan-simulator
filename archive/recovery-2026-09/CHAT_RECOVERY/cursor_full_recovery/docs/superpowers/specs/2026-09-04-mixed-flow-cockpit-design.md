# Mixed-flow cockpit export / score (stage 1)

**Date:** 2026-09-04  
**Status:** accepted  
**Approach:** Add a top-level **Mixed-flow** cockpit tab with core `MixedFlowParams` knobs, isolated Preview/Export via `export_mixed_flow_stl`, and Assess via isolated `evaluate_mixed_flow` (axial MRF free+load). Not NSGA, not volute, not camber/thickness editors, not Fan-tab topology switch.  
**Roadmap:** §4.1 remaining (cockpit).

## Plain language

Mixed-flow already builds and scores from the CLI. Stage 1 puts the same path in the cockpit so you can tweak the cone/tip/stagger, see a preview, export a printable STL, and run the axial-duct CFD score without leaving the UI. It is a separate tab so the axial Fan editor stays untouched.

## Approaches considered

| | Approach | Trade-off |
|---|---|---|
| **1 (chosen)** | New top-level tab + isolated workers | Clean; crash-safe; matches Propeller pattern |
| **2** | Topology switch inside Fan | Couples UIs; easy to break Design/Results |
| **3** | Shell-out only to CLI scripts | No live knobs / preview |

## Goal

### 1. Tab + state

- Top-level `VTab` value `"mixed"` (label like `Mixed-flow — drop-in impeller`).
- State fields for core knobs, initialized from `MixedFlowParams()` defaults:
  - `mf_n_blades`, `mf_r_eye`, `mf_r_back`, `mf_r_tip`, `mf_z_span`, `mf_chord`, `mf_stagger`
- Busy / message: `mf_preview_busy`, `mf_export_busy`, `mf_assess_busy`, `mf_msg` (and optional `mf_info` for captions).
- Own PyVista plotter (do not reuse Fan or Propeller plotters).
- Helper `mixed_params_from_state() -> MixedFlowParams` that builds the dataclass and surfaces `ValueError` (eye/back/mount) as UI text.

### 2. Preview

- Build STL in an **isolated** subprocess (CadQuery native crash must not kill trame), timeout ~300 s.
- Prefer a small `fansim/centrifugal/isolated.py` (or extend `geometry.isolated`) that accepts a JSON dict of MixedFlowParams fields and writes an STL — mirror axial `build_stl_isolated`.
- Load into the mixed-flow plotter; invalid params → message, no crash.

### 3. Export

- `export_mixed_flow_stl(params, path)` into `exports/mixed_flow_<stamp>.stl` (timestamped like Fan export).
- Motor cup carve stays inside the existing helper; report fits / carve honesty in `mf_msg`.
- Block if another mf busy flag is set.

### 4. Assess

- Application hose: reuse `assess_load` with a Mixed-flow preset state `mf_assess_preset` (same items as Fan Assess: legacy / case / heatsink / radiator). Default **case** (8 Pa @ 50 CFM) — mixed-flow is the high-Pa path.
- Optional refine-op: reuse Fan’s `assess_refine_op` **or** a dedicated `mf_refine_op` (prefer dedicated default **off** so tabs do not fight).
- Run `evaluate_mixed_flow` in an isolated subprocess (new worker next to `_eval_worker`, or a `job["kind"]="mixed_flow"` branch). Return `ObjectiveResult` JSON.
- Display: `cfm_free`, `cfm_load`, efficiency, reason / feasible; caption that the domain is the **axial** MRF duct (approximate for mixed-flow).
- Workdir under `runs/cockpit_mf_<stamp>/` (or similar). No catalog write required this cycle.

### 5. UI layout (minimal)

Left: knobs + Application select + Preview / Export / Assess buttons.  
Right: 3-D view + result text.  
No Library, no Optimize, no Feature Features for stage 1.

### 6. Docs

- Spec accepted; roadmap §4.1: cockpit stage 1 done; remaining volute / BEM / campaign.
- Tests that do not need Docker: tab label present in `app.py` source; knob state keys; isolated job builder serializes MixedFlowParams; `mixed_params_from_state` validates eye &lt; back. No `★`.

## Honesty

- Assess still uses the axial through-flow duct — not a volute case. Do not claim Noctua-beating high-Pa until a campaign.
- Preview may be slow (CadQuery fuse); keep busy flags honest.
- Default camber/thickness are fixed; users cannot tune them in this tab yet.

## Tests (no Docker)

- `test_cockpit_view` (or sibling): Mixed-flow tab string / `active_tab` value `"mixed"` present; core `mf_*` state keys initialized.
- Isolated mixed-flow job dict round-trips params fields; worker module imports `evaluate_mixed_flow`.
- `MixedFlowParams` from a helper rejects `r_eye >= r_back` (unit, no UI).
- Existing Fan / Propeller cockpit smoke tests stay green.

## Non-goals

- NSGA `--archetype centrifugal` from cockpit
- Volute / 90° radial domain
- Mixed-flow BEM
- Camber / thickness / camber_pos sliders
- Stator or frame options on mixed-flow Assess
- Catalog auto-ingest of cockpit Assess results
- Fan-tab topology switch

## Success

From the Mixed-flow tab, a user can change core knobs, preview, export an STL, and Assess with the hose picker; axial Fan and Propeller tabs behave as today.
