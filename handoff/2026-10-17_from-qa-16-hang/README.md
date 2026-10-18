# QA round 16: hang investigation (grok), master 9562574, 2026-10-17

- Prereg: `prereg_r6` branch `prereg/round16-hang`, commit `52eca5f39cfa21beccc202ecd19cb2d70cd71929`,
  file `qa_r16_hang/PREREG_R16_HANG.md` (sha256 `6ee13807066416a4d47a5f860502304e898eacda2632ed9f0ef3ea410b4af7b3`),
  committed 16:52 MDT before any data.
- Note: `docs/qa/notes/hang-investigation-r16.md`. QA_REVIEW: QA-43, QA-44 (MED), QA-45 (LOW).
- Run clone `qa/run_r16`, `FANSIM_CACHE_DIR=qa/r16_cache`. No CFD, Docker or OpenFOAM, no fansim edits.

| step | script | data |
|---|---|---|
| P1 designed hang + decomposition (2741) | `scripts/p1_designed.py` | `data/p1_designed.jsonl` |
| A2 attribution (P1 + P2) | `scripts/attrib.py` | `data/attrib_p1.json/.log`, `data/attrib.json/.log` |
| Sobol, guided box (report-only) | `scripts/sobol.py` | `data/sobol_guided.json/.log` |
| P2 built hang (300 CAD) | `scripts/p2_built.py` | `data/p2_built.jsonl/.log` |
| Option A predictors | `scripts/optA.py` | `data/optA.json` |
| Option B skirt (30) | `scripts/optB.py`, `scripts/optB_summary.py`, `scripts/optB_g1_control.py` | `data/optB.jsonl/.log`, `data/optB_summary.json`, `data/optB_g1_control.json` |
| Option C limits | `scripts/optC.py` | `data/optC.json` |
| Auto hub vs 15 mm mount hub (QA-44) | `scripts/p1_mount15.py` | `data/p1_mount15.json` |

Results: P-a, P-b, P-c and P-d PASS (built/designed median 1.77, 1.75 predicted). Option A FAILS as registered
(p95 0.67 > 0.5 mm; it passes on feature-free designs). Option B NOT WORTH IT as registered (12/30 rescued; depth is
the binding gate). Option C costs +2.1 % of the guided space and misses 1/123.
