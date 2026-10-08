# Fan-Simulator — recovery TODO (open items after the 2026-09 rebuild)

**Status:** the project was reconstructed from a dead drive using two Claude Code transcripts +
Cursor's 221 agent transcripts (no backup existed). It now **imports end-to-end, builds real
geometry, and passes ~529 / 622 non-docker tests**, all committed and pushed to
`git@gitea:klhutchins/Fan-simulator.git`. This file tracks what's left.

Run the suite: `uv run --extra dev python -m pytest -m "not docker and not slow" -q`

## Provenance / trust

**2026-09-16:** Leading `# RECOVERED-FROM-CHAT` / `# RECONSTRUCTED` / `# EXTRACTED-FROM-CURSOR*`
apology headers were stripped from all `fansim/*.py` modules (roadmap §15.1). This file is the
single provenance note — do not put recovery apologies back into source headers.

- **Unmarked product code** under `fansim/` is the current trusted tree for day-to-day work.
- **`fansim/geometry/blade.py` geometry-golden signed off 2026-09-16 (roadmap §15.2)** —
  `validation/reference/a12x25_blade_golden.json` + `tests/test_blade_golden.py` freeze parametric
  stock volume/bounds/tip-section and soft-envelope tip/axial vs the close-ref STL. Absolute
  stock↔close-ref volume is still approximate (~1.4×); treat published CFM claims as validation-
  gated, not recipe-gated. Mid-file `# --- spliced` archaeology comments may still exist; ignore them.
- Raw mined archive: `CHAT_RECOVERY/cursor_full_recovery/` (gitignored). Merge manifest:
  `CURSOR_MERGE_MANIFEST.txt`. Recovery narrative: `README_RECOVERY.md`, `HANDOFF_TO_CURSOR.md`.

## Remaining test failures (archetype bucket closed 2026-09-13), by bucket

### 1. Later feature to re-integrate — surrogate prescreen — DONE 2026-09-13 (Cursor)
Wired from transcript patches into `objectives.py` / `study.py` /
`scripts/run_optimization.py`. `tests/test_surrogate_catalog.py` green.

### 2. Behavior polish (tests are the recovered spec) — core path
- `test_le_te_thick` / `test_cylindrical_tip` / `test_search_space` — **DONE 2026-09-13 (Cursor)**:
  restored TE blunt-cap (`TE_BLUNT_FRAC=0.10`, side-aware lift), `tip_section_points` cylinder clamp,
  `TIP_CAP_CLEARANCE_MM=0.5` + `frame_half_mm` on `suggest_params`, GUIDED blades/camber reopened.
  23/23 green.
- `test_stator` / `test_wall_ks` / `test_deflection` / `test_notched_tips` / `test_rounded_plate` —
  **DONE 2026-09-13 (Cursor)**: tip-notch TE bite in `_section_loop`, print η/FSI penalty,
  `build_case(wall_ks_mm=...)`, OpenFOAM template FRAME/CASING/STATOR + `IMPELLER_NUT` placeholders,
  `--stator` argv, `blade_to_flat` `section_family`. 34/34 green.

### 3. Judgment calls (which version is canonical)
- `test_shroud::test_cockpit_declares_shroud_height_slider` — **DONE 2026-09-13**: test now reads
  `fan_tab.py` (09-11 extract).
- `test_placement` / `test_shroud` frame-gap / bio-features / shroud BEM — **DONE 2026-09-13 (Cursor)**:
  `fit_envelope` uses `features_from_flat` + `OPTIMIZER_TIP_GAP_MM` target; tip-notch keys on
  `blade_from_flat`; shroud print gate; `load_designs` merges `shroud_thick_mm`; BEM tip-gap=0 for
  full ring; `_shroud_solid` uses `shroud_axial_range`; dropped duplicate pre-cylindrical placement
  tests. 51/51 green.


### 4. Deprioritized archetypes — DONE 2026-09-13 (Cursor)
Volute / mixed / CROR / prop / wind recovery: `SCREENING_GRID_STAMP`, circular
inlet-area honesty on mixed/CROR, archetype registry wiring, PROP/dual-MRF
templates, prop optimize helpers, stator/`wall_ks`/motor-curve stamps. Focused
suites green (mixed+volute+cror 44/44; prop/wind re-verified same day).

Previously: `test_volute`, `test_mixed_flow*`, `test_cror`, `test_wind_turbine`,
`test_prop_*` — packages reconstructed from Cursor `Write`s but missing trailing
edits. Fixed against their tests.

### 5. Genuinely lost — not code
- `test_uiuc_polars` — **DONE 2026-09-13 (Cursor)**: regenerated NACA + e387/sd7032/s1223 CSVs from
  transcript Shell generators into `fansim/data/polars/`; wired `_cl_cd` → `cl_cd_table`.
  See `CHAT_RECOVERY/NOTE_UIUC_POLARS_RECOVERED.md`. Suite green.

## Also regenerable (gitignored, not lost source)
`runs/**` CFD cases, `catalog/catalog.db`, `exports/**`, `docs/control_images/*.png` — re-create by
re-running the optimizer / scripts once Docker + OpenFOAM are available.
