# A12x25 Recipe Fidelity Plan

> **For agentic workers:** Follow task order. Do **not** rewire cockpit Stock to a datasheet-tuned yaml.

**Goal:** Quantify which parametric station knobs move free-air (BEM), then CFD-check one **experimental** sibling recipe — without claiming OEM CAD or silently replacing Stock.

**Parent:** [proper-state program](2026-09-14-proper-state-program.md) Phase 3 follow-on; validation context in [a12x25_pq_report.md](../../validation/a12x25_pq_report.md).

**Architecture:** Stock stays [`config/problems/a12x25_reference.yaml`](../../../config/problems/a12x25_reference.yaml). Sensitivity uses BEM (`pq_curve`, tip_gap 0.5 mm). At most one `a12x25_flow_candidate.yaml` gets a free-air CFD verify. Geometry and CFD budgets remain independent.

## Global constraints

- Keep `n_blades == 7`, tip **55–57 mm**, hub **20–23 mm**.
- Experimental candidate ≠ Stock; ≠ OEM; header must say so.
- Do not download unlicensed Thingiverse OEM meshes in this plan.
- Prefer `uv run`; do not commit OpenFOAM case trees.

---

### Task 1: BEM one-factor sensitivity

**Files:**
- Create: `scripts/a12x25_recipe_sensitivity.py`
- Create: `docs/validation/a12x25_recipe_sensitivity.md`

- [x] Load Stock via `stock_blade_flat("a12x25")` → `blade_from_flat` → `pq_curve(..., tip_gap_mm=0.5)`.
- [x] Perturb mid/tip stagger, mid/tip chord, max_camber (all stations), tip lean one-at-a-time within GUIDED-ish bands.
- [x] Write markdown table of free-air / shut-off vs baseline.

### Task 2: Experimental CFD candidate

**Files:**
- Create: `config/problems/a12x25_flow_candidate.yaml`
- Create: `docs/validation/a12x25_flow_candidate_summary.json`
- Local only: `runs/validate_a12x25_flow_candidate/`

- [x] Choose knobs from Task 1 that raise BEM free-air toward ~60 CFM without leaving envelope.
- [x] Run free-air CFD at tip_gap 0.5 mm, base_cell 0.006 via `scripts/run_a12x25_validation.py`.
- [x] Commit summary JSON only.

### Task 3: Docs / gates

- [x] Update `docs/validation/a12x25_pq_report.md` and `keep_cut_board.md`.
- [x] Do **not** change `STOCK_GEOMETRY_YAML["a12x25"]` this cycle.
