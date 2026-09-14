# NF-A12x25 reference P–Q validation report

**Status:** Task 3.2 screening + mesh/tip + frame/wall_ks campaigns recorded. **CFD interim gate: fail** on free-air (still outside ±10% of 60.1 CFM). Shut-off remains an extrapolated proxy from the Phase 3.2 P–Q only.

**Published reference:** [a12x25-reference.md](../a12x25-reference.md) — 60.1 CFM free-air @ 0 Pa, 22.9 Pa shut-off @ 2000 RPM.

**Campaign artifacts (local, not in git):**
- Phase 3.2 P–Q: `runs/validate_a12x25_phase3/` → [a12x25_phase3_validation_summary.json](a12x25_phase3_validation_summary.json)
- Mesh ladder + tip A/B: `runs/validate_a12x25_mesh_tip/` → [a12x25_mesh_tip_validation_summary.json](a12x25_mesh_tip_validation_summary.json)
- Frame / wall_ks A/B: `runs/validate_a12x25_physics/` → [a12x25_physics_validation_summary.json](a12x25_physics_validation_summary.json)

**Runner:** `scripts/run_a12x25_validation.py` with `--params config/problems/a12x25_reference.yaml` (cockpit Stock / Phase 2 reference recipe). Defaults tip clearance to **0.5 mm** (`--tip-gap-mm`); supports `--mesh-ladder`, `--ladder-only`, `--tip-gap-study`, `--physics-study`, `--with-frame`, `--wall-ks-mm`.

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

## 2. Mesh ladder + GCI (free-air, tip_gap = 0.5 mm)

Follow-on campaign (~754 s wall, 800 iters, 8 procs, `--ladder-only`):

| `base_cell` [m] | Free-air Q [CFM] | Converged | Drift [%] |
|-----------------|------------------|-----------|-----------|
| 0.008 | 43.9 | yes | 0.0 |
| 0.006 | 44.6 | yes | 0.1 |
| 0.004 | 44.7 | yes | 0.8 |

| GCI field | Value |
|-----------|--------|
| Observed order \(p\) | ~5.25 |
| \(f\) extrapolated | **~44.76 CFM** |
| GCI fine | **~0.06%** |
| Asymptotic ratio | **~1.004** (≈1 ⇒ asymptotic) |
| Grid-converged **claim** (full P–Q) | **No** — free-air ladder only |

**Verdict:** Free-air is **mesh-insensitive** over this ladder (~0.8 CFM from coarse→fine). The Task 3.2 **−32%** gap was **not** a coarse-mesh artifact. Best mesh-resolved free-air at published tip gap is still **~44.7 CFM (0.74× published, −26%)** — outside the interim ±10% band (54.1–66.1 CFM).

---

## 3. Tip-gap A/B (free-air, `base_cell` = 0.006 m)

| Tip gap [mm] | Free-air Q [CFM] | Notes |
|--------------|------------------|--------|
| **1.0** (domain default used in Task 3.2) | **40.9** | Matches Phase 3.2 free-air |
| **0.5** (published) | **44.6** | **+3.6 CFM** vs 1.0 mm |

Closing tip gap to the published **0.5 mm** recovers ~**4 CFM** (~9% relative to the 1.0 mm case) but leaves **~15 CFM** still missing vs 60.1.

---

## 4. Task 3.2 screening P–Q (historical; tip_gap ≈ 1.0 mm)

| Setting | Task 3.2 value |
|---------|----------------|
| P–Q sweep `base_cell` [m] | **0.006** |
| Tip gap (effective) | **~1.0 mm** (domain default; not published 0.5 mm) |
| Solver iterations / MPI | **800** / **8** |
| Wall time | **~466 s** |
| GCI | Not computed in that run |

### 4.1 Free-air vs published (that run)

| Metric | Published | Simulated | Error | Interim band (±10%) | Interim pass? |
|--------|-----------|-----------|-------|---------------------|---------------|
| Free-air Q [CFM] @ 0 Pa | 60.1 | **40.94** | **−31.9%** | **54.1–66.1 CFM** | **No** |

### 4.2 Multi-point P–Q

| Back-pressure [Pa] | Simulated Q [CFM] | Converged | Flow drift [%] |
|--------------------|-------------------|-----------|----------------|
| 0 | 40.94 | yes | 1.0 |
| 5 | 24.86 | yes | 0.5 |
| 10 | 13.10 | yes | 0.3 |
| 15 | 6.64 | yes | 0.6 |
| 20 | −2.37 | **no** | 46.7 |

### 4.3 Shut-off ΔP proxy (Q → 0)

Linear fit of last two **converged** points (**10 Pa / 13.10 CFM**, **15 Pa / 6.64 CFM**):

| Metric | Published | Simulated (proxy) | Error | Interim band (±5 Pa) | Interim pass? |
|--------|-----------|-------------------|-------|----------------------|---------------|
| Shut-off ΔP [Pa] | 22.9 | **~20.1** | **−2.8 Pa** | **17.9–27.9 Pa** | **Yes (proxy only)** |

Not re-run at tip_gap 0.5 mm in the mesh/tip campaign (`--ladder-only`).

---

## 5. Geometry error vs model / idealization error

| Source | What it affects | Current assessment |
|--------|-----------------|---------------------|
| **Geometry error** | Envelope vs OEM | **Envelope pass**; recipe remains reference-parametric |
| **Mesh error** | Discretization | **Ruled out as primary free-air driver** — asymptotic ladder, GCI_fine ≪ 1% |
| **Tip-gap idealization** | Clearance | **Partial:** 1.0→0.5 mm explains ~4 of ~19 CFM shortfall |
| **Model / B.C. error** | Open duct, no frame/struts, MRF, wall_ks | Frame + wall_ks only cost **~1 CFM** (§7). Remaining **~15 CFM** gap is **not** explained by those idealizations — prefer **recipe vs OEM** next. |

| Geometry envelope | CFD interim (free-air) | Interpretation |
|-------------------|------------------------|----------------|
| Pass | **Fail** (−26% at published tip gap, mesh-resolved; frame/ks ~−1 CFM more) | Mesh/tip/frame/ks checked; **recipe fidelity** is the next software lever |

---

## 6. Next physics levers

1. ~~Free-air mesh ladder + GCI~~ — **done**; asymptotic ~44.8 CFM at tip_gap 0.5 mm.  
2. ~~Tip-gap 1.0 vs 0.5 mm~~ — **done**; +3.6 CFM.  
3. ~~Frame / wall_ks free-air A/B~~ — **done**; see §7 (~1 CFM loss only).  
4. **Reference blade recipe vs OEM** (camber / stagger / solidity) — dominant remaining free-air gap.  
5. Near–shut-off numerics at tip_gap 0.5 mm (re-P–Q or finer backs past 15 Pa).  
6. Prism layers / y+ (future).  
7. Hardware Phase 5 when a commercial hub/frame + printed impeller measurement exists.

---

## 7. Frame / wall_ks free-air A/B (tip_gap = 0.5 mm, base_cell = 0.006 m)

Campaign (~562 s): open duct vs four-bar frame and FDM-order sand-grain ``wall_ks = 0.1 mm``.

| Config | Free-air Q [CFM] | Δ vs open |
|--------|------------------|-----------|
| open (baseline) | **44.6** | — |
| frame | 43.8 | **−0.8** |
| wall_ks 0.1 mm | 44.0 | **−0.6** |
| frame + wall_ks | 43.4 | **−1.2** |

**Verdict:** Exhaust struts and print-rough walls are **small losses** (~1 CFM). They move free-air **further from** published 60.1, so they do **not** explain the remaining **~15 CFM (−26%)** shortfall. Missing “real-fan losses” were the right check historically for over-prediction; with the 7-blade reference recipe the dominant issue is now **under-performance of the parametric shape vs OEM**, not open-duct idealization.

Committed summary: [a12x25_physics_validation_summary.json](a12x25_physics_validation_summary.json). Local run: `runs/validate_a12x25_physics/`.

---

## Artifacts

| File | Purpose |
|------|---------|
| `runs/validate_a12x25_phase3/validation.json` | Task 3.2 full P–Q (local) |
| `docs/validation/a12x25_phase3_validation_summary.json` | Committed Phase 3.2 numbers |
| `runs/validate_a12x25_mesh_tip/validation.json` | Mesh ladder + tip study (local) |
| `docs/validation/a12x25_mesh_tip_validation_summary.json` | Committed mesh/tip numbers |
| `runs/validate_a12x25_physics/validation.json` | Frame / wall_ks A/B (local) |
| `docs/validation/a12x25_physics_validation_summary.json` | Committed physics A/B numbers |
| `scripts/run_a12x25_validation.py` | `--mesh-ladder`, `--tip-gap-*`, `--physics-study`, `--with-frame`, `--wall-ks-mm` |
