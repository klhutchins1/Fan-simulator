# §20.2 NeuralFoil / BEMT polar RMS — Implementation Plan

> **For agentic workers:** Execute task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Clear SF 9×4.7 C_T(J) RMS on the table path (or honestly re-scope), harden NeuralFoil opt-in, keep table default.

**Architecture:** Extend A/B diagnostic → apply smallest BEMT/gate fix → NeuralFoil stall/α + Prop Optimize backend wiring → tests + roadmap/audit docs.

**Tech Stack:** Python, BEMT (`fansim.propeller.bemt`), UIUC fixtures, optional NeuralFoil extra.

**Spec:** `docs/superpowers/specs/2026-09-30-neuralfoil-polar-20-2-design.md`

## Global Constraints

- Do **not** flip polar default to NeuralFoil.
- Do **not** datasheet-tune Stock fan stagger.
- Windows PowerShell; `uv run` / `uv run --extra neuralfoil`; green-then-crash OCCT exits = success.
- Commit to master; no `runs/`, `catalog.db`, `.superpowers/sdd/progress.md`.

---

### Task 1: Diagnostic in A/B script

**Files:** `scripts/audit_bemt_polar_ab.py`

- [ ] Add per-sweep report: per-J e_CT, windmill flags, RMS full vs attached (J ≤ first CT≤0 or last CT>0).
- [ ] Print summary dominating windmill vs attached.
- [ ] Run and record decision for Task 2.

### Task 2: Clear table RMS gate

**Files:** `fansim/propeller/bemt.py`, `tests/audit/test_prop_bemt_audit.py`, audit md, ledger if claim met

- [ ] Implement Phase-1 decision (negative thrust and/or attached-window registered gate).
- [ ] Re-run A/B; update xfails / claims.
- [ ] Keep default `table`.

### Task 3: NeuralFoil quality + Optimize wiring

**Files:** `fansim/propeller/neuralfoil_polars.py`, `bemt.py` `_section_aero`, Prop optimize/cockpit, tests

- [ ] Stall / cl_cap parity; widen α band; document supported range.
- [ ] Prop Optimize honors backend picker/env.
- [ ] Tests (skip NeuralFoil if extra missing).

### Task 4: Roadmap + commit

- [ ] Update §20.2 Partial text.
- [ ] Commit + push.
