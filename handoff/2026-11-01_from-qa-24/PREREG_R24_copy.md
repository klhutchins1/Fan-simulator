# QA round 24 pre-registration (grok, QA bot)

Written 2026-11-01 MDT, before any round-24 data. Brief: `handoff/2026-11-01_to-qa-24/CLAUDE_TO_QA.md`.
- **Code:** repo-r24, master 23831da, a fresh clone of `handoff_in/master_23831da.bundle`. Kimball named this bundle; the brief's `fansim.bundle` is not on the box.

**Seen before writing this (context only):**
- the brief;
- the QA_REVIEW tracker rows and repro text for UI-26, UI-27, UI-29, UI-31…UI-38, QA-40, QA-42 and QA-61…QA-64;
- RELEASE_PLAN status lines: R1.10 `ready`, R1.11 `ready`, R3.1 `ready` (not landed), R3.3 `done`;
- the grep hits for the claim string.

**Not independent:** I wrote QA-64 (r23), so I have already seen lt120's 6.85 Pa, +8.1 % (two-mesh mean), +9.5 % (6.2 mm mesh) and the ~34 Pa near-shut-off point.
- Not yet opened this round: the A12x25 and FAN-01 audit numbers, any r24 cockpit render, and any pytest output.
- Because of this, B's rules below are fixed now, and the B verdict is mechanical.

## A. UI and bug pass

**Method.**
- Start the cockpit headless from repo-r24 on :8080 (`scripts/cockpit.py --run <empty dir>`).
- Drive it with Playwright and system Chrome; also use code reading and direct calls of pure functions.
- Run the fast pytest suite once (`-m "not docker and not slow"`) and record the counts.
- Do not click Assess, Sweep, Optimize or CFD.

**Status words (only these):**
- **verified:** the item's own repro no longer shows the problem, by the rule below.
- **still open:** any sub-check still fails.
- **not re-tested:** there is no decisive check, or it could not be run (reason given).

**Rules carried over unchanged from r22 (PREREG_R22, 715891f):** UI-26, UI-27, UI-29, QA-40 and QA-42.
- UI-26: none of the 4 jargon strings appears on the Fan first view in Simple or Expert.
- UI-27: at 1366×768, the viewer's bottom is ≤ 768 px, and the picker and Preview are above the fold.
- UI-29: at 1920×1080, the column is ≥ 25 %, the body text is ≥ 14 px, and 'Start here' is ≥ 14 px and not a grey caption.
- QA-40: the s3 case does not show "No Stock comparison for noise." in Simple.
- QA-42: the Preview weight line names the material, so PLA+ and PETG can be told apart.

**New per-item rules:**
- **QA-61 (Assess time).** Collect every user-visible Assess-duration string in the cockpit source and README (pattern `\d+\s*[–-]\s*\d+\s*min` near "Assess", plus the rendered Actions button).
  - verified: all of them state the same range.
  - still open: two or more different ranges.
- **QA-62.** verified if `pytest tests/test_axial_scripts_oriented.py` passes; still open if it fails with the `validate_lt120.py` message.
- **QA-63.** verified if `pytest tests/test_fuse_memory.py` passes, and `fuse_remaining_estimate_gb(18084)` is less than `fuse_peak_estimate_gb(18084)`.
- **UI-31.** still open if both hold:
  - (a) the Surrogate-guided switch is rendered in Expert, or the state can reach `optimization_argv`;
  - (b) `optimization_argv(surrogate_guided=True, …)` has no `--verify-cfd`, and `run_surrogate_guided` still defaults to `synthetic_label`/`stub_verify`.
  - verified if either (a) or (b) is false on this bundle. Report the bundle only, not `r111-hide-surrogate`.
- **UI-32.** verified if `fan_copy._load_control_images()` returns at least one `opt_*` or `assess_*` key, and a hover over an Optimize switch shows an `<img>`. Otherwise still open.
- **UI-33.** verified if the rendered Expert Optimize panel text says the current Design sliders are not used. The text must contain "slider" or "design", together with one of "not used", "ignore", "from scratch", "new shapes" or "doesn't start". Otherwise still open.
- **UI-34.** verified if any of these is true:
  - the Boost and NN switches are disabled when both GP skip and Surrogate-guided are off;
  - their tooltip names both conditions;
  - `optimization_argv` passes them without either condition.
  - Otherwise still open.
- **UI-35.** Re-run the r-tooltip `range_check.py` against repo-r24.
  - verified if none of the 13 listed models (camber_root/mid/tip, hub_radius, skew_mid/tip, winglet_sweep/lean, tip_notch_depth, thick_mm, le_thick, te_thick, shroud_height) has a generator min/max different from the slider's.
  - still open if any does; report the count.
- **UI-36.** Hover each named control in Expert: Fan model, Hub profile, Application, Print material, Sweep, Allow intake overbuild, Fit hub to the motor, and one action-row button (Preview).
  - verified if all of them show a tooltip; still open otherwise. Report n of 8.
  - Report-only: the source-scan count of Fan-tab settings with no tooltip (was 49).
- **UI-37.** Source scan of the proxy-tab controls.
  - verified if ≥ 90 % have a tooltip; still open otherwise. Report n/N.
- **UI-38.** verified if both hold:
  - the Application or Print material text (label, caption or tooltip) mentions Optimize;
  - picking a design that changes preset, refine or roughness produces a user-visible message, or no longer overwrites them (code reading of `fan_trials.py`).
  - Otherwise still open.

**New bugs:** anything that crashes, contradicts the README or board text, or regresses a verified item gets the next ID (QA-65…, UI-39…), with a repro.

## B. QA-64 wording check (no CFD)

**Claim:** "Fan CFD: validated near free air on three published fans (within 8 %)".

**Data:**
- For A12x25, FAN-01 and lt120: the audit file(s) under `docs/validation/` (and `validation/reference/*`) that state that fan's CFD-vs-published result at its validation point.
- For each fan, record:
  - test pressure P (Pa);
  - the fan's highest published pressure Pmax (shut-off or highest measured point) from its reference data;
  - the headline error E (the number the audit states as its result);
  - any per-mesh or alternative errors;
  - the audit's own PASS/FAIL;
  - the source and licence of the published data.
- Quote the file:line for every number.

**Sub-checks per fan:**
- **(i) published:** the reference data has a cited public source.
- **(ii) validated:** the audit's own verdict is PASS, or the result is within its own pre-registered band.
- **(iii) near free air:** P is 0 Pa, or P/Pmax ≤ 0.10.
- **(iv) within 8 %:** |E| ≤ 8.0 % on the headline number. Report-only: whether any per-mesh number exceeds 8.0 %.

**Verdict (mechanical):**
- **supported as worded:** (i)–(iv) pass for all three fans.
- **needs grok's proposed wording:** the claim fails, but the proposed wording holds for all three. The proposed wording is "within 10 %", with lt120 described as "at its lowest measured load (6.85 Pa)". It holds if:
  - |E| ≤ 10.0 % on the headline and every per-mesh number;
  - 6.85 Pa is lt120's lowest measured load point;
  - (i) and (ii) pass;
  - (iii) passes for A12x25 and FAN-01, or the proposal is extended to them (reported).
- **overstated:** the claim fails and the proposed wording also fails. Report which check fails and a minimal wording that holds.

## C. Is K1 ("loaded probe did not converge") already visible to the user? (proposal only)

**Method:**
- Trace in code where the loaded-probe convergence result is set: evaluate/objectives → saved trial/run json → cockpit.
- Find each place the cockpit turns it into text: Results, flow card, Assess status/caption, tooltip, log.
- Where the builder is a pure function, call it with a synthetic result in which the flag is unconverged, and with one in which it is converged. No CFD.

**Verdict (one of):**
- **VISIBLE (Simple):** a specific unconverged-loaded-probe message reaches the default results/flow card or Assess status in Simple mode.
- **VISIBLE (Expert only):** as above, but only in Expert.
- **PARTIAL:** the flag is only in json/logs/CSV, or only as a generic warning that doesn't name the loaded point. Also PARTIAL if it is shown only for a different trigger.
- **NOT VISIBLE:** the flag is not surfaced anywhere in the UI.

Quote the file:line path from flag to text. Any proposal goes to `docs/qa/patches/` as a patch; no source edits.

## D. Waiting

- The R3.1 export leak check stays waiting, because R3.1 is `ready`, not landed.
- The r21 A claims-audit re-run stays waiting for R1.10 (`ready`).
- Neither is run.
