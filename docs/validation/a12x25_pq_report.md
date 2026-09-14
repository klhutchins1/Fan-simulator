# NF-A12x25 reference P–Q validation report

**Status:** Scaffold (Task 3.1). Numeric results **TBD** until Task 3.2 runs the reduced CFD campaign.

**Runner:** `scripts/run_a12x25_validation.py` with default `--params config/problems/a12x25_reference.yaml` (cockpit Stock / Phase 2 reference recipe).

**Published reference:** [a12x25-reference.md](../a12x25-reference.md) — 60.1 CFM free-air @ 0 Pa, 22.9 Pa shut-off @ 2000 RPM.

---

## 1. Geometry recipe provenance

| Item | Value |
|------|--------|
| Parametric recipe | `config/problems/a12x25_reference.yaml` |
| Blade count (published) | 7 |
| Tip clearance target | 0.5 mm (published) |
| Geometry acceptance doc | [a12x25_geometry_acceptance.md](a12x25_geometry_acceptance.md) |

Geometry pass/fail is **independent** of CFD pass/fail (see geometry acceptance doc). This report focuses on solver P–Q vs published numbers for the reference stock shape.

---

## 2. Mesh and discretization note

| Setting | Task 3.2 value |
|---------|----------------|
| P–Q sweep `base_cell` [m] | TBD |
| Optional free-air `--mesh-ladder` | TBD |
| Cell counts (checkMesh) | TBD |
| GCI / grid-converged claim | **Not claimed** until Roache GCI is computed on three ladder points and documented here |

**Honesty stamp:** Interim screening meshes are **not** grid-converged unless this section records computed GCI with asymptotic-range check (see runner `validation.json` → `gci` when present).

---

## 3. Free-air vs published (60.1 CFM)

| Metric | Published | Simulated | Error | Interim band (±10%) |
|--------|-----------|-----------|-------|---------------------|
| Free-air Q [CFM] @ 0 Pa | 60.1 | TBD | TBD | 54.1–66.1 CFM |

Interim CFD acceptance band from [a12x25_geometry_acceptance.md](a12x25_geometry_acceptance.md): free-air within **±10%** of 60.1 CFM until a mesh/physics study tightens X/Y.

---

## 4. Shut-off / stall proxy vs published (22.9 Pa)

| Metric | Published | Simulated (proxy) | Error | Interim band (±5 Pa) |
|--------|-----------|-------------------|-------|----------------------|
| Shut-off ΔP [Pa] | 22.9 | TBD | TBD | 17.9–27.9 Pa |

Near shut-off points may be **unconverged** (deep stall); report the stable-branch intercept or highest back-pressure converged point and label the proxy clearly in Task 3.2.

---

## 5. Geometry error vs model / idealization error

| Source | What it affects | Task 3.2 assessment |
|--------|-----------------|---------------------|
| **Geometry error** | Envelope vs OEM (blade count, tip/hub, sickle, clearance) | TBD — cite geometry acceptance outcome |
| **Model error** | MRF, walls, tip gap resolution, frame/struts omitted, B.C. idealization | TBD — prioritize levers after P–Q gap is measured |

Do **not** merge geometry and CFD budgets into a single “validation passed” flag.

---

## 6. Next physics levers (after first numbers)

1. Tip-gap and wall treatment vs 0.5 mm published clearance  
2. Frame / strut blockage vs open-duct idealization  
3. Mesh ladder refinement at free-air before tightening absolute CFM claims  
4. Prism layers / y+ (future; not default in screening)  

---

## Artifacts (Task 3.2)

| File | Purpose |
|------|---------|
| `runs/validate_a12x25_phase3/validation.json` | P–Q rows, optional ladder + GCI stamp |
| `runs/validate_a12x25_phase3/validation.png` | P–Q plot vs published points |
