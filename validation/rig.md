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

## Bench setup — what to build (priority order)

You do **not** need an AMCA chamber for the first useful points. Match the **sim operating
condition** (same motor, frame, tip gap idea, **RPM ≈ 2000**) and keep geometry of the *test
fixture* identical between stock impeller vs printed designs.

```text
  SIDE VIEW (free-air, minimum viable)

      inlet air  -->   [ frame + motor + impeller ]  -->  outlet air
                              |         ^
                              |         |  tach laser + reflective tape on hub
                              |
                         12 V PSU

      phone / mic ........ 1.0 m on fan axis (noise)
      anemometer ......... fixed stand at outlet face (or short duct)
```

### Most important (order matters)

1. **RPM match (non-negotiable)**  
   Sim A12x25 is **2000 RPM**. Stick reflective tape on the hub (not a blade tip if possible),
   read tach, adjust voltage/PWM until `tach_rpm ≈ 2000` (±50 is fine for a first pass).  
   Log both `rpm` (setpoint) and `tach_rpm` (measured).

2. **Real mount (commercial frame + motor)**  
   Strip the stock A12x25 impeller; keep **frame + motor + wiring**.  
   Print the impeller from cockpit **Export print STL** (Fit hub/frame **on**).  
   Dry-fit: tip OD ≤ **109 mm** inside **110 mm** frame ID (~**0.5 mm** radial tip gap);
   depth ≤ **25 mm**. If the printed cup binds, caliper the motor boss and re-export
   (`MotorMount` ~37.25 mm cup × 13 mm deep — see `docs/validation/north-star-staged.md`).

3. **Same fixture every run**  
   Same frame orientation, same table, same inlet clearance (keep ≥1 fan diameter of open
   space on the inlet side — for 120 mm fan, ≥**120 mm** clear in front). No hand in the
   stream. Note ambient °C / humidity if easy.

4. **Free-air CFM (anemometer)**  
   Prefer a short outlet duct / cardboard sleeve so the vane sees a known area:  
   `CFM ≈ V_ft/min × area_ft²` (meter does this if you enter area correctly).  
   Measure area with a ruler (ID of sleeve), enter it once, **never change** between designs.  
   Average 5–10 s; take 3 repeats; record mean.  
   Absolute CFM will be biased; **A/B vs stock impeller on the same setup** is what calibrates.

5. **Noise (you already have the app)**  
   Phone on a stand **1.0 m** on the fan centerline, same height as hub, same room, screens off
   / fans elsewhere quiet. Log `noise_dba` — relative only.

6. **Weight (you already have scales)**  
   Weigh the **printed impeller alone** (grams) for the measurement store.

7. **Static pressure / P–Q (after tach + CFM work)** — manometer + DIY box  
   Sealed box on the **inlet** or **outlet** with swappable orifice plates
   (`restriction_id=plate1…`). DP sensor / manometer across the fan (static tap).  
   Free delivery = open; shut-off ≈ plate closed. Same RPM at every plate.

### Distances / dimensions cheat sheet (A12x25-class)

| Thing | Target |
|-------|--------|
| Sim / test RPM | **2000** (measure with tach) |
| Frame ID / tip OD | **110 mm** ID; tip ≤ **109 mm** |
| Axial depth | ≤ **25 mm** |
| Tip gap (radial) | ~**0.5 mm** (matches CFD `--tip-gap`) |
| Inlet clearance | ≥ **1× diameter** open (~120 mm+) |
| Noise mic | **1.0 m** on axis |
| Anemometer | Fixed stand; same face / duct every time |
| Motor cup (print) | ~**37.25 mm** ID × **13 mm** deep (re-caliper your motor) |

### Tools checklist

| Have / buy | Role |
|------------|------|
| A12x25 frame+motor + PSU | Drive unit |
| Printed impeller (export STL) | Test article |
| Laser tach + tape | RPM truth |
| CFM anemometer | Airflow |
| Phone dB app + stand | Relative noise |
| Scale | Impeller mass |
| Manometer (soon) | Static Pa / loaded points |
| Cardboard/PETG sleeve or foam-core box | Known area / later P–Q |
| Calipers | Mount fit vs MotorMount |

### First session recipe (one honest point)

1. Mount **stock** impeller → 2000 RPM → CFM + noise + note orientation.  
2. Mount **printed** design → same RPM / same anemometer pose → CFM + noise + weight.  
3. Cockpit → design → **Record measurement** (`rpm`, `tach_rpm`, `cfm`, `noise_dba`).  
4. Later: manometer + one restriction plate for a loaded point.

Absolute datasheet CFM can wait. **Matched RPM + matched fixture** is what makes the numbers usable for calibration.

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
