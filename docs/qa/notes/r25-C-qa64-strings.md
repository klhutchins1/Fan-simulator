# QA r25 C: are the QA-64 strings still live? (master 9d0118f)

**Tested:** 2026-11-02, MST. **Prereg:** b7e7574e. **Brief:** Cursor's uncommitted draft.

**Method:** `grep -rn "near free air\|within 8"` over the whole tree, excluding `.git`, `.venv` and `archive/`. That gives 19 hits in 10 files (`handoff/2026-11-02_from-qa-25/data/c_grep_raw.txt`). There are no hits in `fansim/`, `README.md` or the cockpit copy.

**Live (release / audit sources):**
- `docs/validation/audits/2026-10-18-lt120-validation-prereg.md:89`: `- "Fan CFD: validated near free air on three published fans (within 8 %)."`
- `docs/validation/audits/2026-10-30-lt120-tip-gap-prereg.md:69`: `- "Fan CFD: validated near free air on three published fans, within 8 %."`
  - Last touched by 7be7109; `RELEASE_PLAN.md:87` says "The release wording is in that file, for R3.8 / R1.10".

**Board, not a claim:** `RELEASE_PLAN.md:92,94` (the grok r23 A / r24 B lines) quote it.

**QA record only:**
- `docs/QA_REVIEW.md` (4 hits);
- `docs/qa/notes/r23-A-lt120-knee.md` and `r24-B-qa64-wording.md`;
- `handoff/2026-10-31_from-qa-23/README.md`, `handoff/2026-11-01_from-qa-24/*` and `handoff/2026-11-01_to-qa-24/CLAUDE_TO_QA.md`.

**Verdict: still live (R1.10 not landed; `RELEASE_PLAN.md:169` R1.10 status `ready`).** Cursor has not changed the wording.

QA-64 stays **open (LOW)**. The r24 B proposed wording stands: "within 10 %", and for lt120 "at its lowest measured load (6.85 Pa)".
