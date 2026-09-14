# NF-A12x25 reference P–Q validation report

**Status:** Task 3.2 screening + mesh/tip + frame/wall_ks + recipe + tip_gap 0.5 mm P–Q + **close-reference STL free-air** recorded. **CFD interim:** free-air still **fail** (−17% on reference STL vs −26% parametric); shut-off **proxy pass** (~24 Pa, parametric tip 0.5 mm).

**Published reference:** [a12x25-reference.md](../a12x25-reference.md) — 60.1 CFM free-air @ 0 Pa, 22.9 Pa shut-off @ 2000 RPM, **9** blades.

**Campaign artifacts (local, not in git):**
- Phase 3.2 P–Q (~1.0 mm tip): `runs/validate_a12x25_phase3/` → [a12x25_phase3_validation_summary.json](a12x25_phase3_validation_summary.json)
- Mesh ladder + tip A/B: `runs/validate_a12x25_mesh_tip/` → [a12x25_mesh_tip_validation_summary.json](a12x25_mesh_tip_validation_summary.json)
- Frame / wall_ks A/B: `runs/validate_a12x25_physics/` → [a12x25_physics_validation_summary.json](a12x25_physics_validation_summary.json)
- Flow candidate free-air: `runs/validate_a12x25_flow_candidate/` → [a12x25_flow_candidate_summary.json](a12x25_flow_candidate_summary.json)
- Stock P–Q @ tip 0.5 mm: `runs/validate_a12x25_shutoff_05/` → [a12x25_shutoff_05_validation_summary.json](a12x25_shutoff_05_validation_summary.json)
- Close-reference STL free-air: `runs/validate_a12x25_ref_stl/` → [a12x25_ref_stl_validation_summary.json](a12x25_ref_stl_validation_summary.json)

**Runner:** `scripts/run_a12x25_validation.py` with `--params config/problems/a12x25_reference.yaml` (cockpit Stock / Phase 2 reference recipe). Defaults tip clearance to **0.5 mm** (`--tip-gap-mm`); supports `--stl` (default `validation/reference/a12x25_impeller.stl`), `--mesh-ladder`, `--ladder-only`, `--tip-gap-study`, `--physics-study`, `--with-frame`, `--wall-ks-mm`.

---

## 1. Geometry recipe provenance

| Item | Value |
|------|--------|
| Parametric recipe | `config/problems/a12x25_reference.yaml` (**9** blades) |
| Close-reference STL | `validation/reference/a12x25_impeller.stl` (user-provided; **not** OEM CAD) |
| Blade count (published) | **9** (Noctua A-series; older docs incorrectly said 7) |
| Tip clearance target | 0.5 mm (published) |
| Geometry acceptance doc | [a12x25_geometry_acceptance.md](a12x25_geometry_acceptance.md) |

Geometry pass/fail is **independent** of CFD pass/fail (see geometry acceptance doc). This report focuses on solver P–Q vs published numbers.

**Geometry budget:** Envelope pytest + STL silhouette (`tests/test_a12x25_reference_geometry.py`) — tip **55–57 mm**, hub band, **9** blades, watertight. Silhouette **pass** for the checked-in close-reference mesh; parametric Stock remains approximate planform (not OEM equivalence).

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
| **Geometry error** | Envelope vs OEM | Silhouette **pass** on close-reference STL; parametric Stock still approximate |
| **Mesh error** | Discretization | **Ruled out as primary free-air driver** — asymptotic ladder, GCI_fine ≪ 1% (parametric) |
| **Tip-gap idealization** | Clearance | **Partial:** 1.0→0.5 mm explains ~4 of ~19 CFM shortfall (parametric) |
| **Model / B.C. error** | Open duct, no frame/struts, MRF, wall_ks | Frame + wall_ks only cost **~1 CFM** (§7). |
| **Parametric recipe vs close STL** | Station stagger/camber/chord vs real planform | Mid/tip stagger raise: BEM **+13 CFM**, CFD only **+0.6 CFM** (§8). Close-reference STL recovers **~+5 CFM** vs parametric (§10). |

| Geometry envelope | CFD interim (free-air) | Interpretation |
|-------------------|------------------------|----------------|
| Pass (STL silhouette) | **Fail** (−17% on close-ref STL; −26% parametric) at tip_gap 0.5 mm | Shape closer; still outside ±10%. Prefer STL for absolute claims. |

---

## 6. Next physics levers

1. ~~Free-air mesh ladder + GCI~~ — **done**; asymptotic ~44.8 CFM at tip_gap 0.5 mm.  
2. ~~Tip-gap 1.0 vs 0.5 mm~~ — **done**; +3.6 CFM.  
3. ~~Frame / wall_ks free-air A/B~~ — **done**; see §7 (~1 CFM loss only).  
4. ~~BEM stagger candidate CFD~~ — **done**; see §8 (~+0.6 CFM only). Stock **not** retuned.  
5. ~~Near–shut-off P–Q at tip_gap 0.5 mm~~ — **done**; see §9 (proxy ~24 Pa, interim pass).  
6. ~~Trusted / close-reference STL~~ — **done**; see §10 (**49.8 CFM**, −17%).  
7. Prism layers / y+ (future).  
8. Hardware Phase 5 when a commercial hub/frame + printed impeller measurement exists.
9. Full P–Q / shut-off on the close-reference STL (same tip/mesh budget as §9).

---

## 7. Frame / wall_ks free-air A/B (tip_gap = 0.5 mm, base_cell = 0.006 m)

Campaign (~562 s): open duct vs four-bar frame and FDM-order sand-grain ``wall_ks = 0.1 mm``.

| Config | Free-air Q [CFM] | Δ vs open |
|--------|------------------|-----------|
| open (baseline) | **44.6** | — |
| frame | 43.8 | **−0.8** |
| wall_ks 0.1 mm | 44.0 | **−0.6** |
| frame + wall_ks | 43.4 | **−1.2** |

**Verdict:** Exhaust struts and print-rough walls are **small losses** (~1 CFM). They move free-air **further from** published 60.1, so they do **not** explain the remaining shortfall. With the parametric recipe the dominant issue was **under-performance of the approximate shape**; the close-reference STL (§10) closes part of that gap.

Committed summary: [a12x25_physics_validation_summary.json](a12x25_physics_validation_summary.json). Local run: `runs/validate_a12x25_physics/`.

---

## 8. Recipe fidelity — BEM sensitivity + experimental CFD candidate

Plan: [2026-09-14-a12x25-recipe-fidelity.md](../superpowers/plans/2026-09-14-a12x25-recipe-fidelity.md).  
BEM table: [a12x25_recipe_sensitivity.md](a12x25_recipe_sensitivity.md).

**BEM (screening):** Stock free-air **65.0 CFM** (already above published 60.1; CFD Stock is ~44.6). Largest lever is **mid stagger** (+9 to +13 CFM at 38–44°). Tip stagger next; chord/lean barely move BEM free-air.

**Experimental yaml:** `config/problems/a12x25_flow_candidate.yaml` — mid stagger **38°**, tip stagger **28°** (Stock 26° / 22°). **Not** Stock; **not** OEM.

| Recipe | BEM free-air [CFM] | CFD free-air [CFM] (tip 0.5 mm, cell 0.006) |
|--------|--------------------|-----------------------------------------------|
| Stock `a12x25_reference.yaml` | 65.0 | **44.6** |
| Candidate `a12x25_flow_candidate.yaml` | 78.0 | **45.2** (+0.6) |
| Published | 60.1 | 60.1 |

**Verdict:** Raising stagger does **not** close the CFD gap. BEM and RANS MRF disagree strongly on this knob. Do **not** retune `STOCK_GEOMETRY_YAML["a12x25"]` from BEM. Prefer a trusted STL or Phase 5 measurement before changing Stock.

Committed summary: [a12x25_flow_candidate_summary.json](a12x25_flow_candidate_summary.json).

---

## 9. Stock P–Q at tip_gap = 0.5 mm (near-shut-off)

Campaign (~796 s): backs **0,5,10,12,14,16,18** Pa, `base_cell=0.006`, open duct, Stock `a12x25_reference.yaml`.

| Back-pressure [Pa] | Simulated Q [CFM] | Converged | Drift [%] |
|--------------------|-------------------|-----------|-----------|
| 0 | **44.57** | yes | 0.0 |
| 5 | 30.54 | yes | 0.3 |
| 10 | 18.49 | yes | 0.4 |
| 12 | 14.61 | yes | 0.1 |
| 14 | 11.41 | yes | 0.2 |
| 16 | 9.12 | yes | 0.2 |
| 18 | 6.74 | **no** | 3.5 |

### Shut-off ΔP proxy (Q → 0)

Linear fit of last two **converged** points (**14 Pa / 11.41 CFM**, **16 Pa / 9.12 CFM**):

| Metric | Published | Simulated (proxy) | Error | Interim band (±5 Pa) | Interim pass? |
|--------|-----------|-------------------|-------|----------------------|---------------|
| Shut-off ΔP [Pa] | 22.9 | **~24.0** | **+1.1 Pa** | **17.9–27.9 Pa** | **Yes (proxy only)** |

Compared with Phase 3.2 at ~1.0 mm tip (proxy ~20.1 Pa; **20 Pa** heavily diverged), the published tip gap yields a **stronger loading branch** and a shut-off proxy **inside** the interim band. Free-air remains **outside** ±10% (44.6 vs 54.1–66.1 CFM).

**Caveat:** **18 Pa** did not meet convergence (3.5% drift). Do not treat shut-off as validated at the same confidence as a converged Q=0 solve.

Committed summary: [a12x25_shutoff_05_validation_summary.json](a12x25_shutoff_05_validation_summary.json).

---

## 10. Close-reference STL free-air (tip_gap = 0.5 mm, base_cell = 0.006 m)

**Mesh:** `validation/reference/a12x25_impeller.stl` — user-provided close reference to NF-A12x25 (**not** OEM CAD). Spin axis prepared to **+Z**; silhouette: **9** blades, tip ~55.3 mm, axial ~16.7 mm. Runner: `--stl --ladder-only --mesh-ladder 0.006` (~120 s).

| Geometry | Free-air Q [CFM] | vs published | Interim ±10% |
|----------|------------------|--------------|--------------|
| Parametric Stock (`a12x25_reference.yaml`) | **44.6** | −26% | **Fail** |
| Close-reference STL | **49.8** | **−17%** | **Fail** (need ≥54.1) |
| Published | 60.1 | — | — |

**Verdict:** The close-reference mesh recovers **~+5.2 CFM** vs the parametric Stock at the same tip gap and cell size — largest single free-air gain since tip-gap 0.5 mm. Still **~10 CFM** short of published and outside interim ±10%. Do **not** claim OEM CAD fidelity; do prefer `--stl` for absolute CFD claims going forward. Next: P–Q / shut-off on this mesh; Phase 5 hardware.

Committed summary: [a12x25_ref_stl_validation_summary.json](a12x25_ref_stl_validation_summary.json). Local run: `runs/validate_a12x25_ref_stl/`.

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
| `runs/validate_a12x25_flow_candidate/validation.json` | Stagger candidate free-air (local) |
| `docs/validation/a12x25_flow_candidate_summary.json` | Committed candidate numbers |
| `runs/validate_a12x25_shutoff_05/validation.json` | Stock P–Q @ tip 0.5 mm (local) |
| `docs/validation/a12x25_shutoff_05_validation_summary.json` | Committed shut-off campaign numbers |
| `runs/validate_a12x25_ref_stl/validation.json` | Close-reference STL free-air (local) |
| `docs/validation/a12x25_ref_stl_validation_summary.json` | Committed STL free-air numbers |
| `validation/reference/a12x25_impeller.stl` | Close-reference impeller (Z-up); not OEM CAD |
| `docs/validation/a12x25_recipe_sensitivity.md` | BEM one-factor table |
| `scripts/run_a12x25_validation.py` | `--stl`, `--mesh-ladder`, `--tip-gap-*`, `--physics-study`, `--with-frame`, `--wall-ks-mm` |
| `scripts/a12x25_recipe_sensitivity.py` | BEM sensitivity runner |
| `config/problems/a12x25_flow_candidate.yaml` | Experimental sibling (not Stock) |
