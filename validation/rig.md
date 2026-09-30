<!-- RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md. -->

# Physical validation rig (plan Phase 6 — deferred hardware; software hooks ready)

The eventual credibility backbone for a "fan showdown": measure a printed part and feed the numbers
back through `validation/ingest.py` to calibrate the simulation. **Hardware not built** — no
calibrated instruments on hand — but the software logger + ingest schema are in place. Nothing in
the pipeline depends on hardware existing.

## What to measure (per operating point)
- **Airflow (CFM)** and **static pressure (Pa)** on a P–Q rig (ISO 5801 / AMCA 210 style): a plenum
  chamber with an auxiliary blower and a set of calibrated nozzles/orifice, so you sweep from free
  delivery to shut-off. This is the gold-standard comparison for `cfm_free`, `cfm_load`, shut-off.
- **Noise dB(A)** at 1 m: even an *uncalibrated* mic captures *relative* A/B deltas between designs
  under identical conditions — enough to check the LBM's relative ranking, which is all it claims.
- **RPM / tach** to fix the operating condition (match the sim's 2000 RPM), and shaft power if a
  torque/current measurement is available (for efficiency).

## Minimum viable version
Print two designs, run both on the same motor at the same RPM in the same duct, and record relative
CFM (anemometer), relative pressure (manometer), and relative noise (phone mic, same distance).
Absolute accuracy is secondary; **matched A/B deltas** validate the *relative* rankings the whole
project optimizes for (the honest north star).

## Shopping list (low-cost — ranked)

**You already have:** used A12x25 (~$15), PSU (~$15), printer + PLA/PETG.

Prices surveyed 2026-09; Amazon ASINs rotate — any equivalent tach / CFM anemometer / Pa manometer is fine.
Machine-readable copy: [`hardware_bom.csv`](hardware_bom.csv).

### Buy first (~$45)

| # | Item | ~$ | Link |
|---|------|----|------|
| 1 | Laser tachometer (non-contact) | 15–25 | [Mulcort ~$15](https://www.amazon.com/dp/B0B9KXP9LZ) · [alt ~$24](https://www.amazon.com/dp/B0DBM7FJ58) |
| 2 | CFM anemometer | 27–37 | [BTMETER BT-6000GH ~$31](https://www.amazon.com/dp/B0D2HGR4QH) · [BT-5000D ~$27](https://www.btmeter-store.com/products/bt-5000d-anemometer-rechargeable) |

Without matched RPM, CFM/Pa cannot calibrate.

### Buy next (~$50)

| # | Item | ~$ | Link |
|---|------|----|------|
| 3 | Dual-port digital manometer (use **Pa**) | 35–45 | [manometer ~$40](https://www.amazon.com/dp/B0FG7XDY3Q) · [alt ±2 psi / Pa](https://www.amazon.com/dp/B0BBHDTQXK) |
| 4 | Pocket scale 500 g × 0.01 g | 10–17 | [Kizing ~$12](https://www.amazon.com/dp/B08BHKW2J8) · [alt ~$14](https://www.amazon.com/dp/B07R32V1Y2) |

### Optional / defer

| Item | ~$ | Link | When |
|------|----|------|------|
| Phone dB(A) at 1 m | 0 | (phone app) | Relative noise A/B only |
| USB-C watt meter | 12–20 | [example](https://www.amazon.com/dp/B0D95QZ9T4) · [alt](https://www.amazon.com/USB-Tester-Type-Power-Meter/dp/B0B48LG5N4) | Only if fan is USB-C powered |
| ESP32 DevKit | 8–15 | [Espressif ~$11](https://www.amazon.com/dp/B087T94ZH9) · [2-pack](https://www.amazon.com/dp/B0B5LFG394) | Later: `rig_logger.py --serial` |
| Sensirion SDP810-500PA | 30–45 | [DigiKey](https://www.digikey.ca/en/products/detail/sensirion-ag/SDP810-500PA/6605489) · [RS](https://my.rs-online.com/web/p/pressure-sensor-ics/1331913) | Later automated ΔP — buy manometer first |
| DIY plenum + orifice plates | 10–30 | (foam-core / printed) | After single-point works (§20.7 sweep) |

### Skip

Lab ±250 Pa meters ([PCE-PME 250](https://www.pce-instruments.com/us/measuring-instruments/test-meters/hvac-meter-hvacr-tester-pce-instruments-hvac-meter-hvacr-tester-pce-pme-250-det_6311246.htm) ~$264+), AMCA chambers, calibrated mics, shaft dynos.

Ingest readings via cockpit **Record measurement** or `scripts/rig_logger.py` (columns below).

## Low-cost P–Q rig (§20.7 — hardware still open)
Build when ready: plenum box, swappable restriction plates, digital differential-pressure sensor
(e.g. Sensirion SDP810), tach, microcontroller. Log straight into the CSV schema below via
`scripts/rig_logger.py`, then `validation.ingest.load_measurements` / the cockpit measurement store.

### CSV columns (`validation.ingest.CSV_COLUMNS`)
| Column | Required | Notes |
|--------|----------|--------|
| `rpm` | yes | Commanded / setpoint RPM |
| `cfm` | no | Measured airflow |
| `static_pressure_pa` | no | Processed static (Pa) |
| `noise_dba` | no | A-weighted noise |
| `source` | no | Instrument / rig id |
| `notes` | no | Free text |
| `restriction_id` | no | Plate / orifice id (e.g. `plate3`) |
| `dp_pa` | no | Raw differential pressure from DP sensor |
| `tach_rpm` | no | Measured tach if distinct from commanded `rpm` |
| `ambient_c` | no | Ambient temperature °C |
| `humidity_pct` | no | Relative humidity % |

Older CSVs with only `rpm,cfm,static_pressure_pa,noise_dba[,source,notes]` still load.

### Logger CLI
```text
# Piped / interactive key=value lines (stdin; no pyserial required)
echo rpm=2000,dp=12.3,cfm=45,noise=38,restriction=plate3 | uv run python scripts/rig_logger.py --out runs/rig.csv --source sdp810

# Serial (optional — needs pyserial)
uv run python scripts/rig_logger.py --out runs/rig.csv --source sdp810 --serial COM3

# Load + calibrate against simulated points
uv run python -c "from validation.ingest import load_measurements, calibrate; ..."
uv run python scripts/calibrate_from_store.py
```

Accepted line aliases: `dp`→`dp_pa`, `noise`→`noise_dba`, `restriction`→`restriction_id`,
`tach`→`tach_rpm`, `ambient`→`ambient_c`, `humidity`→`humidity_pct`, `static`→`static_pressure_pa`.

Cockpit: Fan → Library → **Record measurement** → **Show store calibration** prints aggregate
cfm / static / noise factors from `validation/measurements/` into the status text.

## Ingest
`validation/ingest.py`:
- `load_measurements(csv)` → `list[MeasuredPoint]` (core + optional rig fields above).
- `calibrate(measured, simulated)` → per-quantity sim→reality factors (CFM/pressure ratios, dB offset).

Fill the CSV, pair it with the matching simulated operating points, and the calibration factors tell
you how optimistic the idealized-geometry sim is — and let you correct future predictions.
