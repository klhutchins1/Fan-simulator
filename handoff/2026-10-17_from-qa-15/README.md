# QA round 15 (grok), master 9562574, 2026-10-17

- Prereg: `prereg_r6` branch `prereg/round15`, commit `336211b5e7df0bbee06455b0178db00106d66942`.
  The file is `qa_r15/PREREG_R15.md`, sha256 `6fa2b69d5e887c57164d16b5e4a7b2b382bfbf4e060dd8040bb6a134b9b3eb4b`,
  committed 14:47 MDT before any data.
- Research and analysis only. Nothing downloaded is committed; every source is listed with its URL and licence in
  the notes.

| task | result | note |
|---|---|---|
| A R2.3 CROR | best: Shigemitsu 2018 (OJFD, CC BY 4.0, 40 mm contra-rotating fan); 2nd: 100 mm rig (cite-only) | `docs/qa/notes/r15-data-hunt-cror-mixed-centrifugal.md` |
| B R2.4 mixed-flow | no CC-licensed small mixed-flow data found; best is the 85 mm Treder rig (cite-only) | same |
| C R2.5 centrifugal | best: EPJ WoC 180:02023 (60 mm, CC BY 4.0, licence to confirm), then MDPI Processes 12:353 | same |
| D R0.1 27.3e re-check | D1, D2 PASS; D3a FAIL as registered (grid tie; PASS on a 59-cell grid); D3b FAIL on direction (my prediction was wrong; code is right); D3c, D3d, D4 PASS | `docs/qa/notes/r15-push-planes-recheck.md` |
| R3.3 install guide | **NOT RUN**: guide not written yet; Quickstart dry run OK (report-only) | `docs/qa/notes/r15-install-dry-run.md` |

- `scripts/d_planes.py` is the registered D test.
- `scripts/d_planes_nr59.py` is a report-only variant without the grid tie.
- `scripts/r33_quickstart.sh` is the Quickstart dry run.
