# Prop BEMT-Gate + CFD Refine (Stage 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Skip hopeless prop CFD via an optional BEMT thrust floor, and optionally CFD-refine the top N BEMT Pareto designs after a prop Optuna study.

**Architecture:** Add `bemt_thrust_g` + optional `params` / `bemt_floor_g` on `evaluate_prop_cfd` (no Docker when floor fails). Wire `--bemt-floor` on the CFD CLI and `--cfd-top` / `--bemt-floor` / `--cfd-out` on `run_prop_optimization.py`. Keep CFD out of the Optuna objective.

**Tech Stack:** Python 3.12 (uv), existing BEMT + `evaluate_prop_cfd`, pytest (no Docker in CI).

**Spec:** `docs/superpowers/specs/2026-09-08-prop-bemt-gate-design.md`

## Global Constraints

- Defaults: `bemt_floor_g=0` and `--cfd-top=0` (both **off**).
- Floor skip returns dict with `skipped=True`, `reason`, `bemt_thrust_g`, and CFD stamps (`solver`/`domain`/`regime` still set for honesty of *intent*).
- Do **not** put `rhoSimpleFoam` inside Optuna.
- Do **not** change fan `--bem-prescreen`.
- When CFD runs, stamp `bemt_thrust_g` beside CFD metrics.
- Unit tests: no Docker (`-m "not docker and not slow"`).
- Skip staging `catalog/catalog.db`. Commit when the user asks (plan steps may still list commits).

## File map

| File | Role |
|------|------|
| `fansim/propeller/optimize.py` | `bemt_thrust_g`, `blade_params_from_trial_params` |
| `fansim/propeller/cfd.py` | `evaluate_prop_cfd` floor + optional `params` |
| `scripts/evaluate_prop_cfd.py` | `--bemt-floor` |
| `scripts/run_prop_optimization.py` | `--cfd-top`, `--bemt-floor`, `--cfd-out`, summary JSON |
| `tests/test_prop_bemt_gate.py` | Unit tests |
| `docs/roadmap.md` | §4.3 BEMT-gate note |

---

### Task 1: `bemt_thrust_g` + Pareto → BladeParams helper

**Files:**
- Modify: `fansim/propeller/optimize.py`
- Test: `tests/test_prop_bemt_gate.py`

**Interfaces:**
- Produces:
  - `bemt_thrust_g(params: BladeParams, spec: PropSpec, *, rpm: float | None = None) -> float`
  - `blade_params_from_trial_params(spec: PropSpec, p: dict) -> BladeParams`  
    Rebuilds via `dataclasses.replace(spec, n_blades=..., pitch_in=...)` + `prop_blade_params(..., chord_frac=(cr,cm,ct), camber=...)` matching `run_prop_optimization` export path. Keys: `n_blades`, `pitch_in`, `chord_root`, `chord_mid`, `chord_tip`, `camber`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_prop_bemt_gate.py
from __future__ import annotations
import pytest
from fansim.prop_spec import get_prop_spec

def test_bemt_thrust_g_finite():
    from fansim.propeller.geometry import prop_blade_params
    from fansim.propeller.optimize import bemt_thrust_g
    spec = get_prop_spec("fpv_5inch")
    params = prop_blade_params(spec)
    g = bemt_thrust_g(params, spec)
    assert g > 0 and g == pytest.approx(g)  # finite

def test_blade_params_from_trial_params_roundtrip():
    from fansim.propeller.optimize import blade_params_from_trial_params, suggest_prop
    import optuna
    spec = get_prop_spec("fpv_5inch")
    trial = optuna.trial.FixedTrial({
        "n_blades": 3, "pitch_in": 4.3,
        "chord_root": 0.20, "chord_mid": 0.26, "chord_tip": 0.10, "camber": 0.04,
    })
    a = suggest_prop(trial, spec)
    b = blade_params_from_trial_params(spec, trial.params)
    assert a.n_blades == b.n_blades
    assert a.stations[0].chord == pytest.approx(b.stations[0].chord)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_prop_bemt_gate.py::test_bemt_thrust_g_finite -v`  
Expected: FAIL — import error for `bemt_thrust_g`.

- [ ] **Step 3: Minimal implementation**

```python
# in fansim/propeller/optimize.py
def bemt_thrust_g(params: BladeParams, spec: PropSpec, *, rpm: float | None = None) -> float:
    perf = analyze(params, rpm=float(spec.rpm_max if rpm is None else rpm))
    return float(perf.thrust_g)

def blade_params_from_trial_params(spec: PropSpec, p: dict) -> BladeParams:
    s2 = dataclasses.replace(spec, n_blades=int(p["n_blades"]), pitch_in=float(p["pitch_in"]))
    return prop_blade_params(
        s2,
        chord_frac=(float(p["chord_root"]), float(p["chord_mid"]), float(p["chord_tip"])),
        camber=float(p["camber"]),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_prop_bemt_gate.py -q --tb=short`  
Expected: PASS

---

### Task 2: Floor gate on `evaluate_prop_cfd`

**Files:**
- Modify: `fansim/propeller/cfd.py`
- Test: `tests/test_prop_bemt_gate.py`

**Interfaces:**
- Extend signature:
  ```python
  evaluate_prop_cfd(
      spec, workdir, *, rpm=None, iters=400, procs=8, base_cell=0.005,
      spec_key=None, params: BladeParams | None = None, bemt_floor_g: float = 0.0,
  ) -> dict
  ```
- Resolve blade: `params` if given, else `prop_blade_params(spec)`.
- BEMT at CFD rpm (`0.7*rpm_max` if `rpm is None`).
- If `bemt_floor_g > 0` and `bemt_thrust_g < bemt_floor_g`: return skip dict **without** Docker.
- Else CFD; always include `bemt_thrust_g` in result; `skipped=False` or omit.

**STL when `params` given:** Prefer exporting via `build_impeller` + `export_stl` from `BladeParams` (do not ignore custom chord/camber). Mirror:

```python
from fansim.geometry import build_impeller, export_stl
model = build_impeller(params)
export_stl(model, stl, ...)
```

(Keep `build_prop(spec, ...)` path when `params is None` for back-compat, including optional bore.)

- [ ] **Step 1: Write the failing test**

```python
def test_evaluate_prop_cfd_skips_below_bemt_floor(tmp_path, monkeypatch):
    from fansim.propeller import cfd as prop_cfd
    from fansim.prop_spec import get_prop_spec
    # If Docker were called, fail the test
    monkeypatch.setattr(prop_cfd, "run_mesh", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no mesh")))
    monkeypatch.setattr(prop_cfd, "run_solve_prop", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no solve")))
    spec = get_prop_spec("fpv_5inch")
    out = prop_cfd.evaluate_prop_cfd(spec, tmp_path, bemt_floor_g=1e9)  # impossible floor
    assert out["skipped"] is True
    assert out["bemt_thrust_g"] < 1e9
    assert "reason" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_prop_bemt_gate.py::test_evaluate_prop_cfd_skips_below_bemt_floor -v`  
Expected: FAIL — `bemt_floor_g` not accepted or no skip.

- [ ] **Step 3: Implement floor + optional params**

- [ ] **Step 4: Run tests**

Run: `uv run python -m pytest tests/test_prop_bemt_gate.py -q --tb=short`  
Expected: PASS

---

### Task 3: CFD CLI `--bemt-floor`

**Files:**
- Modify: `scripts/evaluate_prop_cfd.py`
- Test: `tests/test_prop_bemt_gate.py`

- [ ] **Step 1: Failing CLI test**

```python
def test_cli_evaluate_prop_cfd_declares_bemt_floor():
    text = Path("scripts/evaluate_prop_cfd.py").read_text(encoding="utf-8")
    assert "--bemt-floor" in text
```

- [ ] **Step 2: Wire argparse + pass `bemt_floor_g=args.bemt_floor` into `evaluate_prop_cfd`**

Exit code: `0` on skip or success; keep `2` if no Docker when CFD would run. On skip, still write `result.json`.

- [ ] **Step 3: Run tests**

---

### Task 4: `--cfd-top` on prop optimization CLI

**Files:**
- Modify: `scripts/run_prop_optimization.py`
- Test: `tests/test_prop_bemt_gate.py`

**Behavior:**
- `--cfd-top N` (default 0), `--bemt-floor G` (default 0), `--cfd-out PATH` (default `runs/prop_cfd_refine/<spec>/`)
- After Pareto print, if `N > 0`:
  - For `i, row in enumerate(pareto[:N])`:
    - `params = blade_params_from_trial_params(spec, row["params"])`
    - `workdir = cfd_out / f"rank_{i:02d}"`
    - Call `evaluate_prop_cfd(spec, workdir, params=params, bemt_floor_g=..., spec_key=args.spec)`
    - Append summary entry: index, bemt_thrust_g (from row or result), cfd thrust if not skipped, skipped/reason
  - Write `cfd_out / "summary.json"`
- If Docker missing and any CFD would run: print error and exit 2 (same as evaluate_prop_cfd).
- Unit test: assert CLI declares `--cfd-top` and `--bemt-floor`; optional unit of a small `refine_pareto_cfd(...)` helper extracted for testability with mocked `evaluate_prop_cfd`.

Prefer extracting:

```python
# fansim/propeller/optimize.py
def refine_pareto_cfd(spec, pareto, out_dir, *, n_top, bemt_floor_g=0.0, **eval_kw) -> list[dict]:
    ...
```

so tests monkeypatch `evaluate_prop_cfd` without Docker.

- [ ] **Step 1: Test refine helper with mocked CFD**

```python
def test_refine_pareto_cfd_respects_floor(tmp_path, monkeypatch):
    from fansim.propeller import optimize as po
    from fansim.prop_spec import get_prop_spec
    calls = []
    def fake_eval(spec, workdir, **kw):
        calls.append(kw.get("bemt_floor_g"))
        return {"skipped": True, "bemt_thrust_g": 1.0, "reason": "floor"}
    monkeypatch.setattr("fansim.propeller.cfd.evaluate_prop_cfd", fake_eval)
    # or patch where refine imports it
    spec = get_prop_spec("fpv_5inch")
    pareto = [{"thrust_g": 100.0, "params": {
        "n_blades": 3, "pitch_in": 4.3,
        "chord_root": 0.2, "chord_mid": 0.26, "chord_tip": 0.1, "camber": 0.04,
    }}]
    rows = po.refine_pareto_cfd(spec, pareto, tmp_path, n_top=1, bemt_floor_g=50.0)
    assert len(rows) == 1
    assert calls == [50.0]
```

- [ ] **Step 2: Implement helper + CLI wiring**

- [ ] **Step 3: Run all gate tests**

Run: `uv run python -m pytest tests/test_prop_bemt_gate.py -q --tb=short`  
Expected: all PASS

---

### Task 5: Roadmap + optional Docker smoke

**Files:**
- Modify: `docs/roadmap.md` §4.3, design spec status
- Optional: `uv run python scripts/run_prop_optimization.py fpv_5inch --trials 40 --cfd-top 1 --bemt-floor 100 --cfd-out runs/prop_cfd_refine/fpv_5inch`

- [ ] **Step 1: Update roadmap** — BEMT-gate stage 1 done; remaining: polar / datasheet spin cal / Optuna-with-CFD still out
- [ ] **Step 2: Spec status → implemented**
- [ ] **Step 3 (optional):** one Docker refine if image available; otherwise leave note in roadmap as optional

---

## Spec coverage checklist

| Spec item | Task |
|-----------|------|
| `bemt_thrust_g` | Task 1 |
| Floor on `evaluate_prop_cfd` + optional params | Task 2 |
| `--bemt-floor` on CFD CLI | Task 3 |
| `--cfd-top` / summary JSON | Task 4 |
| Tests, no Docker CI | Tasks 1–4 |
| Roadmap | Task 5 |

## Self-review notes

- No TBD; CFD stays out of Optuna.
- Custom `params` STL path must not silently fall back to stock `build_prop(spec)` only.
- Floor default 0 preserves today’s CFD CLI behavior.
