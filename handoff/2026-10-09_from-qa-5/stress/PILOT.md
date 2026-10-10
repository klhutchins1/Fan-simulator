# Task A pilot (QA round 6): 50 designs, master 31228d0

> **Update 2026-10-10 16:05 MDT:** Kimball stopped the full run at n = 120 of 801. See `summary.md`. The full-run ETA below did not hold because the box froze repeatedly (see summary.md, "Why the full run was slow").

- **Pre-registration:** `docs/qa/stress/PREREG.md`, committed in the QA-only clone `/workspace/fansim/qa/prereg_r6`, branch `prereg/round6`, before any build.
  - A0: commit `30ea579089a091589b56d03c1950be0f74e3400a`, sha256 `3e716d5660ec448c82565419b531883f1971edce9e8a073cf80ae60f79dfa602`, 2026-10-09 21:37 MDT.
  - Amendments after the pilot: commit `5cf4a3a096e7207ea579d978a32c9d1bf26b1ecf`, sha256 `d3379f0e7aba14d7ff4a3474c73eeb07db0af361ada1e3054360004dfdf4bbb3`.
- **Inputs:** `inputs.jsonl` holds all 2,341 sampled designs, written before any build (`gen_inputs.py`). Runner: `run_stress.py` (resumable) and `design_job.py`, one process per design.
- **Pilot timing:** 21:47 Oct 9 → 08:04 Oct 10 MDT. Most of that time the box was suspended (see the T6gb note below).

## Results (50/50 built)

| check | PASS | FAIL | other |
|---|---|---|---|
| K1 builds | 50 | 0 | — (no REJECTED, BUILD_FAIL, CRASH or TIMEOUT) |
| K2 printable solid | 50 | 0 | |
| K3 nothing below the hub face | 50 | 0 | |
| K4 inside the tip radius / ring | 50 | 0 | |
| K5 direction proof | 34 | **5** | 11 INCONCLUSIVE |
| K6 mirror | 39 | 0 | 11 N/A |
| K7 cup depth | 18 | **3** | 1 N/A (hub too small for the cup) |
| K8 tier equivalence | 11 | 0 | Volume and vertex count are equal, but **0/11 are byte-identical** |
| K9 tier memory | 11 | 0 | 6 of the T-16gb builds were SKIPPED_MEM |
| K10 determinism | 1 | 0 | |
| K11 readouts | 50 | 0 | |

**Stop rule:** not met (0 % K1 failures).

## Failure classification
- **K5 FAIL ×5: a direction-check artefact (false refusal), not a builder bug.**
  - The designs are CTL 9605, 9606, 9620, 9630 (the known refusals) and **S3_0002**, a new one from the normal guided_lc space.
  - All five read CONCLUSIVE (omega −1, pump +1) with agreement 1.0 over 22–33 sections.
  - They all have very low camber (0.0013–0.016), lean_tip 22–42°, 11 blades and stagger_root 32–47°.
  - The builder is correct by construction, and K6 passes on all five (the mirror flips). So the proof misreads lean curvature as camber. This feeds Task B.
- **K7 FAIL ×3 (S2_0000, S8_0002 edge stagger_root min, S8_0008 edge chord_root min): a real issue in the cup-build path.**
  - The automatic hub is only 12.72 / 12.62 / 10.92 mm tall, shorter than the 13 mm cup. The 13 mm cavity, cut up from the hub face, goes straight through the hub top, so there is no cup floor. The measured "floor" is the hub top.
  - `build_stl_isolated(motor_mount=…)` (the Preview cup path in `fan_viz.py`) doesn't enforce `MotorMount.min_hub_height_mm` (15) and doesn't refuse. Only Export's `prepare_export_flat(fit_hub=True)` grows the hub.
  - Not a threshold artefact: the grip count (20), protrusion (0.69 mm) and Ø 37.93 mm are all correct.
  - QA-16's reference is fixed on master: the cup now starts at the hub face (`z_bounds=(hub_face, …)`). For hubs ≥ 14.3 mm the floor reads 12.98–12.99 mm.
- **K8 note (finding, not a FAIL):** the tier builds have equal volume (≤ 1e-6) and vertex count, but their STL bytes differ in all 11 cases. The `resources.py` docstring's "byte-identical solid" claim does not hold at the file level.

## Time and memory per build kind
Medians cover all pilot builds. The few suspend-inflated builds (see below) barely move the medians.

| kind | n | median s | peak RSS MB (max) |
|---|---|---|---|
| P (8gb tier) | 50 | 25.9 | 5,495 (Stock control; typical design 2–3 GB) |
| C cup (8gb) | 21 | 23.3 | 5,500 |
| T-16gb | 6 run / 5 skipped | 22.2 | 4,241 |
| T-6gb | 11 | 78.0 | 4,727 |
| R | 1 | 19.4 | 2,456 |

- **Workers:** 1. MemAvailable on this shared box varies between 2.4 and 7 GB. Something outside these processes holds 5–9 GB, so a second worker doesn't fit with ≥ 4 GB free.
- **The 8.4 h T-6gb build** (CTL_0002 = design 9606, 11 blades) is **not an OCCT thrash.**
  - It peaked at only 2,464 MB, lower than its own 16gb build (3,942 MB). There is no swap to thrash, and it finished OK.
  - Its 600 s `subprocess.run` timeout (monotonic clock) never fired, even though it ran 30,072 s by wall clock (21:5x → 07:5x).
  - So the box/session was suspended overnight; the agent sessions were interrupted at the same time. Other wall-time outliers (P 375–430 s, T-16gb 886 s) are the same artefact.
- **Runner change after the pilot (logging only):**
  - Every build now records `mono_s`, `child_cpu_s` and `suspect_suspend` (wall − monotonic > 60 s). Flagged builds are left out of the timing tables.
  - The T-16gb memory wait went from 180 s to 60 s.
  - No wall-clock timeout was added: the pre-registered 600 s C/T timeout already exists, and a wall-clock timeout would record suspensions as false TIMEOUTs.

## Full run
- **Counts:** S1–S7 × 0.3 → 660 designs, plus S8 136 and the 5 controls = **801**. The 50 pilot designs are reused, so 751 remain.
- **Started:** 2026-10-10 08:58 MDT, pid 1129199.
- **ETA:** about 9 h if the box isn't suspended (≈ 18:00 MDT).
- Command:

      cd /workspace/fansim/repo-r6 && setsid nohup .venv/bin/python handoff/2026-10-09_from-qa-5/stress/run_stress.py \
        /workspace/fansim/qa/r6_stress/inputs.jsonl /workspace/fansim/qa/r6_stress/run \
        --counts /workspace/fansim/qa/r6_stress/counts.json > /workspace/fansim/qa/r6_stress/full_runner.log 2>&1 < /dev/null &

- Re-running the same command resumes it (ids already in `designs.jsonl` are skipped).
- **Cheap progress check:**

      python3 -c "import json;s=json.load(open('/workspace/fansim/qa/r6_stress/run/summary.json'));print(s['updated'],s['done'],'/',s['planned'],'eta_h',s['eta_h'],s['checks'].get('K1'),s['checks'].get('K5'),s['checks'].get('K7'))"
