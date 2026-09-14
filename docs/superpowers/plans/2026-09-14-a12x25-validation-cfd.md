# A12x25 Validation CFD Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce an honest first P–Q / free-air comparison of the **reference** A12x25 stock recipe against published 60.1 CFM / 22.9 Pa, with a mesh-ladder note and a written report that separates geometry error from model error.

**Architecture:** Prefer a dedicated `scripts/run_a12x25_validation.py` that defaults to `config/problems/a12x25_reference.yaml` (cockpit Stock). Reuse CFD plumbing from `scripts/validate_a12x25.py` / `fansim.cfd.*`. Do not commit case dumps — only script, small JSON summaries under `runs/` if useful, and `docs/validation/a12x25_pq_report.md`.

**Tech Stack:** Python, OpenFOAM via Docker (`image_available`), matplotlib Agg, pytest for CLI/default wiring (no Docker in unit tests).

## Global Constraints

- Default geometry path **must** be `config/problems/a12x25_reference.yaml` (Phase 2 Important carry-forward) — not the legacy approximate path alone.
- Report must separate **geometry error** vs **model/idealization error**; cite `docs/validation/a12x25_geometry_acceptance.md` interim CFD bands (±10% free-air, ±5 Pa shut-off).
- Stamp screening honesty: do not claim grid-converged unless GCI was actually computed.
- Prefer `uv run`. Windows OCCT teardown noise after green pytest is OK.
- Do not commit huge `runs/**` case trees; JSON/png summaries + docs only.
- Leave `CHAT_RECOVERY/` alone. Do not push.

---

### Task 3.1: Validation runner + reference default + report scaffold

**Files:**
- Create: `scripts/run_a12x25_validation.py`
- Create: `docs/validation/a12x25_pq_report.md` (scaffold with TBD tables OK until Task 3.2 fills numbers)
- Create: `tests/test_a12x25_validation_cli.py` (source/help asserts — no Docker)
- Optionally thin-wrap or deprecate default in `scripts/validate_a12x25.py` help to point at the new script

**Interfaces:**
- Consumes: reference yaml + OpenFOAM image when running
- Produces: CLI with `--params` defaulting to reference; `--backs`; `--base-cell` / optional `--mesh-ladder`; `--out`; writes `validation.json` / plot under `--out`

- [ ] **Step 1: Failing CLI test** — assert `run_a12x25_validation.py` help/source default params path contains `a12x25_reference.yaml`.

- [ ] **Step 2: Implement runner** (may adapt `validate_a12x25.py`). Support at least free-air + multi-back P–Q. Optional `--mesh-ladder 0.008,0.005,0.003` for free-air-only ladder; if three CFMs obtained, call `fansim.analyze.grid_convergence` when available and stamp results.

- [ ] **Step 3: Write report scaffold** `docs/validation/a12x25_pq_report.md` with sections: geometry recipe provenance, mesh note, free-air vs 60.1, shut-off/proxy vs 22.9, geometry vs model error, next physics levers. Mark numeric cells TBD until Task 3.2.

- [ ] **Step 4: Pytest** `tests/test_a12x25_validation_cli.py` green.

- [ ] **Step 5: Commit** (script + tests + scaffold report; no case dumps)

```powershell
git add scripts/run_a12x25_validation.py docs/validation/a12x25_pq_report.md tests/test_a12x25_validation_cli.py
git commit -m "Add A12x25 validation runner defaulting to reference stock."
```

---

### Task 3.2: Execute reduced campaign + fill report numbers

**Files:**
- Modify: `docs/validation/a12x25_pq_report.md`
- Optional: small `runs/validate_a12x25_phase3/validation.json` summary only (if committing JSON; skip heavy meshes)

**Procedure:**

- [ ] **Step 1: Confirm** `image_available()` is True.

- [ ] **Step 2: Run a reduced but honest campaign** with the new runner, e.g.:
  - Free-air mesh ladder at least **two** (prefer three) `--base-cell` values, **or** document why only one cell was affordable.
  - Multi-point backs including `0` and near shut-off proxy (e.g. `0,5,10,15,20`) at the medium cell if ladder is costly.
  - Use `--params config/problems/a12x25_reference.yaml` explicitly.

- [ ] **Step 3: Fill the report** with measured CFM/Pa, % error vs published, convergence flags, cell counts if known, GCI note or “not computed”.

- [ ] **Step 4: Commit report** (and tiny JSON if useful). Do **not** `git add` full OpenFOAM case directories.

```powershell
git add docs/validation/a12x25_pq_report.md
git commit -m "Record first A12x25 reference P-Q validation comparison."
```

---

## Phase exit gate

- Runner defaults to reference stock
- Report exists with real numbers (or explicitly BLOCKED with Docker/runtime reason)
- Geometry vs model error discussed; interim acceptance bands cited
- Parent program next: Phase 4 deps/perf
