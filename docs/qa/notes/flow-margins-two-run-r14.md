# Round 14, Task F: 27.3d flow-card margins for a two-run difference (numbers only, v3 table)

Prereg 586bbe9 (F1–F3). Input: the queue's m1–m5 table for five Stock v3 Assess runs (base cell
5.6/5.8/6.2/6.4/6.6 mm, surface level 4). These are **v3 planes**. Script `scripts/f_margins.py` → `data/f_margins.json`.

- **F1 (my 2σ rule vs Claude's numbers): FAIL as strictly registered, a rounding issue.** Bars 0.08 ✓. Mean push:
  2σ/|mean| = 2.81 % → my ceil-to-2-dp gives 0.03 (2.9 % appears only if 2.81 is rounded up first). Noise: 2σ =
  32.67 → 32.7 dB vs the queue's 32.8. The table's own 1-dp rounding allows a true value up to 32.78, so 32.8
  is reachable. No formula defect.
- **F2 (max |Δ| over all 10 pairs):** mean push 3.48 % (m3/m1; 2 pairs exceed today's 3 %). Worst bar 9.5 %
  (bar 1; 3 pairs exceed 8 %). dead_frac 0.009. Backflow 0.0189. Tip ratio: min pair ratio 0.861 (3 ordered pairs
  trip ×0.90). Nothing trips master's current 0.06 / 0.12 / CLOSE 0.15.
- **F3 proposal (v3):** mean 0.04, bars 0.10, dead 0.02, tip ×0.86, backflow 0.02 (the smallest round values no
  same-fan pair trips). The √2·2σ alternative gives 0.04 / 0.12 / 0.02 / 0.03 / tip 0.17. Rows that would flip to
  "about the same": 0 of 8 (9604/9610 same-mesh v3 deltas from the 2026-10-16 audit Q1 table; my r7 Task G rows
  were not kept on this box).
- **Superseded for v4:** Claude's 27.3e audit measured more mesh scatter on v4 planes (2σ 5.7 %) and baked
  BAND_TOL 0.06 / BAR_TOL 0.12. Re-derive F2/F3 on the v4 fields before using any of these numbers.
