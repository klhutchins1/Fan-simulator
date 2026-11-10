# First print session with a tach and a phone: pre-registration (2026-11-09)

Written by Claude before any print or measurement, at Kimball's request. It amends
[`first_print_measure_plan.md`](../first_print_measure_plan.md) (2026-10-13), which assumed an anemometer.
Kimball has a laser tach and a phone (microphone and camera). There is no airflow or pressure meter.

**What is printed:** article B, Stock v3, exactly as frozen in that plan. No optimizer candidate. This session
is about fit, shape, the engraved ID and the test routine. It can check the airflow prediction only by the
bag method below, and only roughly.

**This session cannot validate CFD by itself.** Whatever it shows, v0.1.0 claims stay tied to published data.

## Articles

| # | article |
|---|---|
| A | genuine Noctua A12x25 impeller |
| B | printed Stock v3, with its print-id |

**Same motor or two motors (added 2026-11-09, before any data):** the 2026-10-13 plan runs A and B on the same
frame and motor. If that is not possible and they run on two fans, T5 is INCONCLUSIVE whatever it reads, because
Noctua's own speed tolerance is ±10 % from motor to motor. T6 still works, with the rpm scaling in step 5.

Note material, layer height, nozzle, infill and the export's print-id for B.

## Judged checks (pass / fail rules fixed now)

| id | check | how | pass | if it fails |
|---|---|---|---|---|
| T1 | **Fit** | press B onto the motor by hand; spin by hand in three frame orientations; look at the tip gap all the way round | seats fully by hand, turns freely, never touches the frame, gap looks even and is between 0.3 and 0.8 mm | measure the motor boss and the cup with calipers; that is a mount-gauge finding, not a blade finding |
| T2 | **Weight** | weigh B alone | within ±10 % of the weight the cockpit Preview states for the same material and infill (if the print used other settings, record only) | check infill and wall settings first, then the density the tool assumes |
| T3 | **Engraved ID** | hand B to someone who has not seen the code; arm's length, room light, no magnifier | they read all 5 characters correctly | record which characters failed; widen the stroke or raise the cap height in the mark spec |
| T4 | **Instruments agree** | for A and for B: tach rpm against rpm from the phone recording (`scripts/analyze_fan_recording.py --blades 9`) | within 2 % on both | every rpm-based number from this session is INCONCLUSIVE until one of the two is fixed |
| T5 | **Speed at full drive** | A and B each at 12 V, 100 % PWM, after 2 minutes; tach | B's rpm is 0.93 to 1.03 × A's | below: look for rubbing, a tight cup dragging the bearing, or rough blades. Above: the printed blade is absorbing less power than the real one, so check its shape against the STL |
| T6 | **Airflow ratio by bag** (optional) | see "Bag method" | B/A is 0.85 to 0.97, the band already registered on 2026-10-13 | follow that plan's failure table |

Basis for T5: CFD puts Stock's shaft power at 0.76–0.78 W at 2000 rpm, inside the motor's 0.84 W budget
(`2026-10-10-motor-efficiency.md`), so the printed Stock should hold about the same speed as the real blade. The
band is loose on purpose: the motor's torque curve is not known, and a rougher printed surface adds some drag.
T5 is a drag and fit check. It is not a test of the CFD power number.

**INCONCLUSIVE is not a pass.** T6 is INCONCLUSIVE, not failed, if either article's five fill times vary by more
than 4 % (standard deviation over mean), or if T4 failed.

## Bag method (T6)

A bag that fills in a known time gives airflow without a meter. Absolute numbers are rough, so only the ratio
B/A is judged, as in the 2026-10-13 plan.

1. Use one large thin bag for everything (a 55-gallon drum liner, about 200 L, fills in roughly 7 s at 60 CFM).
   Tape its mouth to a cardboard collar that slips over a short sleeve on the fan's outlet.
2. Lay the bag flat and empty on a table. Run the fan at 2000 rpm by tach with the collar off.
3. Film with the phone. Slip the collar on in one motion. The fill time runs from collar-on to the first frame
   where the bag is fully round and its skin stops moving.
4. Five fills for A, then five for B: same bag, sleeve, table and person. Read the tach during each fill.
5. For each article, airflow is proportional to `1 / mean fill time`. If the two speeds differ, scale by
   `2000 / tach_rpm` first. B/A = `mean time A / mean time B`, after that scaling.

Limits, stated now: judging "full" by eye is good to about half a second, so the ratio is good to roughly
±0.05. That is nearly the width of the band. A result within 0.03 of either band edge is INCONCLUSIVE. A vane
anemometer (about $25) would do this better and is the only thing worth buying for the next session.

## Recorded, not judged (no prediction exists)

The project has no validated noise model, so nothing below can pass or fail. Record it so later sessions have a
baseline.

- Phone recording of A and of B, each at 2000 rpm by tach, phone on a stand 1.0 m in front of the fan on its
  axis, same room, 20 s each, plus 20 s with the fan off. WAV, automatic gain and noise suppression off.
  The tool reports B minus A in dB and how far the blade-pass tone (300 Hz at 2000 rpm, 9 blades) stands above
  the noise. These are relative numbers, not dB(A).
- A recording of each article coasting down after power is cut. Kept for a later torque estimate; not analysed now.
- Photos of the leading and trailing edges, the tip, and the engraved ID.
- Anything that had to be done to make B fit or run (sanding, reaming, a second print).

## What each outcome changes

| outcome | what we do |
|---|---|
| T1 or T2 fails | fix the mount gauge or the weight estimate before any other print |
| T3 fails | change the mark spec; re-print only the hub top as a small test piece |
| T4 fails | no speed or airflow conclusions from this session |
| T5 fails | find the drag (fit, rub, roughness) before trusting T6 |
| T6 passes | the CFD + recipe + print chain holds at free air to about ±6 %; buy the anemometer and repeat properly |
| T6 fails | follow the 2026-10-13 plan's table; do not tune the simulation to the print |
| T6 inconclusive or skipped | nothing is learned about airflow; say so |

## Results (to fill in after the session; do not edit anything above)

| check | A | B | result |
|---|---|---|---|
| T1 fit | n/a | | |
| T2 weight (g) | n/a | measured ___ / Preview ___ | |
| T3 ID read | n/a | code ___ read as ___ | |
| T4 tach / phone rpm | ___ / ___ | ___ / ___ | |
| T5 rpm at 12 V | | | ratio ___ |
| T6 fill times (s) | | | B/A ___ |
| recorded only: level B − A (dB), tone above noise (dB) | | | |
