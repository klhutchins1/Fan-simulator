### Task 1: Open-air domain sizing

**Files:**
- Create: `fansim/propeller/cfd.py`
- Test: `tests/test_prop_cfd.py`

**Interfaces:**
- Consumes: tip radius in metres (caller converts mm)
- Produces:
  - `@dataclass PropOpenAir` with SI fields: `tip_radius`, `domain_radius`, `z_min`, `z_max`, `mrf_z_min`, `mrf_z_max`, `rpm`, `omega_signed`, `u_freestream` (default 0.1)
  - `prop_open_air(tip_radius_m, z_lo_m, z_hi_m, rpm, *, spin=-1, radial_mult=5.0, up_mult=2.0, down_mult=4.0, u_eps=0.1) -> PropOpenAir`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_prop_cfd.py
from __future__ import annotations
import math
import pytest

def test_prop_open_air_extents():
    from fansim.propeller.cfd import prop_open_air
    R = 0.0635  # 5-inch tip radius
    d = prop_open_air(R, z_lo_m=-0.01, z_hi_m=0.01, rpm=21000.0)
    assert d.domain_radius == pytest.approx(5.0 * R)
    assert d.z_min == pytest.approx(-0.01 - 2.0 * R)
    assert d.z_max == pytest.approx(0.01 + 4.0 * R)
    assert d.mrf_z_min < -0.01 and d.mrf_z_max > 0.01
    assert d.omega_signed == pytest.approx(-21000.0 * 2.0 * math.pi / 60.0)
    assert d.u_freestream == pytest.approx(0.1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_prop_cfd.py::test_prop_open_air_extents -v`  
Expected: FAIL — `ModuleNotFoundError` or missing `prop_open_air`.

- [ ] **Step 3: Minimal implementation**

```python
# fansim/propeller/cfd.py
"""Open-air compressible MRF evaluate for drone props (roadmap §4.3 stage 1)."""
from __future__ import annotations
import math
from dataclasses import dataclass

@dataclass
class PropOpenAir:
    tip_radius: float
    domain_radius: float
    z_min: float
    z_max: float
    mrf_z_min: float
    mrf_z_max: float
    rpm: float
    omega_signed: float
    u_freestream: float = 0.1

def prop_open_air(
    tip_radius_m: float,
    z_lo_m: float,
    z_hi_m: float,
    rpm: float,
    *,
    spin: int = -1,
    radial_mult: float = 5.0,
    up_mult: float = 2.0,
    down_mult: float = 4.0,
    u_eps: float = 0.1,
    mrf_margin_m: float = 0.005,
) -> PropOpenAir:
    R = float(tip_radius_m)
    omega = float(rpm) * 2.0 * math.pi / 60.0
    return PropOpenAir(
        tip_radius=R,
        domain_radius=radial_mult * R,
        z_min=z_lo_m - up_mult * R,
        z_max=z_hi_m + down_mult * R,
        mrf_z_min=z_lo_m - mrf_margin_m,
        mrf_z_max=z_hi_m + mrf_margin_m,
        rpm=float(rpm),
        omega_signed=float(spin) * omega,
        u_freestream=float(u_eps),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/test_prop_cfd.py::test_prop_open_air_extents -v`  
Expected: PASS
