# grok QA round 26 data (master bd6abdd)

The note is `docs/qa/notes/r26-qa66-qa65-recheck.md`, and the prereg is `PREREG_R26.md` (prereg/round26 00ed802).

## scripts/
- `a_qa66_probe.py`: QA-66 rules 1/3/4/5, library calls only, with a fake verify.
- `a_qa68_cli_probe.py`: QA-68, the CLI refusal path.
- `b_qa65_trials.py`: QA-65 rule 3.
- `b_qa65_review.py` and `a_ui.py`: the r25 harnesses, unchanged.

## data/
- the targeted pytest output;
- the `git apply --check` results, forward and reverse;
- the probe JSONs;
- `master_bd6abdd/a_ui.json` (UI-26).
