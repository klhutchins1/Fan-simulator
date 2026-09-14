# Fan-Simulator Proper-State Program Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.  
> **Scope note:** This is the **master program plan**. Phases 2–6 should be expanded into focused sub-plans (`docs/superpowers/plans/2026-09-14-*.md`) before deep implementation — do not attempt the whole program in one agent session.

**Goal:** Restore Fan-Simulator from “recovered and runnable” to a trustworthy design loop: correct math/physics, complete tests, a Noctua NF-A12x25–faithful reference geometry, honest screening vs absolute tiers, and a printed impeller whose measured CFM/static/noise land near simulation.

**Architecture:** Keep the existing ladder — geometry → manufacturability gates → BEM/BEMT screen → RANS MRF screening CFD → (optional) finer CFD / LBM / FW-H → print + measure. Separate **screening** (optimizer ranking) from **absolute** claims (datasheet / print validation). Reconcile docs to code before adding features.

**Tech Stack:** Python 3.12, CadQuery/OCP, NumPy/SciPy, Optuna, OpenFOAM (Docker), PyVista/Trame, pytest, uv.

## Global Constraints

- North star unchanged: **print a fan and get results similar to simulation** (roadmap §5 / `docs/validation/north-star-staged.md`).
- Never quote screening CFM/Pa/dB as datasheet-grade without GCI + validation stamps.
- Prefer TDD against recovered tests; do not delete failing physics tests to “green” the suite.
- Pin viz stack for cockpit: `pyvista>=0.44,<0.49`, `trame>=3.6,<4` (`pyproject.toml`).
- Windows OCCT teardown `0xC0000374` after green pytest is noise, not a fail.
- Keep `CHAT_RECOVERY/cursor_transcript_extract/` out of product commits (mining artifacts only).
- Commit frequently; push only when asked (this program’s baseline already on `master` @ `3e426fe`).

---

## Current baseline (2026-09-13)

| Layer | State |
|-------|--------|
| Cockpit launch | Works with `uv run --extra viz --extra optim python scripts/cockpit.py --run runs/opt_run1` |
| Recovery tracker | `RECOVERY_TODO.md` — recovery buckets closed |
| Master roadmap | `docs/roadmap.md` — **stale** (header 2026-09-02; missing §8–§11) |
| Stock A12x25 | Parametric approx in `config/problems/a12x25.yaml` — **not** OEM shape |
| Absolute validation | Blocked on commercial hub; staged runbook exists |
| Math review | Spec `docs/superpowers/specs/2026-09-11-math-accuracy-fixes-design.md` — not fully re-audited on recovered tree |

**Keep (core product):** axial geometry + frame/shroud/stator path, system-curve objectives, motor derate, BEM screen, OpenFOAM MRF case builder, cockpit Fan tab, print export + measurement recorder, honesty stamps (`SCREENING_GRID_STAMP`, circular inlet check).

**Keep but deprioritize for north-star:** mixed / volute / CROR / prop / wind (recover green; don’t block A12x25 print loop).

**Park / don’t expand yet:** DES/FW-H absolute noise campaigns, NN/FNO surrogates, wind turbine scaffold — until free-air + shut-off A12x25 band is honest.

---

## Phase map

| Phase | Outcome | Exit gate |
|-------|---------|-----------|
| **0** Baseline & docs | Roadmap/tests inventory matches reality | Fast suite number + reconciled roadmap committed |
| **1** Math/physics audit | §10.1–10.11 applied or consciously deferred | Physics pytest + checklist signed |
| **2** Reference Noctua geometry | Shape/spec fidelity for A12x25 | Visual + metric comparison vs published + STL target |
| **3** Validation CFD | Sim ↔ published band | Free-air / shut-off error report |
| **4** Speed & package health | Faster loop; deps behave | Timing baselines + pin audit |
| **5** Print ↔ measure | North star closed | Measurement JSON + sim-vs-real |
| **6** Product backlog | Only after 3–5 | Stator/sickle/surrogate as ranked work |

---

### Task 0.1: Full fast-suite baseline

**Files:**
- Create: `docs/validation/suite_baseline_2026-09-14.md`
- Modify: none (read-only measure)

**Interfaces:**
- Consumes: pytest markers `not docker and not slow`
- Produces: pass/fail/skip counts and failing nodeids list

- [ ] **Step 1: Run the fast suite and capture summary**

```powershell
uv run --extra optim --extra viz --extra surrogate --extra dev `
  python -m pytest -m "not docker and not slow" -q --tb=no `
  | Tee-Object docs/validation/_suite_raw.txt
```

Expected: a final `N passed, M failed, K skipped` line (interpreter may still exit `0xC0000374`).

- [ ] **Step 2: Write the baseline note**

Create `docs/validation/suite_baseline_2026-09-14.md` with: date, commit SHA, command, counts, failing nodeids, note that OCCT teardown codes are ignored when assertions passed.

- [ ] **Step 3: Commit**

```powershell
git add docs/validation/suite_baseline_2026-09-14.md
git commit -m "Record post-recovery fast-suite baseline counts."
```

---

### Task 0.2: Reconcile `docs/roadmap.md` to the recovered tree

**Files:**
- Modify: `docs/roadmap.md`
- Read: `RECOVERY_TODO.md`, `scripts/_patch_roadmap_11.py`, `docs/superpowers/specs/2026-09-11-math-accuracy-fixes-design.md`, `docs/validation/north-star-staged.md`

**Interfaces:**
- Consumes: feature presence in `fansim/` (stator, sickle, mixed, volute, UIUC polars, motor curve, GCI stamp, cockpit tab-split)
- Produces: updated checkboxes + restored §8–§11 summary + `Last reviewed: 2026-09-14`

- [ ] **Step 1: Inventory “done in code but open on roadmap”**

Mark done (or “stage 1 done”) only when a test or module proves it, including at least:

| Roadmap ID | Evidence to require |
|------------|---------------------|
| 1.6 / 7.2 UIUC polars | `fansim/data/polars/*.csv` + `tests/test_uiuc_polars.py` |
| 2.2 stator stage | `fansim/cfd/stator.py` + `tests/test_stator.py` |
| 2.3/2.6 sickle/notches | `apply_sickle` / `apply_notched_tips` + tests |
| 2.5 motor curve | `fansim/optimize/motor_curve.py` + evaluate stamps |
| 3.2 guided camber/blades | `search_space` GUIDED bounds + tests |
| 3.3 tip-cap | `TIP_CAP_CLEARANCE_MM` + tests |
| 4.1/4.2 mixed/CROR scaffolds | archetype registry + focused suites |
| 10.x / 11.x honesty | `SCREENING_GRID_STAMP`, duct area, BEMT swirl |

- [ ] **Step 2: Patch roadmap header + recommended sequence**

Set last reviewed to **2026-09-14**. Recommended sequence becomes:

1. Math audit (Phase 1)  
2. Noctua reference geometry (Phase 2)  
3. Validation P–Q (Phase 3)  
4. Print + measure (Phase 5)  
5. Only then surrogate / absolute noise / archetype depth  

- [ ] **Step 3: Commit**

```powershell
git add docs/roadmap.md
git commit -m "Reconcile roadmap checkboxes with post-recovery code reality."
```

---

### Task 0.3: Provenance map for high-risk files

**Files:**
- Create: `docs/validation/provenance_risks.md`
- Read: files tagged `# RECONSTRUCTED` / `# --- spliced` (especially `fansim/geometry/blade.py`)

**Interfaces:**
- Produces: risk table (file → trust → verification test)

- [ ] **Step 1: Generate the list**

```powershell
rg -n "RECONSTRUCTED|spliced from transcript|RECOVERED-FROM-CHAT" fansim -g "*.py" `
  | Out-File -Encoding utf8 docs/validation/_provenance_rg.txt
```

- [ ] **Step 2: Rank top 15 risks** with the test that must pass before trusting that file for absolute CFM claims (geometry build, BEM shut-off, tip gap, etc.).

- [ ] **Step 3: Commit**

```powershell
git add docs/validation/provenance_risks.md
git commit -m "Document reconstructed-file provenance risks and verification tests."
```

---

### Task 1.1: Apply / verify math-accuracy §10 checklist

**Files:**
- Read: `docs/superpowers/specs/2026-09-11-math-accuracy-fixes-design.md`
- Modify (as needed): `fansim/acoustics/fwh.py`, `fansim/acoustics/loading.py`, `fansim/fan_bem.py`, `fansim/propeller/bemt.py`, `fansim/optimize/system_curve.py`, `fansim/cfd/metrics.py`, `fansim/structural/stress.py`, `fansim/optimize/objectives.py`
- Test: `tests/test_bemt.py`, `tests/test_fan_bem.py`, `tests/test_acoustics*.py`, `tests/test_duct_area.py`, `tests/test_deflection.py`

**Interfaces:**
- Consumes: checklist IDs 10.1–10.11
- Produces: `docs/validation/math_audit_2026-09-14.md` with PASS / FIXED / DEFERRED per ID

- [ ] **Step 1: Write failing or characterizing tests for any unchecked ID**

Example — BEMT swirl (10.4) must stay propeller-signed:

```python
# tests/test_bemt.py (characterization if not present)
def test_bemt_relative_tangential_uses_propeller_sign():
    # Vt = Omega*r*(1 - a'); a' > 0 reduces relative swirl speed
    ...
```

- [ ] **Step 2: For each CONFIRMED bug, either fix or document DEFERRED with reason**

Priority order from the accepted spec:

1. 10.4 BEMT `a′` / `Vt` sign (must be fixed)  
2. 10.2 delete extra `½ρW³cB Cd` shaft power if still present  
3. 10.3 ducted fan BEM: gap leakage only (no Prandtl)  
4. 10.5 analytic polar: `cd = cd0` only  
5. 10.6 / 10.9 Re table + ρ / `CFM_PER_M3S` single source  
6. 10.1 FWH / Curle kernels  
7. 10.7–10.11 shutoff, GCI stamp, inlet area, FDM E knockdown  

- [ ] **Step 3: Run physics-focused pytest**

```powershell
uv run pytest tests/test_bemt.py tests/test_fan_bem.py tests/test_duct_area.py `
  tests/test_system_curve.py -q --tb=short
```

Expected: all PASS (ignore OCCT exit).

- [ ] **Step 4: Commit**

```powershell
git add fansim docs/validation/math_audit_2026-09-14.md tests
git commit -m "Complete §10 math audit on recovered tree; stamp PASS/FIXED/DEFERRED."
```

---

### Task 1.2: Honesty contract tests (screening vs absolute)

**Files:**
- Create: `tests/test_honesty_stamps.py`
- Modify: `fansim/optimize/objectives.py` (if axial evaluate missing stamp/inlet check)

**Interfaces:**
- Consumes: `SCREENING_GRID_STAMP`
- Produces: guaranteed `raw["grid_converged"] is False` on screening evaluates

- [ ] **Step 1: Failing test**

```python
from fansim.optimize.objectives import SCREENING_GRID_STAMP

def test_screening_grid_stamp_is_not_converged():
    assert SCREENING_GRID_STAMP["grid_converged"] is False
    assert "GCI" in SCREENING_GRID_STAMP["grid_note"]
```

- [ ] **Step 2: Ensure axial / mixed / CROR / volute evaluate paths include the stamp** (volute must **not** call `require_circular_inlet_area`).

- [ ] **Step 3: Commit**

```powershell
git add tests/test_honesty_stamps.py fansim/optimize/objectives.py
git commit -m "Lock screening GCI honesty stamps with regression tests."
```

---

### Task 2.1: Define Noctua reference acceptance metrics

**Files:**
- Modify: `docs/a12x25-reference.md`
- Create: `docs/validation/a12x25_geometry_acceptance.md`

**Interfaces:**
- Consumes: published 60.1 CFM / 22.9 Pa / 22.6 dB(A) / 2000 RPM / 0.5 mm tip / 7 blades
- Produces: geometry gates separate from CFD gates

- [ ] **Step 1: Document two error budgets**

1. **Geometry fidelity** (vs real impeller / trusted STL): tip radius, hub radius, blade count, axial depth, leading-edge sickle character, tip clearance to frame ID.  
2. **CFD fidelity** (vs published): free-air CFM within ±X%, shut-off Pa within ±Y Pa — X/Y chosen after Task 3.1 mesh study; interim targets: free-air within **10%**, shut-off within **5 Pa**, then tighten.

- [ ] **Step 2: Commit**

```powershell
git add docs/a12x25-reference.md docs/validation/a12x25_geometry_acceptance.md
git commit -m "Define A12x25 geometry vs CFD acceptance budgets."
```

---

### Task 2.2: Obtain / fit reference geometry (actual spec & shape)

**Files:**
- Create or update: `config/problems/a12x25_reference.yaml` (or STL under `validation/reference/`)
- Modify: `fansim/optimize/search_space.py` (`STOCK_GEOMETRY_YAML` entry)
- Modify: `fansim/geometry/config.py` load path as needed
- Test: `tests/test_a12x25_reference_geometry.py` (new)

**Interfaces:**
- Consumes: Thingiverse remix / reverse-engineered stations / scanned outline (user-supplied asset)
- Produces: `stock_blade_flat("a12x25")` returns reference recipe used by cockpit “Stock”

**Procedure:**

- [ ] **Step 1: Choose one primary reference asset** (in priority order):

1. Watertight A12x25 STL (preferred for CFD truth) stored at `validation/reference/a12x25_impeller.stl`  
2. Else multi-station yaml fit that matches planform photos + published envelope  

Do **not** silently treat current `config/problems/a12x25.yaml` as OEM truth — keep it labeled `approximate`.

- [ ] **Step 2: Failing geometry tests**

```python
def test_reference_blade_count_and_envelope():
    from fansim.optimize.search_space import stock_blade_flat
    flat = stock_blade_flat("a12x25")
    assert flat["n_blades"] == 7
    assert 55.0 <= flat["tip_radius"] <= 57.0
    assert 20.0 <= flat["hub_radius"] <= 23.0
```

Add silhouette / solidity checks once STL exists (`trimesh` section area or projected area within band).

- [ ] **Step 3: Wire cockpit stock loader** to the reference recipe; keep approximate yaml available as `a12x25_approx` if needed for regression continuity.

- [ ] **Step 4: Commit**

```powershell
git add config/problems validation/reference fansim/optimize/search_space.py tests/test_a12x25_reference_geometry.py
git commit -m "Add A12x25 reference geometry asset and stock loader wiring."
```

---

### Task 3.1: Validation CFD campaign (published P–Q)

**Files:**
- Create: `scripts/run_a12x25_validation.py`
- Create: `docs/validation/a12x25_pq_report.md`
- Use: `fansim/optimize/objectives.py`, `fansim/cfd/*`, Docker OpenFOAM image

**Interfaces:**
- Consumes: reference geometry + `FanSpec` A12X25
- Produces: free-air CFM, shut-off/proxy Pa, mesh cell count, GCI note

- [ ] **Step 1: Mesh ladder (coarse→medium→fine)** at free delivery; record CFM; run `fansim.analyze.grid_convergence` if three meshes available.

- [ ] **Step 2: Full or multi-point P–Q** at 2000 RPM; compare to 60.1 CFM and 22.9 Pa (`docs/a12x25-reference.md`).

- [ ] **Step 3: Write report** separating geometry error vs model error; list next physics lever (tip gap resolution, frame/struts, wall roughness, transition).

- [ ] **Step 4: Commit report + script** (not huge case dumps).

```powershell
git add scripts/run_a12x25_validation.py docs/validation/a12x25_pq_report.md
git commit -m "Add A12x25 validation runner and first P-Q comparison report."
```

---

### Task 4.1: Dependency & peer-repo audit

**Files:**
- Create: `docs/validation/dependency_peer_audit.md`
- Modify: `pyproject.toml` / `uv.lock` only when pins are justified

**Packages to audit (usage vs upstream expectations):**

| Package | What “works as expected” means here |
|---------|-------------------------------------|
| CadQuery / OCP | Loft/boolean watertight; no silent hollows |
| OpenFOAM 2406 image | `simpleFoam` + MRF + snappy templates match ESI docs |
| Optuna | NSGA-II multi-objective; prune ≠ fake (0,0) |
| PyVista / Trame / trame-vtk | Cockpit plotter survives `server.start` (compat patch documented) |
| trimesh | STL metrics volume/watertight agree with CadQuery export |
| SciPy | PCHIP / integrate used only where continuous |

- [ ] **Step 1: For each package, note version pinned, one smoke test, one known footgun** (e.g. Trame protocol-before-start).

- [ ] **Step 2: Skim 1–2 public repos** per critical stack (OpenFOAM MRF fan tutorials; CCBlade/QProp for BEMT sign; Optuna multi-obj examples) and record “we match / we differ” in the audit doc.

- [ ] **Step 3: Commit**

```powershell
git add docs/validation/dependency_peer_audit.md pyproject.toml uv.lock
git commit -m "Document dependency peer audit and justified pins."
```

---

### Task 4.2: Performance baselines and speedups

**Files:**
- Create: `docs/validation/perf_baseline.md`
- Likely touch: `fansim/optimize/study.py`, `fansim/fan_bem.py`, `fansim/surrogate/*`, `fansim/geometry/isolated.py`, cockpit Assess isolation

**Hotspots (measure before changing):**

1. CadQuery impeller build (preview + evaluate)  
2. snappyHexMesh + simpleFoam wall time  
3. Optuna trial overhead / surrogate miss rate  
4. Cockpit VTK refresh  

- [ ] **Step 1: Time one preview build and one BEM screen**

```powershell
uv run python -c "import time; from fansim.optimize.search_space import stock_blade_flat, blade_from_flat; from fansim.geometry import build_impeller; p=blade_from_flat(stock_blade_flat()); t=time.perf_counter(); build_impeller(p); print('build_s', time.perf_counter()-t)"
```

- [ ] **Step 2: Rank speedups that preserve physics**

Allowed: BEM/GP floors, mesh coarsening for screen only, isolated workers, caching polars, avoiding double mesh on Assess cancel paths.  
Forbidden as “speedup”: deleting frame/tip-gap, slip walls for absolute claims, skipping shut-off checks.

- [ ] **Step 3: Implement only the top 1–2 wins with before/after timings in `perf_baseline.md`.**

- [ ] **Step 4: Commit**

```powershell
git add docs/validation/perf_baseline.md fansim
git commit -m "Add perf baselines and first screening-path speedups."
```

---

### Task 5.1: Print → measure → calibrate (north star)

**Files:**
- Follow: `docs/validation/north-star-staged.md`
- Use: cockpit measurement fields → `validation/measurements/`
- Modify: calibration hooks once one point exists

**Interfaces:**
- Consumes: print-ready STL + commercial A12x25 hub/frame
- Produces: measurement JSON + sim-vs-real delta table

- [ ] **Step 1: Export print-ready reference (or best fitting Assess design)** with motor cup checked against real motor.

- [ ] **Step 2: Print, mount on commercial hub, measure** at least CFM + static (noise/weight/RPM strongly preferred).

- [ ] **Step 3: Save measurement in cockpit; confirm file under `validation/measurements/`.**

- [ ] **Step 4: Run §5.2 calibration** (document scale factors or model fixes — prefer physics fixes over silent fudge).

- [ ] **Step 5: Mark roadmap §5.1 only when a real measurement exists.**

---

### Task 6.1: Product keep/cut board (after Phases 1–3)

**Files:**
- Create: `docs/validation/keep_cut_board.md`

| Item | Default decision until north star moves |
|------|----------------------------------------|
| Axial Fan cockpit + CFD | **KEEP — primary** |
| BEM screen + system curve | **KEEP** |
| Stator / sickle / notches | **KEEP** (stage-1), deepen only if validation needs |
| Mixed / volute / CROR / prop | **KEEP scaffolds**, schedule after A12x25 band |
| Surrogate GP/NN | **KEEP code**, retrain only on load-honest catalog |
| Wind turbine | **PARK** |
| Absolute FW-H / DES | **PARK** until RANS free-air/shut-off trusted |
| Chat recovery extracts | **DON’T SHIP** |

---

## Test strategy (program-wide)

1. **Fast gate (every PR):** `pytest -m "not docker and not slow"`.  
2. **Physics gate:** BEM/BEMT/system-curve/duct/honesty tests.  
3. **Geometry gate:** watertight + A12x25 envelope tests.  
4. **Docker gate (nightly / pre-validation):** mesh+solve smoke on stock case.  
5. **Hardware gate:** one measurement closes absolute claims.

Missing tests to add as gaps appear in Task 0.1 fail list — each fail becomes a Task 0.x/1.x ticket, not a silent skip.

---

## Suggested sub-plans (spawn when starting that phase)

- `docs/superpowers/plans/2026-09-14-math-audit.md` ← Phase 1  
- `docs/superpowers/plans/2026-09-14-a12x25-reference-geometry.md` ← Phase 2  
- `docs/superpowers/plans/2026-09-14-a12x25-validation-cfd.md` ← Phase 3  
- `docs/superpowers/plans/2026-09-14-perf-and-deps.md` ← Phase 4  
- `docs/superpowers/plans/2026-09-14-print-measure-calibrate.md` ← Phase 5  

---

## Self-review (coverage)

| User requirement | Covered by |
|------------------|------------|
| Proper state / re-evaluate plans | Phase 0 |
| Reference Noctua to actual spec/shape | Phase 2 |
| All tests built out | Tasks 0.1, 1.2, 2.2 + test strategy |
| Math/physics correct & used properly | Phase 1 + honesty stamps |
| Peer repos / packages work as expected | Task 4.1 |
| Inefficiencies / speedups | Task 4.2 |
| Keep vs other operations | Task 6.1 + Keep/Park lists |
| Print ≈ simulation north star | Phase 5 + Global Constraints |
