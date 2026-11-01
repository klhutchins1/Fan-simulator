# Handoff: tooltip audit (2026-10-31), from QA

- **Brief:** Kimball, Sat 2026-10-31 12:58 MDT.
- **Code:** master `3b92eea`, clean clone `/workspace/fansim/repo-tt`.
- **Main note:** `docs/qa/notes/tooltip-audit-2026-10-31.md`.
- **Tracker:** new rows UI-31 … UI-38 in `docs/QA_REVIEW.md`.
- **Nothing in `fansim/` or `scripts/` was edited.** The images are proposals only.

## Contents
- `img/`: proposed tooltip PNGs (460×250, the same format as `docs/control_images/`). The file name is the cockpit state model the image is meant for.
  - `img/range_fix/`: 13 re-renders of existing `e_*.png` at the real slider range (UI-35).
- `scripts/`:
  - `run_repo_generator.py`: drives the repo's `scripts/generate_control_images.py` without changing it (swaps its `CONTROLS` and `OUT`).
  - `render_stationary.py`: stator, stack and casing in the same pyvista style.
  - `schematics.py`: matplotlib diagrams for SEARCH/EVAL settings.
  - `scan_controls.py`, `build_inventory.py`, `range_check.py`: inventory tools.
  - `headless_check.py`, `headless_hover2.py`: read-only Playwright checks against the cockpit on :8080.
- `data/`:
  - `inventory.csv` / `.json`: 293 controls with area, mode, tooltip status, image and quoted text.
  - `range_check.json`: slider range vs image range.
  - `headless*.json` and screenshots.

## Re-run (box)
```
REPO=/workspace/fansim/repo-tt
$REPO/.venv/bin/python scripts/run_repo_generator.py missing   # about 1 min per image
$REPO/.venv/bin/python scripts/run_repo_generator.py ranges
cd $REPO && .venv/bin/python <handoff>/scripts/render_stationary.py
$REPO/.venv/bin/python scripts/schematics.py
```
Output goes to `/workspace/fansim/qa_tooltips/img/`. Edit `IMG`/`OUT` in each script if you need another location.

## To adopt (dev)
1. Copy `img/*.png` (and `range_fix/*.png` over the old ones) into `docs/control_images/`.
2. `fansim/cockpit/fan_copy.py:14`: change `glob("e_*.png")` to `glob("*.png")`, so `opt_*` and `assess_*` load.
3. Wrap the plain selects and switches (preset, material, hub profile, fan model, …) with `help_select` / `help_switch`.
4. Move the `MISSING` / `RANGES` rows into `CONTROLS` in `scripts/generate_control_images.py`.
