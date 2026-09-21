# Track A A3: BEMT ↔ measured CT/CP quorum (static)

**Date:** 2026-09-21  
**Status:** approved (2026-09-21)  
**Parent:** `docs/superpowers/specs/2026-09-21-prop-pythrust-power-design.md` (Track A stage 1)  
**Roadmap:** Complements §4.3 CFD; does **not** replace it. Marks bib §7 UIUC PropDB “→ code” from planned → A3 harness.

## Goal

Add a **geometry-honest** quorum that compares fansim BEMT static CT₀/CP₀ against measured
catalog witnesses — without pretending a dia×pitch helix loft is the same blade as the
wind-tunnel prop.

**Witnesses (both):**

1. **APC via PyThrust** (same bundled `apc_202602` tables as stage-1 Q4/Q5) — propulsion-marked.  
2. **One frozen UIUC PropDB static fixture** under `validation/reference/uiuc_propdb/` — always-on CI.

## Plain language

Stage 1 proved our motor/catalog adapter and momentum FoM math. A3 asks a harder question:
*does our BEMT, on a deliberately approximate blade, land in the same neighborhood as measured
static CT/CP?* Wide bands are intentional. Failures mean “look at the model or the fixture,”
not “swap product numbers to the witness.”

## Scope

### In

- Approximate 2-blade loft from **diameter_in + pitch_in** only (helix twist via existing
  `_pitch_angle_deg` / `prop_blade_params`-class geometry; hub/chord defaults frozen in code).
- Static only (`J ≈ 0`): report CT₀, CP₀ at one RPM.
- Shared compare helper used by both witnesses.
- Quorum IDs:
  - **Q6** — BEMT ↔ APC (PyThrust); `@pytest.mark.propulsion`
  - **Q7** — BEMT ↔ UIUC fixture; always-on
- Stamp every compare result with `geometry_match="approximate"`, `source`, `prop_id` / fixture id,
  `rpm`, `band_rel`, deltas.
- Extend `scripts/evaluate_prop_power.py --mode quorum` so one report concatenates
  stage-1 `run_propulsion_quorum` checks (Q3–Q5) **plus** A3 `run_bemt_catalog_quorum`
  (Q6/Q7). Q6 is omitted or `pass: null` / skipped with reason when PyThrust is missing;
  Q7 always runs.
- Document band choice and fixture provenance in honesty notes + bib back-ref.

### Out (non-goals)

- Forward-flight polar / multi-J sweep (follow-on).  
- Digitized UIUC/APC planform or tighter bands.  
- Replacing BEMT product path with catalog CT/CP.  
- Averaging / voting witnesses into user-facing numbers.  
- Hard dependency on PyThrust for Q7.  
- Datasheet marketing claims vs Gemfan/HQ.  
- Stage 2 BEMT→PyThrust CSV export.

## Physics / definitions

Reuse `fansim.propeller.polar` conventions:

- \( n \) = RPM/60 (rev/s), \( D \) = diameter (m), \( \rho = 1.225 \)  
- \( C_T = T / (\rho n^2 D^4) \)  
- \( C_P = P / (\rho n^3 D^5) \)  
- Static: \( J = 0 \) (BEMT `v_forward=0`; catalog point with `j==0` or min `j`).

## API (proposed)

New module: `fansim/propeller/bemt_catalog.py` (keep `power.py` for electrical/catalog adapter).

| Symbol | Role |
|--------|------|
| `approximate_prop_blade(diameter_in, pitch_in, *, blade_count=2) -> BladeParams` | Helix loft; frozen hub/chord defaults |
| `bemt_static_ct_cp(diameter_in, pitch_in, *, rpm, blade_count=2, rho=RHO_AIR) -> dict` | CT₀/CP₀ + thrust/power stamps + `geometry_match` |
| `load_uiuc_static_fixture(path \| id) -> dict` | `{prop_id, diameter_in, pitch_in, rpm, ct, cp, provenance…}` |
| `compare_bemt_to_static_witness(*, diameter_in, pitch_in, rpm, ct_w, cp_w, *, band_rel=0.35, source, prop_id) -> dict` | `{pass, ct_bemt, cp_bemt, ct_w, cp_w, rel_err_ct, rel_err_cp, geometry_match, …}` |
| `run_bemt_catalog_quorum(...) -> dict` | `{checks: [Q6?, Q7], all_pass}` — does **not** replace `run_propulsion_quorum` |

Default props (stage A3 freeze):

| Check | Size | RPM | Witness |
|-------|------|-----|---------|
| Q6 | APC **9×4.7 SF** (`APC_9x4.7SF`) | nearest catalog RPM to **6026** (probe: 6000) | PyThrust APC static CT/CP |
| Q7 | UIUC Vol1 **APC Slow Flyer 9×4.7** static row | **6026** | Vendored fixture JSON |

**Why not stage-1 5×4.5E:** a pre-plan probe with default dia×pitch loft vs `APC_5x4.5E` @ 10k RPM showed ~39% CT / ~54% CP error (outside ±35%). UIUC+APC **9×4.7 SF** sits inside the band with the same loft family. Spec allows independent Q6/Q7 sizes when 5×4.5 UIUC is missing; we align both on 9×4.7.

## Acceptance bands

| Check | Band | Notes |
|-------|------|-------|
| Q6 CT and CP | **±35%** relative | Approximate geometry; do not silently tighten |
| Q7 CT and CP | **±35%** relative | Same |
| Both | Both CT **and** CP must pass | One-sided “lucky” CT is a fail |

On failure: pytest fails with deltas; CLI quorum prints `pass: false` + detail. **Do not** overwrite BEMT outputs.

If real data shows systematic bias outside ±35% with the frozen loft defaults, **stop** and update this spec’s honesty section + band with measured deltas — do not paper over in code alone.

## Fixture format (UIUC)

`validation/reference/uiuc_propdb/<id>.json` example shape:

```json
{
  "prop_id": "UIUC_<NAME>_STATIC",
  "manufacturer": "APC",
  "diameter_in": 5.0,
  "pitch_in": 4.5,
  "blade_count": 2,
  "rpm": 10000,
  "j": 0.0,
  "ct": null,
  "cp": null,
  "provenance": {
    "site": "https://m-selig.ae.illinois.edu/props/propDB.html",
    "file_or_table": "<propDB file or table id>",
    "retrieved": "2026-09-21",
    "notes": "Static row only; vendored for A3 Q7"
  }
}
```

`ct` / `cp` / table id are **schema placeholders** — filled from PropDB at implementation
(not invented in this spec). Fixture must ship with real finite CT/CP before Q7 can pass.

## Tests

| Test | Marker | Asserts |
|------|--------|---------|
| `test_bemt_static_ct_cp_finite` | none | Approximate loft → finite CT/CP > 0 at static |
| `test_quorum_q7_bemt_vs_uiuc_fixture` | none | Q7 pass within ±35% |
| `test_quorum_q6_bemt_vs_apc` | `propulsion` | Q6 pass within ±35% |
| CLI help still lists `quorum` | none | Existing parser test extended if needed |

## Honesty

- Dia×pitch helix ≠ measured blade (airfoil, planform, hub). Wide bands encode that.  
- APC (PyThrust) and UIUC are **independent ingest paths**; agreement of both with BEMT is stronger than either alone.  
- Passing A3 does **not** claim datasheet match for Gemfan/HQ or custom lofts.  
- Q4 stage-1 identity check remains algebraically weak; A3 is the real aero witness.

## Done when

- Spec approved  
- Implementation plan written  
- Helper + Q6/Q7 + UIUC fixture + tests + CLI quorum extension landed  
- Bib §7 UIUC line updated from “planned” to A3 harness path  

## Follow-ons (explicitly later)

- Multi-J polar witness  
- Digitized geometry → tighter bands  
- Stage 2: export BEMT CT/CP tables into PyThrust CSV  
