# Cursor → Claude, 2026-10-15

Kimball’s weekly Claude tokens are back. Cursor carried the cockpit from your Thursday
handoff (`handoff/2026-10-13_claude-to-cursor/`) through 24.2/24.3. **Do not print.**
Wrap is already master (`ae3f1c4`). Do **not** re-merge, rebase, or touch the loft.

Pull **master at the commit that added this folder** (product is `e527a67`; this brief
sits on top). Origin: `git@gitea:klhutchins/Fan-simulator.git`.

## What you should be doing (stop the rest)

Drop the side branches (`claude/admiring-shannon-7ada18` randomize-every-DOF, extra UX).
One thread:

| # | task | why now |
|---|---|---|
| 1 | **29.1 / QA-36 — PLA+ picker actually builds PLA+** | Grok r12 Task D: chip / Assess stamp / optimizer follow `assess_material`; Preview grams and Export README / nozzle / bed / `print_fit` / registry still read `active_spec().material` (PETG). Tests to adopt: `handoff/2026-10-14_from-qa-12/tests/test_ui_says_what_it_does_r12.py` (the two material tests FAIL on HEAD by design). No CFD. |
| 2 | **QA-35 — Linux remaining-growth still under-asks open 9/11-blade fuses** | 27.1 shipped remaining-growth + shroud term. R12: S7_0172_twin (open, 11 blades, 22.7 k faces) 2.19 GiB vs ask 2.12 GiB (1.03×, 3/3). Shrouded ≤ 0.80×. Refit the **open** intercept/slope; do not loosen the shroud term. Notes: `docs/qa/notes/fuse-remaining-r12.md`. |
| 3 | **24.4 — investigate only** | Job × setting → a/b/c/d table (roadmap §24.4). Recommend lock / snapshot / queue. **No fix until Kimball picks one.** QA-22 snapshot already covers Assess; this is the leftover while Preview/Export/Optimize run. |
| 4 | **QA-12 CT0 creep** | Still open. Polar math, not cockpit. Only after 1–2, or if you want a physics slice in parallel with 3. |
| 5 | **QA-37 (LOW)** | Killing the cockpit mid-Export does not stop the isolated worker; orphan STL with no README/sidecars. Optional. |

If tokens run short: stop after (1). (2) is the next physics item. Do not leave a half-wired material path.

## What Cursor landed while you were out (do not re-find)

On `e527a67` (Kimball signed off the Simple copy 2026-10-15):

- **23.56 Preview overlap freeze.** Randomize → Fit → Preview (still running) → Randomize → Preview
  froze the 3-D view with an empty JS console. `preview_busy` is now set **before** `create_task`;
  Randomize / Fit / Scale / Reset / seed are disabled and no-op while Preview/Assess/Export/Optimize
  run. A session already wedged needs a cockpit restart (Ctrl+Shift+R / new tab — leftover VTK tab
  reconnects and dies again).
- **23.57 websocket “client not reading 15 s”.** Often loop starvation: VTK `_draw` / `view_update`
  blocked asyncio, `wait_for` expired, guard aborted the **only** tab. `ws_guard` retries when
  `n_sent==0` and the tick was overdue ≥ 0.2 s; a real stall still aborts and the log says to
  hard-refresh.
- **23.58 / 23.59 Results click.** Impeller STL first (rotatable), then overlay from `cockpit_viz`
  cache / glyph VTP. Loading bar: “Loading 3-D overlay from the saved run (not a new CFD solve)…”.
  Assess is the only re-solve. Leftover arrows cleared. Direction-cue meshes reused.
- **Flow-report VTK flood.** `flow_report_viz` `_face`/`_side` had gone back to raw `.slice()`;
  they use `slice_volume_for_viz` again.
- **27.8 hang UX follow-up.** Hang is still designed TE vs hub face; Preview clips so the mesh
  looks flush. Fit envelope grows hub height until hang ≤ 2 mm (when depth allows). Scale-to-hub
  forwards the same intake-overbuild max depth. Green envelope is outlet-anchored so overbuild
  does not lift z_lo and paint the hub-face TE red.
- **24.2 / 24.3 copy, Kimball signed off.**
  - Start here: `Start here: 1) Pick a design ↓  2) Preview  3) Assess  4) Optimize (optional)  5) Export STL when happy.`
    Durations stay on the banner and buttons.
  - Empty Results hides the flow card (`trial_items.length < 2`).
  - Tabs: Mixed/Volute/CROR · estimate, Prop · fast estimate. Simple strip:
    `Fan: printable PC-fan blades (CFD). Prop: propeller (fast estimate).`
  - Prop Simple banner skips BEMT/Audit; Expert Prop banner keeps it.
  - Mixed/Volute/CROR stay Expert-only (bounce to Fan in Simple).
- Tests Cursor ran on this tree: 105 passed (`test_simple_mode_copy`, `test_ws_guard`,
  `test_fan_tab_parse`, `test_flow_report_viz`, `test_hub_hang`, `test_intake_overbuild`,
  `test_placement`, `test_fan_tab_setup_smoke`). Parent still dies 0xC0000005 / 0xC0000374
  after green — OCCT teardown, ignore. Wrap the suite with `os._exit` as before.

## Grok r12 + r13, digested (please don’t re-find)

Returns live under `handoff/2026-10-14_from-qa-12/` and `…_from-qa-13/`. Notes in
`docs/qa/notes/`. Ledger: `docs/QA_REVIEW.md` (QA-35…38). **No round 14 is queued** unless
you write one after (1).

| round | task | result |
|---|---|---|
| 12 A | QA-34 strip | **PASS.** Featured wraps watertight after sanitize. |
| 12 B | 27.1 remaining | **FAIL 1/26** → **QA-35**. |
| 12 C | 28.2 print-id | **P0–P4 PASS** (SB862) → **QA-37** (LOW, orphan worker). |
| 12 D | PLA+ picker | Chip/Assess/optimizer follow; Preview grams + Export README stay PETG → **QA-36** = 29.1. |
| 12 E | UI tests | Proposal in `from-qa-12/tests/`; 2 FAIL on HEAD (intended). |
| 13 A | 24.2 Simple vs Expert | S0–S3 **PASS**. S4 scatter body below the fold at 1366×768 → **QA-38** (LOW). |
| 13 B | duplicate-after-run | Report table; Cursor hid the Results repeats + empty flow card. |
| 13 C | chunked pytest RSS | **M0/M1 PASS**, 1777 passed, peaks 5.1 / 2.9 / 6.9 GB. |
| 13 D | other-tab captions | Mixed/Volute/CROR/Prop were identical Simple vs Expert *on 143d5a8*. After 24.3, Prop banner is gated and Mixed/Volute/CROR are Expert-only tabs — inventory is partly stale. Do not rewrite those inner Expert essays unless Kimball asks. |

## What grok / Cursor will not do (don’t duplicate)

- **28.3 glyphs** parked until Kimball un-parks.
- **§26 Bring-your-STL** parked.
- **27.2b** external radial-led rule: unconfirmed, do not ship.
- **27.7** optimizer campaign: proposal is already in the roadmap. Do **not** restart the optimizer.
- **Wrap / loft / `_capped_loft` / `correct_clipped_sections` / Stock YAML.** Physics freeze.
- Printing. Hardware is still delayed. First-print plan is 27.9 (B/A **0.91 (0.85–0.97)**).
- Absorbing `logs/`, `docs/qa/notes/fea-blade-modes-proposal.md`, or
  `handoff/2026-10-14_from-qa-research/` — leave those uncommitted.

## Conventions (yours, unchanged)

- Roadmap is the source of truth. Next line already points at 29.1 / QA-36.
- Simple-mode copy: first-time hobbyist; Kimball signs off every new sentence. Do not invent
  long essays. Expert may keep BEMT / Audit / proxy in inner panels.
- `git apply` QA patches: re-implement instead.
- Long runs: Windows Scheduled Task, not shell `&`.
- `FANSIM_CACHE_DIR` for a fresh loft-chord cache. `LOFT_CACHE_VERSION` is 5.

## Gotchas on this box

- Frozen 3-D + empty JS console = server loop / VTK, not the browser.
- After a 15 s websocket drop of the only tab: hard-refresh or a **new** tab. A leftover wedged
  VTK session reconnects and dies again.
- Pytest parent ACCESS_VIOLATION after a green run is OCCT teardown.
- Memory tier: `fansim.resources.current_tier()` from free RAM.
- Two Prop `VAlert`s share `v_model=("prop_ux_banner",)` — dismissing Simple also hides Expert.
  Harmless; fix only if you are already in `prop_tab.py`.
