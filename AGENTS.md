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
3. **Branch per task**, merge to `master` with `--no-ff` when its tests pass. Never force-push master.
4. **Tests first** for every behaviour change: write the failing test and watch it fail. Run the related test
   files, plus `scripts/pytest_chunks.py --chunks 3 --all -- -m "not docker and not slow" -q` before merging anything
   shared. pytest rewrites tracked reference STLs, so restore them (`git checkout -- '*.stl'`) before committing.
5. **Physics changes** go through the audit ledger: `fansim/audit/registry.yaml` and `scripts/audit_status.py`.
   Re-prove any unit you touch.
6. **Don't touch another agent's uncommitted work.** If the tree is dirty with files you didn't write, stop
   and ask Kimball.
7. **Licences:** no NC-licensed data or unknown-origin STLs in the repo (`RELEASE_EXCLUDE`, `THIRD_PARTY.md`).
8. **Plain language in the UI.** Simple mode is for non-experts. Technical detail goes behind Expert.

## Night jobs (how heavy work gets run)

- The Scheduled Task **`fansim-night-queue`** runs every night at **00:30**. It runs `scripts/night_queue.py` from its own
  worktree `T:/Projects/fansim-night`, which it moves to the latest local `master` first.
- To run something heavy, add a job to **`night/queue.json` on master**: `id`, `branch` (optional; the job runs in a fresh
  worktree of it), `cmd` (`"python"` = the venv), `max_hours`, `status: "queued"` and `why`. A pre-registration must
  already be committed if the job judges anything.
- The runner never starts a job that is inside, or could reach, 4–9 PM.
- Results are in `runs/night/<date>/results.json` plus one log per job.
- The next agent reads them, sets each job's `status` to `done` or `failed` with a note, and acts on the board.
- Long CFD campaigns that need many hours can still be their own Scheduled Task, under the same rules.

## Claiming and finishing a task

- **Claim:** in `RELEASE_PLAN.md`, set the task's status to `in progress (<agent>, <date>)` and commit that one line
  first.
- **Finish:**
  - set the status to `done <commit>`;
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
| **Claude** | physics/maths judgment, pre-registrations, reviewing physics changes, rulings | scarce: runs out early in the week, so keep it for judgment |
| **Cursor** | implementation from a written brief, refactors, packaging, docs, CI, UI tests | plentiful |
| **grok (QA bot)** | independent re-derivations, data hunts, clean-clone install tests on Linux, long test rounds; edits only `docs/QA_REVIEW.md`, `docs/qa/**` and its `handoff/*from-qa*` folder | plentiful; reads its queue from the "▶ Next round" section of `docs/QA_REVIEW.md` |
| **night** | CFD campaigns and heavy builds as Scheduled Tasks (rule 2) | free between 9 PM and 4 PM |

A task can move lanes. If Claude is out of tokens, Cursor may take a Claude-lane task **only when** the task's brief
contains the full pre-registered rule. Otherwise it waits.

## Where things are

| what | where |
|---|---|
| backlog of every item (numbered §n.m) | `docs/roadmap.md` |
| release path + task board | `docs/release/RELEASE_PLAN.md` |
| QA bug ledger and grok's queue | `docs/QA_REVIEW.md` |
| validation audits, pre-registrations | `docs/validation/audits/` |
| physics audit ledger | `fansim/audit/registry.yaml`, `scripts/audit_status.py` |
| CFD setup that is validated | `docs/validation/`; Stock = a12x25, `stock_blade_flat("a12x25")` (Stock v3, wrapped sections) |
