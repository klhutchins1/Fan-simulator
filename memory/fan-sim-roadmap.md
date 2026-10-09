---
name: fan-sim-roadmap
description: "Master TODO/roadmap of open engineering work — read docs/roadmap.md before any work session"
metadata:
  type: project
---

The comprehensive, tracked plan of remaining work lives in the repo at
`docs/roadmap.md`. It is the SOURCE OF TRUTH for what's left — READ IT at the start of a Fan-sim
work session before proposing next steps, and check items off / update it as work lands.

**2026-09-15:** Two live lists, not one. **§12** = don’t trust Stock/Fit/Assess math yet (camber flatten, Fit vs Assess gates, free-ΔP / BEM honesty). **§13** = don’t ship as a product (working-tree `fan_tab.py` SyntaxError, tests that never import the Fan tab, README still claims CFD +2% vs P–Q −17/−26%, 551 ruff issues, no CI). Evidence canvases: `math-application-audit.canvas.tsx`, `production-readiness-review.canvas.tsx`. Sequence: fix §13.0 cockpit parse + import smoke, then §12, then validation P–Q (§1.5) and print+measure (§5). Do **not** treat a green fast pytest as production-ready.

It captures the 2026-09-01 engineering review (major sim-fidelity + feature gaps) + the standing backlog,
tagged by impact/effort, in 6 sections: (1) sim fidelity, (2) missing geometry/features, (3) objectives/
constraints/settings, (4) new archetypes, (5) physical validation (needs the user's hardware), (6) papers.

TOP PRIORITIES (updated 2026-09-01 after an open-literature deep-dive, roadmap §7):
(1) APPLICATION PRESETS (cheap quick win) — load point + objective weights for case/heatsink/RADIATOR;
today load_pa defaults to 1.0 Pa ≈ free air, so the optimizer barely tests static pressure = biggest
single flaw, changes what wins. (2) ★★ AXIAL-FAN BEM SCREENING TIER (§7.1) — a COMPUTE-FREE fan
performance model (Euler pressure-rise + blade-element + empirical loss), the fan analog of our prop
BEMT: instant CFM/pressure/power screening, CFD finalist-only = the big SPEED + pressure-ACCURACY win.
Build it on (§7.2) UIUC LOW-Re AIRFOIL POLARS (Re 60-500k real Cl/Cd; also fixes prop BEMT _cl_cd) +
(§7.3) KROGER-VENTER TIP-CLEARANCE loss correction (stops CFM/pressure over-reading). (3) TIP SHROUD/RING
at OPTIMAL clearance (~30% chord shroud height, NOT zero; winglets help partial shrouds, hurt full) —
how high-static fans win. Also queued: ML surrogate on the 110-design catalog (§7.4); FDM anisotropy +
print penalty (§1.3/§7.6); stator vanes; centrifugal archetype.

STANDING: tip-round + bio-features (tubercles/serrations/dimples) tested NULL on flow AND noise — do NOT
re-optimize for tip shape. Physical print+measure is the north-star gap (nothing measured yet; recorder
built). See [[fan-sim-status]], [[fan-sim-adversarial-review]], [[fan-sim-overnight-jobs]].
