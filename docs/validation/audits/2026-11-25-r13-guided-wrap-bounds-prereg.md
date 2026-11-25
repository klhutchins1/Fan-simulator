# Pre-registration: R1.3 guided optimizer bounds under wrap (2026-11-25)

Ruling by Cursor, **before** changing `GUIDED` in `fansim/optimize/search_space.py` (AGENTS.md rule 1).
Board: R1.3. Sources: grok r14 C (`docs/qa/notes/optimizer-space-wrap-r14.md`), grok r17 C
(`docs/qa/notes/r17-C-hang-refusals.md`), Claude start-here 2026-11-17 on the board.

## Why

Today's `GUIDED` stagger lowers (root 24°, mid 32°) sit **above** Stock v3 (root ≈ 23.5°, mid ≈ 31.2°), so the
rules-guided Optimize space cannot reach the parametric Stock recipe under wrap. r14 proposed P0 lowers those
floors (and raises the camber floor slightly) so Stock is inside the box. R1.7 and R1.8 are already on master;
r17 C measured P0 hang refusals at 2.0 % (Wilson 0.9–4.3 %) with both.

## Change under test

Apply r14 **P0** to `GUIDED` only (not `OPEN`, not `GUIDED_LC`):

| key | current | P0 |
|---|---|---|
| `stagger_root` | (24.0, 48.0) | (19.5, 48.0) |
| `stagger_mid` | (32.0, 48.0) | (27.2, 48.0) |
| `stagger_tip` | (18.0, 38.0) | (18.0, 38.0) unchanged |
| `max_camber` | (0.0, 0.06) | (0.015, 0.06) |

All other `GUIDED` keys stay as they are.

## Pass / fail (committed before the edit)

1. **Stock coverage (hard).** After the change, every of these Stock v3 (`stock_blade_flat("a12x25")`) values
   lies inside the new `GUIDED` interval (inclusive): `stagger_root`, `stagger_mid`, `stagger_tip`, `max_camber`.
   FAIL if any sits outside.
2. **Hang-refusal share (hard).** On 300 Optuna `RandomSampler(seed=14004)` draws through the cockpit guided
   path (same recipe as r14/r17: space `"guided"`, hub range that matches the cockpit, max tip 54.5 mm, no
   features/shroud), with the landed R1.7 export hub and R1.8 1.75× designed-hang prefilter, the refused share
   is **≤ 5.0 %** (point estimate). FAIL if > 5.0 %. Wilson 95 % interval is recorded report-only; it need not
   have upper bound ≤ 5 %.
3. **No other space.** `OPEN` and `GUIDED_LC` bounds are unchanged in this task. FAIL the task (not the data) if
   the patch edits them.

INCONCLUSIVE is not a pass. If (2) cannot be re-run cheaply in CI (geometry builds), a unit test of (1) plus a
source assert of the P0 numbers is the merge gate for this branch; (2) is then a recorded re-check against the
r17 C numbers (already PASS at 2.0 %) and is not re-tuned.

## Out of scope

- Re-finding a night Optimize campaign.
- Changing hang limits, hub growth, or printability.
- Widening tip stagger or chord beyond P0.
