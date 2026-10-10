# NF-A12x25 acceptance budgets — geometry vs CFD

**Purpose:** Define two **independent** pass/fail budgets for the Noctua NF-A12x25 PWM reference. Published manufacturer numbers live in [a12x25-reference.md](../a12x25-reference.md). Parametric recipes under `config/problems/` are **not** OEM truth unless labeled and backed by a trusted STL (see [proper-state program](../superpowers/plans/2026-09-14-proper-state-program.md) Phase 2).

**Ground truth consumed:** 60.1 CFM free-air, 22.9 Pa shut-off, 22.6 dB(A), 2000 RPM, **0.5 mm** tip clearance, **9** blades (Noctua A-series; earlier docs incorrectly said 7).

---

## 1. Geometry fidelity budget

**Reference:** Real impeller geometry or a **trusted watertight STL** under `validation/reference/` when present. Until then, compare the stock reference recipe (Task 2.2+) against the **published envelope** below — not against `config/problems/a12x25.yaml` alone without an `approximate` / provenance label.

| Check | Acceptance (parametric envelope) | Notes |
|-------|----------------------------------|--------|
| Blade count | `n_blades == 9` | Must match published NF-A12x25 (nine-blade A-series) |
| Tip radius | **54.0–54.5 mm** | The 110 mm frame ID with 0.5 mm tip clearance caps it at 54.5 mm; the Stock recipe is 54.5 (`tests/test_a12x25_reference_geometry.py`). The old 55–57 band predated the frame-ID correction |
| Hub radius | **20.0–23.0 mm** | ~43 mm hub OD band (STL vertex p5 may read slightly lower — soft band in silhouette test) |
| Axial depth | Impeller fits **25 mm** frame class | Fan form factor is 120×120×25 mm; blade stack + hub margins must not exceed the printable depth budget used by `FanSpec` for `a12x25` (impeller depth within the documented min/max envelope, not a generic 120×38 industrial slot) |
| LE sickle character | Visible tip-weighted LE sweep / sickle | NF-A12x25 planform is not a straight radial blade; reference recipe must encode non-trivial tip LE skew or sickle (e.g. `sickle_mm` / station sweep), not a flat-paddle placeholder |
| Tip clearance → frame ID | **0.5 mm** radial gap (published) | Frame inner diameter **110 mm** (measured mount envelope in `fan_spec`); built outer tip vs casing ID targets **0.5 mm** Sterrox LCP clearance — verify in placement/export, not nominal `tip_radius` alone |

**STL-backed path (when `validation/reference/a12x25_impeller.stl` exists):** Silhouette / bounding metrics against the STL (`tests/test_a12x25_reference_geometry.py`). Geometry pass means the mesh matches the published envelope within sampling tolerance — still **not** a CFD pass. The checked-in mesh is a **user-provided close reference**, not OEM CAD.

**Explicit non-merge:** Geometry acceptance answers “does our reference impeller match the real shape envelope?” It does **not** answer “does OpenFOAM hit 60.1 CFM?”

---

## 2. CFD fidelity budget (vs published)

**Reference:** [a12x25-reference.md](../a12x25-reference.md) at **2000 RPM**, free delivery and shut-off (zero-flow static pressure).

| Operating point | Published | Interim acceptance (Phase 2–3) |
|-----------------|-----------|--------------------------------|
| Free-air airflow | 60.1 CFM | Simulated Q within **±10%** → **54.1–66.1 CFM** |
| Shut-off static pressure | 22.9 Pa | Simulated ΔP within **±5 Pa** → **17.9–27.9 Pa** |

**After Task 3.1 (mesh / physics campaign):** Replace interim **±10% / ±5 Pa** with tighter **X / Y** documented from grid convergence and prioritized physics (tip gap, frame, walls). Until that study lands, interim bands are the only defensible absolute-performance gate.

**Acoustics:** 22.6 dB(A) remains a **future** FW-H / aeroacoustic tier target; it is **not** part of the interim CFD gate above.

**Explicit non-merge:** CFD acceptance answers “does the solver stack reproduce published P–Q at stated tolerance?” It does **not** imply the impeller mesh matches OEM CAD. A coarse 7-blade approximation can fail geometry while accidentally landing inside CFM band, or pass geometry and miss CFM — treat the budgets independently.

---

## 3. Independence rule (binding)

| Geometry pass | CFD pass | Interpretation |
|---------------|----------|------------------|
| Yes | Yes | Reference shape and solver campaign both within budget — strongest claim |
| Yes | No | Shape/envelope OK; fix mesh, physics, or idealizations before absolute CFM/P claims |
| No | Yes | Do not trust absolute “beats stock” — geometry error dominates interpretation |
| No | No | Expected during migration off idealized / wrong-blade baselines |

**Passing geometry does not imply CFD pass, and vice versa.** Do not merge these into a single “validation passed” flag in UI, tests, or docs.

---

## Related

- Published table: [docs/a12x25-reference.md](../a12x25-reference.md)
- Implementation plan: [2026-09-14-a12x25-reference-geometry.md](../superpowers/plans/2026-09-14-a12x25-reference-geometry.md) (Tasks 2.1–2.2)
- Envelope pytest (Task 2.2): `tests/test_a12x25_reference_geometry.py`
