# AMCA total-pressure stamps (stage 1)

**Date:** 2026-09-03  
**Status:** accepted  
**Approach:** Write kinematic total pressure in OpenFOAM, area/flux-average it on the existing inlet and outlet patches, stamp Δp₀ and η_total on `FanMetrics`. Do **not** replace the NSGA `efficiency` objective. Not prism layers, not a 3-mesh GCI campaign, not a full P–Q / shut-off sweep.  
**Roadmap:** §1.5 stage 1. Closes adversarial-review §3.1’s “no total-pressure FO” hole. Leaves AMCA chambers, addLayers, and Roache GCI wiring for later slices.

## Plain language

Efficiency today is `Q × (p_out − p_in) × ρ / P_shaft`. `p` is **static** kinematic pressure on the domain patches. AMCA 210 / ISO 5801 rate a fan on **total-pressure rise** Δp₀ = p₀,out − p₀,in, with η_t = Q Δp₀ / P_shaft. Stage 1 adds that number next to the old one so we can see whether the 10–20% efficiencies are a definition problem. Rankings stay on the old `efficiency` until we decide they should move.

## Problem

```text
inletP / outletP  →  areaAverage of static p
static_rise_pa    = (p_out − p_in) * rho
efficiency        = Q * static_rise_pa / P_shaft
```

Velocity-driven free delivery can even report a **negative** static rise (inlet over-driving the fan). That is not AMCA free-delivery. Without a total-pressure FO we cannot tell metric muddle from a genuinely weak blade.

## Goal

1. **OpenFOAM FOs** in `CONTROL_DICT`, always on, before `inletP0`/`outletP0`:

```text
pTot      pressure FO, mode total, result pTot
          kinematic (same units as p: m²/s²). writeControl none.
inletP0   surfaceFieldValue on patch inlet
          operation weightedAverage, weightField phi, fields (pTot)
outletP0  same on patch outlet
```

Execute on the same `timeStep` / `@FOINT@` as the existing FOs. `pTot` must run first so the field exists. Match `opencfd/openfoam-default:2406` dictionary syntax; if `rhoInf` is required, use **1** so Python still multiplies by `rho` like static p.

2. **`FanMetrics`** — add fields, keep the old ones:

```text
total_pressure_rise_pa   (p0_out − p0_in) * rho
eta_total                Q * total_pressure_rise_pa / P_shaft   (0 if shaft ~ 0)
p0_inlet_kin
p0_outlet_kin
```

`efficiency`, `static_pressure_rise_pa`, `air_power_w` stay static-based. `to_dict()` picks up the new keys automatically (`raw.free` / `raw.load`).

3. **Parse is optional** for old cases: if `inletP0` or `outletP0` `.dat` is missing, set the four new fields to `None` (do not raise). New solves always write the FOs.

4. **Do not** change `OBJECTIVE_NAMES`, catalog columns, NSGA ranking, or Assess caption this cycle.

## Honesty (what this is not)

Patch-averaged p₀ on the **current** CFD inlet/outlet is Bernoulli total pressure in this domain. It is **not** a certified AMCA 210 figure: measuring planes are not 2–3 D chambers, the circular screening duct is still a short cylinder, and velocity-driven free-air inlets are not p₀,in = atm. Pressure-driven load/op solves (totalPressure inlet) are the cleaner comparison. Stamp them all anyway.

Flux-weighted average (`phi`) is the energy-relevant mean. Do not use `|U_avg|²` reconstructed in Python — that under-counts non-uniform dynamic pressure.

## Tests (no Docker)

- `test_parse_fan_metrics` still passes **without** p0 files (new fields `None`).
- New: fake `inletP0` / `outletP0` `.dat` rows → `total_pressure_rise_pa == (p0_out − p0_in) * 1.2` and `eta_total == flow * that / shaft`.
- New: `CONTROL_DICT` text contains `inletP0`, `outletP0`, `mode            total` (or the 2406 equivalent once written). `test_case_build_files` (docker) is not required for stage 1.

## Non-goals

- Replacing NSGA `efficiency` with `eta_total`
- Prism layers / `addLayers` / y+
- Wiring `grid_convergence_index` into `scripts/run_grid_convergence.py`
- Full P–Q, shut-off, AMCA chamber geometry
- Cockpit caption / catalog.db columns
- Changing static `inletP`/`outletP`
