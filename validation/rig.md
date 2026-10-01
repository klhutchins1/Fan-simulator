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

**Already have:** used A12x25, PSU, printer + filament, **scales**, **phone dB(A) app**.
**Maybe have:** ESP32 DevKit (check drawer before buying — only needed later for serial logging).

Links below were **HTTP-checked live on 2026-09-30**. Amazon ASINs still rotate — if a
`/dp/` page 404s, use the **search** link in the same row.
Machine-readable copy: [`hardware_bom.csv`](hardware_bom.csv).

### Still buy (~$45–60 now; +~$36 soon)

| # | Item | ~$ | Buy link (checked) | If link dies |
|---|------|----|--------------------|--------------|
| 1 | Laser tachometer | 15–25 | [Wihsentech ~$21](https://www.amazon.com/dp/B0DBM7FJ58) · [NEIKO 20713A](https://www.amazon.com/Neiko-20713A-Digital-Tachometer-Contact/dp/B000I5LDVC) | [search: laser tach](https://www.amazon.com/s?k=non+contact+laser+tachometer) |
| 2 | CFM anemometer | 27–37 | [BTMETER BT-6000GH](https://www.amazon.com/dp/B0D2HGR4QH) | [search: HoldPeak 866B](https://www.amazon.com/s?k=HoldPeak+866B+anemometer) · [search: CFM anemometer](https://www.amazon.com/s?k=CFM+anemometer+handheld) |
| 3 | Dual-port manometer (**Pa** unit) | 35–45 | [DANOPLUS DP-103 ~$36](https://www.amazon.com/dp/B0B12T9BBC) | [search: digital manometer Pa](https://www.amazon.com/s?k=digital+manometer+differential+Pa+HVAC) |

Without matched RPM, CFM/Pa cannot calibrate. **Do not buy** another scale or sound meter.

### Optional / defer

| Item | ~$ | Buy link (checked) | When |
|------|----|--------------------|------|
| USB-C watt meter | 12–20 | [USB-C watt meter](https://www.amazon.com/dp/B0D95QZ9T4) · [search](https://www.amazon.com/s?k=USB-C+power+meter+watt) | Only if fan is USB-C powered |
| ESP32 DevKit | 8–15 | [ESP32-DevKitC-VE ~$11](https://www.amazon.com/dp/B087TNPQCV) · [search](https://www.amazon.com/s?k=ESP32+DevKitC) | Only if you **don’t** already have one; later `rig_logger.py --serial` |
| Sensirion SDP810-500PA | 30–45 | [Sensirion SDP810-500Pa](https://www.sensirion.com/products/catalog/SDP810-500Pa) | Later automated ΔP — manometer first |
| DIY plenum + orifice plates | 10–30 | (foam-core / printed) | After single-point works (§20.7) |

### Skip

Lab ±250 Pa meters, AMCA chambers, calibrated mics, shaft dynos, **extra scales**.

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
