# Claude → Cursor, 2026-10-29: you are the lead from here

Kimball has made Cursor the day-to-day lead, because Claude's weekly tokens run out too early to be reliable. This note says
where everything is, what is decided, what needs a judgment, and what to do with the old worktrees and branches. Claude
may still review when available, but **don't wait for Claude**.

## Where the progress lives (read in this order)

1. **`AGENTS.md`**: the rules (pre-register, no heavy CPU 4–9 PM, night queue, branch per task, the audit ledger). They
   are unchanged and still non-negotiable. You now also hold the "Claude lane" (judgment, rulings, pre-registrations): see
   "How to make rulings" below.
2. **`docs/release/RELEASE_PLAN.md`**: the board (M0–M4) and the single source of what's next.
3. **`docs/validation/audits/`**: every pre-registration, result and ruling, dated. The live ones:
   - `2026-10-17-prop-cfd-fix-prereg.md`: the prop CFD ladder, results of rungs A, B and A0, and the amended
     definition of "fixed";
   - `2026-10-19-prereg-amendments-r17.md`: R1.8 two-stage hang, CROR and EPJ amendments, rung B J points;
   - `2026-10-20-rulings-r18-r19-rungA.md`: the rung A0 rule, TUD prop accepted, CROR geometry stands, R1.7/R1.8
     approved;
   - `2026-10-18-lt120-validation-prereg.md`: lt120, frozen and queued;
   - `2026-10-18-cror-centrifugal-validation-prereg.md`, plus the r17 amendments: CROR and centrifugal.
4. **`docs/QA_REVIEW.md`**: grok's ledger and queue. **Grok only sees delivered copies**: every round needs a
   "▶ Next round" section **and** `handoff/<date>_to-qa-<n>/` with `CLAUDE_TO_QA.md` (call it what you like) plus
   `git bundle create <dir>/fansim.bundle master`. Then tell Kimball to send the folder.
5. **`night/queue.json`**: heavy jobs run at 00:30 from `T:/Projects/fansim-night`. Results go to `runs/night/<date>/`.
   Mark each job `done` or `failed` after reading its log. Exit 127, 0xC0000005 or 4294967295 after a green summary line is
   the known Windows OCCT/VTK teardown crash, not a failure.
6. **The physics ledger**: `python scripts/audit_status.py` must read 33/33 PROVEN with nothing CHANGED or UNREGISTERED
   before you merge physics. Re-prove a changed unit by running its `checks`, then
   `fansim.audit.status.record_pass(unit, fingerprint_unit(unit), report, date)`. The ledger file is
   `docs/validation/audits/ledger.json`.

## Worktrees and branches: what to do with each

| item | state | action |
|---|---|---|
| `T:/Projects/fansim-night` (detached worktree) | used by the `fansim-night-queue` Scheduled Task | **KEEP.** Never remove it, and never commit in it (it is reset to master every night) |
| `.claude/worktrees/admiring-shannon-7ada18` (`claude/admiring-shannon-7ada18`) | clean, merged | **discard:** `git worktree remove` it, then delete the branch locally and on origin |
| `.claude/worktrees/loving-goldstine-50aab9` (on `claude/practical-almeida-68db47`) | clean; its one commit (exempting `audit_archetype_direction_cfd.py` from the axial orientation guard) is **already on master** in equivalent form | **discard** the worktree and both branches (`claude/practical-almeida-68db47`, `claude/loving-goldstine-50aab9`, local and origin) |
| `.claude/worktrees/upbeat-sammet-4338b7` (detached at 51e116b) | clean, merged | **discard** the worktree and branch `claude/upbeat-sammet-4338b7` |
| `station-mapping-23-35` | a **failed** pre-registered experiment (roadmap §23.35, `docs/validation/audits/2026-10-09-station-mapping.md`) | **do not merge.** Keep it as the reference the roadmap points to, or replace it with a tag (`git tag attempt/station-mapping-23-35 station-mapping-23-35`) and then delete the branch |
| every other local branch (`margins-v4`, `push-planes-27-3e`, `too-close-r03`, `night-queue*`, `prop-jsweep`, `r17-*`, `r18-*`, `r22a-*`, `r33-install-guide`, `r11a-lt120-reference`, `hang-limit`, `cylinder-sections`, `axial-force-bem`, `qa-*`) | all merged into master | **safe to delete** (`git branch -d`, which refuses anything unmerged). Delete their origin copies too if present |
| `docs/release/RELEASE_PLAN.md.bak` (untracked) | a stray backup of the board | safe to delete; git has the history |
| `runs/night/wt-*` folders, if any appear | per-job worktrees the runner makes | `git worktree remove --force` them after reading the job's log, then `git worktree prune` |

## What is decided (don't re-open without Kimball)

- v0.1.0 = **every shipped surface validated** against published data, or labelled / hidden. Rig measurements come in v0.1.1.
- Stock ships with its gap stated (R1.4, done). Mixed-flow is labelled "experimental" (R2.4). Noise is never judged on
  the card (R0.4). 2 mm is the **printed**-blade hang (R1.8, done 10/10).
- The CROR geometry freeze stands: stagger is from the rotation plane, with 4 % camber. The expected result is "trends
  validated" at best (rulings §3).
- The TUD low-Re prop (Casalino 2021, CC BY) is the prop CFD **validation** case. BEMT is good on it (−5 / −7 %).

## Open judgment calls, with Claude's guidance

### 1. Prop CFD rung A0 (C-grid) FAILED: what next

The C-grid resolves the wall (y+ about 0.25) and C_d(0°) is right (−2.4 %). But C_l is −14 % at 5° and −44 % at 10°.
For SST on NACA 0012 at Re 6e6, the NASA TMR reference result is C_l(10°) ≈ 1.07, so a correct setup should pass
easily. **Treat this as a setup bug, not physics.** Pre-register an **A0b diagnostic** (it changes no pass rule) and check,
in this order:
1. **Bookkeeping:** that α is applied to the inflow (U = (cos α, sin α)) **and** that the force function object's
   `liftDir`/`dragDir` use the same α. A lift direction off by α, or α applied twice or not at all, gives exactly
   "drag fine, lift low and worse with α".
2. **Far-field distance:** C-grid radius in chords. Below about 50 chords lift drops noticeably; TMR uses about 500. Run 10°
   with the far field doubled. A > 2 % change in C_l means the domain is too small.
3. **Convergence:** the C_l history over the last 20 % of iterations at 10°. A steady SIMPLE that is still drifting or
   oscillating counts as INCONCLUSIVE, not a result.
4. **Grid:** 2× in each direction at 10°.

Record what each check changed. If A0 then passes with the setup fixed (no turbulence-model change), re-run rung A on
NACA 4406 **unchanged**, which is a fresh test. The 3-D prop mesher is not touched by this.

### 2. lt120 (R1.1a frozen and queued)

When the night results are in, apply `2026-10-18-lt120-validation-prereg.md` exactly:
- PASS = both high-flow points within ±10 % with the two meshes within 3 %;
- otherwise "trends" or FAIL as written.

Write the verdict in that file and set R1.1b on the board. No judgment is needed beyond the written rule.

### 3. grok round 21 (claims audit, VALIDATION draft, lt120 pre-check)

- **Claims audit (`docs/qa/notes/r21-A-release-claims-audit.md`):** every "overstated" or "unsupported" claim becomes a
  board task, either reworded or labelled. Accuracy claims may only say what an audit supports.
- **VALIDATION draft (`r21-B`):** adopt it as `docs/VALIDATION.md` for R3.8. Check every number against its linked
  audit, not against the draft.
- **lt120 pre-check (`r21-C`):** if grok found anything that contradicts the freeze, record it in the lt120 audit
  **before** reading the night results.

### 4. grok round 22

Queue it: the R3.1 leak check (once R3.1 lands), a re-check of A0b, and checks of CROR/centrifugal once those builds land.
Remember the delivery package.

## How to make rulings now that you hold the Claude lane

- A ruling that a written pre-registration doesn't already cover is written **as its own dated audit file before the
  data it governs**, marked "ruling by Cursor". It says what was decided, why, and what it costs if wrong.
- Never change a pass rule after seeing results. Amend only for reasons about the data *source* (as in r17's QA-46/47/48),
  and say so.
- Physics or accuracy claims that would ship to users get one independent check by grok before release.
- If a ruling is genuinely Kimball's (scope, release labels, hide vs label), set the task to `needs Kimball` with a
  one-sentence question.

## Board order (Claude's suggestion; the board is the authority)

1. R2.2 prop: A0b diagnostics → A0 → rung A re-run (day CPU, minutes).
2. R1.1b lt120 verdict (after the night run).
3. grok r21 follow-ups: claims → labels; VALIDATION.md (R3.8).
4. R2.3a / R2.5a / R2.5b: CROR and centrifugal builds, then night runs.
5. QA-51: the NeuralFoil prop backend.
6. M3: R3.1 export hygiene, R3.2 packaging, R3.4 Docker badge, R3.5 / R3.5b CI and the chunk runner, R3.6, R3.7, R3.9.
7. M4: release candidate.

Thank you for carrying it. The project is in good shape: every hard question so far has a written rule and a recorded
answer.
