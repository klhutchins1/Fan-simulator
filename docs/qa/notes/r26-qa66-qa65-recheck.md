# Round 26 (grok, 2026-11-04): re-check of QA-66 / R1.11 and QA-65 on master bd6abdd

- **Build:** master `bd6abdd` (2026-11-04 12:23 MST). Run clone: `/workspace/fansim/repo-r26`, a fresh clone of `master_bd6abdd.bundle`, with no commits and no edits.
- **Prereg:** `prereg/round26` 00ed802 (`qa_r26/PREREG_R26.md`), committed 2026-11-04 12:25 MST, before any data.
- **What did not run:** no CFD, Docker, OpenFOAM, Assess, Sweep or Optimize, and no full fast suite. Probes call library or CLI entry points only, with `image_available` monkeypatched and any CFD verify replaced by a fake or an abort.
- **Data:** `handoff/2026-11-04_from-qa-26/`.

## Targeted tests

`test_surrogate_guided`, `test_r111_cockpit_surrogate`, `test_score_caption` and `test_optimization_argv` give **46 passed** (11 + 8 + 11 + 16) in 7.3 s. The first three are the test files changed in 0635a18..bd6abdd.

## A. QA-66 (R1.11): **verified**, 5/5 rules

1. **`--verify-cfd` trains on no `synthetic_label` rows.**
   - Probe with an 8-row catalog and a fake verify: 0 `synthetic_label` calls; `labels` = "catalog + CFD verify"; "DoE skipped"; n_train 10 (8 catalog rows + 2 verified).
   - Missing Docker refuses: a test covers it, and `run_optimization.py:173` returns 2.
2. **`run_surrogate_search.py` refuses with neither flag.** It returns 2, and `test_r111_cockpit_surrogate` covers this.
3. **The stamp is on disk.** The `--stub-labels` probe writes "synthetic labels, not CFD" both in `surrogate_guided.json` (`labels`) and in 2/2 `stub_result.json` files.
4. **The catalog refusal comes before any search.** With 7 rows, no catalog, or no catalog plus the real verify factory, the run raises "needs a catalog with ≥ 8 CFD rows" with 0 synthetic calls and no JSON written. See also QA-68 below.
5. **Priors are stamped.** `surrogate_guided.json` `priors` = `{efficiency: "prior, not CFD", cfm_load: "prior, not CFD"}`. The cfm_load-with-k case was not built (code only).

**r25-A CLI behaviour test: covered.** Both tests are on master verbatim (`test_cli_parser_routes_surrogate_guided_through_the_gate` and `test_cli_main_checks_the_gate_before_the_surrogate_loop`). The patch fails `--check` only because a later test was appended after them.

**R1.11 / QA-66 closable.** UI-31 and QA-62 were not re-tested; `test_r111_cockpit_surrogate` passes.

### New: QA-68 (LOW). The CLI catalog refusal is an uncaught traceback, not a clean exit 2

- **Behaviour.** `run_optimization.py --surrogate-guided --verify-cfd` with no catalog (or one with fewer than 8 rows) on a machine *with* Docker prints a Python traceback (`RuntimeError`, exit 1). `main` does not catch the refusal from `run_surrogate_guided` (`surrogate_search.py:509`). The out dir is already created at that point.
- **Probe.** `a_qa68_cli_probe.json`, run with Docker monkeypatched.
- **Who sees it.** This happens only where Docker is present, so the refusal itself is correct; the message is just raw.
- **Patch.** `docs/qa/patches/r26-A-qa68-catch-refusal.patch` wraps the call in `except RuntimeError` → print, return 2, and adds a test that fails on master and passes when patched. Results on a scratch clone: r111, surrogate_guided and argv give 36 passed. The patch applies to bd6abdd.
- **Not a blocker for R1.11.**

### Informational

- Under `--verify-cfd`, the top-level `labels` is "catalog + CFD verify", while 2 of 3 objectives train on priors. These are stamped in `priors` and `notes`, so the information is there.
- `test_seed_from_catalog…` checks the returned priors, not the JSON on disk. The probe confirms the on-disk stamp.

## B. QA-65 (R1.2): **verified**, 3/3 rules

1. **The r24-C patch is already on master.** `r24-C-k1-visible.patch` fails `--check` forward and reverse-applies cleanly, so its content is present exactly. `r25-B-qa65-test-and-trials.patch` also reverse-applies cleanly, which makes it **redundant**.
2. **Only `converged is False` warns.** Results from the unchanged r25 `b_qa65_review.py`:

   | `converged` value | warns |
   |---|---|
   | True | no |
   | None | no |
   | key missing | no |
   | old extra | no |
   | the string "False" | no |
   | re-assessed False→True | no |
   | False | **yes** |

   The reject reason is identical to r24. `test_score_caption`: 11 passed.
3. **Optimize trials carry `converged`.**
   - `study.py` sets the trial attr, and `data.py` copies it.
   - Probe (`b_qa65_trials.json`): a temp Optuna study with trials whose `converged` is False, True or absent, read through `load_designs` and then `score_caption` (the `fan_trials.py:96` path). The warning shows only for False.
   - No repo test covers this path. `docs/qa/patches/r26-B-qa65-trial-test.patch` adds one (12 passed on scratch). This is optional and not a blocker.

**QA-65 closable.**

## C. UI-26: **still open**

"Gold = parametric Stock" is on the first view in 3 of 4 views: 1366 Expert, 1920 Simple and 1920 Expert.

The 1366 Simple miss is render timing: the screenshot shows "Running Stock preview… building Stock cache once". This happened again, the same as r25/r25b. The text is at `fan_trials.py:299`.

UI-27, UI-29, UI-32…38, QA-40, QA-42, QA-61, QA-63 and QA-64 were not re-tested and are carried as still open.

## D. Still waiting

- The R3.1 export leak check is waiting for R3.1.
- The r21 A claims audit and the QA-64 strings are waiting for R1.10.

No data.
