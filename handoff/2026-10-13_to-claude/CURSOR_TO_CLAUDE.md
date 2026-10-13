# Cursor → Claude, 2026-10-13

Kimball asked Cursor to brief both of you the same way you brief the QA bot. Round 9 is in
(`handoff/2026-10-12_from-qa-9/`, master `f2dba96` is docs-only). Hardware is delayed; **do not
print**. The print-blocking decision is wrap, not more cockpit UI.

Also a new parked feature: **§28 print-part ID** (hub code so a box of ~30 prints can be
re-tested against the export that made them). Spec is in `docs/roadmap.md` §28. **Do not
implement the cut** until QA’s mark-spec (their round-10 Task A) and wrap are on master.

## What you should be doing (stop the rest)

Drop the side branches (randomize-every-DOF, extra UX). One thread:

| # | task | why now |
|---|---|---|
| 1 | **Adopt wrap + Stock v3 and merge `cylinder-sections`** | Kimball’s call: **yes**, unless you have a *new* reason to reject. V5 FAIL vs planar is understood: planar is 6.5 % low vs the close-ref STL; wrapped is −1.2 % free / mean loaded gap 2.1 % vs 4.4 %. Surface-distance losing outboard does not override airflow-vs-real-STL. |
| 2 | **Do not CFD Grokbot’s round-9 surface-fit YAML** | T3 FAIL (V2 section limits at r/R 0.6 and 0.7). Diagnostic only. A later refit may add stations at 0.55/0.65 with V2 as hard constraints — not on the print-freeze path. |
| 3 | **Rewrite `docs/validation/first_print_measure_plan.md`** from the wrap *validation-rig* numbers (57.6 / 58.3 / 54.5), not the old 53.6 CFM / B/A 0.89. Article B is wrapped Stock once merged. |
| 4 | **27.2** builder refuse-only-when-both-readers-agree (round 8: ready). Wrap V4 already reads S3_0014; still ship the rule on master. |
| 5 | **27.1** fuse guard on *remaining* growth + shroud term (round 9: extra cost ~66 KiB per *blade* face, not ring faces / height). |
| 6 | **QA-32** honesty: BEM on hub-clipped sections. Not another loft. ~15 % of designs, camber 0.005–0.011 low at clipped stations. |
| 7 | **§28** only after (1) and after QA Task A. Registry/sidecar (28.2) may land without the cut if wrap is done and you have tokens. Glyphs (28.3) wait on the mark-spec. |

If you run out of weekly tokens: stop after (1)+(3). Cursor will pick up 27.1 / 27.5 / 28.2 from
the already-written tickets. Do not leave a half-merged wrap.

## Round 9, digested (please don’t re-find)

- **A** truncated 66/150. W2, W4, W5 PASS. W1 FAIL ×1 (featured S5_0167 SIGKILL ~7.7 GB). W3 FAIL ×1 (shrouded 1.6× CPU). **QA-33:** wrapped direction INCONCLUSIVE more often.
- **B** → **QA-32** (clip-reached camber/stagger). Off-clip 50/52 clean.
- **C** surface fit T1/T2 PASS, **T3 FAIL**. Do not treat the proposal YAML as Stock.
- **D** radial-led rule: **not a valid confirmation**. Truth cue (blunt LE / tip lead) is junk on plate prints. Chirality matched; omega cue did not. **Do not ship 27.2b. Do not start §26.**
- **E** shrouded fuse still above the guard on 9/11-blade rings.
- **F** near-stall: still not done. Leave it.

Keep planar YAML as `a12x25_reference_planar.yaml` (already). Optimizer trials found under planar
sliders are different blades under wrap — **do not print t9005 or catalog candidates**. Do not
restart the optimizer until wrap is master.

## §28 print-part ID (design; do not cut yet)

**Intent:** a month from now, a printed impeller in a box still names the export it came from
(recipe, `section_wrap`, git, CFD run, material), and Record measurement can attach a reading
to that row.

**Do**

- Issue a short Crockford code (4–5 chars, no `0/O/1/I` ambiguity) at **Export print STL**.
- Recess it on the **hub**, not the blades. Preferred face: **+Z inlet hub disk**, inboard of
  blade roots, 0.4–0.6 mm deep (hub-down print → last hub layers). Fallback: −Z annulus outside
  the cup, only if QA says +Z has no flat ring.
- Same string in: filename stem, export README (large type = sharpie fallback),
  `validation/prints/index.jsonl`, and later `validation/store.py` as `print_id`.
- Genuine Noctua (article A) has no code.

**Don’t**

- QR / text on blades, shroud OD, LE/TE, tip, cup grip pads.
- Cryptographic hash of the mesh.
- Computer-vision on the two already-printed unlabeled fans. Those stay `unknown`.
- CFD of the pocket unless QA’s dummy pocket is a non-trivial fraction of the hub face.

Existing hooks: `fan_export.do_export` (README + `*_print_fit.json` + handedness),
`validation/store.record_measurement` (`design_id` only today). The gap is the physical code
and the index. Optional Data Matrix next to the text is **after** the alphanumeric works.

QA is measuring the annulus now (round 10 Task A). Use their numbers for glyph size.

## What the QA bot is doing (don’t duplicate)

`handoff/2026-10-13_to-qa-10/CLAUDE_TO_QA.md`:

- **Now:** Task A = hub-face mark-spec on print-ready Stock (planar master). No fansim edits.
- **Not now:** wrap robustness 150-run, external STLs, near-stall, implementing §28.
- **Later:** wrap confirmation on the **merged** master. You send that as round 10b with a
  named commit + bundle, same as usual.

When wrap lands, write `handoff/YYYY-MM-DD_to-qa-10b/CLAUDE_TO_QA.md` yourself. Cursor already
parked the confirmation tasks in the round-10 brief so you can copy them.

## Conventions (yours, unchanged)

- Wrap merge is the one physics change. Cursor will not touch loft / Stock YAML / wrap.
- Do not start §26, NeuralFoil-as-default, tip-round/bio, or a new optimizer campaign.
- Roadmap is the source of truth; §28 is parked there.
