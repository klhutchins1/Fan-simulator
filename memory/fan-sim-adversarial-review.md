<!-- RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md. -->

---
name: fan-sim-adversarial-review
description: Standing request to re-run an adversarial review of Fan-simulator at each milestone
metadata:
  type: feedback
---

User wants a recurring ADVERSARIAL (red-team) review of the Fan-simulator design/approach,
revisited "when we've made more progress" — NOT a one-off. Living doc:
`E:\Projects\programming_2\Fan-simulator\docs\adversarial-review.md`.

**Why:** the project can look impressive while resting on unvalidated low-fidelity CFD; the user
wants the weaknesses surfaced honestly and continuously (what's happening, the overarching idea,
what's missing, where the MATH is wrong, where more research papers are needed, how to get there,
what makes it better).

**How to apply:** at every milestone (new fidelity tier, new objective, before any "showdown"
claim) re-run the review, be genuinely critical of our own work (no performative praise), and
update the doc's tables + bottom line + §8 revisit checklist.

Current top red-team findings (first pass): (1) pressure/efficiency metrics physically muddled
(need total-pressure/AMCA); (2) screening CFD too coarse, NO grid-convergence, MRF + slip walls +
fully-turbulent-at-transitional-Re — ranking never proven resolution-stable; (3) rotation `spin=-1`
patched not derived; (4) "features help" likely noise/solver solution-branch artifact (bimodal
cfm_load doesn't map to features or resolution); features are smooth deformations not real
geometry; (5) ZERO validation vs A12x25 or any benchmark; (6) GPU (4070 Ti) idle, FluidX3D unbuilt;
(7) noise objective doesn't exist yet; (8) printed reality (tip gap + FDM roughness) unmodeled.
Biggest fix: validate against ground truth + prove ranking is resolution-stable BEFORE trusting
numbers or extracting design rules. See [[fan-sim-status]] and [[fan-sim-project]].
