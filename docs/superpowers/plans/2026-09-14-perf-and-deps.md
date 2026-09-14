# Perf and Dependencies Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Document that critical dependencies are used as upstream intends, and land measured performance baselines plus at most 1–2 screening-path speedups that do not weaken physics honesty.

**Architecture:** Task 4.1 is an audit document (versions from `pyproject.toml` / lock / env, smoke pointers, footguns, peer-repo match/differ). Task 4.2 measures preview/BEM timings first, then implements only top ranked speedups with before/after numbers. Absolute CFD claims stay gated by Phase 3 honesty (free-air still fails interim band).

**Tech Stack:** uv, pytest, CadQuery, Optuna, PyVista/Trame, OpenFOAM Docker image, SciPy, trimesh.

## Global Constraints

- Prefer `uv run` / `uv run python -m pytest`.
- Do not weaken physics for speed (no deleting frame/tip-gap, no slip walls for absolute claims, no fake Optuna (0,0) prune).
- Pin changes in `pyproject.toml` / `uv.lock` only when the audit justifies them.
- Leave `CHAT_RECOVERY/` alone; do not push; do not commit huge `runs/` case trees.
- Windows OCCT teardown non-zero after green pytest is noise.
- Cite Phase 3: free-air −32% — screening speedups must not be sold as closing that gap.

---

### Task 4.1: Dependency & peer-repo audit

**Files:**
- Create: `docs/validation/dependency_peer_audit.md`
- Modify: `pyproject.toml` / `uv.lock` only if a pin is clearly justified

**Packages:** CadQuery/OCP, OpenFOAM 2406 image, Optuna, PyVista/Trame/trame-vtk, trimesh, SciPy

- [ ] **Step 1:** For each package: pinned/range version, one smoke test path (file or command), one known footgun.
- [ ] **Step 2:** Skim 1–2 public references per critical stack; record we match / we differ (OpenFOAM MRF fan tutorials; CCBlade/QProp BEMT sign; Optuna multi-obj).
- [ ] **Step 3:** Commit

```powershell
git add docs/validation/dependency_peer_audit.md
# plus pyproject.toml uv.lock only if changed
git commit -m "Document dependency peer audit and justified pins."
```

---

### Task 4.2: Performance baselines and speedups

**Files:**
- Create: `docs/validation/perf_baseline.md`
- Touch code only for the top 1–2 wins (likely BEM/surrogate screen path, geometry isolation/cache — not absolute CFD)

- [ ] **Step 1:** Measure preview `build_impeller` and one BEM screen; record in the doc.
- [ ] **Step 2:** Rank allowed speedups; pick top 1–2.
- [ ] **Step 3:** Implement with before/after timings in `perf_baseline.md`.
- [ ] **Step 4:** Commit

```powershell
git add docs/validation/perf_baseline.md fansim
git commit -m "Add perf baselines and first screening-path speedups."
```

If no safe code win is clear after measurement, commit the baseline doc alone with an explicit “no code change this cycle” note (DONE_WITH_CONCERNS is OK).

---

## Phase exit gate

- Audit doc complete for listed packages
- Perf baseline numbers recorded
- At most 1–2 honest screening speedups or documented deferral
- Parent next: Phase 5 print/measure (hardware-gated) or Phase 6 keep/cut board
