# fansim — Physics-based Fan-Blade Simulator & Optimizer

An automated design loop for cooling-fan impellers: it generates parametric blade geometries, runs
**real CFD** (OpenFOAM MRF) to measure airflow / static pressure / efficiency, scores **noise** on the
GPU (FluidX3D LBM), searches the design space for Pareto improvements, gates every candidate on what's
actually **buildable and mountable**, and exports print-ready STLs — all drivable from an interactive
cockpit. First target: a **Noctua NF-A12x25**-class blade.

The honest north star is **validated relative gains + a real "fan showdown"** against a printed baseline,
not beating a molded LCP fan on absolute numbers with a home print.

Read [`docs/adversarial-review.md`](docs/adversarial-review.md) — it documents what is validated vs. not.
Other docs: [`docs/high-accuracy-plan.md`](docs/high-accuracy-plan.md),
[`docs/design-rules.md`](docs/design-rules.md), [`docs/a12x25-reference.md`](docs/a12x25-reference.md).

## Status (honest)

> **Reading the scores:** the CFM / efficiency shown for a design are CFD results after a motor-power
> limit, a two-point fan-line estimate and a printed-part knockdown. A design the CFD measured at
> 54.8 CFM shows 49.6. Every step, with a worked example, is in
> [`docs/how-scores-are-computed.md`](docs/how-scores-are-computed.md).

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

**Validated CFD method (CFD v5: sealed ring + four-bar frame + prism layers; see
`docs/validation/a12x25_pq_report.md` and `docs/validation/audits/2026-09-28-audit-02-cfd-method-validation.md`):**
- Noctua NF-A12x25 close-reference STL: free-air **59.8 CFM vs published 60.1 (−0.5%)**; 5 / 10 Pa
  converged (52.5 / 41.0 CFM); shut-off ≈ 20–21 Pa vs published 22.9 Pa, but the near-stall points do
  not converge (steady-RANS limit).
- External benchmark FAN-01 (exact published CAD): within **+2.6% / +3.1%**.
- Parametric Stock recipe v2: 56.5 / 49.8 / 40.2 CFM at 0 / 5 / 10 Pa (−5.5% vs the close-ref STL at
  free air).

The cockpit **Assess** uses a faster screening mesh (no prism layers, not grid-converged, GCI ≈ 21%):
use it to **rank** designs, not as absolute CFM. Cockpit "Stock" results dated before 2026-10-08 were
built from a 3-station / uniform-wall approximation of the recipe and should be re-run.

**Honest caveats:** absolute broadband dB(A) is coarse-grid-limited (tone + relative ranking are
usable). Bio-feature benefit tested **null at achievable fidelity** — only a physical print settles
it. BEM is **ranking-only**, not absolute CFM.
Blade vibration (flutter) is a **warning**, not a reject, until printed blades confirm the beam model.
**Scaffolds, not validated:** the wind-turbine archetype (`fansim/wind_turbine`) — tip-speed ratio
does not drive its geometry and its Cp saturates at ≥ 4 blades; do not use it for design claims.

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

## Install

Follow this on a clean machine. The goal is a running cockpit and one Assess. Python **3.12** is required
(3.13+ has no CAD-kernel wheels).

### 1. Install uv

- **Windows:** `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"` then open a new terminal.
- **Linux:** `curl -LsSf https://astral.sh/uv/install.sh | sh` then restart the shell.

Check: `uv --version`.

### 2. Clone and install the project

```bash
git clone <the GitHub URL>
cd Fan-simulator          # or whatever you named the folder
uv sync --extra dev       # core + cockpit + pytest. Plain `uv sync` installs no pytest.
```

`uv` will fetch Python 3.12 if this machine does not have it.

### 3. Docker (needed for CFD / Assess)

- **Windows:** install [Docker Desktop](https://www.docker.com/products/docker-desktop/). It uses WSL2.
  Give WSL2 enough RAM: in `%UserProfile%\.wslconfig` set `memory=16GB` (8 GB is tight; the full test
  suite peaks around 8 GB in one pytest process). Restart WSL with `wsl --shutdown`, then start Docker
  Desktop and wait until it says it is running.
- **Linux:** install [Docker Engine](https://docs.docker.com/engine/install/) and add your user to the
  `docker` group (`sudo usermod -aG docker $USER`), then log out and back in.

Pull the OpenFOAM image (once, a few GB):

```bash
docker pull opencfd/openfoam-default:2406
```

Check: `docker image ls` lists that tag.

### 4. First cockpit and first Assess

```bash
uv run python scripts/cockpit.py --run runs/opt_mountable --reload
```

Open the URL it prints (`http://127.0.0.1:8080`). In the Fan tab, click **Assess**. The first
run downloads nothing extra if step 3 worked; it starts OpenFOAM in Docker and typically takes 30–40 min.

Optional: a small UI test with no Docker is `uv run python -m pytest tests/test_ui_says_what_it_does.py`.
The full fast suite is heavy — use `uv run python scripts/pytest_chunks.py --chunks 3 --all -- -m "not docker and not slow" -q` rather than one long pytest (about 8 GB RSS).

### Troubleshooting

| What you see | What to do |
|---|---|
| `Docker not running` | Start Docker Desktop (Windows) or `sudo systemctl start docker` (Linux). Wait until `docker info` works, then Assess again. |
| image missing / cannot find `opencfd/openfoam-default:2406` | Run the `docker pull` in step 3. |
| WSL2 out of memory / Docker Desktop dies on Windows | Raise `memory=` in `.wslconfig`, `wsl --shutdown`, restart Docker Desktop. |
| `uv: command not found` | Step 1 did not land on PATH. Open a new terminal, or add `$HOME/.local/bin` (Linux) / the uv install dir (Windows). |
| pytest / `No module named pytest` | You ran `uv sync` without `--extra dev`. Repeat step 2 with `--extra dev`. |

## Quickstart

```bash
uv sync --extra dev                                       # core + cockpit + optimizer + pytest/ruff (Python 3.12)
uv run python -m pytest -q -m "not docker and not slow"   # fast tests (no CFD), same as CI
uv run python scripts/cockpit.py --run runs/opt_mountable --reload
```

`--reload` auto-restarts the cockpit when you edit source — no manual restart.
The cockpit is a single-user app: every browser tab connected to one cockpit shares the same state (switching a tab or design in one shows in all). Open one tab per cockpit, or start a second cockpit on another `--port`. A one-off `POST /paraview/ 405` in the browser console at load is the trame-vtk client probing for a launcher; it is harmless.
Optional: `uv sync --extra dev --extra surrogate` adds sklearn; `--extra propulsion` adds PyThrust (without it two prop test modules show as skipped). Plain `uv sync` has no pytest.
On a fresh clone `runs/`, `catalog/catalog.db`, `config/fan_models/` and `build/` don't exist yet: they are created by the first optimizer run, `scripts/catalog.py build`, the first saved user fan model and the first script export. The cockpit starts fine with an empty run folder.

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

## Known limits

Stock is rebuilt from a parametric recipe and reads about 5 % less airflow than the real A12x25 shape (55.7 vs 58.3 CFM in the same test). Designs are compared with this Stock, so comparisons are like for like.

Mixed-flow: Experimental: not validated against published data. Assess runs MRF CFD (not validated against published data).
Volute: ranking only, unvalidated (CFD not yet converged).

## Licence and credits

The code is MIT (`LICENSE`). Third-party models and data keep their own licences and need credit; see
[`THIRD_PARTY.md`](THIRD_PARTY.md). The Stock A12x25 shape is "A12x25" by MajorHardware on Thingiverse (CC BY 4.0).
