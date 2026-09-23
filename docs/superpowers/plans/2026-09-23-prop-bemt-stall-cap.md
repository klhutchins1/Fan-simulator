# BEMT Stall-Cap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop Prandtl–Glauert from raising lift at or past stall, and stop attached lift from passing the incompressible polar peak.

**Architecture:** The helper gains keyword-only `stalled` and `cl_cap`. Vendored tables report stall from the same curve that supplies Cl. The analytic polar reports stall from `stall_deg` and the unclamped linear Cl. `analyze` passes both into the helper on every fixed-point iteration. Wave drag past Mach 0.7 is unchanged.

**Tech Stack:** Python 3.12 (`uv`), pytest. No Docker.

**Spec:** `docs/superpowers/specs/2026-09-23-prop-bemt-stall-cap-design.md`

## Global Constraints

- Attached lift is `cl / beta` with `beta = sqrt(1 - M²)`, then clamped to the polar peak. Stalled lift is the polar Cl, unchanged.
- Wave drag stays `0.02 * ((M - 0.70) / 0.25) ** 2` added to Cd only when Mach > 0.7, including stalled sections. Mach stays clamped to [0, 0.95].
- `analyze` still uses `mach = math.sqrt(W2) / C_AIR` inside the fixed-point loop. `C_AIR` is 343 m/s. BEMT density stays 1.225 kg/m³.
- No disable flag. No Karman–Tsien. Do not change `cl_max`, `stall_deg`, the post-stall drop, or vendored CSV values.
- Table stall tolerance is `1e-4` in Cl. Positive stall angle is the smallest alpha whose Cl is at least `max(Cl) - 1e-4`. Negative stall exists only when `min(Cl) < 0`, and it is the largest alpha whose Cl is at most `min(Cl) + 1e-4`. Angles outside the table are compared directly; do not move the stall angle to the clamped edge.
- Reynolds blend uses the existing log10 weight. Blend positive stall angle, negative stall angle, maximum Cl, and minimum Cl. If either neighbor has `min(Cl) >= 0`, the blend has no negative stall gate.
- `cl_cap` passed to the helper is a positive magnitude. `stalled=True` ignores `cl_cap`.
- Do not run Docker. Do not edit `obj_2_ccw_smoke.json`, `obj_2_ccw_refine.json`, `obj_2_ccw_gci.json`, or `obj_2_ccw_wall.json`.
- Do not add mission presets. Leave the §4.4 checkbox, step 3, and §14.7 open.
- On Windows, pytest may exit `-1073741819`, `-1073740940`, or `3221226356` after a printed pass line. Treat the pass line as success.
- PowerShell: do not chain commands with `&&`.
- Commit only the files a task lists. Do not stage `.superpowers/sdd/progress.md`, `catalog/catalog.db`, or `runs/`.

## File map

| File | Role |
|------|------|
| `fansim/propeller/bemt.py` | Helper keywords. Analytic section returns stall and cap. `analyze` passes them |
| `fansim/propeller/polars.py` | `section_table` returns `(cl, cd, stalled, cl_cap)` or `None`. `cl_cd_table` stays a 2-tuple wrapper |
| `tests/test_prop_fwh_compress.py` | Helper, spy, identity patch, and section tests |
| `tests/test_uiuc_polars.py` | Table stall tests, including a Reynolds blend |
| `tests/test_bemt.py` | RPM-doubling comment and ceiling only if the measured ratio moves |
| `docs/validation/drone_radial_open_air_cfd.md` | Replace the stale stall sentence with the iteration-400 moment split |
| `docs/roadmap.md` | One sentence on step 1 and one on step 2. Checkbox stays open |

---

### Task 1: Stall flag and peak cap on the helper

**Files:**
- Modify: `fansim/propeller/bemt.py` (`_compressibility_cl_cd` only)
- Test: `tests/test_prop_fwh_compress.py`

**Interfaces:**
- Consumes: nothing new
- Produces: `_compressibility_cl_cd(cl: float, cd: float, mach: float, *, stalled: bool = False, cl_cap: float | None = None) -> tuple[float, float]`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_prop_fwh_compress.py`:

```python
def test_stalled_lift_is_unchanged_and_wave_drag_remains():
    cl, cd = _compressibility_cl_cd(1.0, 0.02, 0.5, stalled=True)
    assert cl == 1.0
    assert cd == 0.02
    cl_w, cd_w = _compressibility_cl_cd(1.0, 0.02, 0.85, stalled=True, cl_cap=0.1)
    assert cl_w == 1.0
    assert cd_w == pytest.approx(0.0272)


def test_attached_lift_respects_cap():
    cl, cd = _compressibility_cl_cd(1.0, 0.02, 0.5, stalled=False, cl_cap=1.05)
    assert cl == pytest.approx(1.05)
    assert cd == 0.02
    neg, _ = _compressibility_cl_cd(-0.5, 0.02, 0.5, cl_cap=0.4)
    assert neg == pytest.approx(-0.4)
```

Add `import pytest` to that file.

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `uv run python -m pytest tests/test_prop_fwh_compress.py::test_stalled_lift_is_unchanged_and_wave_drag_remains tests/test_prop_fwh_compress.py::test_attached_lift_respects_cap -q --tb=line`

Expected: FAIL. The helper does not accept `stalled` or `cl_cap` (`TypeError`).

- [ ] **Step 3: Implement the helper**

Replace `_compressibility_cl_cd` in `fansim/propeller/bemt.py` with:

```python
def _compressibility_cl_cd(
    cl: float,
    cd: float,
    mach: float,
    *,
    stalled: bool = False,
    cl_cap: float | None = None,
) -> tuple[float, float]:
    """Prandtl–Glauert on attached Cl, capped at the polar peak; stalled Cl unchanged.

    Soft wave-drag rise past M≈0.7 applies either way. Mach is clamped to [0, 0.95].
    """
    m = max(0.0, min(float(mach), 0.95))
    beta = math.sqrt(max(1e-6, 1.0 - m * m))
    if stalled:
        cl_c = float(cl)
    else:
        cl_c = float(cl) / beta
        if cl_cap is not None:
            limit = abs(float(cl_cap))
            cl_c = math.copysign(min(abs(cl_c), limit), cl_c)
    cd_c = float(cd)
    if m > 0.70:
        cd_c = cd_c + 0.02 * ((m - 0.70) / 0.25) ** 2
    return cl_c, cd_c
```

Leave the call in `analyze` unchanged in this task. Defaults keep the current call working.

- [ ] **Step 4: Run the compressibility tests**

Run: `uv run python -m pytest tests/test_prop_fwh_compress.py -q --tb=line`

Expected: PASS. `test_compressibility_raises_cl_and_drag` still passes because the defaults still divide Cl by beta.

- [ ] **Step 5: Commit**

```powershell
git add -- fansim/propeller/bemt.py tests/test_prop_fwh_compress.py
git commit -m @"
fix(prop): cap Prandtl-Glauert lift and skip it past stall

"@
```

---

### Task 2: Table stall angle and peak

**Files:**
- Modify: `fansim/propeller/polars.py`
- Test: `tests/test_uiuc_polars.py`

**Interfaces:**
- Consumes: existing `cl_cd_table` Reynolds ladder (`family_for_camber`, `load_polar_family`, `_polar_re_levels`, `_interp_alpha`)
- Produces: `section_table(alpha_rad: float, camber: float, re: float, thickness: float = 0.12) -> tuple[float, float, bool, float] | None`

`None` means the same miss as `cl_cd_table` (non-finite Re, Re below the lowest table, or no CSV). On a hit the first two values equal `cl_cd_table`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_uiuc_polars.py`. Import `section_table` from `fansim.propeller.polars`.

```python
def test_naca4412_stall_gate_at_table_re():
    clear_polar_cache()
    attached = section_table(math.radians(4.0), 0.04, 80000.0)
    assert attached is not None
    cl, _cd, stalled, cap = attached
    assert stalled is False
    assert cl == pytest.approx(0.65703, abs=1e-5)
    assert cap == pytest.approx(1.04017, abs=1e-5)
    stalled_row = section_table(math.radians(16.0), 0.04, 80000.0)
    assert stalled_row is not None
    cl_s, _cd_s, stalled_s, cap_s = stalled_row
    assert stalled_s is True
    assert cl_s == pytest.approx(0.89370, abs=1e-5)
    assert cap_s == pytest.approx(1.04017, abs=1e-5)
    past = section_table(math.radians(64.0), 0.04, 80000.0)
    assert past is not None
    cl_p, _cd_p, stalled_p, cap_p = past
    assert stalled_p is True
    assert cl_p == pytest.approx(0.83129, abs=1e-5)
    assert cap_p == pytest.approx(1.04017, abs=1e-5)
    neg = section_table(math.radians(-5.0), 0.04, 80000.0)
    assert neg is not None
    cl_n, _cd_n, stalled_n, cap_n = neg
    assert stalled_n is True
    assert cl_n == pytest.approx(-0.28280, abs=1e-5)
    assert cap_n == pytest.approx(0.28280, abs=1e-5)
    near = section_table(math.radians(-4.0), 0.04, 80000.0)
    assert near is not None
    cl_a, _cd_a, stalled_a, cap_a = near
    assert stalled_a is False
    assert cl_a == pytest.approx(-0.17838, abs=1e-5)
    assert cap_a == pytest.approx(0.28280, abs=1e-5)


def test_stall_gate_blends_neighbor_tables():
    clear_polar_cache()
    re_mid = 10 ** (0.5 * (math.log10(40000.0) + math.log10(80000.0)))
    row = section_table(math.radians(16.0), 0.04, re_mid)
    assert row is not None
    cl, _cd, stalled, cap = row
    assert stalled is True
    assert cl == pytest.approx((0.79638 + 0.89370) / 2.0, abs=1e-5)
    assert cap == pytest.approx((0.95708 + 1.04017) / 2.0, abs=1e-5)
    attached = section_table(math.radians(4.0), 0.04, re_mid)
    assert attached is not None
    cl_a, _cd_a, stalled_a, cap_a = attached
    assert stalled_a is False
    assert cl_a == pytest.approx((0.63210 + 0.65703) / 2.0, abs=1e-5)
    assert cap_a == pytest.approx((0.95708 + 1.04017) / 2.0, abs=1e-5)


def test_section_table_misses_when_cl_cd_table_misses():
    clear_polar_cache()
    assert section_table(math.radians(4.0), 0.04, 16000.0) is None
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `uv run python -m pytest tests/test_uiuc_polars.py::test_naca4412_stall_gate_at_table_re tests/test_uiuc_polars.py::test_stall_gate_blends_neighbor_tables tests/test_uiuc_polars.py::test_section_table_misses_when_cl_cd_table_misses -q --tb=line`

Expected: FAIL with `ImportError` (`section_table` is not defined).

- [ ] **Step 3: Implement `section_table` and wrap `cl_cd_table`**

Add the helpers below `_interp_alpha` in `fansim/propeller/polars.py`, then replace `cl_cd_table` with the wrapper. Keep `_interp_alpha` as it is.

```python
_STALL_TOL = 1e-4


def _curve_limits(alphas: np.ndarray, cls: np.ndarray) -> tuple[float, float | None, float, float]:
    """Positive stall angle, negative stall angle or None, peak Cl, trough Cl."""
    cl_peak = float(np.max(cls))
    cl_trough = float(np.min(cls))
    pos = np.flatnonzero(cls >= cl_peak - _STALL_TOL)
    a_pos = float(alphas[int(pos[0])])
    a_neg: float | None = None
    if cl_trough < 0.0:
        neg = np.flatnonzero(cls <= cl_trough + _STALL_TOL)
        a_neg = float(alphas[int(neg[-1])])
    return a_pos, a_neg, cl_peak, cl_trough


def _blend_limits(
    lo: tuple[float, float | None, float, float],
    hi: tuple[float, float | None, float, float],
    w: float,
) -> tuple[float, float | None, float, float]:
    a_pos = (1.0 - w) * lo[0] + w * hi[0]
    if lo[1] is None or hi[1] is None:
        a_neg = None
    else:
        a_neg = (1.0 - w) * lo[1] + w * hi[1]
    cl_peak = (1.0 - w) * lo[2] + w * hi[2]
    cl_trough = (1.0 - w) * lo[3] + w * hi[3]
    return a_pos, a_neg, cl_peak, cl_trough


def _stall_from_limits(
    alpha_deg: float,
    cl: float,
    a_pos: float,
    a_neg: float | None,
    cl_peak: float,
    cl_trough: float,
) -> tuple[bool, float]:
    stalled = float(alpha_deg) >= a_pos or (
        a_neg is not None and float(alpha_deg) <= a_neg
    )
    cap = abs(cl_trough) if cl < 0.0 else cl_peak
    return stalled, float(cap)


def section_table(
    alpha_rad: float,
    camber: float,
    re: float,
    thickness: float = _DEFAULT_THICKNESS,
) -> tuple[float, float, bool, float] | None:
    """Table `(cl, cd, stalled, cl_cap)` or None when `cl_cd_table` would miss."""
    if re is None or not math.isfinite(float(re)):
        return None
    fam = family_for_camber(camber, thickness)
    tables = load_polar_family(fam)
    if not tables:
        return None
    a_deg = math.degrees(float(alpha_rad))
    res = _polar_re_levels(fam)
    r = float(re)
    if r < res[0]:
        return None
    if r <= res[0] or r >= res[-1]:
        key = res[0] if r <= res[0] else res[-1]
        alphas, cls, cds = tables[key]
        cl, cd = _interp_alpha(a_deg, alphas, cls, cds)
        a_pos, a_neg, cl_peak, cl_trough = _curve_limits(alphas, cls)
        stalled, cap = _stall_from_limits(a_deg, cl, a_pos, a_neg, cl_peak, cl_trough)
        return cl, cd, stalled, cap
    for lo, hi in zip(res[:-1], res[1:]):
        if lo <= r <= hi:
            w = (math.log10(r) - math.log10(lo)) / (math.log10(hi) - math.log10(lo))
            a0, cl0, cd0 = tables[lo]
            a1, cl1, cd1 = tables[hi]
            c0, d0 = _interp_alpha(a_deg, a0, cl0, cd0)
            c1, d1 = _interp_alpha(a_deg, a1, cl1, cd1)
            cl = c0 * (1.0 - w) + c1 * w
            cd = d0 * (1.0 - w) + d1 * w
            limits = _blend_limits(_curve_limits(a0, cl0), _curve_limits(a1, cl1), w)
            stalled, cap = _stall_from_limits(a_deg, cl, *limits)
            return cl, cd, stalled, cap
    return None


def cl_cd_table(
    alpha_rad: float,
    camber: float,
    re: float,
    thickness: float = _DEFAULT_THICKNESS,
) -> tuple[float, float] | None:
    """Table Cl, Cd at (α, Re) for the camber+thickness-mapped family, or None if unavailable."""
    row = section_table(alpha_rad, camber, re, thickness=thickness)
    if row is None:
        return None
    return row[0], row[1]
```

- [ ] **Step 4: Run the polar tests**

Run: `uv run python -m pytest tests/test_uiuc_polars.py -q --tb=line`

Expected: PASS. Existing `cl_cd_table` tests still pass because the wrapper returns the same Cl and Cd.

- [ ] **Step 5: Commit**

```powershell
git add -- fansim/propeller/polars.py tests/test_uiuc_polars.py
git commit -m @"
feat(prop): report table stall angle and peak lift

"@
```

---

### Task 3: Use the stall gate inside `analyze`

**Files:**
- Modify: `fansim/propeller/bemt.py` (`_cl_cd`, `_cl_cd_analytic`, `analyze`, module docstring)
- Modify: `tests/test_prop_fwh_compress.py` (spy, identity lambda, section tests)
- Modify: `tests/test_bemt.py` only if the measured RPM ratio leaves the current comment

**Interfaces:**
- Consumes: `_compressibility_cl_cd(..., *, stalled, cl_cap)` from Task 1. `section_table` from Task 2.
- Produces: `_section_aero(alpha_rad: float, camber: float, re: float | None = None, thickness: float = 0.12) -> tuple[float, float, bool, float]`

`_cl_cd` stays a 2-tuple wrapper over `_section_aero`.

- [ ] **Step 1: Write the failing section tests**

Append to `tests/test_prop_fwh_compress.py`:

```python
def test_analytic_stall_is_not_scaled():
    from fansim.propeller.bemt import _section_aero

    cl, _cd, stalled, cap = _section_aero(math.radians(20.0), 0.0, re=None)
    assert stalled is True
    assert cap == pytest.approx(1.4)
    assert cl == pytest.approx(1.148)
    out, cd_out = _compressibility_cl_cd(cl, _cd, 0.5, stalled=stalled, cl_cap=cap)
    assert out == pytest.approx(cl)
    assert cd_out == pytest.approx(_cd)


def test_analytic_clamp_before_stall_angle_is_stalled():
    from fansim.propeller.bemt import _section_aero

    cl, _cd, stalled, cap = _section_aero(math.radians(13.0), 0.0, re=None)
    assert stalled is True
    assert cl == pytest.approx(1.4)
    assert cap == pytest.approx(1.4)


def test_attached_table_lift_rises_inside_the_peak():
    from fansim.propeller.bemt import _section_aero

    cl, cd, stalled, cap = _section_aero(math.radians(4.0), 0.04, re=80000.0)
    assert stalled is False
    assert cl == pytest.approx(0.65703, abs=1e-5)
    out, _cd = _compressibility_cl_cd(cl, cd, 0.5, stalled=stalled, cl_cap=cap)
    assert out > cl
    assert out == pytest.approx(cl / math.sqrt(0.75))
    assert out <= cap


def test_low_re_section_uses_analytic_stall():
    from fansim.propeller.bemt import _section_aero

    cl, _cd, stalled, cap = _section_aero(math.radians(20.0), 0.0, re=16000.0)
    assert stalled is True
    assert cap == pytest.approx(0.920926996097583)
    assert cl == pytest.approx(0.6366166630228922)
```

Add `import math` to `tests/test_prop_fwh_compress.py`.

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `uv run python -m pytest tests/test_prop_fwh_compress.py::test_analytic_stall_is_not_scaled tests/test_prop_fwh_compress.py::test_analytic_clamp_before_stall_angle_is_stalled tests/test_prop_fwh_compress.py::test_attached_table_lift_rises_inside_the_peak tests/test_prop_fwh_compress.py::test_low_re_section_uses_analytic_stall -q --tb=line`

Expected: FAIL with `ImportError` (`_section_aero` is not defined).

- [ ] **Step 3: Implement `_section_aero` and call it from `analyze`**

In `fansim/propeller/bemt.py`, replace the module docstring sentence that begins `analyze applies _compressibility_cl_cd` with:

```python
analyze applies _compressibility_cl_cd (Prandtl-Glauert on attached Cl, capped at
the polar peak; stalled Cl unchanged; wave drag past Mach 0.7) using local
relative speed over C_AIR. A compressible CFD tier can still refine finalists.
```

Replace `_cl_cd` so it delegates:

```python
def _cl_cd(
    alpha_rad: float,
    camber: float,
    re: float | None = None,
    thickness: float = 0.12,
):
    """Cambered-airfoil polar: vendored UIUC-style table when Re is set, else analytic.

    REYNOLDS-AWARE (roadmap §7.2 / §1.6): with ``re`` given, prefer ``fansim.data.polars``
    tables (NACA *12 + Selig e387/sd7032/s1223), matched on camber + thickness. If the
    table path is unavailable, use the analytic low-Re trends. ``re=None`` keeps the
    original high-Re analytic (back-compat).
    """
    cl, cd, _stalled, _cap = _section_aero(alpha_rad, camber, re=re, thickness=thickness)
    return cl, cd


def _section_aero(
    alpha_rad: float,
    camber: float,
    re: float | None = None,
    thickness: float = 0.12,
) -> tuple[float, float, bool, float]:
    """Incompressible `(cl, cd, stalled, cl_cap)` from the same branch as `_cl_cd`."""
    if re is not None:
        from fansim.propeller.polars import section_table

        tab = section_table(alpha_rad, camber, re, thickness=thickness)
        if tab is not None:
            return tab
    return _analytic_section(alpha_rad, camber, re)
```

Replace `_cl_cd_analytic` with a wrapper plus `_analytic_section`. Keep the Cl and Cd numbers identical to today's analytic polar.

```python
def _cl_cd_analytic(alpha_rad: float, camber: float, re: float | None = None):
    """Analytic cambered-airfoil polar (high-Re or Re-aware trends)."""
    cl, cd, _stalled, _cap = _analytic_section(alpha_rad, camber, re)
    return cl, cd


def _analytic_section(
    alpha_rad: float, camber: float, re: float | None = None
) -> tuple[float, float, bool, float]:
    a_deg = math.degrees(alpha_rad)
    cl_max, cd0, stall_deg, slope = 1.4, 0.012, 14.0, 2.0 * math.pi
    if re is not None:
        r = max(float(re), 5000.0)
        f = math.log10(r / 20000.0)
        cl_max = max(0.80, min(1.5, 0.95 + 0.30 * f))
        stall_deg = max(8.0, min(15.0, 10.0 + 3.0 * f))
        cd0 = max(0.010, 0.008 + 5.0 / math.sqrt(r))
        slope = 2.0 * math.pi * max(0.75, min(1.0, 0.88 + 0.12 * f))
    cl_lin = slope * camber + slope * alpha_rad
    cl = max(-cl_max, min(cl_max, cl_lin))
    if a_deg > stall_deg:
        cl *= max(0.55, 1.0 - (a_deg - stall_deg) * 0.03)
    stalled = a_deg > stall_deg or abs(cl_lin) >= cl_max
    return cl, cd0, stalled, cl_max
```

In `analyze`, replace the `_cl_cd` / helper pair with:

```python
            cl, cd, stalled, cl_cap = _section_aero(
                alpha, camber, re=math.sqrt(W2) * c / NU_AIR
            )
            mach = math.sqrt(W2) / C_AIR
            cl, cd = _compressibility_cl_cd(
                cl, cd, mach, stalled=stalled, cl_cap=cl_cap
            )
```

In `tests/test_prop_fwh_compress.py`, change the Mach spy to accept the keywords:

```python
    def _spy(cl, cd, mach, *, stalled=False, cl_cap=None):
        recorded.append(float(mach))
        return real(cl, cd, mach, stalled=stalled, cl_cap=cl_cap)
```

Change the identity patch in `test_compressibility_raises_high_rpm_thrust` to:

```python
    def _identity(cl, cd, mach, *, stalled=False, cl_cap=None):
        return (cl, cd)

    monkeypatch.setattr(bemt_mod, "_compressibility_cl_cd", _identity)
```

- [ ] **Step 4: Run the BEMT and compressibility tests**

Run: `uv run python -m pytest tests/test_prop_fwh_compress.py tests/test_bemt.py tests/test_uiuc_polars.py -q --tb=line`

Expected: PASS.

Then measure the RPM-doubling ratio:

```powershell
uv run python -c "from fansim.prop_spec import get_prop_spec; from fansim.propeller.geometry import prop_blade_params; from fansim.propeller.bemt import analyze; p = prop_blade_params(get_prop_spec('fpv_5inch')); t1 = analyze(p, rpm=15000).thrust_n; t2 = analyze(p, rpm=30000).thrust_n; print(t2 / t1)"
```

If the printed ratio is within 0.05 of 4.76, leave `tests/test_bemt.py` unchanged. If it moved by more than 0.05 and is still greater than 3.3, set the ceiling to `min(5.0, round(ratio + 0.1, 2))` and replace the comment and assertion with:

```python
    # ~4x from rpm^2. 30000 RPM is tip Mach ~0.58. The stall cap keeps
    # post-stall Cl at the polar value, so the high-RPM point is no longer
    # inflated. Measured ratio is RATIO.
    assert 3.3 < t2 / t1 < CEILING
```

Substitute the printed ratio (two decimals) for `RATIO` and the ceiling for `CEILING`. Do not raise the ceiling above 5.0. Do not lower the floor below 3.3. If the ratio is ≤ 3.3 or the test still fails after that edit, stop and report the ratio. Do not retune the polar.

- [ ] **Step 5: Commit**

```powershell
git add -- fansim/propeller/bemt.py tests/test_prop_fwh_compress.py tests/test_bemt.py
git commit -m @"
fix(prop): keep stalled BEMT sections off the Prandtl-Glauert lift factor

"@
```

If `tests/test_bemt.py` was not modified, leave it out of `git add`.

---

### Task 4: Record the stall cap and the pressure moment

**Files:**
- Modify: `docs/roadmap.md` (§4.4 steps 1 and 2 only)
- Modify: `docs/validation/drone_radial_open_air_cfd.md` (wall section, last sentence)

**Interfaces:**
- Consumes: the code from Task 3
- Produces: the two doc sentences in spec criterion 10

- [ ] **Step 1: Update the validation sentence**

In `docs/validation/drone_radial_open_air_cfd.md`, replace:

```markdown
layout=axial; outer surfaces face outward. This is not a pass band. Thrust rose against the smoke fixture while shaft power stayed near 2.2 kW, so figure of merit rose from 0.11 to 0.14. `wall_resolved` is false: level 4 on a 0.005 m base cell is 0.31 mm, and three cells across a 0.36 mm wall need about 0.12 mm. BEMT Prandtl-Glauert also raises lift past stall, so this CFD result is not a BEMT comparison.
```

with:

```markdown
layout=axial; outer surfaces face outward. This is not a pass band. Thrust rose against the smoke fixture while shaft power stayed near 2.2 kW, so figure of merit rose from 0.11 to 0.14. `wall_resolved` is false: level 4 on a 0.005 m base cell is 0.31 mm, and three cells across a 0.36 mm wall need about 0.12 mm. At iteration 400 the shaft moment is 0.818 N·m, of which 0.812 N·m is pressure and 0.006 N·m is viscous. This CFD result is not a BEMT comparison.
```

- [ ] **Step 2: Update roadmap steps 1 and 2**

On the §4.4 step 1 done item, after the compressibility plan link, add:

```markdown
     Stall cap: attached Cl is divided by `sqrt(1 - M²)` and limited to the polar peak; Cl at or past stall is unchanged. Spec/plan:
     `docs/superpowers/specs/2026-09-23-prop-bemt-stall-cap-design.md`,
     `docs/superpowers/plans/2026-09-23-prop-bemt-stall-cap.md`.
```

On the §4.4 step 2 done item, after the wall-mesh plan link, add:

```markdown
     At iteration 400 the shaft moment is 0.818 N·m, of which 0.812 N·m is pressure and 0.006 N·m is viscous.
```

Leave the `- [ ] **4.4` checkbox, step 3, and §14.7 unchanged.

- [ ] **Step 3: Commit**

```powershell
git add -- docs/roadmap.md docs/validation/drone_radial_open_air_cfd.md
git commit -m @"
docs(prop): record the BEMT stall cap and the obj_2 pressure moment

"@
```

Do not stage `runs/` or the CFD stamp JSON files.
