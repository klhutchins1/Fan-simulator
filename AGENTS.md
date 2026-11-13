# Working on Fan Simulator (for every agent: Claude, Cursor, grok, others)

Read this first. Then open **`docs/release/RELEASE_PLAN.md`**, the single task board for the release. Take the
first task in your lane whose status is `ready`.

## The project in one paragraph

This is a desktop tool for designing 3-D-printable fans and propellers. It has a Trame cockpit UI
(`scripts/cockpit.py`), OpenFOAM CFD in Docker for "Assess", BEM/BEMT for fast screening, and STL export.
- The owner is Kimball.
- The goal is a public GitHub release where **every shipped feature is validated** against published data
  (printed-rig measurements come in v1.1).
- **Accuracy first:** correct maths before features. Saved designs are disposable. Nothing gets printed until
  the tools and maths are right.

## Rules (non-negotiable)

1. **Pre-register before data.** Any run that sets a threshold, accepts a model or judges a fix needs its
   pass/fail rule committed *before* the run, in `docs/validation/audits/<date>-<topic>-prereg.md`. If the
   result fails, record it. Never re-tune until it passes. INCONCLUSIVE is not a pass.
2. **No heavy CPU from 4 PM to 9 PM local time, any day.** The power bill has a peak-demand charge that a single
   run sets for the whole month. This covers CFD, optimizer runs, the full test suite and big builds. Run heavy jobs
   overnight or in the early morning as a Windows Scheduled Task that runs `.venv\Scripts\python.exe -u scripts\<runner>.py`
   **directly**, with no `cmd /c` wrapper. Each runner must write its own progress JSON after every unit and must
   not start a new unit after 3:30 PM.
3. **Branch per task**, merge to `master` with `--no-ff` when its gate is green, then push. Never force-push master.
   Small related changes (wording, labels, small QA fixes) go on **one branch with one gate**, not one branch each.
4. **Tests first** for every behaviour change: write the failing test and watch it fail. Run the related test
   files. Before merging anything shared, run the gate **yourself, the same day**:
   `.venv\Scripts\python.exe scripts\gate.py <branch>`. It runs the fast suite (about 45 minutes) in its own worktree,
   refuses if it could reach 4 PM, and prints the line for the board. Exit 0 = merge. Do not queue a test suite for
   the night unless it is after 2:30 PM and the merge cannot wait until morning. pytest rewrites tracked reference
   STLs, so restore them (`git checkout -- '*.stl'`) before committing.
5. **Physics changes** go through the audit ledger: `fansim/audit/registry.yaml` and `scripts/audit_status.py`.
   Re-prove any unit you touch.
6. **Don't touch another agent's uncommitted work.** If the tree is dirty with files you didn't write, stop
   and ask Kimball.
7. **Licences:** no NC-licensed data or unknown-origin STLs in the repo (`RELEASE_EXCLUDE`, `THIRD_PARTY.md`).
8. **Plain language in the UI.** Simple mode is for non-experts. Technical detail goes behind Expert.
9. **Accuracy work first, and never an idle night.** Take tasks in the board's "Work order", which puts the tasks
   that unblock a CFD validation run ahead of wording and packaging. If tonight's queue has no CFD job, the next
   task is whichever one produces one.

## Night jobs (how heavy work gets run)

- **Nights are for CFD and other long jobs.** Test suites run the same day with `scripts/gate.py` (rule 4).
- The Scheduled Task **`fansim-night-queue`** runs every night (currently 11:30 PM). It runs `scripts/night_queue.py`
  from its own worktree `T:/Projects/fansim-night`, which it first moves to `origin/master`. **Push** the queue change,
  or the job will not run.
- To run something heavy, add a job to **`night/queue.json` on master**: `id`, `branch` (optional; the job runs in a fresh
  worktree of it), `cmd` (`"python"` = the venv), `max_hours`, `status: "queued"` and `why`. A pre-registration must
  already be committed if the job judges anything.
- The runner never starts a job that is inside, or could reach, 4–9 PM.
- Results are in the **main** checkout: `runs/night/<date>/results.json` plus one log per job. A job runs once; set `status: "rerun"` to repeat it.
- After the last job the runner runs `scripts/morning_check.py --apply`. It sets each job to `done` or `failed` on
  master and writes **`runs/night/STATUS.md`**. Read that file first each morning: its "Needs an agent" list is the
  whole follow-up.
- Add `"merge_on_green": true` to a job to have the branch merged to master automatically. That happens only when
  every job for the branch is green, the branch has not moved since, master has changed nothing but docs since the
  branch forked, and there is no conflict. Otherwise STATUS.md says why and an agent merges. The script never writes
  the board: the task's owner still adds the `done <commit>` line.
- Long CFD campaigns that need many hours can still be their own Scheduled Task, under the same rules.

## Claiming and finishing a task

- **Claim:** in `RELEASE_PLAN.md`, set the task's status to `in progress (<agent>, <date>)` and commit that one line
  first.
- **Finish:**
  - set the status to `done <commit>`;
  - once nothing is left on a task, move its whole block to `docs/release/RELEASE_DONE.md` and leave one line on
    the board, so the board stays a list of open work;
  - add one line under the task saying what landed and what is left;
  - if the task produced a decision for Kimball, set it to `needs Kimball` with the question in one sentence.
- **Running out of tokens mid-task:** commit what works on the branch, set the status to `paused (<agent>)`, and write
  a 3–6 line **Resume** note under the task covering: the branch, what's done, the next step, and any traps.
  The next agent starts from that note.
- **Hand-offs** between agents go on the board, not in chat. The dated `handoff/` folders are for bundles and bulky
  data only.

## Lanes (who should take what)

| lane | best for | budget |
|---|---|---|
| **Claude** | occasional reviewer when available (since 2026-10-29 **Cursor is the lead** and holds judgment, rulings and pre-registrations too; see `handoff/2026-10-29_claude-to-cursor/CLAUDE_TO_CURSOR.md`) | scarce and unreliable week to week, so never block on it |
| **Cursor** | implementation from a written brief, refactors, packaging, docs, CI, UI tests | plentiful |
| **grok (QA bot)** | independent re-derivations, data hunts, clean-clone install tests on Linux, long test rounds; writes only new files: `docs/qa/rounds/r<NN>.md` (its round report, with any new or changed ledger rows), `docs/qa/**` notes and patches, and its `handoff/*from-qa*` folder. It never edits `docs/QA_REVIEW.md` or the board; the lead copies the rows in. Best use: independent re-derivations and bug hunts. Re-check a fix only when the bug was HIGH; one full claims audit at the release candidate | plentiful. **It works on a delivered copy, not this folder:** a round reaches it only as `handoff/<date>_to-qa-<n>/` (`CLAUDE_TO_QA.md` + a fresh `git bundle create … master`), which Kimball sends. Also put the same tasks in the "▶ Next round" section of `docs/QA_REVIEW.md` |
| **night** | CFD campaigns and heavy builds as Scheduled Tasks (rule 2) | free between 9 PM and 4 PM |

Cursor takes Claude-lane tasks. A ruling not covered by an existing pre-registration is written as its own dated audit
file **before** the data it governs, marked "ruling by Cursor" (see the 2026-10-29 handoff).

## Where things are

| what | where |
|---|---|
| backlog of every item (numbered §n.m) | `docs/roadmap.md` |
| release path + task board | `docs/release/RELEASE_PLAN.md` |
| QA bug ledger and grok's queue | `docs/QA_REVIEW.md` |
| validation audits, pre-registrations | `docs/validation/audits/` |
| physics audit ledger | `fansim/audit/registry.yaml`, `scripts/audit_status.py` |
| CFD setup that is validated | `docs/validation/`; Stock = a12x25, `stock_blade_flat("a12x25")` (Stock v3, wrapped sections) |
