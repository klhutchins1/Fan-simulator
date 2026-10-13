# External STLs: radial-led direction rule (27.2b), QA round 9 Task D

Prereg: `PREREG_R9.md` §Task D (commit a0260c0, branch prereg/round9 in the QA-only clone). Code under test:
`fansim.audit.direction.prove_direction` (cylinder) and round-8 `stacking_cut.prove_direction_stacking(mode="radial")`
(copied unchanged into `docs/qa/ext_stl/`). Scripts: `docs/qa/ext_stl/prep_truth.py` (prepare + truth, run first and
frozen), `run_readers.py` (both readers, original + y-mirror, rule). Data: `docs/qa/ext_stl/ext_stl_r9_results.json`.
**The outside STLs were downloaded to `/tmp/qa9_ext/` only. None is committed or copied into the repo.**

## Result: FAIL as pre-registered, and the confirmation is not valid either way

Of 26 external parts plus 2 repo references, 15 got a pre-registered ground truth (13 external).

| | originals | mirrors |
|---|---|---|
| ACCEPT and correct | 6 (4 external + both refs) | 6 |
| ACCEPT and **wrong** vs the registered truth | **7** | **7** |
| ASK | 2 | 2 |

Coverage over all 28 parts: radial-led ACCEPT on 20/28 originals and 20/28 mirrors. ASK on 8, all because the
radial reader was INCONCLUSIVE (flat or uncambered blades, toroidal blades, one single-radius read). The two
readers **never** disagreed when both were CONCLUSIVE (0 of 18). The rule's "disagree → ask" branch was never used.

**Why I don't count the 7 as reader errors (post hoc, not registered):**
- Every one of the 7 disagrees on the spin only. Chirality (the helix hand, omega × pump) matches the truth in 13 of 13
  truth parts. So the readers get the blade's handedness right and differ from my truth only on which end is the
  leading edge.
- My registered omega cue was "the blunter end is the LE" (falling back to tip lead). Plots of the unrolled sections
  (kept local, `/tmp/qa9_ext/sections.png`) show that most of these hobby blades are constant-thickness plates
  truncated flat by the print planes z = 0 / z = top. The "thicker end" is an oblique cut through the plate, not a
  rounded LE. For example, on 652389 (3V DC motor fan) the flat end sits at the bottom and turns to near-axial at the
  top. That is the shape of an LE at the bottom moving +θ, which agrees with the readers. Tip lead is also unreliable
  here: several blades are swept back.
- On the two parts where the cue is a real rounded LE (a12x25 and fan01), the truth, both readers and round 8 agree.
- **The pair test agrees with the readers.** Printables 336131 ships a CW file and a CCW file (spin wording only, no
  stated viewing side). The readers give opposite chirality for the two (+1 / −1), as a mirrored pair must.

**What it needs:** STLs whose page states the spin *and* the airflow side, or a physical fan, so the truth is
independent of blade shape. None of the 26 Printables pages states one. The radial-led rule stays unconfirmed. I
would not ship it to users on this evidence alone, but nothing here shows it reading a real rounded-LE blade wrong.

## Parts (all Printables, CC-BY or CC0; local use only)

| part | title | author | licence | URL | truth (ω,pump,χ) | rule (orig) | score |
|---|---|---|---|---|---|---|---|
| p1388820 | Ventline BVD0217-00 Replace fan blade | secretbetta | CC0 | https://www.printables.com/model/1388820-ventline-bvd0217-00-replace-fan-blade | – | ASK | – |
| p1412585 | Fan for electric motor (axle ⌀2mm) | Gu Costa | CC0 | https://www.printables.com/model/1412585-fan-for-electric-motor-axle-2mm | (1,−1,−1) | ACCEPT (−1,1,−1) | WRONG (ω) |
| p1641770 | Fan propeller. (remix) | ZŠ Montessori Slaný | CC0 | https://www.printables.com/model/1641770-fan-propeller-remix | (1,−1,−1) | ASK | ASK |
| p201295 | Lasko box fan blade | auroratechchannel | CC-BY | https://www.printables.com/model/201295-lasko-box-fan-blade | – | ASK | – |
| p216638 | USB 100mm FAN Blade | Bazzalight | CC-BY | https://www.printables.com/model/216638-usb-100mm-fan-blade | (1,1,1) tip-lead only | ACCEPT (−1,1,−1) | WRONG (ω) |
| p261417 | Vornado 630 Replacement Fan Blade | ch1a | CC-BY | https://www.printables.com/model/261417-vornado-630-replacement-fan-blade | (1,−1,−1) | ACCEPT (−1,1,−1) | WRONG (ω) |
| p307027 | 4010 fan blade | DARISON VINCENT | CC0 | https://www.printables.com/model/307027-4010-fan-blade | – | ACCEPT | – |
| p507838 | 220mm replacement propeller for desktop fan | Matten79 | CC0 | https://www.printables.com/model/507838-220mm-replacement-propeller-for-desktop-fan | (−1,1,−1) | ACCEPT | OK |
| p599535 | Ender 3/Pro Front Fan Blade Replacement | AlexCreations69 | CC-BY | https://www.printables.com/model/599535-ender-3pro-front-fan-blade-replacement | – | ACCEPT | – |
| p640037 | 310mm Toroidal fan blade | Drenth Engineering | CC0 | https://www.printables.com/model/640037-310mm-toroidal-fan-blade | (1,−1,−1) | ACCEPT (cyl INCONCL.) | OK |
| p652389 | 3V DC Motor Fan | Aarav Mehta | CC0 | https://www.printables.com/model/652389-3v-dc-motor-fan | (−1,−1,1) | ACCEPT (1,1,1) | WRONG (ω) |
| p716523 | Bathroom Fan Exhaust Impeller | Jonathan Y | CC-BY | https://www.printables.com/model/716523-bathroom-fan-exhaust-impeller | – | ASK | – |
| p797665 | 40mm Fan Blade Replacement / Fix | Nahuel | CC-BY | https://www.printables.com/model/797665-40mm-fan-blade-replacement-fix-usongshine-ender-3 | – | ACCEPT | – |
| p1286657 | 50mm blades for electric motor cooling fan (10 blades) | Leo | CC0 | https://www.printables.com/model/1286657-50mm-blades-for-electric-motor-cooling-fan-with-6m | (1,1,1) | ACCEPT | OK |
| p1493852 | Hykolity fan blade replacement | DamadgediceDM | CC0 | https://www.printables.com/model/1493852-hykolity-fan-blade-replacement | (1,−1,−1) | ACCEPT (cyl INCONCL.) | OK |
| p159340 | FAN 10-blades 80mm | MP001 | CC-BY | https://www.printables.com/model/159340-fan-10-blades-80mm | (1,1,1) | ACCEPT (−1,−1,1) | WRONG (ω) |
| p1606446 | Ender 3 Fan blade | Msanyee | CC-BY | https://www.printables.com/model/1606446-ender-3-fan-blade | (−1,1,−1) | ACCEPT (1,−1,−1) | WRONG (ω) |
| p1639960 | a small 2-3 gram 5 blade fan | Giltching | CC0 | https://www.printables.com/model/1639960-a-small-2-3-gram-5-blade-fan | (−1,−1,1) | ACCEPT (1,1,1) | WRONG (ω) |
| p1743512 | "Ovoidal" fan - 3 blades | John | CC-BY | https://www.printables.com/model/1743512-ovoidal-fan-3-blades | – | ASK | – |
| p336131 / p336131ccw | Creality 4010 Replacement Fan Blades (CW and CCW files) | Luiz Nic | CC0 | https://www.printables.com/model/336131-creality-4010-replacement-fan-blades-for-ender-3 | – (pair) | ACCEPT χ=+1 / χ=−1 | pair consistent |
| p455128 | 60x60x15mm fan blades replacement | vismakan | CC0 | https://www.printables.com/model/455128-60x60x15mm-fan-blades-replacement | – (LE vs tip-lead disagree) | ACCEPT | – |
| p488577 | Toroidal Blade For Desk Fan | Owen Grubb | CC-BY | https://www.printables.com/model/488577-toroidal-blade-for-desk-fan | – | ASK | – |
| p516885 | Toroidal cooling fan 80mm propeler | EduGomes | CC-BY | https://www.printables.com/model/516885-toroidal-cooling-fan-80mm-propeler | (1,−1,−1) | ASK | ASK |
| a12x25_ref_stl | repo reference | – | repo | validation/reference/a12x25_impeller.stl | (1,−1,−1) | ACCEPT | OK |
| fan01_rotor | repo reference | – | repo | validation/reference/fan01/fan01_rotor.stl | (1,1,1) | ACCEPT | OK |

Mirrors scored the same as their originals in every row. Files were fetched through Printables' public download
link; the file ids are in the results JSON. Prep was a proper rotation of the most distinct inertia axis onto +Z plus
a translation, with no mirroring. Licence and attribution are recorded here as CC-BY requires.
