# QA → Claude, 2026-10-09 (requests 2, 4 and 5)

Tested `qa-fixes-2026-10-09` @ d781894 in a separate clone (not /workspace/fansim/repo). Nothing
was committed or pushed.

## Criteria hashes (taken before running anything)
| file | sha256 |
|---|---|
| `docs/qa/notes/axial-force-retune-criteria.md` (master 6f31514; QA copy; QA pre-registration commit 12065f9c, 2026-10-09 07:49 MDT) | `17e1e9c469014c8c55aaa90dab8543cf4bbf63dbbff298f13f305f107207f7e2` (all three are byte-identical) |
| `docs/qa/notes/prop-ct0-rpm-creep-criteria.md` (new; QA pre-registration commit 3bc79d76, 2026-10-09 11:00 MDT) | `428c808ea9aa720cd3538e6db6f3493a6931a8b3397feb43a9a0eb91b700cea4` |

The criteria file is not on `qa-fixes-2026-10-09`; it exists only on master. I used it as is.

## (2) Axial-force BEM re-tune: rules a, b, b2, d
- `fansim/fan_bem.py` and `tests/test_fan_bem.py` on d781894 are unchanged from 961f953, so the
  axial-force patch was **not** applied on the branch.
- `docs/qa/patches/axial-force-pressure.diff` on master (sha256 e6060cc5…) is byte-identical to
  the QA patch. It applies cleanly to d781894, and I applied it in the QA clone.
- Tuned constants (unchanged): `AX_SLIP = 0.65`, `AX_K_FRICTION = 1.9`, `CD_90 = 1.8` (fixed).

| rule | result | numbers (2000 rpm, default 0.5 mm gap) |
|---|---|---|
| (a) Stock 54.1–66.1 CFM and 17.2–28.6 Pa | **PASS** | 59.8 CFM, 22.08 Pa (euler today: 58.2 / 38.87) |
| (b) exploits dead | **PASS** | Limits: free < 29.9 CFM and η < 0.237, or no positive pressure. Paddle 89°: 14.0 CFM, η 0.009 (euler 62.5 / 0.549). Reversed −45°: no rise, −22.5 Pa at shut-off. Reversed −60°: no rise, −19.2 Pa. 0 blades: free 0, no crash. |
| (b2) top-5 survive | **PASS** | All 5 cross zero. Free 66.7–68.5 CFM (limit ≥ 47.8). η 0.416–0.455 (limit ≥ 0.237). 5/5 still beat Stock. |
| (d) opt-in safe | **PASS** | Default `euler`: 22 curves (11 cases × stator off/on) byte-identical to unpatched d781894 (85,814 bytes of repr). The 8 existing tests (`test_fan_bem` + `test_bem_no_rise`) pass unpatched. Patched: 74 passed across test_fan_bem (incl. 9 new), test_bem_no_rise, audit/test_fan_bem_audit, test_mixed_flow_bem, test_shroud and test_math_consistency. |
| (c) ranking vs CFD | **PENDING** | needs `cfd_designs.csv` |

- Reminder: the strict pre-registered recipe failed (a) and (b) on 2026-10-08/09. These passes are
  for the variant with two changes declared after the fact (post-stall polar and inlet-velocity
  reference). The Stock match is therefore a fit; (b) and (b2) are the hold-outs. Details are in
  `docs/qa/notes/axial-force-pressure-accounting.md` (QA research copy).
- Re-run (b2 needs the screen designs, which are on the QA box at `/workspace/fansim/screen/designs`):
  ```
  git apply docs/qa/patches/axial-force-pressure.diff
  uv run python handoff/2026-10-09_from-qa/check_rules_abd.py --screen-dir <dir with 01_..05_*.flat.json>
  ```

## Rule (c): `eval_rank_vs_cfd.py` (ready to run tonight)
```
git apply docs/qa/patches/axial-force-pressure.diff      # the script refuses to run without the mode
uv run python handoff/2026-10-09_from-qa/eval_rank_vs_cfd.py cfd_designs.csv --out rule_c.json
# optional secondary column (not the verdict):  --cfd-col <your scored/load column>
```
**CSV columns** (header row required; extra columns are ignored):
- `design_id`: any unique label.
- `cfd_free_cfm`: CFD free-air CFM, raw. **This column decides the verdict** (the Audit #4 metric).
- Geometry, one of these per row:
  - `geometry`: a `.flat.json` or `.yaml` path, or the word `stock`;
  - `flat`: the flat dict as an inline JSON string;
  - the flat keys as separate columns: `n_blades, stagger_root, stagger_mid, stagger_tip,
    chord_root, chord_mid, chord_tip, sweep_mid, sweep_tip, lean_mid, lean_tip, max_camber,
    thickness_root, thickness_mid, thickness_tip, camber_pos, hub_radius, tip_radius,
    chord_basis`. A `flat.` prefix is also accepted.
- **The Stock 7-station row must have `geometry=stock`**, which loads the YAML. A flat dict
  truncates Stock to 3 stations (QA bug #1).
- Optional: `rpm` (default 2000) and `tip_gap_mm` (default: model default).

The script recomputes base ρ (today's euler BEM) on the same rows. Verdict rule
(pre-registered): **PASS** if n ≥ 5 AND ρ_new ≥ 0.6 AND ρ_new ≥ ρ_base − 0.10; also PASS if
0.5 ≤ ρ_new < 0.6 with top-3 overlap ≥ 2 (same ρ_base condition); n < 5 is INCONCLUSIVE. I
smoke-tested all three geometry input styles; they give identical results.

## (4) UIUC GWS 5×4.3 source files
`uiuc_gws_5x4.3/`: the 3 files, unmodified (extracted from the UIUC zip and also byte-identical to
the per-file URLs), plus `SOURCES.md` with URLs and sha256.
**The files use CRLF.** The repo's `* text=auto eol=lf` would rewrite them, so the folder carries a
`.gitattributes` with `*.txt -text`. LF hashes are listed too.

## (5) Prop CT0 rpm creep
Note: `docs/qa/notes/prop-ct0-rpm-creep.md`, plot `prop-ct0-rpm-creep.png`, script and raw output
in `scripts/`. **No patch.** The pre-registered patch rule failed: the one-line clamp fixes static
but worsens the J sweep.

---

# QA → Claude, 2026-10-09 (requests 1 and 3)

Tested `qa-fixes-2026-10-09` @ d781894 in `/workspace/fansim/repo` (Linux, no Docker/CFD). Nothing was committed.

- **Bundle note:** `master` in the bundle is `6b7f3bf`, not `6f31514`. 6f31514 is an ancestor of master, with 6 docs/handoff-only commits plus one `.gitignore` line after it. It is not an ancestor of the fix branch, which forks from 961f953. `docs/QA_REVIEW.md` therefore exists only on master. I started from master's copy and left the updated file untracked in the branch working tree.
- **(1) Re-test:** statuses are in `docs/QA_REVIEW.md` (tracker plus the section "Re-test 2026-10-09 (2)").
  - **Verified:** UI-5, UI-16, UI-17, UI-18, UI-19, QA-11, §23.32. Nothing reopened.
  - **Needs a browser pass:** UI-4, 8, 9, 13, 20, 21, 22. Steps are in `docs/qa/browser_checklist_2026-10-09.md`.
  - **New:** QA-12 (prop CT0 rpm creep, LOW).
- **(3) Websocket:** `ws/` has the scripts, a README and before/after results.
  - 961f953: a frozen client freezes every new session until it is killed.
  - d781894: new sessions keep connecting (0.25–0.38 s) and the frozen client is dropped after about 15 s.
  - KeyError leak: 20 → 0.
  - `observerCount` after 30 aborted sessions: 30 → `{}`.
