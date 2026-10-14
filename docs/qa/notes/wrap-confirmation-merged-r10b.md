# Wrap confirmation on merged master (QA round 10b Task B) — FINAL

Prereg: `qa_r10/PREREG_R10.md` @ `26aa359`. Code: repo-r10 master a09905a (wrap merge ae3f1c4). There are 40 designs, seed
10010, in these groups: CTL 5, featured 5 (S5_0167 forced in), near-bounds (S8) 5, shrouded 5, notched 4, winglet 4,
tip-round 4, uneven 4, plain 4. Notched, winglet, tip-round and uneven were set on random bases, because the population has
no such designs. Runner: `handoff/2026-10-13_from-qa-10/scripts/{sample_b,run_b,job_b}.py` + `hook_b/sitecustomize.py`
(K12 faces + a `fuse_many` call log). It ran unattended under setsid nohup and was resumable, with one build at a time.
MemAvailable was 5–11 GB during the run (more than the 3 GB seen at prereg), so no gate waited.

## Outcomes
- Planar P builds: 40/40 OK.
- Cylinder P builds: 38 OK and 2 **refused (hang)**, both featured: S5_0228 (designed hang 3.51 mm) and S5_0112 (2.55 mm).
  Both refusals came up front from `validate_blade_params`, with the plain hang message.
- Cup (C) builds: 10/10 OK.
- The featured group therefore has only **3 buildable** wrapped designs (one fewer than the "≥ 4 of each" ask). This is
  disclosed and was not topped up after the data came in.

## Rules
| rule | result |
|---|---|
| W1 sound | **FAIL ×1**: featured **S5_0184** (tubercles + serrations + dimples, designed hang 0). Its wrapped STL is not watertight, with 8 mesh bodies and 7 degenerate faces, although the B-rep fuse returned 1 solid. The planar build of the same design is watertight with 1 body. Its zmin and rmax are fine. → **QA-34**. The other 37 pass. |
| W2 volume | PASS. V_cyl/V_planar − 1 ranges from −1.37 % to +2.50 %. |
| W3 time | PASS, strict ratio too: median 1.14×, max 1.62×. No suspect suspends. |
| W4 cup K7 | PASS 10/10. |
| W5 direction | PASS: 0 CONCLUSIVE-wrong. 18 of 38 wrapped builds are INCONCLUSIVE (QA-33 still stands, no new rule). |
| W6 one solid | **FAIL ×1**, the same S5_0184. Every hub+blades `fuse_many` returned 1 solid, and the ring fuses did too. But S5_0184's STL is not one watertight body, so W6 fails as registered on its watertight clause. No build failed with "did not join into one solid". **The one-blade-at-a-time fallback fired 0/38 times.** |

- The known W1 miss, S5_0167 (featured, formerly OOM), built OK this time at an 8.76 GB peak, with 10.7 GB available. It
  passes only because memory was there: the guard question is round-10 Task D / 27.1 and was not tested here.
- Reading: the fuse net works and was never needed here. The remaining wrap risk is in **mesh export of feature-heavy
  wrapped blades**, not the fuse.
- **QA-34 closed 2026-10-14:** S5_0184's 8 bodies were 1 watertight impeller + 7 collapsed tessellation
  needles (one per blade) at the hub. `export_stl` strips them. See `docs/qa/notes/qa-34-featured-wrap-stl.md`.
- Kept mesh: `handoff/.../data/S5_0184_Pc.stl.gz` (gitignored).
