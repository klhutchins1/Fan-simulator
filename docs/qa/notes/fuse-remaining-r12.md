# 27.1 remaining-growth guard on master 143d5a8 (round 12 Task B)

Prereg `42004b3`. The sample reuses the round-9 Task E IDs: same selection code, and the ID list matches the r9 file exactly. That is 28 builds: 12 shrouded S7, 12 open twins and 4 controls.
Hook `handoff/2026-10-13_to-qa-11/hook_c11`, 8gb tier, FANSIM_FUSE_GUARD unset, serial.
remaining = (VmHWM_exit − VmRSS_call)·1024; ask = 1.15·fuse_remaining_estimate_gb(...)·2³⁰.

**Result: FAIL, 1 of 26 paired OK builds.** S7_0172_twin (open, 11 blades, 22 729 faces at the call) had
remaining 2.185 GiB against an ask of 2.117 GiB (ratio 1.032). An unregistered repeat of that build (×3) gave 2.213, 2.213 and 2.185 GiB,
so the overshoot is real and not noise. Without the 1.15 margin the estimate is 1.84 GiB, which is about 19 % low for this build.

| kind | n | remaining/ask min–max |
|---|---|---|
| shrouded | 11 | 0.58–0.80 |
| open twin | 11 | 0.71–**1.03** |
| open control | 4 | 0.73–0.96 (S5_0223, 86 k faces: 0.96) |

- Shroud term: on every shrouded call, `n_blade_faces == n_faces − 4`. Shrouded builds sit well under the ask (≤ 0.80), so the
  66 KiB/blade-face term is, if anything, generous.
- Open builds are the tight side. Every twin with 9 or 11 blades (≥ 18.6 k faces) lands at 0.91–1.03. The 72 KiB/face slope is too low for those
  open builds on this HEAD. Faces at the call went up since r9 (S7_0172_twin: 21 596 → 22 729) and so did remaining growth (1.70 → 2.19 GiB).
- Not OK (excluded from the ratio): S7_0097 and its twin are **refused (hang)**. The blades hang 3.4 mm below the hub's motor face, against the 2 mm limit, which
  did not exist in r9.
- → **QA-35**.

Data: `data/b_results.jsonl`, `b_results.calls.jsonl`, `b_analysis.json`, `b_repeat_S7_0172_twin.jsonl`.
