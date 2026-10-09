### Task 4: Spec accepted + roadmap

**Files:**
- `docs/superpowers/specs/2026-09-02-ring-to-frame-gap-design.md` — `Status: accepted`
- `docs/roadmap.md`
- Also add the untracked plan `docs/superpowers/plans/2026-09-02-ring-to-frame-gap.md` in this commit so the branch has the implementation plan

§1.1 remaining line today still says “designed shroud-to-frame gap (§7.5)”. Change remaining to circular AMCA only.

Suggested §1.1 replacement:

```markdown
- [x] **1.1 Tip clearance + frame struts in the optimizer CFD (stage 1). DONE 2026-09-01**
  Optimizer uses **0.5 mm** min leftover (`--tip-gap`) and a four-bar stationary `frame.stl`
  downstream of the MRF zone. Spec-backed CFD pins the square duct to the frame ID
  (leftover = frame/2 − built r). Remaining: circular AMCA rig.
```

§2.1 remaining: drop “ring-to-frame gap in CFD”; keep winglet interaction.

Suggested §2.1 remaining sentence:

```markdown
  BEM drops tip-loss when the ring is on. Remaining: partial-height ring (cockpit
  `shroud_height_frac`, TE-anchored) done 2026-09-02; ring-to-frame CFD gap
  (pinned frame ID + leftover ≥ 0.5 mm) done 2026-09-02; remaining winglet
  interaction (§7.5).
```

§7.5 stays **unchecked**. Add that CFD clearance (pinned frame ID + leftover ≥ 0.5 mm) is in; winglet×shroud policy is not.

Suggested §7.5 opening:

```markdown
- [ ] **7.5 Tip shroud/ring — with the RIGHT clearance, and the winglet interaction.** **[impact: high]**
  **[effort: med]** CFD clearance (pinned frame ID, leftover ≥ `--tip-gap`) is in;
  winglet×shroud policy is not.
```

Keep the rest of the §7.5 literature paragraph.

Recommended sequence item 1: still §7.5, but “ring-to-frame CFD gap done; winglet interaction remains”.

Suggested recommended sequence item 1:

```markdown
1. **Tip shroud refinement** — partial-height ring and ring-to-frame CFD gap done;
   winglet interaction remains (§7.5).
   §1.1 stage 1 (pinned frame ID + four-bar `frame.stl`) and §1.2 stage 1 (system curve) done 2026-09-02.
```

Recently shipped: mention pinned frame-ID duct / leftover `--tip-gap` floor.

- [ ] **Step 1: Edit the docs** (spec status `accepted`; roadmap as above; include the plan file)

- [ ] **Step 2: Run** `uv run python -m pytest tests/test_cfd.py tests/test_optimize.py tests/test_fan_bem.py tests/test_shroud.py tests/test_frame.py -q --tb=short -m "not docker"`

Expected: assertions PASS. CadQuery teardown exit is not a failure.

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/specs/2026-09-02-ring-to-frame-gap-design.md docs/roadmap.md docs/superpowers/plans/2026-09-02-ring-to-frame-gap.md
git commit -m "Accept the ring-to-frame gap spec and mark §7.5 CFD clearance done"
```

Do not commit `catalog/catalog.db`. Do not `git push`. Do not commit to `master`.
