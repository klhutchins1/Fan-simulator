# A12x25 Reference Geometry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Separate geometry fidelity from CFD fidelity for the Noctua NF-A12x25 reference, and wire a labeled stock recipe (yaml now; STL when available) so cockpit “Stock” and validation share one honest baseline.

**Architecture:** Acceptance docs define two independent budgets (geometry vs published envelope / trusted STL; CFD vs published P–Q). Stock geometry loads via `STOCK_GEOMETRY_YAML` → `stock_blade_flat("a12x25")`. Keep today’s parametric file as an explicitly approximate alias; promote a reference entry that is either a tighter yaml fit or an STL-backed recipe. Do not claim OEM CAD without a watertight STL under `validation/reference/`.

**Tech Stack:** Python, yaml blade configs (`fansim.geometry.config`), Optuna stock loader, pytest, docs under `docs/validation/`.

## Global Constraints

- Never treat `config/problems/a12x25.yaml` as OEM truth without an `approximate` / provenance label.
- Geometry gates and CFD gates stay separate documents/sections; do not merge into one “pass/fail”.
- Interim CFD targets until mesh study (Phase 3): free-air within **10%** of 60.1 CFM; shut-off within **5 Pa** of 22.9 Pa.
- Published ground truth lives in `docs/a12x25-reference.md` (60.1 CFM / 22.9 Pa / 22.6 dB(A) / 2000 RPM / 0.5 mm tip / 7 blades).
- Prefer `uv run` / `uv run python -m pytest` for tests.
- Do not commit huge OpenFOAM case dumps or unlicensed OEM CAD.
- Windows OCCT teardown non-zero exits after green pytest are noise — judge by pytest summary.
- Commit only files this task owns; leave `CHAT_RECOVERY/` and unrelated untracked docs alone.

---

### Task 2.1: Define Noctua reference acceptance metrics

**Files:**
- Modify: `docs/a12x25-reference.md`
- Create: `docs/validation/a12x25_geometry_acceptance.md`

**Interfaces:**
- Consumes: published 60.1 CFM / 22.9 Pa / 22.6 dB(A) / 2000 RPM / 0.5 mm tip / 7 blades
- Produces: geometry gates separate from CFD gates

- [ ] **Step 1: Write `docs/validation/a12x25_geometry_acceptance.md`** with:

1. **Geometry fidelity** (vs real impeller / trusted STL when present; else vs published envelope): tip radius, hub radius, blade count, axial depth, LE sickle character, tip clearance to frame ID (0.5 mm published). Include numeric bands matching the Task 2.2 tests (`n_blades == 7`, tip 55–57 mm, hub 20–23 mm).
2. **CFD fidelity** (vs published): interim free-air ±10%, shut-off ±5 Pa; note that X/Y tighten after Task 3.1 mesh study.
3. Explicit statement that passing geometry does **not** imply CFD pass and vice versa.

- [ ] **Step 2: Cross-link from `docs/a12x25-reference.md`** — short section pointing at the acceptance doc and restating the two budgets; keep existing published table intact.

- [ ] **Step 3: Commit**

```powershell
git add docs/a12x25-reference.md docs/validation/a12x25_geometry_acceptance.md
git commit -m "Define A12x25 geometry vs CFD acceptance budgets."
```

---

### Task 2.2: Reference stock recipe + envelope tests (yaml path)

**Files:**
- Keep / relabel: `config/problems/a12x25.yaml` (approximate)
- Create: `config/problems/a12x25_approx.yaml` (copy of current approximate, or symlink-equivalent content)
- Create or update: `config/problems/a12x25_reference.yaml` (best available parametric reference; same envelope as tests; header must say parametric-fit / not OEM STL)
- Optional placeholder note: `validation/reference/README.md` (how to drop `a12x25_impeller.stl` later)
- Modify: `fansim/optimize/search_space.py` (`STOCK_GEOMETRY_YAML`)
- Create: `tests/test_a12x25_reference_geometry.py`

**Interfaces:**
- Consumes: existing approximate yaml + published envelope
- Produces: `stock_blade_flat("a12x25")` → reference recipe; `stock_blade_flat("a12x25_approx")` → approximate regression continuity

**Procedure:**

- [ ] **Step 1: Failing tests** in `tests/test_a12x25_reference_geometry.py`:

```python
def test_reference_blade_count_and_envelope():
    from fansim.optimize.search_space import stock_blade_flat
    flat = stock_blade_flat("a12x25")
    assert flat["n_blades"] == 7
    assert 55.0 <= flat["tip_radius"] <= 57.0
    assert 20.0 <= flat["hub_radius"] <= 23.0

def test_approx_alias_still_loads():
    from fansim.optimize.search_space import stock_blade_flat
    flat = stock_blade_flat("a12x25_approx")
    assert flat["n_blades"] == 7
```

Skip or soft-assert STL silhouette checks unless `validation/reference/a12x25_impeller.stl` exists.

- [ ] **Step 2: Wire `STOCK_GEOMETRY_YAML`** so `"a12x25"` points at `a12x25_reference.yaml` and `"a12x25_approx"` at the approximate file. Ensure yaml headers label provenance (`approximate` vs `reference-parametric`).

- [ ] **Step 3: Add `validation/reference/README.md`** stating STL drop path and that CFD absolute claims wait for STL + Phase 3.

- [ ] **Step 4: Run** `uv run python -m pytest tests/test_a12x25_reference_geometry.py -q --tb=short`

- [ ] **Step 5: Commit**

```powershell
git add config/problems validation/reference fansim/optimize/search_space.py tests/test_a12x25_reference_geometry.py
git commit -m "Add A12x25 reference geometry recipe and stock loader wiring."
```

**Blocked escalation:** If a licensed/OEM STL appears later, replace yaml-backed reference with STL import without changing acceptance doc structure — that is a follow-up, not this task.

---

## Phase exit gate

- Task 2.1 + 2.2 complete and reviewed
- Cockpit Stock for `a12x25` loads reference recipe within envelope bands
- Docs clearly separate geometry vs CFD budgets
- Parent program next: Phase 3 Task 3.1 (validation CFD campaign)
