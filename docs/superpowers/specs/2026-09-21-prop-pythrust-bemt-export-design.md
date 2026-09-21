# Track A Stage 2: BEMT → PyThrust CT/CP CSV export (+ Prop Analyze)

**Date:** 2026-09-21  
**Status:** draft (awaiting user review of this file)  
**Parent:** `docs/superpowers/specs/2026-09-21-prop-pythrust-power-design.md`  
**Related:** A3 (`2026-09-21-prop-bemt-uiuc-a3-design.md`) — static quorum; this slice is the **catalog bridge** for custom lofts.  
**Roadmap:** Complements §4.3 CFD; does **not** replace BEMT product path or bundled APC.

## Goal

Export a **PyThrust-compatible** propeller catalog entry (JSON metadata + CSV polar) from fansim
BEMT on the current Design blade, with an **Analyze-tab button** next to STL export. Default grid
is APC-like (multi-RPM × J); knobs allow thinning/thickening.

## Plain language

Stage 1 matched COTS props already in PyThrust’s APC tables. Stage 2 lets a *custom*
lofted blade speak the same catalog language: we run BEMT over a grid, write the same
CSV/JSON shape PyThrust loads, and drop files under `exports/pythrust/` so they can be
loaded later (or offline) without forking PyThrust.

## Scope

### In

- Library module `fansim/propeller/pythrust_export.py`:
  - `default_export_grid()` → default RPM list + advance-ratio (J) list
  - `export_bemt_pythrust_catalog(params, *, prop_id, diameter_in, pitch_in, blade_count, out_dir, rpm_list=None, j_list=None, rho=RHO_AIR) -> dict`  
    Writes `{prop_id}.json` + `{prop_id}.csv` (PyThrust pair); returns paths + stamps.
  - Helpers to build rows via existing `run_bemt_polar` / `analyze` + `nondim`.
- CSV columns match APC dataset header (same names/order as bundled files):

  `rpm,speed_mps,advance_ratio,efficiency,thrust_coeff,power_coeff,power_w,torque_nm,thrust_n,thrust_per_power_n_w,mach,reynolds,figure_of_merit`

  Fill what BEMT provides; set unused/unknown to `0.0` or empty only if PyThrust tolerates — prefer **0.0** for numeric cols PyThrust always parses. Stamp honesty in sidecar meta (not a fake physics claim).
- JSON metadata shape (PyThrust):

  ```json
  {
    "id": "<prop_id>",
    "manufacturer": "fansim",
    "model": "<human or prop_id>",
    "diameter_in": 5.0,
    "pitch_in": 4.5,
    "blade_count": 2,
    "data_csv": "<prop_id>.csv"
  }
  ```

  Plus optional fansim-only sidecar `*.export.json` (or embed under a `"fansim"` key if we keep a single JSON — **prefer separate** `{prop_id}.export.json` so PyThrust’s strict JSON loader stays clean):

  `source=bemt`, `geometry_match` (`design_blade` | `approximate`), grid knobs, tip radius, timestamp.
- CLI: `scripts/export_prop_pythrust_csv.py` — `--spec` / blade from PropSpec + optional explicit RPM/J lists; writes to `--out` (default `exports/pythrust`).
- Cockpit Prop Analyze: button **Export CT/CP (PyThrust)** beside STL export; uses `prop_editor_params()` + current PropSpec dia/pitch/blades; async + busy ticker like STL export; message in `prop_export_msg` (or `prop_pythrust_export_msg` if shared msg is too noisy — prefer **reuse** `prop_export_msg` with clear prefix).
- Tests:
  - Always-on: export tiny grid → CSV header exact, finite CT/CP, JSON loads, `PropellerDatabase().load(tmp_dir)` finds the id when propulsion extra present (mark that assert `@pytest.mark.propulsion` or skip).
  - Always-on: `default_export_grid` returns non-empty RPMs and Js including `0.0`.

### Out (non-goals)

- Optimize / Pareto batch export.  
- Motor–battery solve UI in Analyze (catalog operating point remains CLI / stage 1).  
- Writing into the **bundled** `apc_202602` site-packages tree.  
- Cockpit motor picker / OpenMDAO.  
- Digitized geometry or tighter A3 bands.  
- Hard dependency on PyThrust for Analyze (export is pure fansim BEMT; load-smoke is optional).

## Default grid (configurable)

Frozen defaults in code (override via CLI flags / optional Analyze advanced later — Stage 2 Analyze uses defaults only unless cheap text fields are trivial):

| Knob | Default |
|------|---------|
| RPM list | `1000, 3000, 5000, 7000, 9000, 11000` (or clamp to `≤ spec.rpm_max`) |
| J list | `0.0, 0.05, 0.10, …, 0.60` step `0.05` |
| Density | ρ = 1.225 |

CLI: `--rpm 1000,5000,9000` and `--j 0,0.1,0.2,0.4` override. Analyze button: defaults only in Stage 2.

## Physics

For each (RPM, J):

1. \( D \) from tip radius (mm→m) or PropSpec diameter.  
2. \( V_\infty = J \cdot n \cdot D \) with \( n = \mathrm{RPM}/60 \).  
3. `analyze(params, rpm, v_forward=V∞)` → T, Q, P.  
4. `nondim` → CT, CP, η.  
5. Fill CSV row; FoM from BEMT hover identity when J=0 (existing `figure_of_merit`), else 0 or omit → use `0.0` if column required.

## API (proposed)

| Symbol | Role |
|--------|------|
| `DEFAULT_RPM_LIST`, `DEFAULT_J_LIST` | Frozen defaults |
| `default_export_grid(*, rpm_max: float \| None = None) -> tuple[list[float], list[float]]` | Clamp RPMs to rpm_max when set |
| `export_bemt_pythrust_catalog(...) -> dict` | Write JSON+CSV(+export.json); return `{csv, json, export_meta, n_rows, prop_id, …}` |
| `prop_id_for_export(spec_key: str, *, suffix: str = "BEMT") -> str` | Sanitize id e.g. `FANSIM_cine_3inch_BEMT` |

## Cockpit behavior

Mirror `export_prop_stl`:

- Guard with `prop_export_busy` (shared lock with STL — one export at a time).  
- Executor: call `export_bemt_pythrust_catalog` with editor params.  
- Success message: path to CSV + row count.  
- Failure: exception type + message in `prop_export_msg`.

## Honesty

- Tables are **BEMT**, not wind-tunnel or APC measured. Stamp `source=bemt` in export meta.  
- Custom loft ≠ catalog APC even at same dia×pitch (A3 bands apply if compared).  
- Prefer BEMT FoM at J=0 from `analyze` / `PropPerf.figure_of_merit`; for J>0 write `0.0` in
  `figure_of_merit` (column required by PyThrust header) rather than inventing a false FoM.
- Prefer tip Mach from tip speed / 343 when easy; else `0.0`. Reynolds: `0.0` unless we already
  compute local Re in the polar path (do not invent).
- Filling mach/reynolds with 0.0 must not be marketed as measured.

## Done when

- Spec approved + implementation plan written.  
- Library + CLI + Analyze button + tests landed.  
- Bib / roadmap one-liner: Stage 2 bridge noted (optional short note under prop / Track A).  

## Follow-ons

- Analyze motor solve against exported id (local DB dir).  
- Optimize top-N CSV dump.  
- Richer column fidelity (Re, Mach from tip speed).  
