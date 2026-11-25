# Pre-registration: FAN-01 re-run against its measured curve (RV-2, 2026-11-24)

Written by Claude at Kimball's request, **before** the run (AGENTS.md rule 1). It closes RV-2's question 2:
FAN-01 was reported (+2.5 % / +3.1 %) but never judged, because no pass mark was set before its first run
(2026-09-28, audit-02).

## In plain words

We already know the old answer, so a pass mark written today cannot be applied to the old numbers. This file
sets the pass mark for a **fresh run**. The mark is not chosen by looking at FAN-01. It is copied from the
mark the project already uses for the other two fans, so all three are judged the same way.

## The question

Does the Fan CFD, as it is on `master` at the time of the run, match FAN-01's measured flow on the stable part
of its curve?

## The run (fixed now)

```
python scripts/run_fan01.py --points 7,64,126,135,205,253 --iters 1000 --base-cell 0.02 --out runs/fan01-rv2
```

- Same geometry, rpm (1486), mesh size and iteration count as the 2026-09-28 run. `--procs` may differ
  (it changes speed, not the answer). Record the `master` commit and `--procs` in the results.
- One mesh, as in the original run. This is weaker than lt120, which also required two meshes to agree within
  3 %. That limitation is stated in the result, not fixed afterwards.

## The pass mark

| what | rule |
|---|---|
| judged points | **7 Pa and 64 Pa** (free delivery to mid-curve) |
| tolerance | CFD flow within **±10 %** of the measured flow at each judged point |
| where ±10 % comes from | the existing free-air interim band (`docs/roadmap.md` §10, set 2026-09-14) and the lt120 rule (`2026-10-18-lt120-validation-prereg.md`). It was not chosen with FAN-01 in mind |
| measured flow | `measured_q_m3s` at each point, from `validation/reference/fan01/characteristic.csv` as the runner reads it |
| converged | the runner's own `converged` flag for that point |

**Verdict:**
- **PASS**: both judged points converged and within ±10 %.
- **FAIL**: any converged judged point outside ±10 %.
- **INCONCLUSIVE**: any judged point not converged. INCONCLUSIVE is not a pass.

**Not judged, recorded only:** 126, 135, 205 and 253 Pa. These are the design point and the stall region, where
steady RANS with a frozen rotor is a known method limit (audit-02 §1, the same reason no near-stall A12x25
point is claimed).

## After the run

- Commit the rows as `docs/validation/fan01/fan01_cfd_rv2.json` and switch the two FAN-01 scoreboard rows to it,
  with this file as their tolerance source.
- Write the verdict below. Do not change the mesh, iterations, points or tolerance to rescue a FAIL or an
  INCONCLUSIVE. A different question needs a new pre-registration.

## Where to run it

About 3.5 h on the Windows PC (16 procs), as a night-queue job or its own Scheduled Task (AGENTS.md rule 2), or
roughly twice that on the 8-core laptop. Kimball chooses.

## Result

**Attempt 1 (2026-11-25, laptop, master `d816438`, 8 procs): no data.** `snappyHexMesh` was killed with exit 137
(SIGKILL) at about 2.0 M cells, during refinement, before any point was solved. A full test suite (3 pytest
processes) was running on the laptop at the same time, and zram swap showed use, so this is most likely memory;
the kernel log was not readable to confirm it. This is a failed run, not a result: nothing is judged from it.

**Attempt 2 (2026-11-25 12:01, same command, master `d816438`): no data.** Killed (exit 137) at 12:57:01 in
`simpleFoam`, iteration 232 of the first point, before any point finished.

**Cause of both (found 2026-11-25, `claude/cfd-session-scope` `74fe176`): not memory.** A process with no
`FANSIM_CFD_SESSION` did an unscoped container cleanup that `docker kill`ed every `fansim_cfd=1` container
without a session label. `tests/test_cfd_watchdog.py::test_run_watched_kills_on_hard_cap` reaches that cleanup for
real, and Cursor's test-suite gates on the same laptop ran it at about 11:00 and 12:57. The runs died from
outside; nothing about FAN-01 caused it, and nothing is judged from either attempt.

**Attempt 3:** the same command, from `master` once that fix is merged (its containers carry a session label, so
even an old-code cleanup skips them).
