# RV-4 script triage (2026-11-25)

Cursor, worktree `runs/worktrees/rv4-script-triage`.

## Status

| bucket | count | notes |
|---|---:|---|
| **keep** (still in `scripts/`) | 92 | ops tools, validation drivers, cockpit entrypoints |
| **archive** (`archive/scripts/`) | 38 | unreferenced one-offs; see README there |
| **promote** (still scripts; maths to move) | 3 | listed below — tracked as GitHub issues |

`scripts/audit_forensics.py` added (with `tests/test_audit_forensics.py`).

## promote (follow-up issues)

| script | why |
|---|---|
| `prop_section_2d.py` | 2-D section maths for props — move into `fansim/` + ledger unit |
| `fan_noise_curle.py` | rewrites Curle sum already proven in `acoustics.curle_dipole` |
| `fan_noise_cv.py` | CV noise rewrite — same rule |

Rule: no code that produces a validation verdict lives only in `scripts/`.

## keep highlights

Operational / process: `gate.py`, `night_queue.py`, `morning_check.py`, `stray_work.py`,
`audit_status.py`, `audit_forensics.py`, `physics_snapshot.py`, `pytest_chunks.py`, `export_release.py`.

Validation drivers with tests stay in `scripts/` until a later promote pass.

## Done

1. Archived 38 unreferenced scripts (17 plan orphans + 21 review clear-outs).
2. Added `audit_forensics.py` + tests.
3. Promote trio filed as GitHub issues (see board / issues).
