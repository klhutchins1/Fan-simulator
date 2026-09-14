# NF-A12x25 reference P–Q validation report

**Status:** First reduced campaign recorded (Task 3.2). **CFD interim gate: fail** on free-air; shut-off is an extrapolated proxy only.

**Runner:** `scripts/run_a12x25_validation.py` with `--params config/problems/a12x25_reference.yaml` (cockpit Stock / Phase 2 reference recipe).

**Published reference:** [a12x25-reference.md](../a12x25-reference.md) — 60.1 CFM free-air @ 0 Pa, 22.9 Pa shut-off @ 2000 RPM.

**Campaign artifact (local, not in git):** `runs/validate_a12x25_phase3/validation.json`, `validation.png`. Committed summary: [a12x25_phase3_validation_summary.json](a12x25_phase3_validation_summary.json).

---

## 1. Geometry recipe provenance

| Item | Value |
|------|--------|
| Parametric recipe | `config/problems/a12x25_reference.yaml` |
| Blade count (published) | 7 |
| Tip clearance target | 0.5 mm (published) |
| Geometry acceptance doc | [a12x25_geometry_acceptance.md](a12x25_geometry_acceptance.md) |

Geometry pass/fail is **independent** of CFD pass/fail (see geometry acceptance doc). This report focuses on solver P–Q vs published numbers for the reference stock shape.

**Geometry budget (Task 2.2):** Envelope pytest (`tests/test_a12x25_reference_geometry.py`) passes blade count, tip **55–57 mm**, and hub **20–23 mm** for the reference loader. Treat as **geometry envelope pass** for the parametric recipe — not OEM CAD equivalence (see yaml `reference-parametric` provenance).

---

## 2. Mesh and discretization note

| Setting | Task 3.2 value |
|---------|----------------|
| P–Q sweep `base_cell` [m] | **0.006** (single screening size) |
| Optional free-air `--mesh-ladder` | **Not run** — one affordable cell size for the full back-pressure sweep |
| Solver iterations per point | **800** |
| MPI processes | **8** |
| Wall time (campaign) | **~466 s** |
| Cell counts (checkMesh) | Not stamped in `validation.json` for this run |
| GCI / grid-converged claim | **Not computed** — no three-point ladder; **not grid-converged** |

**Honesty stamp:** This is a **single-mesh screening sweep**. Interim CFM/Pa numbers must not be read as mesh-independent until a free-air ladder and Roache GCI (or equivalent) are documented (runner `validation.json` → `gci` when present).

---

## 3. Free-air vs published (60.1 CFM)

| Metric | Published | Simulated | Error | Interim band (±10%) | Interim pass? |
|--------|-----------|-----------|-------|---------------------|---------------|
| Free-air Q [CFM] @ 0 Pa | 60.1 | **40.94** | **−31.9%** (−19.2 CFM) | **54.1–66.1 CFM** | **No** |

Simulated point: **0 Pa** back-pressure, **converged** (flow drift **1.0%**).

Interim CFD acceptance from [a12x25_geometry_acceptance.md](a12x25_geometry_acceptance.md): free-air within **±10%** of 60.1 CFM until a mesh/physics study tightens X/Y. At **0.68×** published flow, this run **misses the interim band by a wide margin**.

---

## 4. Shut-off / stall proxy vs published (22.9 Pa)

Direct zero-flow shut-off was **not** converged in this sweep. The **20 Pa** point stalled (**−2.37 CFM**, **unconverged**, **46.7%** flow drift).

### 4.1 Multi-point P–Q (medium cell)

| Back-pressure [Pa] | Simulated Q [CFM] | Converged | Flow drift [%] |
|--------------------|-------------------|-----------|----------------|
| 0 | 40.94 | yes | 1.0 |
| 5 | 24.86 | yes | 0.5 |
| 10 | 13.10 | yes | 0.3 |
| 15 | 6.64 | yes | 0.6 |
| 20 | −2.37 | **no** | 46.7 |

### 4.2 Shut-off ΔP proxy (Q → 0 extrapolation)

**Method:** Linear extrapolation of static pressure vs flow using the last **two converged** points on the loading branch (**10 Pa / 13.10 CFM** and **15 Pa / 6.64 CFM**) to estimate ΔP at **Q = 0**.

| Metric | Published | Simulated (proxy) | Error | Interim band (±5 Pa) | Interim pass? |
|--------|-----------|-------------------|-------|----------------------|---------------|
| Shut-off ΔP [Pa] | 22.9 | **~20.1** | **−2.8 Pa** (~−12%) | **17.9–27.9 Pa** | **Yes (proxy only)** |

**Caveats:** Proxy depends on linear fit near stall; **20 Pa** did not converge; a dedicated near–zero-flow solve or finer mesh may move this intercept. Do **not** treat shut-off as validated at the same confidence as free-air until the stall branch is resolved.

---

## 5. Geometry error vs model / idealization error

| Source | What it affects | Task 3.2 assessment |
|--------|-----------------|---------------------|
| **Geometry error** | Envelope vs OEM (blade count, tip/hub, sickle, clearance) | **Envelope pass** (pytest bands); recipe remains **reference-parametric**, not watertight OEM STL. Sickle/depth are qualitative acceptance items — not fully automated. |
| **Model error** | MRF, walls, tip-gap resolution, frame/struts omitted, B.C. idealization, **coarse single mesh** | **Likely dominant** for the **−32%** free-air gap: screening mesh, open-duct idealization, and MRF stack are prioritized levers before blaming envelope numerics alone. |

**Independence table (this run):**

| Geometry envelope | CFD interim (free-air + shut-off proxy) | Interpretation |
|-------------------|----------------------------------------|----------------|
| Pass | **Fail** (free-air); shut-off proxy in band | Shape bands OK; **do not** claim absolute stock P–Q match — fix mesh ladder and physics idealizations first ([acceptance doc §3](a12x25_geometry_acceptance.md)). |

Do **not** merge geometry and CFD budgets into a single “validation passed” flag.

---

## 6. Next physics levers (after first numbers)

1. **Free-air mesh ladder** (`--mesh-ladder`) before tightening absolute CFM claims; compute GCI when three ladder CFMs exist.  
2. Tip-gap and wall treatment vs **0.5 mm** published clearance at **0.006 m** base cell.  
3. Frame / strut blockage vs open-duct idealization (explains part of low Q).  
4. Near–shut-off numerics: smaller back-pressure steps or longer iterations past **15 Pa**; avoid trusting extrapolation once **20 Pa** diverges.  
5. Prism layers / y+ (future; not default in screening).  

---

## Artifacts (Task 3.2)

| File | Purpose |
|------|---------|
| `runs/validate_a12x25_phase3/validation.json` | Full P–Q rows (local run tree) |
| `runs/validate_a12x25_phase3/validation.png` | P–Q plot vs published points |
| `docs/validation/a12x25_phase3_validation_summary.json` | Same numeric payload as JSON above, for docs/git |
