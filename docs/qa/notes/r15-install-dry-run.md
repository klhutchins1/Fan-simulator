# Round 15: R3.3 install-guide dry run (master 9562574, box only)

Prereg: `qa_r15/PREREG_R15.md`, branch `prereg/round15`, commit `336211b` (sha256 `6fa2b69d…b3eb4b`).
The registered rule: PASS only if the README install section, followed word for word on a clean Linux box, gets to
a running cockpit. If the section does not exist yet, the result is **NOT RUN**.

## Result: **NOT RUN.** The install guide is not written yet
At 9562574 the README has a "Quickstart" but no install section. It does not yet cover Windows/Linux, Docker
Engine, `docker pull opencfd/openfoam-default:2406`, the first Assess or troubleshooting. R3.3 is still `ready`
(Cursor), so this is expected.

## Report-only: Quickstart in a fresh clone with an empty uv cache
Script: `handoff/2026-10-17_from-qa-15/scripts/r33_quickstart.sh`. Log: `…/data/r33_quickstart.log`.
Run 14:48 MDT 2026-10-17 in `/tmp/qa15_install` with `UV_CACHE_DIR=/tmp/qa15_uvcache` (empty).

| step | result |
|---|---|
| `uv sync --extra dev` | rc 0, 2.2 s (fast box network; Python 3.12.15 was already on the box, so no download timing) |
| `uv run python -V` | 3.12.15 |
| `import fansim` | ok, imports from the fresh clone |
| `pytest tests/test_ui_says_what_it_does.py` | 6 passed |
| `scripts/cockpit.py --help` | rc 0 |
| full fast suite | skipped: peaks at about 8 GB in one process (see r13 notes) |
| Docker / OpenFOAM / first Assess | skipped: not allowed on this box |

## For the guide (proposals)
- Say that `uv sync` without `--extra dev` installs no pytest. The README test command needs the dev extra
  (old item 10).
- Give the memory need of the full test suite, or point to the chunked runner.
- When the guide lands, grok re-runs this rule word for word. A machine that has never had uv would be better.
  The box already has uv and Python 3.12, so the "install uv" step cannot be tested here.
