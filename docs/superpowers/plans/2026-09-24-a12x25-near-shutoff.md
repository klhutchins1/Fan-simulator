# Dense near-shut-off P–Q Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Densify A12x25 near-stall P–Q on Stock + close-ref STL, stamp honest shut-off from converged rows, update the validation report.

**Architecture:** Reuse `scripts/run_a12x25_validation.py` pressure sweep. Add a pure helper that maps `pq_rows` → shut-off report (`fansim.analyze.fan_curve` + converged filter). CLI `--near-shutoff` preset. Docker campaigns write local `runs/`; committed JSON summaries + report §12.

**Tech Stack:** Python 3.12, existing OpenFOAM Docker runner, pytest (no Docker in unit tests).

---

### Task 1: Shut-off report helper from pq_rows

**Files:**
- Create: `fansim/validation/pq_shutoff.py`
- Test: `tests/test_pq_shutoff.py`
- Modify: (none yet)

**Interfaces:**
- Consumes: `fansim.analyze.fan_curve.shut_off_pa`
- Produces: `shutoff_report_from_pq_rows(pq_rows, *, published_pa=22.9, q_near_zero=5.0, interim_tol_pa=5.0) -> dict`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pq_shutoff.py
from fansim.validation.pq_shutoff import shutoff_report_from_pq_rows

def test_uses_honest_shut_off_when_near_zero():
    rows = [
        {"back_pa": 10.0, "cfm": 8.0, "converged": True},
        {"back_pa": 20.0, "cfm": 2.0, "converged": True},
        {"back_pa": 22.0, "cfm": 0.5, "converged": False},
    ]
    r = shutoff_report_from_pq_rows(rows, published_pa=22.9)
    assert r["n_converged"] == 2
    assert r["lowest_converged_cfm"] == 2.0
    assert r["method"].startswith("shut_off_pa")
    assert r["shutoff_pa"] is not None
    assert r["interim_pass"] in (True, False)

def test_falls_back_to_last_two_proxy_when_far_from_zero():
    rows = [
        {"back_pa": 14.0, "cfm": 11.4, "converged": True},
        {"back_pa": 16.0, "cfm": 9.1, "converged": True},
        {"back_pa": 18.0, "cfm": 6.7, "converged": False},
    ]
    r = shutoff_report_from_pq_rows(rows, published_pa=22.9, q_near_zero=5.0)
    assert r["method"].startswith("last_two_converged")
    assert abs(r["shutoff_pa"] - 23.97) < 0.2
    assert "proxy" in r["note"].lower()

def test_ignores_unconverged_only():
    assert shutoff_report_from_pq_rows(
        [{"back_pa": 18.0, "cfm": 1.0, "converged": False}],
    )["shutoff_pa"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_pq_shutoff.py -q --tb=line`  
Expected: FAIL (module missing)

- [ ] **Step 3: Write minimal implementation**

```python
# fansim/validation/pq_shutoff.py
from __future__ import annotations

from fansim.analyze.fan_curve import shut_off_pa

PUB_SHUTOFF_PA = 22.9


def shutoff_report_from_pq_rows(
    pq_rows: list[dict],
    *,
    published_pa: float = PUB_SHUTOFF_PA,
    q_near_zero: float = 5.0,
    interim_tol_pa: float = 5.0,
) -> dict:
    conv = [r for r in pq_rows if r.get("converged")]
    if len(conv) < 2:
        return {
            "method": "insufficient_converged",
            "shutoff_pa": None,
            "published_pa": float(published_pa),
            "error_pa": None,
            "interim_band_pa": [published_pa - interim_tol_pa, published_pa + interim_tol_pa],
            "interim_pass": False,
            "n_converged": len(conv),
            "lowest_converged_cfm": None,
            "note": "Need ≥2 converged P–Q points for shut-off",
        }
    points = [
        {"cfm": float(r["cfm"]), "static_pa": float(r["back_pa"])}
        for r in conv
    ]
    lowest = min(p["cfm"] for p in points)
    honest = shut_off_pa(points, q_near_zero=q_near_zero)
    if honest is not None:
        so = float(honest)
        method = f"shut_off_pa (q_near_zero={q_near_zero:g}; lowest converged CFM={lowest:.2f})"
        note = "Converged near-zero branch — preferred over last-two proxy"
    else:
        pts = sorted(points, key=lambda p: p["cfm"])
        a, b = pts[0], pts[1]
        q1, p1 = a["cfm"], a["static_pa"]
        q2, p2 = b["cfm"], b["static_pa"]
        so = p1 + (p2 - p1) / (q2 - q1) * (0.0 - q1) if q2 != q1 else p1
        method = (
            f"last_two_converged proxy "
            f"({p1:g} Pa / {q1:.2f} CFM, {p2:g} Pa / {q2:.2f} CFM)"
        )
        note = (
            f"Lowest converged CFM {lowest:.2f} > q_near_zero={q_near_zero:g}; "
            "proxy only — not a converged Q=0 solve"
        )
    err = so - float(published_pa)
    lo, hi = published_pa - interim_tol_pa, published_pa + interim_tol_pa
    return {
        "method": method,
        "shutoff_pa": round(so, 2),
        "published_pa": float(published_pa),
        "error_pa": round(err, 2),
        "interim_band_pa": [lo, hi],
        "interim_pass": lo <= so <= hi,
        "n_converged": len(conv),
        "lowest_converged_cfm": round(lowest, 2),
        "note": note,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/test_pq_shutoff.py -q --tb=line`  
Expected: PASS (Windows non-zero exit after green is OK)

- [ ] **Step 5: Commit**

```bash
git add fansim/validation/pq_shutoff.py tests/test_pq_shutoff.py
git commit -m "feat(validation): shut-off report from converged P–Q rows"
```

---

### Task 2: Wire helper into validation runner + `--near-shutoff`

**Files:**
- Modify: `scripts/run_a12x25_validation.py`
- Test: extend `tests/test_pq_shutoff.py` or add `tests/test_a12x25_validation_shutoff.py` importing the helper path used by the script (prefer testing `write_outputs` payload via a thin extract if needed — at minimum assert CLI default backs for the flag)

**Interfaces:**
- Consumes: `shutoff_report_from_pq_rows`
- Produces: `validation.json["shutoff"]`; `--near-shutoff` sets backs + iters

- [ ] **Step 1: Add CLI flag**

In `build_parser()`:

```python
ap.add_argument(
    "--near-shutoff",
    action="store_true",
    help="dense near-stall backs (0..26 Pa) and iters=1200 for §1.5 Q→0 campaign",
)
```

In `main`, after parse:

```python
if args.near_shutoff:
    if args.backs == "0,5,10,15,20":  # argparse default
        args.backs = "0,5,10,12,14,15,16,17,18,20,22,24,26"
    if args.iters == 1000:
        args.iters = 1200
```

- [ ] **Step 2: Stamp shutoff in `write_outputs`**

```python
from fansim.validation.pq_shutoff import shutoff_report_from_pq_rows

# inside write_outputs, after building payload:
if pq_rows:
    payload["shutoff"] = shutoff_report_from_pq_rows(pq_rows)
```

Print a one-line summary after write.

- [ ] **Step 3: Unit test CLI preset without Docker**

```python
def test_near_shutoff_preset_backs():
    from scripts import run_a12x25_validation as m
    # or: parse known args
    ap = m.build_parser()
    ns = ap.parse_args(["--near-shutoff"])
    # apply same override logic extracted to apply_near_shutoff_defaults(ns)
    m.apply_near_shutoff_defaults(ns)
    assert ns.backs.startswith("0,5,10,12")
    assert ns.iters == 1200
```

Extract `apply_near_shutoff_defaults(args) -> None` so the test does not need Docker.

- [ ] **Step 4: Run tests**

Run: `uv run python -m pytest tests/test_pq_shutoff.py -q --tb=line`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/run_a12x25_validation.py tests/test_pq_shutoff.py
git commit -m "feat(validation): --near-shutoff preset and shutoff stamp on validation.json"
```

---

### Task 3: Run Stock + STL Docker campaigns

**Files:**
- Create (local): `runs/validate_a12x25_near_shutoff_stock/`, `runs/validate_a12x25_near_shutoff_stl/`
- Create (git): `docs/validation/a12x25_near_shutoff_stock_summary.json`, `docs/validation/a12x25_near_shutoff_stl_summary.json`

**Interfaces:**
- Consumes: runner CLI
- Produces: committed summaries with `campaign`, `pq_rows`, `shutoff`, `published`

- [ ] **Step 1: Stock campaign**

```bash
uv run python scripts/run_a12x25_validation.py --near-shutoff --base-cell 0.006 --procs 8 \
  --out runs/validate_a12x25_near_shutoff_stock
```

Expected: 13 back-pressure solves; `validation.json` has `shutoff`.

- [ ] **Step 2: STL campaign**

```bash
uv run python scripts/run_a12x25_validation.py --near-shutoff --stl --base-cell 0.006 --procs 8 \
  --out runs/validate_a12x25_near_shutoff_stl
```

- [ ] **Step 3: Write committed summaries**

Copy `published`, `pq_rows`, `shutoff`, plus a `campaign` block (kind, tip_gap, base_cell, backs, iters, procs, local_run_dir) into the two JSON files under `docs/validation/`.

- [ ] **Step 4: Commit summaries**

```bash
git add docs/validation/a12x25_near_shutoff_stock_summary.json \
        docs/validation/a12x25_near_shutoff_stl_summary.json
git commit -m "docs(validation): near-shutoff Stock+STL campaign summaries"
```

---

### Task 4: Report + roadmap

**Files:**
- Modify: `docs/validation/a12x25_pq_report.md`
- Modify: `docs/roadmap.md` (§1.5)
- Modify: `docs/superpowers/specs/2026-09-24-a12x25-near-shutoff-design.md` (status → implemented)

- [ ] **Step 1: Add report §12** with both tables, shutoff method, interim pass/fail, free-air note.

- [ ] **Step 2: Update roadmap §1.5** with date + pointer to §12; leave unchecked if free-air still fail / shut-off still proxy-only; check a sub-bullet for the dense campaign if useful.

- [ ] **Step 3: Commit + push master**

```bash
git add docs/validation/a12x25_pq_report.md docs/roadmap.md \
        docs/superpowers/specs/2026-09-24-a12x25-near-shutoff-design.md
git commit -m "docs: record A12x25 dense near-shutoff campaign (§1.5)"
git push origin master
```

---

## Spec coverage

| Spec item | Task |
|-----------|------|
| Helper + converged-only shut-off | 1 |
| `--near-shutoff` + stamp | 2 |
| Stock + STL runs + summaries | 3 |
| Report + roadmap | 4 |
| No blocked outlet / LBM | (explicit non-goal) |
