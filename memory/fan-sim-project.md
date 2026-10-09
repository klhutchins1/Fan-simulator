---
name: fan-sim-project
description: Fan-simulator project goals, scope decisions, and hard constraints
metadata:
  type: project
---

**fansim** = physics-based parametric fan-blade simulator + multi-objective optimizer.
Generates parametric blades → CFD (CFM, static pressure, noise) → iterates bio-inspired
features (tubercles, TE serrations, dimples, sweep, winglets) → Pareto search → 3D-print.
First target: Noctua NF-A12x25 envelope; architecture generalized via a config-driven
`Problem`/archetype layer (only axial-fan implemented; windmill/centrifugal are future work).

Approved plan: `C:\Users\Kimball\.claude\plans\i-want-a-plan-smooth-sifakis.md`.

**Confirmed decisions (2026-08-26):**
- CFD: hybrid ladder — OpenFOAM steady-MRF (CPU) primary/reported, FluidX3D (GPU LBM) as
  screening + real-time viz tier. Noise: cheap RANS proxy (Proudman/Curle) first, LES+FW-H
  on finalists only.
- Frontend: Trame/PyVista design cockpit, built early (Phase 1b).
- Generality: build the interface now, implement one archetype (axial fan) only.
- Physical validation (print+measure+calibrate): DEFERRED — user has a 3D printer + a
  regular (non-measurement) mic, no Noctua fan on hand, no calibrated instruments. Hooks only.
- Structural/manufacturability: lightweight analytic gate now, full FEA on finalists.
  Printable filaments limited to PLA/PLA+/PETG/ABS/TPU (no ASA/CF/glass-filled). PETG is the
  structural default; PLA flagged for thermal creep ~55-60C near warm case air.

**Honest north star:** beating stock A12x25 in ABSOLUTE terms with a printed part is
unlikely (LCP stiffness + sub-0.1mm tip clearance). Provable win = validated open-source
framework + RELATIVE feature gains over a printed baseline under identical conditions.

See [[fan-sim-environment]] for the toolchain.
