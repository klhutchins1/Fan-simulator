# Wrapped-builder robustness, QA round 9 Task A (FINAL, truncated at 66/150)

**The run was stopped at 66/150 designs by user decision (Kimball), because of repeated box suspends.** Scored on
those 66 against the pre-registered rules.
- Code: branch `cylinder-sections` @ 7b02bed.
- Prereg: `PREREG_R9.md` (a0260c0) plus amendment A1 (9438a9b), which lowered the cup-build (C) memory gate to 3.5 GB.
- Sample: `handoff/.../data/a_sample.jsonl.gz`. Results: `data/a_results.jsonl.gz` (gitignored). Score:
  `data/a_analysis.json`, from `scripts/analyse_a.py`.
- **Coverage of the 66:** CTL 5, S8 10, shrouded 15, featured 15, notched 15, winglet 6. Not reached: tip-round,
  uneven spacing, plain. Notched and winglet options were set on random base designs (the population has none).
- Tasks B, C and E overlapped the first ~25 designs. 4 designs are excluded from W3 as suspend-flagged.

| rule | result | detail |
|---|---|---|
| W1 | **FAIL (1/66)** | S5_0167 (featured): the wrapped P build was SIGKILLed (exit −9) at a 7.7 GB peak; its planar build peaked at 7.4 GB and survived. Most likely the OOM killer on this ~8–9 GB-usable box. All other 65 wrapped builds are sound. |
| W2 | PASS | volume −2.4 % … +3.9 % vs planar, median +0.08 % (65 pairs) |
| W3 | **FAIL (1/61)** | S7_0160 (shrouded): wrapped 206.5 s vs planar 54.7 s. CPU time was 93 vs 58 s (~1.6×); the rest was contention. Median ratio 1.12. |
| W4 | PASS | 13/13 cup builds pass K7 |
| W5 | PASS | 0 CONCLUSIVE-wrong. The cylinder proof can't tell on **30/65 wrapped builds vs 24/66 planar**; all 30 wrapped ones are "no cambered sections" → **QA-33** |

QA-33 (LOW–MED): wrapped sections show their true camber, which often falls below the proof's 0.02 gate. Planar
builds picked up extra apparent camber from the cylinder cut. With wrapping the default, more designs will read
"can't tell".
