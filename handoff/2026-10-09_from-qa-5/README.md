# QA handoff, round 6 (from-qa-5). Tasks B–E (the stress/ subfolder is Task A's, not mine)

- **B (direction attempt 2):** done on partial stress data (n=120 of 801). Option (a) removes all 7 K5 false refusals, adds 0 new refusals and catches 95/95 K6 mirrors. P1, P2 and P4 PASS; P3a, P3b and P5 are untested (they need a build or a patch). See docs/qa/notes/direction-attempt-2.md; scripts: flatten_stress.py, then direction_option_a_count.py.
- **C (motor efficiency):** done. docs/qa/notes/motor-efficiency.md proposes η_m = 0.50 (range 0.40–0.65). The 1.68 W input is a start-up maximum; the measured draw is 1.3–1.5 W.
- **D (benchmark library):** done. docs/qa/benchmarks/ has 8 fans, 3 with full geometry, plus the BEM comparison. Scripts: scripts/make_lib.py, scripts/run_bem.py.
- **E (near-stall flag):** not started (optional; time spent on D quality).

## Task A: builder stress test (the other QA worker), partial
- **Status: partial. Stopped early by Kimball; n = 120 of 801 planned.**
- Outputs: `stress/summary.md` (rate table, findings, K5 map, timing/memory), `stress/PILOT.md`, `stress/repro/`, `stress/designs.jsonl.gz` and `stress/inputs.jsonl.gz` (both gitignored, copy them by hand).
- Prereg `docs/qa/stress/PREREG.md`, in `/workspace/fansim/qa/prereg_r6`: A0 `30ea579` (sha256 `3e716d56…dfa602`), amendments `5cf4a3a` (sha256 `d3379f0e…4bbb3`).
- **Findings:**
  - QA-18: the motor cup goes through hubs shorter than 13 mm.
  - QA-19: `prove_direction` falsely refuses low-camber, high-lean designs (7).
  - QA-20: the memory tiers' STLs are not byte-identical.
  - QA-21: the tip trim raises on a featured S5 design.
- **The full run was slow** because of box freezes (about 6.1 of 7.1 wall-hours), not because of the builds.
- Follow-up for the runner: log chirality from the proof (raised by Task B).
