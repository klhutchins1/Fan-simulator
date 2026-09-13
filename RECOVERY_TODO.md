# Fan-Simulator — recovery TODO (open items after the 2026-09 rebuild)

**Status:** the project was reconstructed from a dead drive using two Claude Code transcripts +
Cursor's 221 agent transcripts (no backup existed). It now **imports end-to-end, builds real
geometry, and passes ~529 / 622 non-docker tests**, all committed and pushed to
`git@gitea:klhutchins/Fan-simulator.git`. This file tracks what's left.

Run the suite: `uv run --extra optim python -m pytest -m "not docker and not slow" -q`

## Provenance / trust
- **Unmarked files** = verbatim Cursor `Write`s (the drive-death bytes) — trust these.
- **`# RECONSTRUCTED` / `# --- spliced ...`** (notably `fansim/geometry/blade.py`, and small
  helpers) = rebuilt from replayed edits or authored from a test contract — **verify** if a bug
  surfaces. `blade.py` is the main one (my 420-line base + replayed Cursor edits + splices).
- **`# RECOVERED-FROM-CHAT`** = my Aug26–Sep03 snapshot, kept only where nothing newer existed.
- Raw mined archive: `CHAT_RECOVERY/cursor_full_recovery/` (334 files). Merge manifest:
  `CURSOR_MERGE_MANIFEST.txt`. Recovery narrative: `README_RECOVERY.md`, `HANDOFF_TO_CURSOR.md`.

## Remaining test failures (~74), by bucket

### 1. Later feature to re-integrate — surrogate prescreen (5) — `test_surrogate_catalog`
The 2026-09-04 surrogate/boost work. My restored `fansim/optimize/objectives.py` (clean Sep-03)
predates it; Cursor's staging copy was truncated. Needs splicing from Cursor transcripts:
- `evaluate_candidate(..., surrogate_prescreen_cfm=...)` gate,
- `run_study(..., surrogate_prescreen_cfm=...)` pass-through + online refit after each feasible trial,
- `scripts/run_optimization.py` `--surrogate-prescreen` flag + help ("Refits after each feasible…").
`fansim/surrogate/{gp,catalog}.py` are present; `CatalogEntry.cfd_stale/k` now added.

### 2. Behavior polish (tests are the recovered spec) — core path
- `test_le_te_thick` (2): `apply_le_te_thickness`/`le_te_thick_factors` are RECONSTRUCTED fallbacks
  (never in any transcript). Needs the real TE-blunt-cap behavior (no mid-chord sign spike; TE capped
  below LE nose). See `fansim/geometry/blade.py`.
- `test_cylindrical_tip` (1): `_trim_blade_to_tip_cylinder` trims to ~52.3 mm vs expected ≤50 —
  verify the real trim tolerance.
- `test_stator` (2), `test_wall_ks` (3), `test_deflection` (2), `test_notched_tips` (1),
  `test_rounded_plate` (1) — assorted reconstructed-behavior gaps.

### 3. Judgment calls (which version is canonical)
- `test_shroud::test_cockpit_declares_shroud_height_slider` — the shroud slider moved from `app.py`
  to `fan_tab.py` in the 09-11 extract; my Sep-03 test still checks `app.py`. Update the test to
  `fan_tab.py`, or restore the old location.
- Several `test_placement`/`test_shroud` frame-gap asserts use strict `<` on my Sep-03 frame-gap API
  vs the newer reconstructed `placement.py`. Pick the canonical `placement.py` + matching tests.
- `test_search_space` (4): later `suggest_params(frame_half_mm=...)` param + guided-space behavior.

### 4. Deprioritized archetypes (skipped per "core fan path first")
`test_volute` (5), `test_mixed_flow*` (11), `test_cror` (2), `test_wind_turbine` (1),
`test_prop_*` (10). Later packages reconstructed from Cursor `Write`s but missing trailing edits
(no timestamps to order the replay). Fixable against their tests when these archetypes matter.

### 5. Genuinely lost — not code
- `test_uiuc_polars` (3): the UIUC LSAT airfoil-polar **CSV data files** never existed in any
  transcript. **Re-download** from the UIUC low-speed airfoil database and drop them where the test
  expects (`fansim/propeller/polars/` or similar per the test path).

## Also regenerable (gitignored, not lost source)
`runs/**` CFD cases, `catalog/catalog.db`, `exports/**`, `docs/control_images/*.png` — re-create by
re-running the optimizer / scripts once Docker + OpenFOAM are available.
