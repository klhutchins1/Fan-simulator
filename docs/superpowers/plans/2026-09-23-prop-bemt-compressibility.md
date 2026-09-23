# BEMT Compressibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `analyze` apply the existing Prandtl–Glauert / wave-drag helper on every blade station so Mach 0.35–0.58 props are no longer scored as incompressible.

**Architecture:** One call inside the BEM fixed-point loop, after the incompressible polar and before thrust and torque are formed. Local Mach is `sqrt(W2) / C_AIR` with the prop-path constant 343 m/s. The helper body stays as it is. Induced velocity therefore sees the corrected lift.

**Tech Stack:** Python 3.12 (`uv`), pytest. No Docker.

**Spec:** `docs/superpowers/specs/2026-09-23-prop-bemt-compressibility-design.md`

## Global Constraints

- Call `_compressibility_cl_cd` from `analyze`. Do not edit the helper body.
- Mach = `math.sqrt(W2) / C_AIR`. Import `C_AIR` from `fansim.prop_spec` (343 m/s). Do not add another speed-of-sound constant.
- The call sits inside the fixed-point iteration, after `_cl_cd`, before `dT` and `f_theta`.
- No disable flag. Every `analyze` call uses the correction.
- BEMT density stays 1.225 kg/m³. Do not switch the screener to the CFD thermo state.
- Do not touch CFD fixtures, AMI code, `run_prop_study` objectives, or `_compressibility_cl_cd`.
- CI tests only. No Docker.
- On Windows, pytest may exit `-1073741819` or `-1073740940` after a printed pass line. Treat the pass line as success.
- PowerShell: do not chain commands with `&&`.
- Commit only the files a task lists. Do not stage `.superpowers/sdd/progress.md` or `catalog/catalog.db`.
- `docs/roadmap.md` already has uncommitted §4.4 and §14.7 text. Task 2 edits step 1 of that text and commits the whole `docs/roadmap.md` file. Do not use interactive `git add -p`.

## File map

| File | Role |
|------|------|
| `fansim/propeller/bemt.py` | Import `C_AIR`. One call in `analyze`. One docstring sentence |
| `tests/test_prop_fwh_compress.py` | Mach recording test and high-RPM thrust test |
| `tests/test_bemt.py` | Raise the RPM-squared upper bound that compressibility breaks |
| `docs/roadmap.md` | Mark §4.4 step 1 done. Leave the checkbox and steps 2–3 open |

A dry run of this loop (not committed) on `fpv_5inch` at 30000 RPM moved thrust from 16.083 N to 17.628 N. Doubling RPM from 15000 to 30000 moved the thrust ratio from inside `(3.3, 4.7)` to **4.76**. Registry figure-of-merit and g/W bands still hold. Only that one assertion needs a new ceiling.

---

### Task 1: Apply compressibility inside `analyze`

**Files:**
- Modify: `fansim/propeller/bemt.py` (module docstring, imports, the `_cl_cd` line inside `analyze`)
- Modify: `tests/test_prop_fwh_compress.py`
- Modify: `tests/test_bemt.py` (one assertion)
- Test: `tests/test_prop_fwh_compress.py`, `tests/test_bemt.py`

**Interfaces:**
- Consumes: `_compressibility_cl_cd(cl: float, cd: float, mach: float) -> tuple[float, float]` in `fansim/propeller/bemt.py`. `C_AIR: float = 343.0` in `fansim/prop_spec.py`. `analyze(params, rpm, v_forward=0.0, rho=1.225, n_elem=24) -> PropPerf`.
- Produces: `analyze` calls `_compressibility_cl_cd` every iteration with `mach = sqrt(W2) / C_AIR`. No new public function.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_prop_fwh_compress.py`:

```python
def test_analyze_records_local_mach(monkeypatch):
    from fansim.propeller import bemt as bemt_mod

    recorded = []
    real = bemt_mod._compressibility_cl_cd

    def _spy(cl, cd, mach):
        recorded.append(float(mach))
        return real(cl, cd, mach)

    monkeypatch.setattr(bemt_mod, "_compressibility_cl_cd", _spy)
    p = prop_blade_params(get_prop_spec("fpv_5inch"))
    analyze(p, rpm=30000.0)
    assert recorded, "analyze never called _compressibility_cl_cd"
    lo, hi = min(recorded), max(recorded)
    assert hi >= 0.45
    assert hi >= 1.5 * lo


def test_compressibility_raises_high_rpm_thrust(monkeypatch):
    from fansim.propeller import bemt as bemt_mod

    p = prop_blade_params(get_prop_spec("fpv_5inch"))
    with_correction = analyze(p, rpm=30000.0)
    monkeypatch.setattr(
        bemt_mod, "_compressibility_cl_cd", lambda cl, cd, mach: (cl, cd)
    )
    without = analyze(p, rpm=30000.0)
    assert with_correction.thrust_n > without.thrust_n
```

`analyze` must keep resolving `_compressibility_cl_cd` as a global in `fansim.propeller.bemt`. Patch that module attribute. Patching a locally imported copy does not change the loop.

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `uv run python -m pytest tests/test_prop_fwh_compress.py::test_analyze_records_local_mach tests/test_prop_fwh_compress.py::test_compressibility_raises_high_rpm_thrust -q --tb=line`

Expected: FAIL. The Mach test fails on the empty-recording assertion. The thrust test fails because both calls are still incompressible, so `thrust_n` is equal.

- [ ] **Step 3: Wire the call**

In `fansim/propeller/bemt.py`, add the import after the `BladeParams` import:

```python
from fansim.prop_spec import C_AIR
```

Replace this module-docstring sentence:

```text
proxy screens fans. (A compressible open-air CFD tier can refine finalists later; tips run ~Mach 0.5.)
```

with:

```text
proxy screens fans. analyze applies _compressibility_cl_cd (Prandtl-Glauert on Cl,
wave drag past Mach 0.7) using local relative speed over C_AIR. A compressible CFD tier
can still refine finalists.
```

Inside the fixed-point loop, replace the polar line with these three lines. Keep them before the Prandtl tip-loss comment:

```python
            cl, cd = _cl_cd(alpha, camber, re=math.sqrt(W2) * c / NU_AIR)   # Re-aware polar (§7.2)
            mach = math.sqrt(W2) / C_AIR
            cl, cd = _compressibility_cl_cd(cl, cd, mach)
```

Do not change `_compressibility_cl_cd`, the momentum updates, or the `PropPerf` formulas.

- [ ] **Step 4: Run the new tests to verify they pass**

Run: `uv run python -m pytest tests/test_prop_fwh_compress.py -q --tb=line`

Expected: PASS (`5 passed`). A Windows process teardown code after that line is non-blocking.

- [ ] **Step 5: Run the existing BEMT bands**

Run: `uv run python -m pytest tests/test_bemt.py -q --tb=line`

Expected: FAIL in `test_thrust_scales_with_rpm_squared`. The ratio is about **4.76**, and the assertion is `t2 / t1 < 4.7`. The other four tests in this file pass. Figure of merit stays about 0.66 and g/W about 2.83 on `fpv_5inch` at 30000 RPM, inside the existing bands.

- [ ] **Step 6: Raise that one ceiling**

In `tests/test_bemt.py`, replace:

```python
    assert 3.3 < t2 / t1 < 4.7                       # ~4x, allowing for induced/tip-loss nonlinearity
```

with:

```python
    # ~4x from rpm^2. 30000 RPM is tip Mach ~0.58, so Prandtl-Glauert lifts that point
    # more than 15000 RPM (tip Mach ~0.29). Measured ratio is 4.76.
    assert 3.3 < t2 / t1 < 5.0
```

Do not change the other assertions in this file.

- [ ] **Step 7: Re-run both files**

Run: `uv run python -m pytest tests/test_prop_fwh_compress.py tests/test_bemt.py -q --tb=line`

Expected: PASS (`10 passed`).

- [ ] **Step 8: Commit**

```powershell
git add -- fansim/propeller/bemt.py tests/test_prop_fwh_compress.py tests/test_bemt.py
git commit -m @"
feat(prop): apply BEMT compressibility in the element loop

"@
```

---

### Task 2: Mark roadmap step 1 done

**Files:**
- Modify: `docs/roadmap.md` (the numbered item 1 under §4.4)
- Test: none (prose only)

**Interfaces:**
- Consumes: Task 1 has landed. `analyze` calls the helper.
- Produces: §4.4 step 1 reads as done and points at this spec and plan. The §4.4 checkbox stays open. Steps 2 and 3 stay as they are.

- [ ] **Step 1: Replace step 1**

In `docs/roadmap.md`, replace the §4.4 item that begins `1. Call `_compressibility_cl_cd`` with:

```markdown
  1. **Done.** `bemt.analyze` calls `_compressibility_cl_cd` with local Mach
     (`sqrt(W2) / C_AIR`, 343 m/s) inside the element loop. Spec/plan:
     `docs/superpowers/specs/2026-09-23-prop-bemt-compressibility-design.md`,
     `docs/superpowers/plans/2026-09-23-prop-bemt-compressibility.md`.
```

Leave items 2 and 3, and the unchecked `- [ ] **4.4` line, unchanged.

- [ ] **Step 2: Commit the roadmap**

This commit includes the §4.4 and §14.7 text that was already in the working tree, plus the step-1 edit. Do not stage any other file.

```powershell
git add -- docs/roadmap.md
git commit -m @"
docs(prop): mark BEMT compressibility step done on the roadmap

"@
```
