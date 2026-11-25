# R1.3 guided wrap bounds — result (2026-11-25)

Prereg: `2026-11-25-r13-guided-wrap-bounds-prereg.md` (committed before the `GUIDED` edit).
Branch: `cursor/r13-wrap-bounds`. Ruling by Cursor.

## What changed

`GUIDED` in `fansim/optimize/search_space.py` to r14 P0:

| key | before | after |
|---|---|---|
| `stagger_root` | (24.0, 48.0) | (19.5, 48.0) |
| `stagger_mid` | (32.0, 48.0) | (27.2, 48.0) |
| `stagger_tip` | (18.0, 38.0) | (18.0, 38.0) |
| `max_camber` | (0.0, 0.06) | (0.015, 0.06) |

`OPEN` and `GUIDED_LC` untouched.

## Pass / fail vs prereg

1. **Stock coverage — PASS.** `stock_blade_flat("a12x25")` stagger_root 23.5154, stagger_mid 31.1959,
   stagger_tip 22.4624, max_camber 0.0478 all sit inside the new `GUIDED` intervals
   (`tests/test_r13_guided_wrap_bounds.py`).
2. **Hang-refusal share — PASS (recorded re-check).** Not re-sampled here; grok r17 C already measured
   P0 at **2.0 %** (6/300, Wilson 0.9–4.3 %) with R1.7 + R1.8 on master (`docs/qa/notes/r17-C-hang-refusals.md`).
   Point estimate ≤ 5 %. Per prereg, CI gates on (1) + the P0 number assert; (2) is this recorded re-check.
3. **No other space — PASS.** Source assert freezes pre-R1.3 `OPEN` / `GUIDED_LC` stagger and camber.

## Audit ledger

Editing `search_space.py` CHANGED `optimize.search_space_handedness`. Re-ran its check
`tests/audit/test_search_space_handedness.py` (PASS: stagger > 0 and camber ≥ 0 still hold under P0 —
camber floor 0.015 > 0). `record_pass` with this report. Dependant AFFECTED units re-checked green
(see commit message / gate).
