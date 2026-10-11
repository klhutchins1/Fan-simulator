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

## Result

(filled in after the run)
