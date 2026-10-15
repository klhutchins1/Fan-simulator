# QA-34 strip check on master 143d5a8 (round 12 Task A)

Prereg `42004b3` (branch prereg/round12). Run clone `/workspace/fansim/qa/run_r12` (local clone of repo-r13 @ 143d5a8).
P builds, `section_wrap="cylinder"`, `build_stl_isolated(preview=False)`, 8gb tier, serial. B-rep solid count is from the
r10 hook_b `fuse_many` wrapper (last call). Mesh checks are on the file the builder wrote.

| id | kind | outcome | watertight | bodies | faces < 1e-9 mm² | B-rep solids | faces | s |
|---|---|---|---|---|---|---|---|---|
| S5_0184 | control | OK | yes | 1 | 0 | 1 | 78 260 | 51 |
| S5_0080 | new (seed 11013) | OK | yes | 1 | 0 | 1 | 86 156 | 67 |
| S5_0242 | new (seed 11013) | OK | yes | 1 | 0 | 1 | 133 532 | 131 |

Pool: 297 featured unshrouded S5 designs (S5_0184/0228/0112 removed). No hang refusals, so nothing was dropped.

- **F0 PASS:** S5_0184 is now a single watertight body with 0 degenerate faces, and the B-rep is still 1 solid. In r10b it was 8 bodies with 7 degenerate faces.
- **F1 PASS:** both new featured wraps are also 1 watertight body with 0 degenerate faces.
- F2 (report only): S5_0080 has 7 blades with tubercles, serrations and dimples (4×6). S5_0242 has 11 blades with all three features (2×2).

QA-34 stays closed. Two new designs is a small sample, so this confirms the strip on the known case but does not measure how often the problem occurs.
Data: `handoff/2026-10-14_from-qa-12/data/a_results.jsonl`; script `scripts/run_a.py`.
