# Track A A3: BEMT ↔ UIUC/APC Static CT/CP Quorum Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship geometry-honest static CT₀/CP₀ quorum: approximate dia×pitch BEMT vs PyThrust APC (Q6) and one vendored UIUC PropDB fixture (Q7), with ±35% bands and no product-number swapping.

**Architecture:** New `fansim/propeller/bemt_catalog.py` owns approximate loft, BEMT→CT/CP, fixture load, compare helper, and `run_bemt_catalog_quorum`. Stage-1 `run_propulsion_quorum` stays unchanged; CLI `--mode quorum` concatenates both reports. UIUC fixture is always-on; Q6 requires `--extra propulsion`.

**Tech Stack:** Python 3.12 (uv), pytest, existing BEMT + `polar.nondim`, optional `setuav-pythrust==0.2.3`.

**Spec:** `docs/superpowers/specs/2026-09-21-prop-bemt-uiuc-a3-design.md`

## Global Constraints

- Band: **±35%** relative on **both** CT and CP (`band_rel=0.35`); do not silently tighten.
- Stamp `geometry_match="approximate"` on every A3 compare.
- On failure: diagnostics only — never overwrite BEMT product numbers with the witness.
- Freeze props: **Q6** `APC_9x4.7SF` @ nearest RPM to 6026; **Q7** UIUC `apcsf_9x4.7` static @ **6026** RPM (CT=0.1192, CP=0.0484 from Vol1 file).
- No top-level `pythrust` import in `bemt_catalog.py` / `__init__.py` / `bemt.py`.
- Q7 always-on (no PyThrust); Q6 `@pytest.mark.propulsion` + skip/omit without extra.
- Do not stage `catalog/catalog.db`. Commit when the user asks (plan steps may still list commits).
- Pre-plan probe: default `prop_blade_params` loft vs `APC_5x4.5E` @ 10k exceeds ±35% on CP — do **not** use 5×4.5 for A3 without a documented band update.

## File map

| File | Role |
|------|------|
| `fansim/propeller/bemt_catalog.py` | Approximate loft, BEMT static CT/CP, UIUC load, compare, Q6/Q7 quorum |
| `fansim/propeller/__init__.py` | Export public A3 helpers |
| `validation/reference/uiuc_propdb/apcsf_9x4.7_static.json` | Vendored UIUC static fixture |
| `validation/reference/README.md` | Short note on uiuc_propdb |
| `tests/test_bemt_catalog.py` | Always-on: finite CT/CP + Q7 |
| `tests/test_prop_power_propulsion.py` | Append Q6 propulsion test |
| `scripts/evaluate_prop_power.py` | Quorum mode concatenates stage-1 + A3 |
| `docs/bibliography.md` | UIUC → code path (drop “planned”) |

---

### Task 1: UIUC fixture + loader + `bemt_static_ct_cp`

**Files:**
- Create: `fansim/propeller/bemt_catalog.py`
- Create: `validation/reference/uiuc_propdb/apcsf_9x4.7_static.json`
- Modify: `validation/reference/README.md`
- Modify: `fansim/propeller/__init__.py`
- Test: `tests/test_bemt_catalog.py`

**Interfaces:**
- Produces:
  - `DEFAULT_UIUC_FIXTURE_ID = "apcsf_9x4.7_static"`
  - `UIUC_DIR = <repo>/validation/reference/uiuc_propdb`
  - `BAND_REL_A3 = 0.35`
  - `approximate_prop_blade(diameter_in: float, pitch_in: float, *, blade_count: int = 2) -> BladeParams`
  - `bemt_static_ct_cp(diameter_in: float, pitch_in: float, *, rpm: float, blade_count: int = 2, rho: float = RHO_AIR) -> dict`
  - `load_uiuc_static_fixture(path_or_id: str | Path | None = None) -> dict`

Frozen loft defaults (match `prop_blade_params` design defaults unless noted):

- Hub: `hub_dia_mm = max(0.15 * diameter_mm, 8.0)` (fraction of diameter; not a PropSpec shaft table)
- Shaft mount dummy for `PropSpec`: `PropShaftMount(shaft_dia_mm=5.0, hub_bore_dia_mm=5.0, hub_dia_mm=hub_dia_mm)`
- Use `prop_blade_params(spec)` with default chord/thickness/camber (helix from pitch)

`bemt_static_ct_cp` result keys:

```python
{
  "ct": float, "cp": float, "thrust_n": float, "power_w": float,
  "rpm": float, "diameter_in": float, "pitch_in": float, "blade_count": int,
  "geometry_match": "approximate", "j": 0.0, "rho": float,
}
```

Use `fansim.propeller.bemt.analyze` + `fansim.propeller.polar.nondim` (`v_inf=0`).

- [ ] **Step 1: Write the UIUC fixture file**

Create `validation/reference/uiuc_propdb/apcsf_9x4.7_static.json`:

```json
{
  "prop_id": "UIUC_APC_SF_9x4.7_STATIC",
  "manufacturer": "APC",
  "diameter_in": 9.0,
  "pitch_in": 4.7,
  "blade_count": 2,
  "rpm": 6026,
  "j": 0.0,
  "ct": 0.1192,
  "cp": 0.0484,
  "provenance": {
    "site": "https://m-selig.ae.illinois.edu/props/propDB.html",
    "file_or_table": "volume-1/data/apcsf_9x4.7_static_kt1032.txt",
    "retrieved": "2026-09-21",
    "notes": "Vol1 APC Slow Flyer 9x4.7; row RPM=6026 CT=0.1192 CP=0.0484; vendored for A3 Q7"
  }
}
```

Source URL (verify still reachable):  
`https://m-selig.ae.illinois.edu/props/volume-1/data/apcsf_9x4.7_static_kt1032.txt`

- [ ] **Step 2: Write failing tests**

```python
# tests/test_bemt_catalog.py
from __future__ import annotations
import math
import pytest

def test_bemt_static_ct_cp_finite():
    from fansim.propeller.bemt_catalog import bemt_static_ct_cp
    out = bemt_static_ct_cp(9.0, 4.7, rpm=6026.0, blade_count=2)
    assert out["geometry_match"] == "approximate"
    assert out["j"] == 0.0
    assert out["ct"] > 0.0 and out["cp"] > 0.0
    assert math.isfinite(out["ct"]) and math.isfinite(out["cp"])

def test_load_uiuc_fixture_apcsf_9x47():
    from fansim.propeller.bemt_catalog import load_uiuc_static_fixture
    fx = load_uiuc_static_fixture("apcsf_9x4.7_static")
    assert fx["diameter_in"] == pytest.approx(9.0)
    assert fx["pitch_in"] == pytest.approx(4.7)
    assert fx["rpm"] == pytest.approx(6026)
    assert fx["ct"] == pytest.approx(0.1192)
    assert fx["cp"] == pytest.approx(0.0484)
```

- [ ] **Step 3: Run tests (expect fail)**

Run: `uv run python -m pytest tests/test_bemt_catalog.py -v`  
Expected: FAIL (module missing)

- [ ] **Step 4: Implement `bemt_catalog.py` (loft + CT/CP + loader)**

```python
# fansim/propeller/bemt_catalog.py (slice for Task 1)
from __future__ import annotations
import json
import math
from pathlib import Path
from typing import Any

from fansim.geometry.blade import BladeParams
from fansim.prop_spec import PropSpec, PropShaftMount
from fansim.propeller.bemt import RHO_AIR, analyze
from fansim.propeller.geometry import prop_blade_params
from fansim.propeller.polar import nondim

ROOT = Path(__file__).resolve().parents[2]
UIUC_DIR = ROOT / "validation" / "reference" / "uiuc_propdb"
DEFAULT_UIUC_FIXTURE_ID = "apcsf_9x4.7_static"
BAND_REL_A3 = 0.35
MM_PER_IN = 25.4


def approximate_prop_blade(
    diameter_in: float, pitch_in: float, *, blade_count: int = 2
) -> BladeParams:
    dia_mm = float(diameter_in) * MM_PER_IN
    hub_dia_mm = max(0.15 * dia_mm, 8.0)
    shaft = PropShaftMount(
        shaft_dia_mm=5.0, hub_bore_dia_mm=5.0, hub_dia_mm=hub_dia_mm
    )
    spec = PropSpec(
        name=f"approx_{diameter_in}x{pitch_in}x{blade_count}",
        diameter_in=float(diameter_in),
        pitch_in=float(pitch_in),
        n_blades=int(blade_count),
        shaft=shaft,
        rpm_max=max(10000.0, float(diameter_in) * 2000.0),
    )
    return prop_blade_params(spec)


def bemt_static_ct_cp(
    diameter_in: float,
    pitch_in: float,
    *,
    rpm: float,
    blade_count: int = 2,
    rho: float = RHO_AIR,
) -> dict[str, Any]:
    blade = approximate_prop_blade(diameter_in, pitch_in, blade_count=blade_count)
    perf = analyze(blade, rpm=float(rpm), v_forward=0.0, rho=float(rho))
    d_m = float(diameter_in) * MM_PER_IN / 1000.0
    nd = nondim(
        perf.thrust_n, perf.power_w, rpm=float(rpm), diameter_m=d_m,
        v_inf=0.0, rho=float(rho),
    )
    return {
        "ct": float(nd["CT"]),
        "cp": float(nd["CP"]),
        "thrust_n": float(perf.thrust_n),
        "power_w": float(perf.power_w),
        "rpm": float(rpm),
        "diameter_in": float(diameter_in),
        "pitch_in": float(pitch_in),
        "blade_count": int(blade_count),
        "geometry_match": "approximate",
        "j": 0.0,
        "rho": float(rho),
    }


def load_uiuc_static_fixture(path_or_id: str | Path | None = None) -> dict[str, Any]:
    if path_or_id is None:
        path = UIUC_DIR / f"{DEFAULT_UIUC_FIXTURE_ID}.json"
    else:
        p = Path(path_or_id)
        path = p if p.suffix.lower() == ".json" or p.is_file() else UIUC_DIR / f"{path_or_id}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in ("prop_id", "diameter_in", "pitch_in", "rpm", "ct", "cp"):
        if key not in data or data[key] is None:
            raise ValueError(f"UIUC fixture missing {key}: {path}")
    return data
```

Export from `__init__.py`: `bemt_static_ct_cp`, `load_uiuc_static_fixture`, `approximate_prop_blade`, `BAND_REL_A3`.

Add a short `## UIUC PropDB fixture` note to `validation/reference/README.md` pointing at the JSON + PropDB URL.

- [ ] **Step 5: Run tests (expect pass)**

Run: `uv run python -m pytest tests/test_bemt_catalog.py -v`  
Expected: PASS

- [ ] **Step 6: Commit** (when user asks)

```bash
git add fansim/propeller/bemt_catalog.py fansim/propeller/__init__.py \
  validation/reference/uiuc_propdb/apcsf_9x4.7_static.json \
  validation/reference/README.md tests/test_bemt_catalog.py
git commit -m "feat(prop): approximate BEMT static CT/CP + UIUC fixture loader"
```

---

### Task 2: Compare helper + Q7 quorum (always-on)

**Files:**
- Modify: `fansim/propeller/bemt_catalog.py`
- Modify: `tests/test_bemt_catalog.py`
- Modify: `fansim/propeller/__init__.py`

**Interfaces:**
- Consumes: Task 1 APIs
- Produces:
  - `compare_bemt_to_static_witness(*, diameter_in, pitch_in, rpm, ct_w, cp_w, *, band_rel=BAND_REL_A3, source: str, prop_id: str, blade_count: int = 2) -> dict`
  - `run_bemt_catalog_quorum(*, include_apc: bool = True) -> dict`  
    Returns `{checks: [...], all_pass: bool}`. Q7 always present. Q6 only if `include_apc` and pythrust available; else omit Q6 **or** append `{id:"Q6", pass: None, detail: "pythrust missing"}` — prefer **omit** when unavailable so `all_pass` is not poisoned; CLI documents that.

Compare pass rule: `rel_err_ct <= band_rel` **and** `rel_err_cp <= band_rel`, where  
`rel_err = abs(bemt - witness) / abs(witness)` (witness > 0).

Q7 check dict:

```python
{
  "id": "Q7",
  "pass": bool,
  "detail": str,
  "ct_bemt": float, "cp_bemt": float,
  "ct_w": float, "cp_w": float,
  "rel_err_ct": float, "rel_err_cp": float,
  "band_rel": 0.35,
  "geometry_match": "approximate",
  "source": "uiuc_fixture",
  "prop_id": fx["prop_id"],
  "rpm": float(fx["rpm"]),
}
```

- [ ] **Step 1: Failing Q7 test**

```python
def test_quorum_q7_bemt_vs_uiuc_fixture():
    from fansim.propeller.bemt_catalog import run_bemt_catalog_quorum
    report = run_bemt_catalog_quorum(include_apc=False)
    by_id = {c["id"]: c for c in report["checks"]}
    assert "Q7" in by_id
    assert by_id["Q7"]["pass"] is True
    assert by_id["Q7"]["geometry_match"] == "approximate"
    assert report["all_pass"] is True
```

- [ ] **Step 2: Run (expect fail)**

Run: `uv run python -m pytest tests/test_bemt_catalog.py::test_quorum_q7_bemt_vs_uiuc_fixture -v`  
Expected: FAIL until `run_bemt_catalog_quorum` exists

- [ ] **Step 3: Implement compare + Q7 path**

```python
def compare_bemt_to_static_witness(
    *,
    diameter_in: float,
    pitch_in: float,
    rpm: float,
    ct_w: float,
    cp_w: float,
    band_rel: float = BAND_REL_A3,
    source: str,
    prop_id: str,
    blade_count: int = 2,
) -> dict[str, Any]:
    bemt = bemt_static_ct_cp(
        diameter_in, pitch_in, rpm=rpm, blade_count=blade_count
    )
    ct_b, cp_b = float(bemt["ct"]), float(bemt["cp"])
    ct_w, cp_w = float(ct_w), float(cp_w)
    if ct_w <= 0.0 or cp_w <= 0.0:
        raise ValueError("witness ct/cp must be > 0")
    rel_ct = abs(ct_b - ct_w) / ct_w
    rel_cp = abs(cp_b - cp_w) / cp_w
    ok = rel_ct <= float(band_rel) and rel_cp <= float(band_rel)
    return {
        "pass": ok,
        "ct_bemt": ct_b,
        "cp_bemt": cp_b,
        "ct_w": ct_w,
        "cp_w": cp_w,
        "rel_err_ct": rel_ct,
        "rel_err_cp": rel_cp,
        "band_rel": float(band_rel),
        "geometry_match": "approximate",
        "source": source,
        "prop_id": prop_id,
        "rpm": float(rpm),
        "diameter_in": float(diameter_in),
        "pitch_in": float(pitch_in),
        "detail": (
            f"CT rel_err={rel_ct:.4f} CP rel_err={rel_cp:.4f} "
            f"band={band_rel} ({'PASS' if ok else 'FAIL'})"
        ),
    }


def run_bemt_catalog_quorum(*, include_apc: bool = True) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    fx = load_uiuc_static_fixture()
    q7 = compare_bemt_to_static_witness(
        diameter_in=float(fx["diameter_in"]),
        pitch_in=float(fx["pitch_in"]),
        rpm=float(fx["rpm"]),
        ct_w=float(fx["ct"]),
        cp_w=float(fx["cp"]),
        source="uiuc_fixture",
        prop_id=str(fx["prop_id"]),
        blade_count=int(fx.get("blade_count", 2)),
    )
    checks.append({"id": "Q7", **q7})
    # Q6 filled in Task 3 when include_apc
    if include_apc:
        q6 = _quorum_q6_apc()  # Task 3
        if q6 is not None:
            checks.append(q6)
    all_pass = all(c.get("pass") is True for c in checks)
    return {"checks": checks, "all_pass": all_pass}
```

For Task 2 only: implement Q7; stub `_quorum_q6_apc` as `return None` or gate `include_apc` unused until Task 3.

Export `compare_bemt_to_static_witness`, `run_bemt_catalog_quorum`.

- [ ] **Step 4: Run always-on suite**

Run: `uv run python -m pytest tests/test_bemt_catalog.py -v`  
Expected: PASS  
If Q7 fails outside ±35%, **stop** — update spec honesty + `BAND_REL_A3` with measured deltas (do not tweak loft silently).

- [ ] **Step 5: Commit** (when user asks)

```bash
git add fansim/propeller/bemt_catalog.py fansim/propeller/__init__.py tests/test_bemt_catalog.py
git commit -m "test(prop): A3 Q7 BEMT vs UIUC static CT/CP quorum"
```

---

### Task 3: Q6 BEMT ↔ APC (propulsion-marked)

**Files:**
- Modify: `fansim/propeller/bemt_catalog.py`
- Modify: `tests/test_prop_power_propulsion.py`

**Interfaces:**
- Consumes: `_apc_static_coefficients`, `_load_apc_db`, `pythrust_available` from `fansim.propeller.power` (lazy; import inside `_quorum_q6_apc`)
- Produces: Q6 check in `run_bemt_catalog_quorum(include_apc=True)`

Q6 freeze:

- `prop_id = "APC_9x4.7SF"`
- `rpm_request = 6026.0` → use APC nearest RPM key via `_apc_static_coefficients`
- Compare BEMT at **that catalog RPM** (not necessarily 6026) so witness and BEMT share RPM

- [ ] **Step 1: Failing propulsion test**

```python
# append to tests/test_prop_power_propulsion.py
def test_quorum_q6_bemt_vs_apc():
    from fansim.propeller.bemt_catalog import run_bemt_catalog_quorum
    report = run_bemt_catalog_quorum(include_apc=True)
    by_id = {c["id"]: c for c in report["checks"]}
    assert by_id["Q6"]["pass"] is True
    assert by_id["Q7"]["pass"] is True
    assert report["all_pass"] is True
```

- [ ] **Step 2: Run (expect fail until Q6 wired)**

Run: `uv run --extra propulsion python -m pytest tests/test_prop_power_propulsion.py::test_quorum_q6_bemt_vs_apc -v`  
Expected: FAIL or missing Q6

- [ ] **Step 3: Implement `_quorum_q6_apc`**

```python
def _quorum_q6_apc() -> dict[str, Any] | None:
    from fansim.propeller.power import (
        _apc_static_coefficients,
        _load_apc_db,
        pythrust_available,
    )
    if not pythrust_available():
        return None
    prop_id = "APC_9x4.7SF"
    db = _load_apc_db()
    entry = db.get(prop_id)
    rpm_used, ct_w, cp_w = _apc_static_coefficients(entry, 6026.0)
    meta = entry.metadata
    cmp_ = compare_bemt_to_static_witness(
        diameter_in=float(meta.diameter_in),
        pitch_in=float(meta.pitch_in),
        rpm=float(rpm_used),
        ct_w=float(ct_w),
        cp_w=float(cp_w),
        source="pythrust_apc",
        prop_id=prop_id,
        blade_count=int(getattr(meta, "blade_count", 2) or 2),
    )
    return {"id": "Q6", **cmp_}
```

Wire `include_apc=True` path in `run_bemt_catalog_quorum` to append this check.

- [ ] **Step 4: Run propulsion + always-on**

Run: `uv run --extra propulsion python -m pytest tests/test_prop_power_propulsion.py tests/test_bemt_catalog.py -v`  
Expected: PASS  
If Q6 fails ±35%, stop and update spec band with measured deltas (pre-plan probe vs 9×4.7SF was ~23%/18% — should pass).

- [ ] **Step 5: Commit** (when user asks)

```bash
git add fansim/propeller/bemt_catalog.py tests/test_prop_power_propulsion.py
git commit -m "test(prop): A3 Q6 BEMT vs PyThrust APC static CT/CP"
```

---

### Task 4: CLI quorum merge + bibliography

**Files:**
- Modify: `scripts/evaluate_prop_power.py`
- Modify: `tests/test_prop_power.py` (optional assert help still has quorum)
- Modify: `docs/bibliography.md`

**Interfaces:**
- Consumes: `run_propulsion_quorum`, `run_bemt_catalog_quorum`, `pythrust_available`

CLI `--mode quorum` output shape:

```python
{
  "mode": "quorum",
  "checks": [ ...Q3..Q5..., ...Q6?..., Q7 ],
  "all_pass": bool,
  "propulsion_extra": bool,
}
```

When PyThrust missing: run stage-1 quorum only if possible — actually stage-1 Q3–Q5 need PyThrust. Current CLI already raises `PropulsionExtraMissing` for quorum. **Change:** without extra, still run A3 with `include_apc=False` (Q7 only) and exit 0 if Q7 passes; with extra, concatenate stage-1 + A3 (include_apc=True).

```python
elif args.mode == "quorum":
    from fansim.propeller.bemt_catalog import run_bemt_catalog_quorum
    from fansim.propeller.power import pythrust_available, run_propulsion_quorum
    checks = []
    if pythrust_available():
        checks.extend(run_propulsion_quorum()["checks"])
        a3 = run_bemt_catalog_quorum(include_apc=True)
    else:
        a3 = run_bemt_catalog_quorum(include_apc=False)
    checks.extend(a3["checks"])
    out = {
        "mode": "quorum",
        "checks": checks,
        "all_pass": all(c.get("pass") is True for c in checks),
        "propulsion_extra": bool(pythrust_available()),
    }
```

Do **not** exit 2 when only Q7 is available.

- [ ] **Step 1: Extend CLI + smoke**

Run:

```bash
uv run python scripts/evaluate_prop_power.py --mode quorum
uv run --extra propulsion python scripts/evaluate_prop_power.py --mode quorum
```

Expected: JSON with Q7; with extra also Q3–Q6; `all_pass` true when green.

- [ ] **Step 2: Bibliography**

Update UIUC PropDB bullet in `docs/bibliography.md`: change **→ code (planned)** to  
**→ code:** `fansim/propeller/bemt_catalog.py` (A3 Q7 fixture `validation/reference/uiuc_propdb/apcsf_9x4.7_static.json`; Q6 via PyThrust APC).

- [ ] **Step 3: Commit** (when user asks)

```bash
git add scripts/evaluate_prop_power.py tests/test_prop_power.py docs/bibliography.md
git commit -m "feat(prop): quorum CLI merges A3 Q6/Q7; document UIUC harness"
```

---

## Spec coverage checklist

| Spec requirement | Task |
|------------------|------|
| `approximate_prop_blade` / `bemt_static_ct_cp` | Task 1 |
| UIUC fixture + loader | Task 1 |
| `compare_bemt_to_static_witness` ±35% both CT&CP | Task 2 |
| Q7 always-on | Task 2 |
| Q6 APC via PyThrust | Task 3 |
| CLI concatenates stage-1 + A3 | Task 4 |
| Bib UIUC → code | Task 4 |
| No product overwrite / approximate stamp | Tasks 2–3 |
| 9×4.7 freeze (not 5×4.5) | Global + Tasks 1–3 |

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-21-prop-bemt-uiuc-a3.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — execute tasks in this session with checkpoints  

Which approach?
