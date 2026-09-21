# Prop Power Budget + PyThrust Quorum (Track A Stage 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship always-on hover Wh/power budgeting from FoM/BEMT, an optional pinned PyThrust adapter for catalog motor–prop matching, and quorum cross-checks that verify our math without duplicating production solvers.

**Architecture:** New `fansim/propeller/power.py` owns hover budget + adapter + quorum helpers. PyThrust (`setuav-pythrust==0.2.3`) is an optional extra imported only inside the adapter. Quorum witnesses (analytic FoM, PyThrust field parity, APC catalog static) fail tests on disagreement — never average sources into user numbers.

**Tech Stack:** Python 3.12 (uv), pytest, optional `setuav-pythrust==0.2.3` (Apache-2.0).

**Spec:** `docs/superpowers/specs/2026-09-21-prop-pythrust-power-design.md`

## Global Constraints

- Extra pin: `setuav-pythrust==0.2.3` under `[project.optional-dependencies] propulsion`.
- Core install / default CI **must not** require PyThrust.
- Never import `pythrust` at module top of `bemt.py`, `cfd.py`, or cockpit package `__init__`.
- Defaults: `eta_elec=0.70`, `usable_frac=0.80`, `system.resistance_ohm=0.02`.
- Quorum Q4 band ±15%; Q5 catalog FoM window `[0.50, 0.85]`.
- On quorum failure: fail with diagnostics; do not switch product numbers to the witness.
- Stage 1 UI: CLI first; no cockpit motor picker.
- Unit tests without extra stay green; propulsion tests use `@pytest.mark.propulsion` and skip if unavailable.
- Skip staging `catalog/catalog.db`. Commit when the user asks (plan steps may still list commits).

## File map

| File | Role |
|------|------|
| `pyproject.toml` | `propulsion` extra + `propulsion` pytest marker |
| `fansim/propeller/power.py` | Hover budget, adapter, quorum, exceptions |
| `fansim/propeller/__init__.py` | Export public power helpers |
| `scripts/evaluate_prop_power.py` | CLI: `hover-budget` / `catalog` / `quorum` |
| `tests/test_prop_power.py` | Always-on tests (Q1, budget, missing extra) |
| `tests/test_prop_power_propulsion.py` | Marked propulsion tests (Q3–Q5, catalog smoke) |
| `docs/bibliography.md` | PyThrust + Drela + UIUC PropDB notes |
| `docs/roadmap.md` | Short Track A / power-budget note under prop work |

---

### Task 1: Extra pin + pytest marker

**Files:**
- Modify: `pyproject.toml`
- Test: none yet (config only; verified by later tasks)

**Interfaces:**
- Produces: optional extra name `propulsion`; marker `propulsion`

- [ ] **Step 1: Add optional dependency and marker**

In `pyproject.toml`, under `[project.optional-dependencies]`, add:

```toml
propulsion = ["setuav-pythrust==0.2.3"]
```

Under `[tool.pytest.ini_options].markers`, add:

```toml
"propulsion: requires optional setuav-pythrust (uv sync --extra propulsion)",
```

- [ ] **Step 2: Verify pin resolves**

Run: `uv sync --extra propulsion`  
Expected: installs `setuav-pythrust==0.2.3` without conflicting with `requires-python = ">=3.12,<3.13"`.

Run: `uv run --extra propulsion python -c "import pythrust; print(pythrust.__version__)"`  
Expected: `0.2.3`

- [ ] **Step 3: Commit** (when user asks)

```bash
git add pyproject.toml uv.lock
git commit -m "$(cat <<'EOF'
deps: optional pinned setuav-pythrust for prop power matching

EOF
)"
```

---

### Task 2: `hover_power_budget` + FoM quorum (Q1)

**Files:**
- Create: `fansim/propeller/power.py`
- Modify: `fansim/propeller/__init__.py`
- Test: `tests/test_prop_power.py`

**Interfaces:**
- Produces:
  - `class PropulsionExtraMissing(RuntimeError)`
  - `RHO_AIR = 1.225`
  - `hover_power_budget(*, all_up_weight_n: float, n_rotors: int, tip_radius_m: float, figure_of_merit: float, eta_elec: float = 0.70, battery_wh: float | None = None, usable_frac: float = 0.80, shaft: float = RHO_AIR, shaft_power_w: float | None = None) -> dict`
  - Result keys always include: `power_model` (`"momentum_fm"` | `"bemt_shaft"`), `thrust_per_rotor_n`, `disk_area_m2`, `ideal_power_w`, `shaft_power_w`, `elec_power_w_total`, `eta_elec`, `hover_minutes` (or `None`), stamps.

Physics (must match spec §3):

1. `T = all_up_weight_n / n_rotors`
2. `A = π R²`
3. `P_i = T**1.5 / sqrt(2 ρ A)`
4. If `shaft_power_w` is None: clamp FM to `(0.05, 1.0)`, `P_shaft_rotor = P_i / FM`, `power_model="momentum_fm"`
5. Else: use provided shaft power as **per-rotor** shaft watts, `power_model="bemt_shaft"`
6. `P_elec_total = (P_shaft_rotor * n_rotors) / eta_elec`
7. If `battery_wh`: `hover_minutes = 60 * battery_wh * usable_frac / P_elec_total`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_prop_power.py
from __future__ import annotations
import math
import pytest

def test_hover_power_budget_minutes_scale_with_wh():
    from fansim.propeller.power import hover_power_budget
    a = hover_power_budget(
        all_up_weight_n=19.6133,  # 2 kg
        n_rotors=4,
        tip_radius_m=0.0635,
        figure_of_merit=0.70,
        battery_wh=50.0,
    )
    b = hover_power_budget(
        all_up_weight_n=19.6133,
        n_rotors=4,
        tip_radius_m=0.0635,
        figure_of_merit=0.70,
        battery_wh=100.0,
    )
    assert a["power_model"] == "momentum_fm"
    assert a["hover_minutes"] is not None and b["hover_minutes"] is not None
    assert b["hover_minutes"] == pytest.approx(2.0 * a["hover_minutes"], rel=1e-9)
    assert a["eta_elec"] == pytest.approx(0.70)

def test_hover_power_budget_bemt_shaft_override():
    from fansim.propeller.power import hover_power_budget
    out = hover_power_budget(
        all_up_weight_n=20.0,
        n_rotors=4,
        tip_radius_m=0.05,
        figure_of_merit=0.7,
        shaft_power_w=100.0,  # per rotor
        battery_wh=None,
    )
    assert out["power_model"] == "bemt_shaft"
    assert out["shaft_power_w"] == pytest.approx(100.0)
    assert out["elec_power_w_total"] == pytest.approx(400.0 / 0.70)

def test_quorum_q1_fom_identity():
    """FM = T^1.5 / (P sqrt(2 rho A)) rearranges with hover_power_budget."""
    from fansim.propeller.power import RHO_AIR, hover_power_budget
    T = 5.0
    R = 0.06
    A = math.pi * R * R
    FM = 0.65
    P_i = T ** 1.5 / math.sqrt(2.0 * RHO_AIR * A)
    P_shaft = P_i / FM
    # AUW = 4 rotors * T
    out = hover_power_budget(
        all_up_weight_n=4.0 * T,
        n_rotors=4,
        tip_radius_m=R,
        figure_of_merit=FM,
        eta_elec=1.0,  # isolate shaft
    )
    assert out["shaft_power_w"] == pytest.approx(P_shaft, rel=1e-9)
    # recover FM from T, P, A
    fm_back = (T ** 1.5 / math.sqrt(2.0 * RHO_AIR * A)) / out["shaft_power_w"]
    assert fm_back == pytest.approx(FM, rel=1e-9)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_prop_power.py -v`  
Expected: FAIL (module or symbols missing)

- [ ] **Step 3: Implement `fansim/propeller/power.py` (budget + Q1 only)**

```python
# fansim/propeller/power.py (initial slice)
from __future__ import annotations
import math
from typing import Any

RHO_AIR = 1.225

class PropulsionExtraMissing(RuntimeError):
    """Raised when a catalog/PyThrust feature is requested without the extra installed."""


def hover_power_budget(
    *,
    all_up_weight_n: float,
    n_rotors: int,
    tip_radius_m: float,
    figure_of_merit: float,
    eta_elec: float = 0.70,
    battery_wh: float | None = None,
    usable_frac: float = 0.80,
    rho: float = RHO_AIR,
    shaft_power_w: float | None = None,
) -> dict[str, Any]:
    if int(n_rotors) < 1:
        raise ValueError("n_rotors must be >= 1")
    if float(tip_radius_m) <= 0.0:
        raise ValueError("tip_radius_m must be > 0")
    if float(eta_elec) <= 0.0 or float(eta_elec) > 1.0:
        raise ValueError("eta_elec must be in (0, 1]")
    T = float(all_up_weight_n) / float(n_rotors)
    A = math.pi * float(tip_radius_m) ** 2
    P_i = (T ** 1.5) / math.sqrt(2.0 * float(rho) * A) if T > 0.0 else 0.0
    if shaft_power_w is None:
        fm = min(1.0, max(0.05, float(figure_of_merit)))
        P_shaft = P_i / fm if fm > 0.0 else 0.0
        power_model = "momentum_fm"
    else:
        P_shaft = float(shaft_power_w)
        power_model = "bemt_shaft"
    P_elec_total = (P_shaft * float(n_rotors)) / float(eta_elec) if eta_elec > 0.0 else 0.0
    minutes = None
    if battery_wh is not None and P_elec_total > 0.0:
        minutes = 60.0 * float(battery_wh) * float(usable_frac) / P_elec_total
    return {
        "power_model": power_model,
        "thrust_per_rotor_n": T,
        "disk_area_m2": A,
        "ideal_power_w": P_i,
        "shaft_power_w": P_shaft,
        "elec_power_w_total": P_elec_total,
        "eta_elec": float(eta_elec),
        "usable_frac": float(usable_frac),
        "battery_wh": None if battery_wh is None else float(battery_wh),
        "hover_minutes": minutes,
        "n_rotors": int(n_rotors),
        "tip_radius_m": float(tip_radius_m),
        "figure_of_merit_used": (
            min(1.0, max(0.05, float(figure_of_merit))) if shaft_power_w is None else float(figure_of_merit)
        ),
        "rho": float(rho),
    }
```

Export from `fansim/propeller/__init__.py`:

```python
from fansim.propeller.power import hover_power_budget, PropulsionExtraMissing

__all__ = [
    # ...existing...
    "hover_power_budget",
    "PropulsionExtraMissing",
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_prop_power.py -v`  
Expected: PASS

- [ ] **Step 5: Commit** (when user asks)

```bash
git add fansim/propeller/power.py fansim/propeller/__init__.py tests/test_prop_power.py
git commit -m "$(cat <<'EOF'
feat(prop): hover power budget with FoM identity quorum

EOF
)"
```

---

### Task 3: PyThrust availability + catalog adapter

**Files:**
- Modify: `fansim/propeller/power.py`
- Modify: `fansim/propeller/__init__.py`
- Test: `tests/test_prop_power.py`, `tests/test_prop_power_propulsion.py`

**Interfaces:**
- Produces:
  - `pythrust_available() -> bool`
  - `list_catalog_props(*, manufacturer: str = "APC") -> list[dict]`
  - `find_catalog_prop(diameter_in: float, pitch_in: float, *, blade_count: int = 2) -> dict`
  - `solve_catalog_operating_point(*, motor: dict, battery_voltage_v: float, prop_id: str | None = None, diameter_in: float | None = None, pitch_in: float | None = None, blade_count: int = 2, throttle: float = 0.7, airspeed_mps: float = 0.0, rho: float = RHO_AIR, system_resistance_ohm: float = 0.02) -> dict`
  - Motor dict keys: `kv_rpm_per_v`, `resistance_ohm`, `no_load_current_a`, `current_max_a`
  - Result stamps: `source="pythrust"`, `pythrust_version`, `prop_id`, plus fields listed in the spec

Import path (from smoke investigation):

```python
from pathlib import Path
from pythrust import dataset_dir
from pythrust.propellers.database import PropellerDatabase
from pythrust.propulsion.solver import PropulsionSolver
from pythrust.propulsion.models.motor import MotorSpec
from pythrust.propulsion.models.battery import FixedVoltageBattery
from pythrust.propulsion.models.system import SystemSpec
from pythrust.propulsion.models.propeller import PropellerSpec
```

Load DB once per call (or module-level lazy cache):  
`PropellerDatabase().load(Path(dataset_dir()) / "propellers" / "apc_202602")`

- [ ] **Step 1: Write failing tests (always-on missing path)**

```python
# append to tests/test_prop_power.py
def test_pythrust_available_false_when_missing(monkeypatch):
    import fansim.propeller.power as power
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "pythrust" or name.startswith("pythrust."):
            raise ImportError("blocked")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    # clear any cached availability if implemented
    if hasattr(power, "_pythrust_ok"):
        monkeypatch.setattr(power, "_pythrust_ok", None)
    assert power.pythrust_available() is False
    with pytest.raises(power.PropulsionExtraMissing):
        power.solve_catalog_operating_point(
            motor={"kv_rpm_per_v": 1900, "resistance_ohm": 0.05,
                   "no_load_current_a": 1.0, "current_max_a": 40},
            battery_voltage_v=22.2,
            diameter_in=5.0,
            pitch_in=4.5,
        )
```

- [ ] **Step 2: Write propulsion smoke test**

```python
# tests/test_prop_power_propulsion.py
from __future__ import annotations
import pytest

pytest.importorskip("pythrust")

pytestmark = pytest.mark.propulsion

def test_catalog_solve_apc_5x45_feasible():
    from fansim.propeller.power import solve_catalog_operating_point
    out = solve_catalog_operating_point(
        motor={
            "kv_rpm_per_v": 1900.0,
            "resistance_ohm": 0.05,
            "no_load_current_a": 1.0,
            "current_max_a": 40.0,
        },
        battery_voltage_v=22.2,
        diameter_in=5.0,
        pitch_in=4.5,
        throttle=0.7,
        airspeed_mps=0.0,
    )
    assert out["source"] == "pythrust"
    assert out["pythrust_version"] == "0.2.3"
    assert out["is_feasible"] is True
    assert out["thrust_n"] > 0.0
    assert out["rpm"] > 1000.0
    assert out["prop_id"]
```

- [ ] **Step 3: Run always-on test (expect fail until implemented)**

Run: `uv run python -m pytest tests/test_prop_power.py::test_pythrust_available_false_when_missing -v`  
Expected: FAIL until helpers exist

- [ ] **Step 4: Implement adapter functions in `power.py`**

Minimal shapes:

```python
def pythrust_available() -> bool:
    try:
        import pythrust  # noqa: F401
        return True
    except ImportError:
        return False

def _require_pythrust():
    if not pythrust_available():
        raise PropulsionExtraMissing(
            "Catalog propulsion requires optional extra: "
            "uv sync --extra propulsion  (setuav-pythrust==0.2.3)"
        )

def _load_apc_db():
    from pathlib import Path
    from pythrust import dataset_dir
    from pythrust.propellers.database import PropellerDatabase
    db = PropellerDatabase()
    db.load(Path(dataset_dir()) / "propellers" / "apc_202602")
    return db

def list_catalog_props(*, manufacturer: str = "APC") -> list[dict]:
    _require_pythrust()
    db = _load_apc_db()
    rows = []
    for pid in db.list_propellers():
        meta = db.get(pid).metadata
        if manufacturer and manufacturer.upper() not in (meta.manufacturer or "").upper():
            # APC ids are APC_*; still filter by metadata.manufacturer when present
            if manufacturer.upper() != "APC":
                continue
        rows.append({
            "prop_id": meta.id,
            "manufacturer": meta.manufacturer,
            "diameter_in": meta.diameter_in,
            "pitch_in": meta.pitch_in,
            "blade_count": meta.blade_count,
        })
    return rows

def find_catalog_prop(diameter_in: float, pitch_in: float, *, blade_count: int = 2) -> dict:
    _require_pythrust()
    db = _load_apc_db()
    entry = db.find_by_size(float(diameter_in), float(pitch_in), blade_count=int(blade_count))
    meta = entry.metadata
    return {
        "prop_id": meta.id,
        "manufacturer": meta.manufacturer,
        "diameter_in": meta.diameter_in,
        "pitch_in": meta.pitch_in,
        "blade_count": meta.blade_count,
        "_entry": entry,  # internal; strip before returning from public solve if preferred
    }

def solve_catalog_operating_point(...):  # as Interfaces above
    _require_pythrust()
    import pythrust
    from pythrust.propulsion.solver import PropulsionSolver
    from pythrust.propulsion.models.motor import MotorSpec
    from pythrust.propulsion.models.battery import FixedVoltageBattery
    from pythrust.propulsion.models.system import SystemSpec
    from pythrust.propulsion.models.propeller import PropellerSpec
    db = _load_apc_db()
    if prop_id:
        entry = db.get(prop_id)
    else:
        if diameter_in is None or pitch_in is None:
            raise ValueError("provide prop_id or diameter_in+pitch_in")
        entry = db.find_by_size(float(diameter_in), float(pitch_in), blade_count=int(blade_count))
    meta = entry.metadata
    prop = PropellerSpec(diameter_m=float(meta.diameter_in) * 0.0254)
    m = MotorSpec(
        kv_rpm_per_v=float(motor["kv_rpm_per_v"]),
        resistance_ohm=float(motor["resistance_ohm"]),
        no_load_current_a=float(motor["no_load_current_a"]),
        current_max_a=float(motor["current_max_a"]),
    )
    batt = FixedVoltageBattery(voltage_v=float(battery_voltage_v))
    sys = SystemSpec(resistance_ohm=float(system_resistance_ohm))
    pt = PropulsionSolver().solve_operating_point(
        motor=m, battery=batt, system=sys, propeller=prop, prop_entry=entry,
        rho=float(rho), airspeed_mps=float(airspeed_mps), throttle=float(throttle),
    )
    return {
        "rpm": float(pt.rpm),
        "thrust_n": float(pt.thrust_n),
        "thrust_g": float(pt.thrust_n) / 9.80665 * 1000.0,
        "torque_nm": float(pt.torque_nm),
        "shaft_power_w": float(pt.shaft_power_w),
        "motor_power_w": float(pt.motor_power_w),
        "battery_power_w": float(pt.battery_power_w),
        "motor_current_a": float(pt.motor_current_a),
        "battery_current_a": float(pt.battery_current_a),
        "motor_efficiency": float(pt.motor_efficiency),
        "is_feasible": bool(pt.is_feasible),
        "infeasible_reason": pt.infeasible_reason,
        "source": "pythrust",
        "pythrust_version": getattr(pythrust, "__version__", "0.2.3"),
        "prop_id": meta.id,
        "throttle": float(throttle),
        "airspeed_mps": float(airspeed_mps),
    }
```

Strip `_entry` from any public `find_catalog_prop` return (return metadata dict only).

- [ ] **Step 5: Run tests**

Run: `uv run python -m pytest tests/test_prop_power.py -v`  
Expected: PASS

Run: `uv run --extra propulsion python -m pytest tests/test_prop_power_propulsion.py -v`  
Expected: PASS

- [ ] **Step 6: Commit** (when user asks)

```bash
git add fansim/propeller/power.py fansim/propeller/__init__.py tests/test_prop_power.py tests/test_prop_power_propulsion.py
git commit -m "$(cat <<'EOF'
feat(prop): optional PyThrust catalog motor–prop adapter

EOF
)"
```

---

### Task 4: Quorum Q3–Q5 helpers + tests

**Files:**
- Modify: `fansim/propeller/power.py`
- Modify: `tests/test_prop_power_propulsion.py`

**Interfaces:**
- Produces: `run_propulsion_quorum(*, prop_id: str = "APC_5x4.5E", rpm_static: float = 10000.0) -> dict`  
  Returns `{ "checks": [ {"id": "Q3"|"Q4"|"Q5", "pass": bool, "detail": str, ...} ], "all_pass": bool }`

**Q3:** Call `solve_catalog_operating_point` and also call PyThrust solver directly with the same inputs; assert `rpm`, `thrust_n`, `shaft_power_w`, `motor_current_a` match within `rel=1e-9` (or `abs=1e-9`).

**Q4:** From APC entry at `rpm_static`, take static (`J≈0`) `ct`, `cp`.  
`n = rpm/60`, `D = dia_in * 0.0254`,  
`T = ct * rho * n**2 * D**4`,  
`P = cp * rho * n**3 * D**5`,  
`A = π (D/2)**2`,  
`P_i = T**1.5 / sqrt(2 rho A)`,  
`FM = P_i / P`,  
Compare `P` to `P_i / FM` (identity) and also compare `hover_power_budget` shaft (with that FM and thrust) to `P` within **±15%**.

**Q5:** Same static FM must lie in `[0.50, 0.85]`.

- [ ] **Step 1: Write failing propulsion quorum test**

```python
def test_quorum_q3_q4_q5_apc_5x45():
    from fansim.propeller.power import run_propulsion_quorum
    report = run_propulsion_quorum(prop_id="APC_5x4.5E", rpm_static=10000.0)
    assert report["all_pass"] is True
    by_id = {c["id"]: c for c in report["checks"]}
    assert by_id["Q3"]["pass"] and by_id["Q4"]["pass"] and by_id["Q5"]["pass"]
```

- [ ] **Step 2: Run to verify fail**

Run: `uv run --extra propulsion python -m pytest tests/test_prop_power_propulsion.py::test_quorum_q3_q4_q5_apc_5x45 -v`  
Expected: FAIL until `run_propulsion_quorum` exists

- [ ] **Step 3: Implement `run_propulsion_quorum`**

Implement using `_load_apc_db`, bilinear/static lookup from `entry.data_by_rpm[rpm_static]` (pick nearest RPM key if exact missing), first point with `j == 0` or min `j`.

For Q3 motor defaults (match smoke): Kv 1900, Ri 0.05, I0 1.0, Imax 40, Vbat 22.2, throttle 0.7.

- [ ] **Step 4: Run propulsion tests**

Run: `uv run --extra propulsion python -m pytest tests/test_prop_power_propulsion.py -v`  
Expected: PASS

If Q4/Q5 fail on real APC data, **do not** silently loosen in code without updating the spec honesty section and this plan’s Global Constraints with the measured delta.

- [ ] **Step 5: Commit** (when user asks)

```bash
git add fansim/propeller/power.py tests/test_prop_power_propulsion.py
git commit -m "$(cat <<'EOF'
test(prop): quorum cross-checks vs PyThrust and APC catalog

EOF
)"
```

---

### Task 5: CLI `evaluate_prop_power.py`

**Files:**
- Create: `scripts/evaluate_prop_power.py`
- Test: `tests/test_prop_power.py` (parser flags) or reuse `tests/_cli_parsers.py` if present

**Interfaces:**
- CLI modes: `hover-budget`, `catalog`, `quorum`
- Prints JSON to stdout; exit 0 on success; exit 2 if catalog/quorum requested without extra

- [ ] **Step 1: Write failing CLI flag test**

```python
def test_cli_evaluate_prop_power_declares_modes():
    from tests._cli_parsers import load_build_parser
    ap = load_build_parser("evaluate_prop_power.py")()
    help_text = ap.format_help()
    assert "hover-budget" in help_text or "hover_budget" in help_text or "--mode" in help_text
```

If `load_build_parser` expects `build_parser`, export `build_parser()` from the script like `evaluate_prop_cfd.py`.

- [ ] **Step 2: Implement CLI**

Mirror structure of `scripts/evaluate_prop_cfd.py`:

```python
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Prop hover power / catalog matching / quorum")
    ap.add_argument("--mode", choices=("hover-budget", "catalog", "quorum"), required=True)
    # hover-budget
    ap.add_argument("--auw-n", type=float, default=None)
    ap.add_argument("--n-rotors", type=int, default=4)
    ap.add_argument("--tip-radius-m", type=float, default=None)
    ap.add_argument("--fm", type=float, default=0.70)
    ap.add_argument("--eta-elec", type=float, default=0.70)
    ap.add_argument("--battery-wh", type=float, default=None)
    # catalog
    ap.add_argument("--prop-id", default=None)
    ap.add_argument("--dia-in", type=float, default=None)
    ap.add_argument("--pitch-in", type=float, default=None)
    ap.add_argument("--kv", type=float, default=1900.0)
    ap.add_argument("--ri", type=float, default=0.05)
    ap.add_argument("--i0", type=float, default=1.0)
    ap.add_argument("--imax", type=float, default=40.0)
    ap.add_argument("--vbat", type=float, default=22.2)
    ap.add_argument("--throttle", type=float, default=0.7)
    ap.add_argument("--rsys", type=float, default=0.02)
    return ap
```

Wire each mode to `hover_power_budget` / `solve_catalog_operating_point` / `run_propulsion_quorum`. Catch `PropulsionExtraMissing` → stderr message + exit 2.

- [ ] **Step 3: Manual smoke**

```bash
uv run python scripts/evaluate_prop_power.py --mode hover-budget --auw-n 19.6 --tip-radius-m 0.0635 --fm 0.7 --battery-wh 50
uv run --extra propulsion python scripts/evaluate_prop_power.py --mode catalog --dia-in 5 --pitch-in 4.5
uv run --extra propulsion python scripts/evaluate_prop_power.py --mode quorum
```

Expected: JSON with finite numbers; quorum `"all_pass": true`.

- [ ] **Step 4: Commit** (when user asks)

```bash
git add scripts/evaluate_prop_power.py tests/test_prop_power.py
git commit -m "$(cat <<'EOF'
feat(prop): CLI for hover budget, catalog match, and quorum

EOF
)"
```

---

### Task 6: Docs touch-up

**Files:**
- Modify: `docs/bibliography.md` (§7 prop note)
- Modify: `docs/roadmap.md` (short note under prop / §4.x or research)
- Modify: research canvas optional (already has Round 3)

- [ ] **Step 1: Bibliography entries**

Add under §7 (or a new §7.x bullet):

- PyThrust (`setuav-pythrust`) — optional motor–prop–battery matching; Apache-2.0; pin 0.2.3  
- Drela first-order DC motor model (MIT) — linked from PyThrust theory  
- UIUC Propeller Data Site — measured CT/CP witness corpus (A3)

- [ ] **Step 2: Roadmap one-liner**

Note Track A stage 1: hover budget + optional PyThrust + quorum (spec/plan dated 2026-09-21); not a substitute for §4.3 CFD.

- [ ] **Step 3: Commit** (when user asks)

```bash
git add docs/bibliography.md docs/roadmap.md
git commit -m "$(cat <<'EOF'
docs: prop power budget / PyThrust quorum references

EOF
)"
```

---

## Spec coverage checklist

| Spec requirement | Task |
|------------------|------|
| Optional pin `==0.2.3` | Task 1 |
| `hover_power_budget` + stamps | Task 2 |
| Q1 FoM identity | Task 2 |
| Adapter + `PropulsionExtraMissing` | Task 3 |
| Catalog solve + version stamp | Task 3 |
| Quorum Q3–Q5 + bands | Task 4 |
| CLI modes including `quorum` | Task 5 |
| No cockpit picker stage 1 | (non-goal; no task) |
| Bibliography / roadmap | Task 6 |
| No hard dep / no top-level pythrust imports | Tasks 1–3 |

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-21-prop-pythrust-power.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — execute tasks in this session with checkpoints  

Which approach?
