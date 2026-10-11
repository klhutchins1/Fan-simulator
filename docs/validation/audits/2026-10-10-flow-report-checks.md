# Flow report card: do the verdict rules behave on real runs? (pre-registered 2026-10-10)

Spec: `docs/superpowers/specs/2026-10-10-flow-report-card-design.md` (Validation §2–4). Thresholds are the
spec's verdict table, fixed before this run:
- backflow Δ ≤ +0.02;
- bands ±10 %;
- swirl ≤ 1.10 × Stock;
- dead ≤ Stock + 0.02 and tip ratio ≥ 0.90 × Stock;
- noise ΔSWL ≤ +1.0 dB.

**Reference:** `runs/screen_rank_audit/stock_hubclip/full` (Stock, 2026-10-09, hub clip, level-4 floor,
case hose).

| id | check | pass rule |
|---|---|---|
| F0 | Flow-axis assumption | the reference's mean exit Uz > 0 (forward = +Z). If not, stop: the measurements need a sign fix first |
| F1 | Self-consistency | reference vs itself: every row ✓, every band "similar", overall "About the same as Stock on every check." |
| F2 | Run-to-run | `runs/screen_rank_audit/stock/full` (Stock, pre-clip, same settings) vs the reference: every row ✓ and every band "similar". If it fails, the failing threshold is widened to the smallest value that passes; the old and new values and the reason are written here and in the spec, then the run is repeated |
| F3 | Known stall | `runs/screen_rank_audit/r3_9610/full` (near stall on the fine mesh) gets ≥ 1 ⚠. **No tuning for this**: if it fails, record FAIL and ask Kimball |
| F4 | Known best | `runs/screen_rank_audit/t9005/full` gets no ✕, and its overall line names more "better" than "worse" rows |

`r3_9604/full` is run as well and reported, with no rule.

## Result (2026-10-10, `scripts/flow_report_checks.py` → `runs/screen_rank_audit/flow_report_checks.json`)

### Run 1, rules exactly as registered

| id | verdict | evidence |
|---|---|---|
| F0 | PASS | mean exit Uz +2.475 m/s |
| F1 | PASS | all ✓, "About the same as Stock on every check." |
| F2 | **FAIL** | Stock-prev vs Stock: noise ⚠ (ΔSWL +2.75 dB) and band 2 "stronger" (+19.6 %) |
| F3 | PASS | 9610: direction ⚠, dead ⚠, noise ⚠ |
| F4 | PASS (but see below) | t9005: no ✕; better 2 / worse 1. Its push read "weaker" in 4 of 5 bands |

### Measurement fix (a definition error, not a threshold change)

Run 1's "push" was the total-pressure rise p + ½|U|², which **counts the swirl kinetic energy as push**:
- Stock leaves 62 % of its exit kinetic energy as swirl; t9005 leaves 33 %.
- So Stock's push looked stronger than that of t9005, the better fan. Swirl is already its own row
  ("wasted spin"), so this double-counted it.
- **Changed:** push = static + forward dynamic pressure, p + ½Uz², with swirl excluded.
  `FLOW_REPORT_VERSION` 1 → 2; test `test_band_rise_excludes_swirl_energy` (failed first, then passed).
- This change was made after seeing data, and it is recorded here for that reason. It changes what is
  measured, not a threshold.

### Run 2, corrected push

F2 still failed: band 2 differed by +14.3 % and noise by +2.75 dB between the two Stock runs. Following
F2's own rule, each failing threshold was widened to the **smallest value that passes**:

| threshold | registered | now | why |
|---|---|---|---|
| push band tolerance | ±10 % | **±15 %** | Stock run-to-run 14.3 % |
| noise margin | +1.0 dB | **+2.8 dB** | Stock run-to-run 2.75 dB |

### Run 3, final

| id | verdict | evidence |
|---|---|---|
| F0 | **PASS** | +2.475 m/s |
| F1 | **PASS** | all ✓ |
| F2 | **PASS** (after the widening above) | all ✓, "About the same as Stock on every check." |
| F3 | **PASS** | 9610: direction ⚠ (backflow 8.4 % vs 2.8 %), dead ⚠ (tip ratio 0.27 vs 0.91), noise ⚠ |
| F4 | **PASS** | t9005: all ✓. "Better than Stock at: push along the blade, wasted spin, dead or blocked air." |

**9604 (reported, no rule):** "Better at wasted spin; worse at push, noise".
- Its push bands are 3–13 Pa against Stock's 8–17, and its noise is **+24.9 dB**, while its scored load
  CFM is higher than Stock's.
- That combination is suspicious: possibly an unsettled k field, or the measuring planes catching the
  frame struts.
- **Follow-up (roadmap §24.1):** check 9604's convergence and k field before the card is relied on for
  noise. The noise row already says "rough estimate, compare only".

**Reading:**
- The noise proxy and the per-band push vary 2.75 dB and 14 % between two runs of the *same* fan.
  Differences smaller than that are noise, which is why those rows now use the wider margins.
- The direction, spin and dead-air rows were stable run-to-run.
