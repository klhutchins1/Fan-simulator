# Task A: builder stress test, summary (QA round 6, master 31228d0)

> **Stopped early by Kimball.** n = **120 of 801 planned** designs: the 50 pilot designs plus 70 from the full run. Kimball killed the run at 16:05 MDT on Oct 10. Every rate below comes from this partial sample and is **not** a population estimate. 120/120 records parsed; none was partial.

- **Pre-registration:** `docs/qa/stress/PREREG.md`, in the QA-only clone `/workspace/fansim/qa/prereg_r6` (branch `prereg/round6`).
  - A0, before any build: commit `30ea579089a091589b56d03c1950be0f74e3400a`, sha256 `3e716d56…dfa602`.
  - Amendments after the pilot: commit `5cf4a3a0…ecf`, sha256 `d3379f0e…4bbb3`. They cover counts (×0.3), the 16gb memory wait (60 s) and the new timing fields. No pass rule was changed.
- **Per-stratum counts done / planned:** S1 14/180, S2 14/90, S3 14/60, S4 14/120, S5 14/90, S6 14/60, S7 13/60, S8 18/136, CTL 5/5.
- **Files:**
  - `designs.jsonl.gz`: one line per design (inputs, builds, checks, measurements).
  - `inputs.jsonl.gz`: all 2,341 sampled inputs.
  - `summary.json`: the runner's last summary.
  - `repro/`: one params file per finding.
  - `PILOT.md`; the scripts `gen_inputs.py`, `run_stress.py`, `design_job.py`, `make_tables.py` and `counts.json`.
  - No STLs were kept: no K2, K3 or K4 failure occurred.

## Why the full run was slow (6 min per design, not about 30 s)

The time went to **the box being frozen, not to building**. In the 70 full-run designs:
- **Wall time:** 7.1 h in total.
- **Real work:** monotonic time for the P builds is **0.56 h** and the build processes' CPU time is **0.65 h**.
- **Six P builds** (S8_0010, S5_0008, S4_0009, S5_0010, S5_0011, S6_0013) have wall ≫ monotonic: 349 / 1,049 / 6,550 / 10,896 / 3,006 / 1,326 s of wall time against 33–128 s monotonic. Together that is about **6.1 h of the 7.1 h**. All six are `suspect_suspend` (wall − monotonic > 60 s).
- **Memory waits are not the cause.** No T builds ran in the full run (S1–S7 had not yet reached idx 20), so there were 0 `SKIPPED_MEM` and 0 memory-wait seconds. Per-design overhead outside the builds is a median 3 s (0.07 h in total).
- **Freezes and memory.** The three highest-peak builds of the full run (the S5 featured designs S5_0011, S5_0008 and S5_0010, at 7.6 / 6.0 / 5.9 GB against a 2.5 GB median) were all frozen. The other three frozen builds peaked at 2.3–3.8 GB. This looks like the sandbox or host pausing the box, which is worse under memory pressure (no swap; MemAvailable is often 2–4 GB because of memory outside these processes). It is not something in the code.
- **Excluding the frozen builds,** a design takes about 26–30 s. 801 designs would then take about 7–9 h, as estimated.

### Rate table (fail / tested; N/A, SKIPPED and INCONCLUSIVE are not 'tested'; K5 INCONCLUSIVE in brackets)

| stratum | n | K1 | K2 | K3 | K4 | K5 | K6 | K7 | K8 | K9 | K10 | K11 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 | 14 | 0/14 | 0/14 | 0/14 | 0/14 | 0/14 (3) | 0/11 | 0/1 | 0/1 | 0/1 | 0/2 | 0/14 |
| S2 | 14 | 0/14 | 0/14 | 0/14 | 0/14 | 0/14 (4) | 0/10 | 1/1 | 0/1 | 0/1 | — | 0/14 |
| S3 | 14 | 0/14 | 0/14 | 0/14 | 0/14 | 1/14 (3) | 0/11 | 0/1 | 0/1 | 0/1 | 0/1 | 0/14 |
| S4 | 14 | 0/14 | 0/14 | 0/14 | 0/14 | 2/14 (4) | 0/10 | 0/1 | 0/1 | 0/1 | — | 0/14 |
| S5 | 14 | 1/14 | 0/13 | 0/13 | 0/13 | 0/13 (3) | 0/10 | — | — | — | — | 0/14 |
| S6 | 14 | 0/14 | 0/14 | 0/14 | 0/14 | 0/14 (3) | 0/11 | 0/1 | 0/1 | 0/1 | — | 0/14 |
| S7 | 13 | 0/13 | 0/13 | 0/13 | 0/13 | 0/13 (4) | 0/9 | 0/1 | 0/1 | 0/1 | — | 0/13 |
| S8 | 18 | 0/18 | 0/18 | 0/18 | 0/18 | 0/18 (0) | 0/18 | 2/18 | — | — | — | 0/18 |
| CTL | 5 | 0/5 | 0/5 | 0/5 | 0/5 | 4/5 (0) | 0/5 | 0/5 | 0/5 | 0/5 | — | 0/5 |
| all | 120 | 1/120 | 0/119 | 0/119 | 0/119 | 7/119 (24) | 0/95 | 3/29 | 0/11 | 0/11 | 0/3 | 0/120 |

### K5 map: FAIL / INCONCLUSIVE / tested, by max_camber × lean_tip

| max_camber \ lean_tip | 0–10° | 10–20° | 20–30° | ≥30° |
|---|---|---|---|---|
| 0–0.01 | 0 / 0 / 1 | 0 / 6 / 6 | 3 / 3 / 7 | 1 / 3 / 4 |
| 0.01–0.02 | 0 / 0 / 4 | 0 / 0 / 1 | 0 / 1 / 4 | 3 / 3 / 7 |
| 0.02–0.04 | 0 / 0 / 6 | 0 / 0 / 5 | 0 / 0 / 25 | 0 / 8 / 16 |
| 0.04–0.06 | 0 / 0 / 7 | 0 / 0 / 7 | 0 / 0 / 6 | 0 / 0 / 13 |

### Time and memory per build kind (suspend-flagged builds excluded from times)

| kind | n | n suspend-flagged | median wall s | median monotonic s | median child CPU s | max peak RSS MB | median peak MB |
|---|---|---|---|---|---|---|---|
| P | 120 | 6 | 22.8 | 21.2 | 26.3 | 7591 | 2522 |
| R | 3 | 0 | 21.8 | 22.0 | 26.5 | 2821 | 2615 |
| C | 29 | 1 | 20.1 | 18.9 | 23.4 | 5500 | 2337 |
| T16gb | 6 | 0 | 22.2 | — | — | 4241 | 3829 |
| T6gb | 11 | 0 | 77.6 | — | — | 4727 | 2543 |

T16gb SKIPPED_MEM: 5. K8 byte-identical across tiers: 0/11.

Reading the tables:
- K6 N/A means one of the two proofs was INCONCLUSIVE.
- K7 N/A means the hub was too small for the cup (1 design).
- K8 and K9 apply only to designs with T builds (the pilot's idx-0 designs and the controls).
- The "max peak RSS" column for P is 7,591 MB, from S5_0011 (a featured design) **at the forced 8gb tier**. That is above the 8gb tier's own 6.5 GB `min_free_gb`. K9 only judges T builds, so this is an observation, not a FAIL.

## Findings (ranked by how often S1–S3 hit them)

| id | check | count / tested | strata | shared inputs | repro | measured / message |
|---|---|---|---|---|---|---|
| **A-F3** direction proof false refusal | K5 | 7/119, plus 24 INCONCLUSIVE | S3 ×1, S4 ×2, CTL ×4 (9605, 9606, 9620, 9630) | **All 7 have max_camber < 0.02 and lean_tip ≥ 20°**: camber 0.0008–0.0164, lean_tip 22–42°, root stagger 29–47°, 8–11 blades. That cell is 7 FAIL + 10 INCONCLUSIVE out of 22 tested (32 % FAIL). No FAIL anywhere with camber ≥ 0.02. | `repro/A-F3_direction_false_refusal.json` (S3_0002, guided_lc) | CONCLUSIVE omega −1 / pump +1, agreement 1.0 over 18–33 sections. The mirror (K6) passes on all 7, so it's the **checker** misreading lean curvature as camber, not the builder. This feeds Task B. |
| **A-F2** motor cup goes through a short hub (no floor) | K7 | 3/29 | S2 ×1, S8 ×2 (edge stagger_root min, edge chord_root min) | The auto hub is 12.72 / 12.62 / 10.92 mm tall, below the 13 mm cup. All hubs ≥ 14.3 mm pass (floor at 12.98–12.99 mm). | `repro/A-F2_cup_through_short_hub.json` (S8_0008) | The "floor" sits at the hub top (12.73 / 12.64 / 10.93 mm above the hub face), so the cup is open at both ends. Grips 20, 0.69 mm, Ø 37.93 are correct. `build_stl_isolated(motor_mount=…)` (the cockpit cup **Preview** path) doesn't enforce `MotorMount.min_hub_height_mm` = 15. Only Export's `prepare_export_flat(fit_hub=True)` grows the hub. **Real builder/path bug.** |
| **A-F1** tip trim fails on a featured, high-lean, wide-tip blade | K1 | 1/120 | S5 ×1 | 10 blades, tip_radius 52.55, chord_tip 36.4, lean_tip 42.8°, camber 0.053, tubercles 0.098 × 3, serrations 0.036 × 5, dimples 0.083 | `repro/A-F1_tip_trim_build_fail.json` (S5_0007) | `RuntimeError: tip trim failed: blade crosses R=52.55 mm (reaches 56.09 mm) and no intersection ended at R…`, worker exit 3. **Real builder bug** (see the classification below). |
| **A-F4** memory tiers are not byte-identical | K8 (info) | 0/11 FAIL, but 0/11 byte-identical | pilot T designs | — | `repro/A-F4_tiers_not_byte_identical.json` (S1_0000) | Volume within 1e-6 and the same vertex count (K8 PASS), but the STL sha256 differs between the 16gb, 8gb and 6gb tiers every time. The `resources.py` docstring's "byte-identical solid" claim is false at the file level (most likely face/vertex order from the parallel vs serial Boolean). |

**Classification of the K1 failure (S5_0007).**
- The runner labelled it `CRASH`. Under the pre-registered wording ("non-zero exit with no Python traceback in the tail") that label is technically right, but only because `run_worker_module` keeps a 160-character stderr tail, which cut the traceback off.
- Really it is a **handled Python exception (exit 3) → BUILD_FAIL**: there was no signal and no native crash. Either way it fails K1.
- It is a **real builder robustness bug, not a design-space artefact.** The design came straight from the optimizer's own `--extended --features` space and passed `validate_blade_params`. The builder should have built it or refused it cleanly with a `ValueError`, but raised in the tip trim instead: the featured surface bulges 3.5 mm past `tip_radius` and the trim intersection doesn't close.

## K5 map (Task B input)
See the table above: FAILs appear only for max_camber < 0.02 with lean_tip ≥ 20°. INCONCLUSIVE is concentrated at camber < 0.01 (any lean ≥ 10°) and at camber 0.02–0.04 with lean ≥ 30° (8/16). No better-separating axis was searched; n is too small.

## Re-check of the pilot classification
- **K5:** the pilot's 5 FAILs plus 2 new full-run FAILs (S4_0005, S4_0012; 8 and 9 blades, so not only 11-blade designs). All 7 fall in the same camber/lean cell, and all pass K6. The classification stands: a direction-check false refusal.
- **K7:** still the same 3 pilot designs. The 8 full-run C builds all passed. The classification stands: a short-hub cup in the Preview path.
