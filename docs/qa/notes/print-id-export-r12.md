# 28.2 print-id on Stock Export (round 12 Task C)

Prereg `42004b3`. Headless cockpit session: CockpitCtx + `setup_fan_tab` on a real asyncio loop, with the real
`export_stl_current` and the real isolated export worker. Cold open selects Stock v3 (trial 100000), PETG, `cup_build_ok` True.
Export took 175 s. Output: `exports/SB862_a12x25_stock_reference_20261014-180345.stl` (+ .step, .md, _print_fit.json,
_mount_checklist.md) in the run clone. These files are not copied here because they are gitignored and large.

| id | result | evidence |
|---|---|---|
| P0 | PASS | `SB862_a12x25_stock_reference_20261014-180345.stl`; `verify_print_id("SB862")` is True |
| P1 | PASS | README line 1 is `# Print sheet — SB862`, and the README contains "Sharpie" |
| P2 | PASS | print_fit.json has print_id SB862, section_wrap cylinder, recipe_hash 07234ef2d8e62778, git 143d5a8…, material PETG |
| P3 | PASS | index.jsonl went 0 → 1 line, with the same print_id and stl path |
| P4 | PASS | watertight, 1 body, 0 degenerate. K7: floor 12.985 mm, 20 grips, 0.696 mm, identical to r10 Task A (vol 27 447.8 mm³, also identical) |

Caption: "↳ Print-id `SB862` — Sharpie that on the hub (+Z). Same code in the README."

Harness disclosure: my first attempt (before the busy-wait fix) pressed Export right after cold open and exited after 0.5 s.
No export was recorded or measured from that run, but its worker left `exports/Q8B8G_…-180327.stl`: an STL with no README or
sidecars, whose id is not in index.jsonl. The cockpit does not normally exit mid-export, but closing it during an Export
does the same thing. Found while writing up r13: killing my first harness left its export worker running.
That orphan overlapped the second (good) C export, and the kernel OOM-killed a 6.2 GB python process, which is most likely the orphan.
dmesg shows `Killed process 254790 (python) … anon-rss:6178372kB`. SB862 and HES4W both completed and their checks pass.
→ **QA-37 (LOW)**: the isolated export worker outlives the cockpit process.
