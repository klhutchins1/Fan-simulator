# Realistic System Curve (Stage 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** After the two existing CFD solves, score `cfm_load` and efficiency at the ΔP = k Q² intersection instead of at the fixed-Pa wall, with k from Pa at 50 CFM.

**Architecture:** `fansim/optimize/system_curve.py` converts `load_pa` → k and intersects the 2-point fan line (derated free, derated probe) with the parabola. `evaluate_candidate` still meshes once and solves twice; it then replaces load CFM/eta and stamps `k` / `dp_op_pa` / `q_ref_cfm`. Presets stay 8 / 20 / 35.

**Tech Stack:** Python 3.12 via uv, pytest, Optuna trial user attrs. No Docker.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-02-system-curve-design.md`
- Python `>=3.12,<3.13` via `uv`; tests: `uv run python -m pytest -q -m "not docker and not slow"`
- `REF_CFM = 50.0`; k = `load_pa / (REF_CFM / CFM_PER_M3S)²` with `CFM_PER_M3S = 2118.88` from `fansim.fan_bem`
- Two CFD solves unchanged (free + probe at `load_pa`); no third solve; no `--k` flag
- NSGA-II stays `(cfm_free, cfm_op, eta_op)`; `cfm_free` is still derated free-delivery
- Probe Pa is not RPM-derated (matches today’s motor-limit law)
- BEM `--bem-prescreen` stays free-delivery CFM
- Infeasible prefix `system-curve:`; unconverged CFD stays a note on a feasible result
- Historical catalog rows without the new attrs stay wall-scored (do not backfill)
- No `★` in CLI help
- Windows: CadQuery teardown exit 3221226356 / -1073741819 is not a test failure — judge by assertion output
- Commit after each task; do not `git push`

---

## File structure

| Path | Responsibility |
|---|---|
| `fansim/optimize/system_curve.py` | `REF_CFM`, `k_from_pa`, `intersect_fan_line`, `score_operating_point` |
| `tests/test_system_curve.py` | Math fixtures, infeasible cases, CLI help |
| `fansim/optimize/presets.py` | Docs: Pa at 50 CFM; numbers stay 8/20/35 |
| `fansim/optimize/objectives.py` | After derate, call `score_operating_point` |
| `fansim/optimize/study.py` | Stamp `k`, `dp_op_pa`, `q_ref_cfm`; `pareto_summary` |
| `fansim/cockpit/data.py` | `load_designs` extra keys |
| `scripts/run_optimization.py` | `--preset` / `--load-pa` help |
| `tests/test_presets.py` | Pa means `REF_CFM` |
| `tests/test_optimize.py` | Provenance on dummy trials |
| `docs/roadmap.md` + spec | §1.2 stage 1 done; status accepted |

---

### Task 1: System-curve math

**Files:**
- Create: `fansim/optimize/system_curve.py`
- Test: `tests/test_system_curve.py`

**Interfaces:**
- Consumes: `fansim.fan_bem.CFM_PER_M3S`
- Produces:
  - `REF_CFM = 50.0`
  - `class SystemCurveError(ValueError)`
  - `k_from_pa(load_pa: float, ref_cfm: float = REF_CFM) -> float`
  - `intersect_fan_line(q_free_cfm: float, q_probe_cfm: float, p_probe_pa: float, k: float) -> tuple[float, float]` → `(q_op_cfm, p_op_pa)`
  - `@dataclass(frozen=True) class OperatingPoint` with `q_op_cfm: float`, `p_op_pa: float`, `eta: float` (0–1 fraction), `k: float`
  - `score_operating_point(q_free_cfm, q_probe_cfm, p_probe_pa, eta_free, eta_load, load_pa) -> OperatingPoint`

Convert CFM → m³/s for the quadratic (`q / CFM_PER_M3S`). Spec closed form, Q in m³/s:

```text
a = k * (Q0 - Q1)
b = P1
c = -P1 * Q0
```

Take the unique root in `(0, Q0)`, convert back to CFM. Raise `SystemCurveError` (message is the suffix after `system-curve:`) when Q0 ≤ 0, Q1 ≤ 0, Q1 ≥ Q0, P1 ≤ 0, k ≤ 0, discriminant < 0, or no root in `(0, Q0)`.

`score_operating_point`: `k = k_from_pa(load_pa)`, intersect with `p_probe_pa` (same number as `load_pa` in the optimizer), linearly interpolate eta vs CFM:

```text
t = (q_op - q_free) / (q_probe - q_free)
eta = eta_free + t * (eta_load - eta_free)
```

- [ ] **Step 1: Write the failing tests**

```python
import math
import pytest

from fansim.fan_bem import CFM_PER_M3S
from fansim.optimize.system_curve import (
    REF_CFM,
    SystemCurveError,
    intersect_fan_line,
    k_from_pa,
    score_operating_point,
)


def test_ref_cfm_is_fifty():
    assert REF_CFM == 50.0


def test_k_from_pa_eight_at_fifty_cfm():
    q_ref = REF_CFM / CFM_PER_M3S
    assert k_from_pa(8.0) == pytest.approx(8.0 / q_ref**2)


def test_intersection_at_calibration_point_is_fifty_cfm_eight_pa():
    k = k_from_pa(8.0)
    q_op, p_op = intersect_fan_line(80.0, 50.0, 8.0, k)
    assert q_op == pytest.approx(50.0)
    assert p_op == pytest.approx(8.0)


def test_weaker_probe_moves_op_to_higher_flow_lower_pressure():
    k = k_from_pa(8.0)
    q_op, p_op = intersect_fan_line(80.0, 40.0, 8.0, k)
    assert q_op > 40.0
    assert p_op < 8.0
    assert 0.0 < q_op < 80.0


def test_inverted_curve_raises():
    k = k_from_pa(8.0)
    with pytest.raises(SystemCurveError):
        intersect_fan_line(40.0, 50.0, 8.0, k)


def test_score_interpolates_efficiency_vs_cfm():
    op = score_operating_point(
        q_free_cfm=80.0, q_probe_cfm=50.0, p_probe_pa=8.0,
        eta_free=0.20, eta_load=0.35, load_pa=8.0)
    assert op.q_op_cfm == pytest.approx(50.0)
    assert op.p_op_pa == pytest.approx(8.0)
    assert op.eta == pytest.approx(0.35)
    assert op.k == pytest.approx(k_from_pa(8.0))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_system_curve.py -q --tb=short`

Expected: import fail (no `fansim.optimize.system_curve`).

- [ ] **Step 3: Implement `fansim/optimize/system_curve.py`**

Use `math.sqrt` for the discriminant. Prefer the quadratic root in `(0, Q0_m3s)`; convert that Q back with `* CFM_PER_M3S`. `p_op` = `k * Q_m3s**2` (do not re-evaluate the fan line for P — they match at the root).

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_system_curve.py -q --tb=short`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add fansim/optimize/system_curve.py tests/test_system_curve.py
git commit -m "Add the Pa-at-50-CFM system-curve intersection"
```

Windows PowerShell: `git commit -m @"` / `"@` here-string, no bash HEREDOC.

---

### Task 2: Wire optimizer, provenance, CLI

**Files:**
- Modify: `fansim/optimize/objectives.py` (after derate, before `ObjectiveResult`)
- Modify: `fansim/optimize/study.py` (`set_user_attr` + `pareto_summary`)
- Modify: `fansim/cockpit/data.py` (`load_designs` extra)
- Modify: `fansim/optimize/presets.py` (module docstring only — numbers unchanged)
- Modify: `scripts/run_optimization.py` (`--preset` / `--load-pa` help)
- Modify: `tests/test_presets.py`
- Modify: `tests/test_optimize.py`
- Modify: `tests/test_system_curve.py` (CLI assertions)

**Interfaces:**
- Consumes: `score_operating_point`, `SystemCurveError`, `REF_CFM`
- Produces: `cfm_load` / `efficiency` at the operating point; trial attrs `k`, `dp_op_pa`, `q_ref_cfm`; `raw` keys `k`, `dp_op_pa`, `q_ref_cfm`, `cfm_probe`

In `evaluate_candidate`, after existing derate of `cfm_free` / `cfm_load` (keep the probe CFM in a local `cfm_probe` before replacing):

```python
from fansim.optimize.system_curve import REF_CFM, SystemCurveError, score_operating_point

cfm_probe = cfm_load
try:
    op = score_operating_point(
        q_free_cfm=cfm_free,
        q_probe_cfm=cfm_probe,
        p_probe_pa=load_pa,
        eta_free=m_free.efficiency,
        eta_load=m_load.efficiency,
        load_pa=load_pa,
    )
except SystemCurveError as exc:
    return _infeasible(f"system-curve: {exc}", t0)
cfm_load = op.q_op_cfm
efficiency = max(op.eta * 100.0, 0.0)
```

Pass `efficiency=efficiency` into `ObjectiveResult` instead of `max(m_load.efficiency * 100.0, 0.0)`. Put `k=op.k`, `dp_op_pa=op.p_op_pa`, `q_ref_cfm=REF_CFM`, `cfm_probe=cfm_probe` in `raw`.

`run_study` after evaluate (also on infeasible — use `result.raw.get` so missing keys become None):

```python
trial.set_user_attr("k", result.raw.get("k"))
trial.set_user_attr("dp_op_pa", result.raw.get("dp_op_pa"))
trial.set_user_attr("q_ref_cfm", result.raw.get("q_ref_cfm"))
```

`pareto_summary` rows add `"k"`, `"dp_op_pa"`, `"q_ref_cfm"` from user attrs (None if absent).

`load_designs` extra: same three keys, None if absent.

CLI help (no `★`):

```python
ap.add_argument("--preset", ...,
    help="application impedance as Pa at 50 CFM (system curve dP = k Q^2): "
         "case=8 Pa, heatsink=20 Pa, radiator=35 Pa. Sets --load-pa unless you pass --load-pa.")
ap.add_argument("--load-pa", ...,
    help="system-curve Pa at 50 CFM (not a fixed wall). Default 1.0 or the --preset value.")
```

Use `dP = k Q^2` not `ΔP` if Windows consoles mangle the delta. Still no `--k`.

`presets.py` docstring: those Pa are **at 50 CFM** on ΔP = k Q²; CFD probe is still that Pa; scored load CFM is the intersection.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_presets.py`:

```python
def test_preset_pa_is_at_ref_cfm():
    from fansim.optimize.system_curve import REF_CFM
    assert REF_CFM == 50.0
    assert PRESETS["case"].load_pa == 8.0
```

Append to `tests/test_system_curve.py`:

```python
def test_run_optimization_help_mentions_fifty_cfm_and_has_no_k_flag():
    from pathlib import Path
    text = Path("scripts/run_optimization.py").read_text(encoding="utf-8")
    assert "50 CFM" in text
    assert "--k" not in text
    assert "★" not in text
```

Append to `tests/test_optimize.py` (same dummy-trial pattern as `test_pareto_summary_carries_tip_gap_and_frame_stl`):

```python
def test_pareto_summary_carries_system_curve_attrs():
    from fansim.optimize.search_space import OBJECTIVE_DIRECTIONS
    from fansim.optimize.study import pareto_summary

    study = optuna.create_study(directions=list(OBJECTIVE_DIRECTIONS))
    t = study.ask()
    t.suggest_int("n_blades", 7, 7)
    t.set_user_attr("feasible", True)
    t.set_user_attr("n_blades", 7)
    t.set_user_attr("k", 1.23)
    t.set_user_attr("dp_op_pa", 6.5)
    t.set_user_attr("q_ref_cfm", 50.0)
    study.tell(t, [10.0, 5.0, 1.0])
    row = pareto_summary(study)[0]
    assert row["k"] == 1.23
    assert row["dp_op_pa"] == 6.5
    assert row["q_ref_cfm"] == 50.0
```

- [ ] **Step 2: Run tests — expect FAIL** (help text / missing pareto keys)

Run: `uv run python -m pytest tests/test_system_curve.py tests/test_optimize.py tests/test_presets.py -q --tb=short`

- [ ] **Step 3: Implement wiring**

Do not add a third `solve_at`. Do not change `bem_prescreen`. Catch `SystemCurveError` only.

- [ ] **Step 4: Re-run the same pytest command — PASS**

- [ ] **Step 5: Commit**

```bash
git add fansim/optimize/objectives.py fansim/optimize/study.py fansim/cockpit/data.py fansim/optimize/presets.py scripts/run_optimization.py tests/test_presets.py tests/test_optimize.py tests/test_system_curve.py
git commit -m "Score load CFM on the Pa-at-50-CFM system curve"
```

---

### Task 3: Spec accepted + roadmap

**Files:**
- `docs/superpowers/specs/2026-09-02-system-curve-design.md` — `Status: accepted`
- `docs/roadmap.md` — mark §1.2 stage 1 done; recommended sequence next is §7.5

Suggested §1.2 replacement:

```markdown
- [x] **1.2 Realistic operating point / system curve (stage 1). DONE 2026-09-02**
  Presets / `--load-pa` are **Pa at 50 CFM** on ΔP = k Q². Two CFD solves stay
  (free + that Pa); `cfm_load` / efficiency are the 2-point fan line ∩ parabola.
  Remaining: third CFD at the predicted op, affinity-correct P∝RPM² under derate,
  BEM prescreen on the curve.
```

Recommended sequence item 1: §1.2 done; next **Tip shroud refinement (§7.5)**. Recently shipped: mention system curve stage 1.

- [ ] **Step 1: Edit the two docs**
- [ ] **Step 2: Run** `uv run python -m pytest tests/test_system_curve.py tests/test_presets.py tests/test_optimize.py tests/test_shroud.py -q --tb=short -m "not docker"`
- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/specs/2026-09-02-system-curve-design.md docs/roadmap.md
git commit -m "Accept the system-curve spec and mark roadmap 1.2 stage 1 done"
```

---

## Self-review

1. Spec coverage: REF_CFM 50, k formula, two solves, intersection, eta interp, infeasible prefix, provenance, CLI no `--k`, no Docker, BEM unchanged, derate P unscaled, catalog not rescored, presets 8/20/35.
2. Placeholders: none.
3. Names: `REF_CFM`, `k_from_pa`, `intersect_fan_line`, `score_operating_point`, `OperatingPoint`, `SystemCurveError`, attrs `k` / `dp_op_pa` / `q_ref_cfm` consistent.
