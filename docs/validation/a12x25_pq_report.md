# NF-A12x25 reference P–Q validation report

## 2026-09-29 recipe v2 (roadmap §19.7): refit to the close-ref STL sections

After fixing the builder's back-to-front airfoil (3a577c6) and refitting the recipe section by section
(`config/problems/a12x25_reference.yaml`, fb625de, promoted to Stock; built sections within ±0.8 mm chord, ±0.7°
stagger of the reference), the complete setup (ring + frame + layers, matched surface level 3–4) gives:

| back-pressure | v2 recipe | close-ref STL | v2 vs ref | old Stock recipe |
|---|---|---|---|---|
| 0 Pa | **56.5** | 59.8 | −5.5% | 77.4 (+29%) |
| 5 Pa | **49.8** | 52.5 | −5.1% | 46.7 (−11%) |
| 10 Pa | **40.2** | 41.0 | −2.0% | 11.2 (−73%) |

All points converged; sanity physics PASS (skew-only WARN at tip/ring — typically several faces,
max skew ~7–9; §19.10). On the default (wall-derived, coarser)
mesh level, v2 read 55.6 / 48.4 / 38.5, so mesh level moves results 1–4%. The remaining ~2–6% deficit is
likely the extrapolated root station and the builder realising only ~70% of the recipe chord near the tip.

## 2026-09-28 full P–Q in the complete setup (CFD_VERSION 5) — current best

Close-ref STL, sealed 25 mm ring, four-bar frame, prism layers (y+ ≈ 2), 2000 rpm, tip gap 0.5 mm.
Runs: `runs/v5_ab_both` (0 Pa) + `runs/v5_full_pq_loaded` (5–20 Pa); wall time 2 h 50 min (pilot est. 3 h).

| back-pressure | CFM | converged | sanity |
|---|---|---|---|
| 0 Pa | **59.8** (Noctua 60.1, −0.5%) | yes | all physics PASS |
| 5 Pa | 52.5 | yes | all physics PASS |
| 10 Pa | 41.0 | yes | all physics PASS |
| 15 Pa | 26.8 | no (osc 16%) | physics PASS |
| 20 Pa | 2.2 | no (osc 41%) | mass balance FAIL (near stall) |

**Shut-off:** the curve crosses zero at ≈ **20–21 Pa** (interpolating 15→20 Pa) vs published **22.9 Pa**,
inside the ±5 Pa tolerance, but both near-shut-off points are unconverged. The automated proxy
(extrapolating the converged 5–10 Pa points) gives 28.0 Pa, a formal FAIL by 0.1 Pa over the band.
**Verdict:** free air validated; the loaded branch is realistic in shape and roughly right near
shut-off, and the remaining uncertainty is steady-RANS convergence near stall. The Stock parametric
recipe still over-delivers (+22–29% free air) and is the next fidelity target.

## 2026-09-27 domain fixes (CFD_VERSION 5) — free-air gate results

The v3 numbers below were solved in the default **square slip-wall tunnel**, whose open corners let air
bypass the blade tips (the nominal 0.5 mm gap existed at four points only). With the tip gap made real:

| domain (Stock, 2000 rpm, 0 Pa) | free-air CFM | vs 60.1 | sanity |
|---|---|---|---|
| v3 square tunnel (open corners) | 58.7 | −2% | duct_shape WARN |
| v4 full-length noSlip round duct | 39.6 | −34% | pipe friction, not free air |
| v5 short sealed 25 mm ring | 80.4 | +34% | mass/energy/power/thrust PASS |
| **v5 ring + four-bar frame** | **73.1** | **+22%** | mass/energy/power/thrust/inlet PASS; y+ avg 5 WARN |

| v5 ring + frame + prism layers (Stock recipe) | 77.4 | +29% | all physics PASS; y+ avg 1.9 |
| **v5 ring + frame, close-ref STL** | **58.4** | **−3%** | all physics PASS |
| **v5 ring + frame + layers, close-ref STL** | **59.8** | **−0.5%** | all physics PASS; y+ avg 1.8 |

**Factor A/B (2026-09-27):** with the domain physically complete (sealed 25 mm ring, four-bar frame,
resolved walls), the **close-ref STL matches the datasheet free air within 0.5–3%**, while the Stock
parametric recipe over-delivers by 22–29%. Prism layers change CFM by only 2–6%. So the CFD method now
validates at free air with the right geometry, and the remaining free-air gap belongs to the **Stock
recipe's blade geometry**, not the solver or domain.

**Reading:** the v3 −2% agreement was largely two errors cancelling (tip leakage through the open corners
vs. the missing frame). With the gap sealed and the frame included, steady RANS on the Stock recipe
**over-predicts free air by ~22%**. Candidate causes: blade-recipe fidelity (the Stock recipe and close-ref
STL are approximations, not OEM geometry), wall resolution (y+ ≈ 5 sits in the wall-function buffer
region), and frame/hub representation. The loaded P–Q was not re-run (free-air gate outside 50–70 CFM).
Next: an external benchmark fan with published geometry and measured P–Q to separate method error from
geometry error.

## 2026-09 direction fix (CFD_VERSION 3) — current numbers

**Everything below this section was solved with the rotor spinning backwards** (Audit #1,
`docs/validation/audits/2026-09-25-audit-01-flow-direction.md`) and with an MRF zone that clipped the
blade ends in the optimizer path. Keep it as history only.

Stock recipe, tip gap 0.5 mm, base_cell 5 mm, 1000 iters, no frame, designed rotation
(`fansim/cfd/orientation.py`), convergence rule A. Run: `runs/validate_a12x25_dirfix/validation.json`.
Evidence: `docs/validation/audits/2026-09-26-audit-01b-direction-fix.md`.

| back-pressure | CFM before (reversed) | **CFM after** | Noctua | converged / osc |
|---|---|---|---|---|
| 0 Pa | 44.6 | **58.7** | 60.1 | yes / 7.9% |
| 5 Pa | 30.5 | 21.6 | — | **no** / 11.4% |
| 10 Pa | 18.5 | −6.2 | — | yes / 16.8% |
| 15 Pa | ≈10 (interp.) | −72.5 | — | yes / 0.8% |
| 20 Pa | — | −116.5 | — | no / 6.0% |

- **Free air: −2% vs datasheet — PASS.** The earlier "−15…−26% plate-model ceiling" was mostly the reversed rotor.
- **Shut-off: 9.5 Pa vs 22.9 Pa — FAIL** (interim band 17.9–27.9). In the designed rotation the steady solve stalls
  early and oscillates strongly under load; steady RANS cannot represent that regime. Next levers (roadmap §19.6):
  URANS at 5–15 Pa, frame/struts, prism layers, recipe fidelity.

---


**Status:** Task 3.2 + mesh/tip + frame/wall_ks + recipe + tip_gap 0.5 P–Q + close-reference STL free-air/P–Q + **prism layers**. **CFD interim:** free-air **fail** (−17% / layers −16%); shut-off **proxy fail** on STL (~14.6 Pa) vs **proxy pass** on parametric Stock (~24 Pa). Screening free-air levers exhausted.

> **⚠ CORRECTION (2026-09-18) — free-air numbers below are superseded.** §2's verdict ("free-air is
> mesh-insensitive ~44.7 CFM; the gap is **not** a coarse-mesh artifact") was wrong. That ladder
> varied `base_cell` only while the snappy **surface** refinement stayed coarse, so the ~1.5 mm blade
> wall was meshed to ~1 cell at every rung — the result was pinned by *wall* under-resolution, not
> `base_cell`. Resolving the wall to ≥3 cells (`MeshResolution.for_blade`, surf3) with tail-mean
> metrics gives a GCI ladder of **6 mm→37.4, 4 mm→45.2, 2.7 mm→48.4 CFM, Richardson ≈50.8 CFM
> (GCI_fine 6.2%)**. The true grid-converged free-air is **~48–51 CFM (−15…−20% vs 60.1)**, just under
> the measured STL — the residual is the 3-station plate-model fidelity limit, not a solver artifact.
> The ~44.6/44.7 tables below are retained as historical (under-resolved) measurements.

**Published reference:** [a12x25-reference.md](../a12x25-reference.md) — 60.1 CFM free-air @ 0 Pa, 22.9 Pa shut-off @ 2000 RPM, **9** blades.

**Campaign artifacts (local, not in git):**
- Phase 3.2 P–Q (~1.0 mm tip): `runs/validate_a12x25_phase3/` → [a12x25_phase3_validation_summary.json](a12x25_phase3_validation_summary.json)
- Mesh ladder + tip A/B: `runs/validate_a12x25_mesh_tip/` → [a12x25_mesh_tip_validation_summary.json](a12x25_mesh_tip_validation_summary.json)
- Frame / wall_ks A/B: `runs/validate_a12x25_physics/` → [a12x25_physics_validation_summary.json](a12x25_physics_validation_summary.json)
- Flow candidate free-air: `runs/validate_a12x25_flow_candidate/` → [a12x25_flow_candidate_summary.json](a12x25_flow_candidate_summary.json)
- Stock P–Q @ tip 0.5 mm: `runs/validate_a12x25_shutoff_05/` → [a12x25_shutoff_05_validation_summary.json](a12x25_shutoff_05_validation_summary.json)
- Close-reference STL free-air: `runs/validate_a12x25_ref_stl/` → [a12x25_ref_stl_validation_summary.json](a12x25_ref_stl_validation_summary.json)
- Close-reference STL P–Q: `runs/validate_a12x25_ref_stl_pq/` → [a12x25_ref_stl_pq_summary.json](a12x25_ref_stl_pq_summary.json)
- Close-reference STL + layers: `runs/validate_a12x25_ref_stl_layers/` → [a12x25_ref_stl_layers_summary.json](a12x25_ref_stl_layers_summary.json)

**Runner:** `scripts/run_a12x25_validation.py` — `--stl`, `--layers` (prism), tip **0.5 mm**, mesh ladder / physics / P–Q flags as before.

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

**Verdict (SUPERSEDED — see correction banner at top):** This ladder varied `base_cell` only and
held the snappy surface level fixed, so the thin blade wall stayed under-resolved (~1 cell) at every
rung — the "mesh-insensitive ~44.7 CFM" reading was an artifact of that, **not** evidence the gap is
real. Resolving the wall (surf3) + tail-mean gives a grid-converged **~48–51 CFM** (Richardson ≈50.8,
GCI 6.2%), still below the interim ±10% band but ~6 CFM higher than reported here. See the 2026-09-18
convergence investigation and `fansim/cfd/openfoam_case.MeshResolution.for_blade`.

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
7. ~~Prism layers / y+~~ — **done**; see §12 (**+0.6 CFM** only).  
8. Hardware Phase 5 when a commercial hub/frame + printed impeller measurement exists.
9. ~~Full P–Q / shut-off on the close-reference STL~~ — **done**; see §11 (shut-off proxy **fail** ~14.6 Pa).

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

> **NOTE (2026-09-18):** this section predates both the V3-faithful recipe refit (2026-09-17, commit 5caa070) and the wall-resolution fix — its CFD ~44.6 CFM is for the earlier recipe at the coarse (under-resolved) surface level. The current Stock's grid-converged free-air is ~48–51 CFM (see the correction banner at top).

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

Compared with Phase 3.2 at ~1.0 mm tip (proxy ~20.1 Pa; **20 Pa** heavily diverged), the published tip gap yields a **stronger loading branch** and a shut-off proxy **inside** the interim band. Free-air remains **outside** ±10% even after the wall-resolution correction (grid-converged ~48–51 CFM vs 54.1–66.1 CFM; the 44.6 here is the under-resolved figure — see the correction banner at top).

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

> **CORRECTION (2026-09-18):** both rows here used the coarse surface level, which under-resolves the
> parametric Stock's thinner ~1.5 mm wall more than the STL's — so much of the "+5.2 CFM STL
> advantage" is a resolution artifact. With the wall resolved (surf3 + tail-mean) the parametric
> Stock's grid-converged free-air is **~48–51 CFM** (Richardson ≈50.8), i.e. it largely closes to the
> STL. Prefer `--stl` for absolute claims, but the parametric gap is smaller than this table implies.

Committed summary: [a12x25_ref_stl_validation_summary.json](a12x25_ref_stl_validation_summary.json). Local run: `runs/validate_a12x25_ref_stl/`.

---

## 11. Close-reference STL P–Q (tip_gap = 0.5 mm, base_cell = 0.006 m)

Campaign (~582 s): backs **0,5,10,12,14,16,18** Pa, open duct, `--stl`.

| Back-pressure [Pa] | Simulated Q [CFM] | Converged | Drift [%] |
|--------------------|-------------------|-----------|-----------|
| 0 | **49.77** | yes | 0.2 |
| 5 | 22.85 | yes | 1.1 |
| 10 | 7.64 | yes | 0.0 |
| 12 | 4.34 | yes | 0.2 |
| 14 | 0.87 | **no** | 15.5 |
| 16 | −2.82 | **no** | 10.9 |
| 18 | −6.98 | **no** | 11.8 |

### Shut-off ΔP proxy (Q → 0)

Linear fit of last two **converged** points (**10 Pa / 7.64 CFM**, **12 Pa / 4.34 CFM**):

| Metric | Published | Simulated (proxy) | Error | Interim band (±5 Pa) | Interim pass? |
|--------|-----------|-------------------|-------|----------------------|---------------|
| Shut-off ΔP [Pa] | 22.9 | **~14.6** | **−8.3 Pa** | **17.9–27.9 Pa** | **No** |

**Verdict:** Free-air still **−17%** (outside ±10%). Loading branch is **much steeper** than parametric Stock (§9): higher free-air but **weaker** shut-off (~14.6 vs Stock ~24 Pa). Geometry pass on silhouette does **not** imply CFD pass — both free-air and shut-off fail interim on this mesh. Prefer documenting both curves; do not promote absolute claims.

Committed summary: [a12x25_ref_stl_pq_summary.json](a12x25_ref_stl_pq_summary.json). Local run: `runs/validate_a12x25_ref_stl_pq/`.

---

## 12. Prism layers free-air A/B (close-ref STL, tip 0.5 mm, cell 0.006)

Runner `--layers` enables snappy `addLayers` (3 surface layers on impeller).

| Config | Free-air Q [CFM] | Δ |
|--------|------------------|---|
| no layers (§10) | **49.8** | — |
| `--layers` | **50.4** | **+0.6** |
| Published | 60.1 | — |

**Verdict:** Near-wall prism growth is a **negligible** free-air lever here (~1% relative). Remaining ~10 CFM gap is not a missing-layer artifact at this mesh budget. Next honest software path is thin; absolute free-air needs better geometry fidelity and/or Phase 5 hardware, not more screening knobs.

Committed summary: [a12x25_ref_stl_layers_summary.json](a12x25_ref_stl_layers_summary.json). Local run: `runs/validate_a12x25_ref_stl_layers/`.

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
| `runs/validate_a12x25_ref_stl_pq/validation.json` | Close-reference STL P–Q (local) |
| `docs/validation/a12x25_ref_stl_pq_summary.json` | Committed STL P–Q + shut-off proxy |
| `runs/validate_a12x25_ref_stl_layers/validation.json` | STL free-air with prism layers (local) |
| `docs/validation/a12x25_ref_stl_layers_summary.json` | Committed layers A/B numbers |
| `docs/validation/a12x25_recipe_sensitivity.md` | BEM one-factor table |
| `scripts/run_a12x25_validation.py` | `--stl`, `--layers`, `--mesh-ladder`, `--tip-gap-*`, `--physics-study`, … |
| `scripts/a12x25_recipe_sensitivity.py` | BEM sensitivity runner |
| `config/problems/a12x25_flow_candidate.yaml` | Experimental sibling (not Stock) |
