# Product keep / cut / park board

**Status:** Default product scope after Phases 0–4 validation work (2026-09-14).  
**Plan parent:** [proper-state program](../superpowers/plans/2026-09-14-proper-state-program.md) Task 6.1.

This board records what we **keep** in the product, what we **park** until honesty gates move, and what we **do not ship**. It is not a roadmap replacement — it prevents scope creep while the A12x25 reference band is still open.

---

## Default decisions

| Item | Decision | Rationale (short) |
|------|----------|-------------------|
| Axial Fan cockpit + CFD | **KEEP — primary** | Core design loop: CadQuery → BEM prescreen → OpenFOAM on stock axial cases. |
| BEM screen + system curve | **KEEP** | Load-honest ranking (hose / heatsink / radiator ΔP) is the right optimizer objective; free-air-only prescreen is documented legacy. |
| Stator / sickle / notches | **KEEP** (stage-1) | Phase 2 reference-parametric recipe (`a12x25_reference.yaml`) encodes 7-blade envelope + sickle/notch levers; deepen geometry only when validation or hardware measurement requires it — not OEM STL equivalence yet. |
| Mixed / volute / CROR / prop | **KEEP scaffolds**, schedule after A12x25 band | Alternate machine types stay in tree for reuse; no expansion campaigns until published P–Q on the reference axial fan is honest. |
| Surrogate GP/NN | **KEEP code**, retrain only on load-honest catalog | Models stay wired; new training runs must use catalog rows scored on system-curve load, not free-air-only studies. |
| Wind turbine | **PARK** | Out of north-star path until axial reference CFD closes. |
| Absolute FW-H / DES | **PARK** until RANS free-air/shut-off trusted | Mesh-resolved free-air at published tip gap is still **~−26%** vs 60.1 CFM ([a12x25_pq_report.md](a12x25_pq_report.md)); Task 3.2 screening was **~−32%** at ~1.0 mm tip gap. Absolute aeroacoustics would over-claim before P–Q is defensible. |
| Chat recovery extracts | **DON'T SHIP** | Local transcript/recovery trees are developer archaeology only — never product docs, configs, or defaults. |

---

## Validation context (binding)

| Phase | What we learned | Effect on this board |
|-------|-----------------|----------------------|
| **Phase 2** (reference geometry) | Stock recipe is **reference-parametric** with envelope pytest pass (blade count, tip/hub bands) — **not** watertight OEM STL. | KEEP stator/sickle/notch work at stage-1; do not sell “matches Noctua CAD” without `validation/reference/` STL or print/measure. |
| **Phase 3** (CFD vs published) | Screening free-air **40.9 CFM (−32%)** at ~1.0 mm tip; follow-on ladder at **0.5 mm** → **~44.7 CFM (−26%)**, GCI asymptotic. Shut-off **proxy** only. Interim ±10% band **not met**. | PARK absolute aeroacoustics / “validated stock”; next levers are frame/casing and wall_ks — not mesh. |
| **Phase 4** (perf / deps) | Screening speed and dependency hygiene help scale trials; they **do not** close the CFM gap. | KEEP perf work as throughput; do not reinterpret speedups as validation. |
| **Phase 5** (print → measure) | **Hardware-gated** — see [north-star-staged.md](north-star-staged.md) and [.superpowers/sdd/task-5.1-blocked.md](../../.superpowers/sdd/task-5.1-blocked.md). | No absolute calibration or “§5.1 done” until a commercial A12x25 hub/frame + printed impeller yields at least one real CFM/static (preferably noise/weight/RPM) point in `validation/measurements/`. |

---

## When to revisit

Re-open **PARK** rows when **all** of the following hold for the reference recipe at 2000 RPM:

1. Free-air Q within the documented interim band (currently ±10% of 60.1 CFM, or tighter X from a mesh study).
2. Shut-off ΔP validated beyond extrapolation proxy (converged near-zero-flow or agreed alternative).
3. Optional but strong: at least one hardware measurement from Phase 5 on the same hub class.

Until then, treat mixed/volute/CROR/prop scaffolds and surrogate retraining as **secondary** to closing the A12x25 axial band.

---

## Related

- Published numbers: [a12x25-reference.md](../a12x25-reference.md)
- Geometry vs CFD budgets: [a12x25_geometry_acceptance.md](a12x25_geometry_acceptance.md)
- Phase 3 campaign write-up: [a12x25_pq_report.md](a12x25_pq_report.md)
- Print/measure runbook: [north-star-staged.md](north-star-staged.md)
