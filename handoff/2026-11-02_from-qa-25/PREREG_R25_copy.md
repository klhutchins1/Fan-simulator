# QA round 25 pre-registration (grok, QA bot)

Written 2026-11-02 MST, before any round-25 data.

**Brief:** `handoff_in/CLAUDE_TO_QA_r25_DRAFT.md`.
- This is Cursor's **uncommitted draft**, verbatim. It is not in any commit.
- It says `fansim.bundle`. That file doesn't exist; Kimball named `master_9d0118f_plus_r111.bundle` instead.

**Code:** `/workspace/fansim/repo-r25`, a fresh clone of that bundle.
- master = 9d0118f.
- `origin/r111-hide-surrogate` = 237a094: 7 commits not on master, unmerged. The merge-base with master is b0228fe.

**Seen before writing this:**
- the draft brief;
- the commit subjects on both heads (`git log --oneline`);
- Kimball's message: 9e36cea says R1.11 is OK to merge but needs a CLI stub path plus a behaviour test; 9d0118f adopts my QA-65 patch under R1.2.
- My own r24 patch, which I wrote.

**Not yet opened:** any diff or file content of 9d0118f, 9e36cea or the r111 commits; any render; any pytest output.

## Status words

**On branch r111-hide-surrogate @237a094** (task A only):
- "fixed on branch (pending merge)";
- "still open on branch";
- "not re-tested".

Every A result carries the label "verified on unmerged branch r111-hide-surrogate @237a094, not on master".

**On master 9d0118f:**
- "verified": only for something that is on master;
- "still open";
- "not re-tested".

Nothing is closed unless it is on master.

## A. UI-31 / QA-62, plus the other UI and bug items

**Method:**
- Run A on the branch (checkout 237a094 in a second clone, `/workspace/fansim/repo-r25-r111`). Repeat the same checks on master 9d0118f.
- Cockpit: headless on :8080, Playwright with system Chrome. Only Preview may be clicked.
- No Optimize, Assess, Sweep or CFD. `run_optimization.py` is **not executed**; it is read, and its pure guards are called directly.
- The other items use the PREREG_R24 (88c4e79) per-item rules and the same harnesses, unchanged.

**UI-31 sub-checks.** UI-31 is fixed only if all of these hold:
- (a) **render:** no visible control whose label contains "Surrogate-guided" is rendered in Expert, with all Optimize panels expanded.
- (b) **cockpit argv:** the cockpit's path from state to argv cannot emit `--surrogate-guided`, even when `state.opt_surrogate_guided` is forced True. Checked by calling the cockpit argv builder/helper directly; if there is no callable seam, by code reading with file:line.
- (c) **CLI stub guard:** `scripts/run_optimization.py` with `--surrogate-guided` and without `--verify-cfd` refuses to rank with `synthetic_label`/`stub_verify`, unless some explicit test/dev opt-in is given. Checked by code reading plus a direct call of any pure guard function.

**R1.11 closing items (9e36cea).** Report each as present / absent, with file:line:
- (d) **CLI stub path:** an explicit, named CLI path for the stub (a flag or env var), so the stub is reachable only on purpose.
- (e) **behaviour test:** a pytest test that drives the CLI entry or argv (`main`/parse plus the guard), asserts the refusal, and passes here.
- A source-grep test alone counts as "absent (grep-only test)".

**R1.11 verdict:**
- "fixed on branch (pending merge)" needs (a), (b) and (c).
- "R1.11 closable" additionally needs (d) and (e).

**QA-62:**
- fixed if `pytest tests/test_axial_scripts_oriented.py` passes, and `validate_lt120.py` is listed in `AXIAL_SCRIPTS` or `EXEMPT` (report which);
- still open if the test fails.

**UI-26, 27, 29, 32–38 and QA-40, 42, 61, 63:** the r24 rules (88c4e79), unchanged.
- UI-31 render and UI-36 hover use the r24 `a_tooltips.py`, with the Surrogate-guided hover expected to be absent on the branch.
- UI-35 uses `range_check.py`.

**New bugs:** anything that crashes, contradicts the board or README, or regresses an item gets the next ID (QA-66…, UI-39…). One example would be a dead or orphaned state key, or a tooltip pointing at a hidden control.

**Fast suite:** `-m "not docker and not slow"`, run once on each head (237a094 and 9d0118f), in separate clones. Record the counts and the failing test IDs.

## B. QA-65 patch as adopted on master 9d0118f (review only)

1. **Fidelity:** compare the code hunks of 9d0118f with `docs/qa/patches/r24-C-k1-visible.patch`. Report identical / differs, listing the differences and any extra files or tests.
2. **Applies:**
   - `git apply --check` of the patch on 23831da (the r24 base) must pass;
   - on 9d0118f, `git apply --check -R` must pass, meaning it is fully applied, or the differences from step 1 are explained.
3. **Shows when unconverged** (pure calls on master): `score_caption(stamp_score_extra({}, raw, …))` contains the unconverged warning when `raw["converged"] is False`.
   - Code reading: `_assess` and `_assess_existing` keep `result.reason`, and `stamp_score_extra` copies `converged`.
4. **Only then.** No warning for:
   - `converged` True;
   - `converged` missing (old designs);
   - `converged` None.
   - Also, the reject message from `_operating_point_reason` must be unchanged (same text as r24 for the same inputs).
5. **Coverage.** For each route a scored design can reach the user, check whether it carries `converged` to `score_caption`:
   - (i) Assess new design;
   - (ii) Assess existing/stale design;
   - (iii) Optimize trials loaded via `data.py`;
   - (iv) designs reloaded from `design.json` on disk;
   - (v) `scripts/refresh_stale_designs.py`;
   - (vi) any test pinning (3) and (4).
6. Run the relevant tests (`score_caption`/assess tests, if any) once.

**Verdict:**
- **wrong** if 3 or 4 fails;
- **holes** if 3 and 4 pass but any route in 5 (i)–(iv) drops the flag, or no test pins 3 and 4. List them.
- **worth landing** otherwise.

## C. QA-64 strings still live? (master 9d0118f)

Grep the whole tree except `archive/`, `.git` and `.venv` for:
- "near free air";
- "within 8" (with "%", "%" preceded by a no-break space, or " %");
- "validated near free air on three published fans".

Report every hit with file:line and the exact line.

**Per file:**
- **live**: a release-facing or audit source (`docs/validation/**`, README, `docs/release/**`, cockpit copy) still states the claim;
- **QA record**: QA_REVIEW, `docs/qa/**`, `handoff/**`; these quote the claim and are not live.

**Verdict:** "still live (R1.10 not landed)" if any live hit remains; "changed" if none remain, quoting the replacement.

## D. Waiting

- The R3.1 export leak check stays waiting (R3.1 not landed).
- The r21 A claims audit stays waiting for R1.10. Neither is run.
