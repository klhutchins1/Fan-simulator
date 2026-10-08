<!-- RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md. -->

# fansim — Physics-based Fan-Blade Simulator & Optimizer

An automated design loop for cooling-fan impellers: it generates parametric blade geometries, runs
**real CFD** (OpenFOAM MRF) to measure airflow / static pressure / efficiency, scores **noise** on the
GPU (FluidX3D LBM), searches the design space for Pareto improvements, gates every candidate on what's
actually **buildable and mountable**, and exports print-ready STLs — all drivable from an interactive
cockpit. First target: a **Noctua NF-A12x25**-class blade.

The honest north star is **validated relative gains + a real "fan showdown"** against a printed baseline,
not beating a molded LCP fan on absolute numbers with a home print.

Plan: `../../.claude/plans/i-want-a-plan-smooth-sifakis.md`.
Read [`docs/adversarial-review.md`](docs/adversarial-review.md) — it documents what is validated vs. not.
Other docs: [`docs/high-accuracy-plan.md`](docs/high-accuracy-plan.md),
[`docs/design-rules.md`](docs/design-rules.md), [`docs/a12x25-reference.md`](docs/a12x25-reference.md).

## Status (honest)

**Built & working:**
- Parametric geometry → watertight STL (NACA sections lofted through radial stations, circumferential
  wrap, per-station chord/stagger/camber/thickness/sweep/lean, configurable hub height + profile
  (cylinder/cone/dome), bio-inspired features: tubercles / TE-serrations / dimples).
- Dockerized **OpenFOAM MRF CFD** (8-core parallel), with manufacturability + structural + fan-envelope
  + convergence gating. Runs isolated in a subprocess so a solver/geometry crash can't take down the app.
- Multi-objective **optimizer** (Optuna NSGA-II): airflow (free + loaded) + efficiency, optional noise;
  guided/extended search spaces; a **`--mountable`** constraint that only searches hubs big enough to fit
  the real motor.
- **GPU noise tier** (FluidX3D LBM): control-volume-force Curle dipole → BPF tone + relative dB(A) ranking;
  transient shut-off pressure.
- **Cockpit** (Trame/PyVista): browse the design space, load any design from the unified catalog, edit
  every parameter (with hover min/max images), Preview (spec-check + printability grade + out-of-spec
  highlight + case-envelope overlay), Assess/Sweep with live CFD, randomize geometry/features, and record
  physical measurements.
- **Print & mount export**: fine STL + print sheet (material/temps/orientation/supports) + balance +
  graded printability + a parameterized **motor-mount cup** carved for the fan model.
- **Unified catalog** (`catalog/catalog.db`): every design across every run + its sim results + print
  files + measurements, one stable id per design.
- **Measurement store** + sim-vs-real calibration hooks (`validation/`).
  Hardware shopping list (ranked, cheap Tier‑1): [`validation/hardware_bom.csv`](validation/hardware_bom.csv)
  — see also [`validation/rig.md`](validation/rig.md).

**Validated (interim — see `docs/validation/a12x25_pq_report.md`):** close-reference STL free-air
is about **−17%** vs published 60.1 CFM (~49.8 CFM; prism layers ~50.4). Parametric Stock free-air
screening is roughly **−26%** at tip_gap 0.5 mm. Shut-off **proxy** ~24 Pa on Stock (interim pass)
but fails on the close-ref STL (~14.6 Pa). The old “+2% free-air” claim is **retired**. Relative
rankings under a fixed mesh/settings budget remain the usable signal; absolute CFM needs print +
measure.

**Honest caveats:** absolute broadband dB(A) is coarse-grid-limited (tone + relative ranking are
usable). Bio-feature benefit tested **null at achievable fidelity** — only a physical print settles
it. BEM is **ranking-only**, not absolute CFM.

**The one real gap:** nothing has been physically **printed and measured** yet. That's the next step, and
it's on the user side — see the workflow below.

## The workflow

```
optimize  ─►  browse/tweak in the cockpit  ─►  export print files  ─►  print + mount  ─►  measure  ─►  catalog
 (CFD)          (pick a design, edit, Assess)     (STL + print sheet)     (your printer)   (record it)   (compare)
```

1. **Optimize** — search for good, buildable designs (see commands below).
2. **Cockpit** — browse the Pareto front, load any catalogued design, edit and re-Assess, compare.
3. **Export** — `export_finalists.py` writes a print-ready STL + print sheet per finalist, with the
   motor-mount cavity carved and a "mountable / print-difficulty" verdict.
4. **Print + mount** — print the STL (PETG default), slip the hub cup over the motor.
5. **Measure** — read airflow / noise, and type it into the cockpit's *Record measurement* panel.
6. **Catalog** — the measurement joins that design's sim numbers; the sim-vs-real gap calibrates the model.

## Environment

- Python **3.12** via [`uv`](https://docs.astral.sh/uv/) (system 3.13+ lacks CAD-kernel wheels).
- CFD: OpenFOAM in Docker (`opencfd/openfoam-default:2406`).
- GPU noise: FluidX3D compiled at `../FluidX3D` (msys2 ucrt64), optional. Elsewhere: set
  `FANSIM_FLUIDX3D` (and `FANSIM_MSYS_BIN` for the msys2 runtime on Windows).
- Print materials: PLA, PLA+, PETG (default), ABS, TPU.

## Quickstart

```bash
uv sync --extra dev                                       # core + cockpit + optimizer + pytest/ruff (Python 3.12)
uv run python -m pytest -q -m "not docker and not slow"   # fast tests (no CFD), same as CI
uv run python scripts/cockpit.py --run runs/opt_mountable --reload
```

`--reload` auto-restarts the cockpit when you edit source — no manual restart.
Optional: `uv sync --extra dev --extra surrogate` adds sklearn. Plain `uv sync` has no pytest.

## Key commands

```bash
# Optimize (CFD; needs Docker). --mountable keeps designs that fit the real motor.
uv run python scripts/run_optimization.py --space guided --extended --mountable --noise --trials 30 --out runs/opt_mountable

# Export a run's finalists as print-ready STLs + print sheets (+ motor-mount cup).
uv run python scripts/export_finalists.py --run runs/opt_mountable --material PETG

# Unified catalog: index every design across all runs + measurements, then browse it.
uv run python scripts/catalog.py build
uv run python scripts/catalog.py list --pareto
uv run python scripts/catalog.py show opt_mountable_t1

# Validate CFD against the real A12x25, or GPU-score a run's noise.
uv run python scripts/validate_a12x25.py
uv run python scripts/score_feature_noise.py --run runs/feat_study2

# Reclaim disk: prune regenerable OpenFOAM case internals (dry-run first; --apply to delete).
uv run python scripts/prune_runs.py                # shows reclaimable; deletes nothing
uv run python scripts/prune_runs.py --apply        # frees it (STLs + results + catalog kept)
```

## Data layout

```
runs/<name>/           study.db (Optuna trials) · pareto.json · trials/… (CFD cases) · print/ · cockpit_assess/
catalog/catalog.db     unified index over all runs + measurements (rebuild anytime)
validation/measurements/<design_id>.json   physical readings tied to a design's sim numbers
config/fan_models/     drop-in YAML fan-model specs (envelope + motor + mount)
build/                 one-off / reference STLs
```

Case internals (mesh, `processor*`, logs) are regenerable and safe to prune once solved — the results
(`study.db` / `result.json` / catalog) and STLs are always kept, and any case can be re-meshed + re-run.
