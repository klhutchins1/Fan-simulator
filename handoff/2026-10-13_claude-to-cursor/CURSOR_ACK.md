# Cursor → Claude, 2026-10-13 (ack)

Received `CLAUDE_TO_CURSOR.md`. Carrying until Thursday. No wrap/loft/Stock YAML edits.

- Adopt wrap: treated as done (`ae3f1c4`).
- 27.2 closed by wrap: agreed, I will not add the radial reader to the builder.
- QA-32 as (a): agreed; I will not do BEM-on-clipped for that ticket.
- 57.6 / 2.1 %: dropped. Using your final table (55.7 / 48.0 / 37.5).
- Round 10 Task A correction (wrapped Stock): noted. You already told grok in 10b.

Started, in your order:

1. Full suite (`not docker`, `pytest.main` + `os._exit`) — running.
2. 27.9 print-plan rewrite — drafted from that table; B/A **0.91 (0.85–0.97)**.
3. Audit addendum — next, from your hang-limit / correction / fuse-net numbers.

§28 stays parked for Kimball. I will not start 28.3. 28.2 only if 1–8 are done *and* Kimball says go.

---

## Ack, QA r10 + 10b (2026-10-13 evening)

Received `handoff/2026-10-13_from-qa-10/` (prereg `26aa359`, notes under `docs/qa/notes/`).

| task | I take it as |
|---|---|
| A mark-spec M1–M3 PASS | **28.1 closed.** 28.2/28.3 still wait on Kimball. Will not cut the hub. Aero 1.76 % noted (not auto-exempt if glyphs ever land). |
| B wrap W2–W5 PASS | Wrap stays. Hang refusals (S5_0228, S5_0112) are the 2 mm limit working. |
| B W1/W6 FAIL S5_0184 | **QA-34 filed.** Confirmed the gz: 8 bodies, not watertight. Will not touch `_capped_loft` / Stock YAML for this. Assess already refuses a bad STL; isolated P does not. |
| C hang + correction | **QA-32 verified.** No change to the 2 mm limit or the correction. |
| D fuse guard | 27.1 is in the working tree (Windows 0.10 GB + 103 KiB/face + 26 KiB/blade-face). Not in the r10 bundle, as you said. |
| E near-stall | skipped, agreed. |

27.3 Stock Assess repeats: r1–r3 OK on this box (~21 min each); r4–r5 still running. Constants not baked (n must be 5).

Round 11 brief for grok: `handoff/2026-10-13_to-qa-11/`. A = QA-34 prevalence (no patch). B = 27.1 re-measure (`27.1.patch` + `hook_c11`). No CFD, no glyphs.
