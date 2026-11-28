# Fan Simulator v0.1.0 — Release Notes

First public release of **Fan Simulator (`fansim`)**, a desktop tool for designing 3-D-printable PC cooling
fans and drone propellers, checking airflow with OpenFOAM MRF CFD or fast BEMT estimates, and exporting
print-ready STLs with carved motor-mount cavities.

Every accuracy statement below comes from [`docs/VALIDATION.md`](../VALIDATION.md) and the CI-checked
validation scoreboard [`docs/validation/scoreboard.md`](../validation/scoreboard.md).

---

## Highlights

- **Interactive Trame/PyVista cockpit (`fansim-cockpit` / `scripts/cockpit.py`):**
  - **Home start page** with plain-language choices (*Design a PC fan*, *Design a propeller*, *Open a saved design*,
    *How accuracy is checked*) and inline visual guides for blade pitch, sweep, scoop, hub ratio, and static pressure.
  - **Simple mode** by default (plain language, validated surfaces only); **Expert mode** exposes full geometry
    controls, multi-design optimization, and experimental tabs.
  - **Live Docker / OpenFOAM readiness badge** showing whether CFD is ready or what needs to be installed/started.
- **Parametric wrapped-section blade builder & STL export:**
  - NACA and rounded-plate sections lofted on cylindrical stations with hub-clip correction and a two-stage
    hub-hang print refusal gate (blades hanging more than 2 mm below the hub motor face are refused).
  - Print-ready STL export with a carved motor-mount cavity, balance summary, print checklist, and optional
    engraved Crockford print-ID on the hub face.
- **Axial Fan CFD & Optuna NSGA-II optimizer:**
  - Dockerized OpenFOAM MRF CFD (`opencfd/openfoam-default:2406`) with convergence, mass-balance, flow-direction,
    structural, and mountability gating (`--mountable`).
  - Guided wrap-aware search bounds (R1.3 `GUIDED` space) covering Stock with a 2.0 % hang-refusal share.
  - Unified SQLite catalog (`catalog/catalog.db`) indexing designs, CFD results, exports, and user measurements.
- **Propeller fast designer (BEMT):**
  - ~1 s thrust, power, and figure-of-merit analysis plus live multi-objective BEMT optimization using vendored
    UIUC low-Re airfoil polar tables.
- **Safety nets & reproducibility:**
  - Machine-checked validation scoreboard (`docs/validation/scoreboard.md`, tested on every CI run).
  - Physics regression snapshot (`tests/data/physics_snapshot.json`) pinning BEM, BEMT, structural, acoustics,
    and air constants against unintended drift.
  - 34-unit physics audit ledger (`fansim/audit/registry.yaml`, enforced with `scripts/audit_status.py --strict`).

---

## What is validated (against published data)

Full evidence and audit links: [`docs/VALIDATION.md`](../VALIDATION.md) · [`docs/validation/scoreboard.md`](../validation/scoreboard.md) (12 claims: **7 PASS, 3 FAIL, 2 NOT JUDGED**).

| Surface | Published benchmark | Result | Verdict (pre-registered tolerance) |
|---|---|---|---|
| **Fan CFD (axial, CFD v5)** | Noctua NF-A12x25 datasheet (close-ref STL, free air) | **59.8 vs 60.1 CFM (−0.5 %)** | **PASS** (±10 %) |
| **Fan CFD (axial, CFD v5)** | Noctua NF-A12x25 shut-off (formal linear proxy) | **28.0 Pa vs 22.9 Pa (+5.1 Pa)** | **FAIL** (±5 Pa) |
| **Fan CFD (axial, CFD v5)** | Lin & Tsai lt120 (frozen 0.5 mm tip gap, lowest measured load 6.85 Pa) | **90.8 vs 84.0 CFM (+8.1 %)** | **PASS** (±10 %) |
| **Fan CFD (axial, CFD v5)** | Lin & Tsai lt120 (mid load 13.71 Pa) | **75.5 vs 60.0 CFM (+25.8 %)** | **FAIL** (±10 %; overall lt120 verdict: **TRENDS**) |
| **Fan CFD (axial, CFD v5)** | FAN-01 exact CAD (Zenodo 10787093, 7 Pa / 64 Pa) | **+2.5 %** at 7 Pa / **+3.1 %** at 64 Pa | **NOT JUDGED** (no tolerance was pre-registered) |
| **Propeller BEMT** | UIUC APC E 9x6 (near 6000 rpm, default tables) | static C_T **+0.4 %**, static C_P **−5.3 %**, C_T(J) RMS **0.0085** | **PASS / PASS / PASS** (±15 % / ±20 % / ≤ 0.015) |
| **Propeller BEMT** | UIUC APC SF 9x4.7 (near 6000 rpm, default tables) | static C_T **−12.5 %** (PASS), static C_P **−20.2 %** (FAIL), C_T(J) RMS **0.0139** (PASS vs ≤ 0.015) | Static C_T & sweep RMS **PASS**; static C_P **FAIL** (known limit) |

---

## Experimental surfaces (frozen for v0.1.0)

Per the 2026-11-15 release scope decision, the following four surfaces ship in Expert mode labelled
**"Experimental: not validated against published data."** Their validation moves to v0.1.1:

- **Propeller CFD** — fails against UIUC (−44 % C_T / −40 % C_P static; −40 / −45 / −58 % C_T in forward flight).
  Use for flow direction and visualization only; use Propeller BEMT for performance estimates.
- **Mixed-flow** — rotation direction proved by geometry; no open-licensed small-fan benchmark curve yet.
- **Volute / centrifugal** — direction proved, but steady RANS is unconverged on the fine mesh (relaxation sweep
  chose `none`/`none`); transient averaging (`pimpleFoam`) moves to v0.1.1.
- **CROR** — rotation direction proved by geometry; Shigemitsu 2018 validation campaign moves to v0.1.1.

Excluded from v0.1.0: the wind-turbine scaffold (`fansim/wind_turbine`) and standalone centrifugal archetype are
not exposed in the cockpit or README quickstart.

---

## Known limits

1. **No physical airflow or acoustic measurements yet:** printed-rig measurements come in v0.1.1. Displayed scores
   apply an assumed 5 % printed-part knockdown (×0.95) that has not been measured yet
   ([`docs/how-scores-are-computed.md`](../how-scores-are-computed.md)).
2. **Stock parametric recipe gap:** shipping Stock v3 reads about 5 % less airflow than the close-reference A12x25
   STL (**55.7 vs 58.3 CFM**, −4.5 %, in the cylinder-sections diagnostic rig; vs 59.8 CFM for the close-ref STL
   in full CFD v5). Designs are compared against Stock in the same test, so comparisons are like for like.
3. **Assess is a screening mesh (`GCI_fine ≈ 21 %`):** rank designs against Stock at identical settings (±1 %
   repeatability on Stock); never compare Assess numbers directly with a manufacturer datasheet.
4. **Loaded and near-stall steady RANS limits:** steady RANS does not converge near stall (≥ 15 Pa on A12x25,
   ≥ 126 Pa on FAN-01) and over-predicts lt120 at 13.71 Pa by +25.8 % (tip-gap follow-up: G3, not explained).
   Treat loaded airflow as a ranking signal; unconverged loaded points display a warning.
5. **Noise is not validated:** blade-pass tone frequency (`rpm × blades`) is exact, but all sound-level outputs
   are unvalidated estimates for exploration only.
6. **Structural and blade vibration checks are estimates, not validated:** closed-form beam checks only; the
   vibration check is a resonance check, not flutter.
7. **Propeller BEMT limits:** static thrust within ±15 %, worse toward zero-thrust J on props with unknown airfoil
   sections; power (`C_P`) can read ~21 % low on slow-flyer props.

---

## Install & quickstart

Requires **Python 3.12** via [`uv`](https://docs.astral.sh/uv/) (3.13+ lacks CAD-kernel wheels) and Docker with
`opencfd/openfoam-default:2406` for CFD / Assess. See the full Windows and Linux guide in [`README.md`](../../README.md).

```bash
uv sync --extra dev
docker pull opencfd/openfoam-default:2406
uv run python scripts/cockpit.py
```

Open `http://127.0.0.1:8080` in your browser. For the fast test suite without Docker:

```bash
uv run python scripts/pytest_chunks.py --chunks 3 --all -- -m "not docker and not slow" -q
```

---

## Licence & third-party credits

- Code: **MIT** ([`LICENSE`](../../LICENSE)).
- Third-party geometries and benchmark datasets keep their own licences and attributions — see
  [`THIRD_PARTY.md`](../../THIRD_PARTY.md) (including MajorHardware's A12x25 STL CC BY 4.0, FAN-01 Zenodo 10787093
  CC BY 4.0, UIUC Propeller Data Site, and Tutar & Cam / Lin & Tsai lt120 CC BY 4.0). Non-MIT-compatible data and
  unknown-origin STLs listed in [`RELEASE_EXCLUDE`](../../RELEASE_EXCLUDE) are excluded from the public export.
