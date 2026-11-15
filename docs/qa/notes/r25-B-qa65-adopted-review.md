# QA r25 B: the QA-65 patch "as adopted" on master 9d0118f (review only)

**Tested:** 2026-11-02, MST. **Prereg:** b7e7574e. **Brief:** Cursor's uncommitted draft, not committed.

**Method:**
- No source edits in `repo-r25` and no CFD.
- The patch was applied only to scratch copies (`qa_r25/b_apply`, `qa_r25/b_full`, built from `git archive 9d0118f`), and the pure calls were run there.

## 1. Fidelity: the code is NOT on master

9d0118f changes **only `docs/release/RELEASE_PLAN.md`**, +4 lines. It records the decision "QA-65 … adopt. Apply `docs/qa/patches/r24-C-k1-visible.patch` … with a test that a `converged=False` result shows it and a converged one does not". `git show 9d0118f -- '*.py'` is empty.

| check | result |
|---|---|
| `git apply --check r24-C-k1-visible.patch` on 9d0118f | **passes**: still applies cleanly, i.e. not applied |
| `git apply --check -R` | fails (`score_caption.py:29`) |
| unpatched master, `stamp_score_extra` + `score_caption` with `converged=False` | `converged` not stamped, **no warning** |

So "adopted" is a board decision, and QA-65 is **still open on master**.

## 2–4. Behaviour of the patch (scratch master + patch)

| input | `converged` in extra | warning "loaded point did not settle" |
|---|---|---|
| raw `converged=False` | False | **shown** |
| raw `converged=True` | True | not shown |
| raw `converged=None` | absent | not shown |
| key missing (old design) | absent | not shown |
| old `extra` with no key | — | not shown |
| `extra["converged"]="False"` (a string) | — | not shown (`is False` only) |
| stale False, re-assessed with True | True | not shown (overwritten) |

- The reject message from `_operating_point_reason` is **unchanged**, byte-identical to r24 for the same inputs.
- Shows-only-when-False: **pass**.
- `_assess` and `_assess_existing` keep `result.reason`, by code reading. On a feasible design that reason is `conv_note` (`objectives.py:599-608,634`). It is persisted to `design.json`, but not displayed in the cockpit.

## 5. Coverage of the routes a scored design reaches the user by

| route | carries `converged` to the caption with the patch? |
|---|---|
| (i) Assess, new design | yes: `run_settings.stamp` → `stamp_score_extra` (`run_settings.py:63`) |
| (ii) Assess existing / stale design | yes: same stamp; the `converged=True` overwrite works |
| (iii) Optimize trials loaded by `data.py` | **no**. `study.py:228-238` stores no `converged` user attr, and `data.py:147-157` builds `extra` without it. The caption (`fan_trials.py:96`) is silent; the UNCONVERGED text exists only in the trial's hidden `reason` |
| (iv) designs reloaded from `design.json` | yes: `fan_helpers.py:191` copies `extra` whole, and the patch stamps the key before the write |
| (v) `scripts/refresh_stale_designs.py` | yes: `stamp_score_extra` at `:107` |
| (vi) a test pinning 3 and 4 | **none**. `tests/test_score_caption.py` has no `converged` test; 9d0118f itself asks for one |

## Verdict: **holes**

The patch is right for Assess, and the "only when False" behaviour holds, but it has two holes:
1. Optimize-trial designs (iii) never show it.
2. No test pins it.

It is still worth landing as-is for Assess. The proposed add-on is `docs/qa/patches/r25-B-qa65-test-and-trials.patch`:
- **Tests:** two cases in `tests/test_score_caption.py`. One checks that False shows the warning. The other checks that True, None and a missing key stay silent, including an old extra.
- **Trials:** `study.py` sets the `converged` user attr, and `data.py` copies it into `extra` (None on old studies, so they stay silent).

**Checks on the add-on:**
- `git apply --check` on 9d0118f passes, both alone and together with `r24-C-k1-visible.patch`.
- Scratch master with both patches: `test_score_caption.py` 11/11 pass.
- All 14 test files that import `cockpit.data`, `optimize.study` or `fan_assess` give 142 passed. Unpatched master gives 131 passed for the same files without the 2 new tests (9 + 2 = 11 caption tests).

QA-65 stays **open on master**, severity unchanged (MED).
