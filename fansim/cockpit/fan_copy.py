"""Fan Design slider tooltips / Optimize help (single source for Fan tab + widgets)."""

from __future__ import annotations

import base64
from pathlib import Path

_CTRL_IMG_DIR = Path(__file__).resolve().parents[2] / "docs" / "control_images"
CONTROL_IMAGES_URL_PREFIX = "fansim_control_images"


_CONTROL_IMAGE_PATTERNS = (
    "e_*.png",
    "opt_*.png",
    "assess_*.png",
    "p_*.png",
    "mf_*.png",
    "volute_*.png",
    "cror_*.png",
)


def _load_control_images() -> dict:
    """Load hover PNGs. Stems match state models across Fan, Prop, Mixed, Volute, and CROR."""
    uris = {}
    if not _CTRL_IMG_DIR.exists():
        return uris
    for pattern in _CONTROL_IMAGE_PATTERNS:
        for p in sorted(_CTRL_IMG_DIR.glob(pattern)):
            try:
                uris[p.stem] = "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()
            except OSError:
                continue
    return uris


_IMG_URI = _load_control_images()


def control_image_url(model: str) -> str:
    """Return the static HTTP URL for a rendered control PNG, or ``""`` if none exists.

    Serving PNGs statically via ``server.enable_module`` keeps the Trame Vue template
    under ~300 KB instead of inlining ~3 MB of base64 data URIs on every layout flush.
    """
    if model in _IMG_URI:
        return f"/{CONTROL_IMAGES_URL_PREFIX}/{model}.png"
    return ""

CONTROL_DESC = {
    "e_n_blades": "How many blades. More = more airflow & pressure, but louder and less efficient.",
    "e_camber": "Mid-span blade SCOOP (legacy alias). Prefer Camber root/mid/tip.",
    "e_camber_root": "Blade SCOOP at the hub — the face curves from leading edge to trailing edge (technical name: camber). Tip-on, a scooped blade looks U-shaped; zero camber is a flat paddle. This is what matches the white reference scoop. Wrap/sickle only move the planform outline.",
    "e_camber_mid": "Blade SCOOP at mid-span (camber). Raise this with tip camber until the tip-on overlay matches the reference. Works on NACA and Rounded plate.",
    "e_camber_tip": "Blade SCOOP at the tip (camber) — usually the biggest visual match to the reference tip-on U-curve. Stock tip is ~0.12; slider goes to 0.15. Press Preview after changing.",
    "e_stagger_root": "Blade PITCH angle at the hub. Higher = more axial (flow); lower = blades overlap (pressure).",
    "e_stagger_mid": "Blade PITCH angle at mid-span.",
    "e_stagger_tip": "Blade PITCH angle at the tip.",
    "e_chord_root": "Blade WIDTH at the hub — leading edge to trailing edge (planform). Not wall thickness.",
    "e_chord_mid": "Blade WIDTH at mid-span (LE→TE). Not the thin wall through the blade.",
    "e_chord_tip": "Blade WIDTH at the tip (LE→TE). Raise this when the tip flattens (lower stagger) so the planform still covers the reference. Slider goes to 70 mm.",
    "e_lean_mid": "Circumferential WRAP at mid-span — wraps blades so they overlap like a real fan.",
    "e_lean_tip": "Circumferential WRAP at the tip (0 = a flat radial paddle).",
    "e_sweep_mid": "Axial rake of the WHOLE mid section (mm, + toward outlet / +Z). Wider range for matching reference STLs.",
    "e_sweep_tip": "Axial rake of the WHOLE tip section (mm, + toward outlet / +Z).",
    "e_le_mid": "Rakes only the LEADING edge at mid-span (mm) — curves the LE line, trailing edge unchanged.",
    "e_le_tip": "Rakes only the LEADING edge at the tip (mm).",
    "e_le_skew_mid": "Sickle / LE skew at mid-span (mm) — shifts only the leading-edge region sideways in the rotation plane (scimitar). Trailing edge stays put. 0 = radial LE. Not live: press Preview. If Preview times out, the old mesh stays on screen so sickle looks like it did nothing.",
    "e_le_skew_tip": "Sickle / LE skew at the tip (mm). Typical printed PC-fan tips sit around 4–12 mm. Same axis as Optimize → Sickle leading edge. Press Preview — a timed-out build keeps the previous orange mesh.",
    "e_skew_mid": "Skew (mm) — shifts the whole mid section sideways (tangentially). Fine balance/overlap tweak.",
    "e_skew_tip": "Skew (mm) — shifts the whole tip section sideways (tangentially). Wide range for matching reference planforms.",
    "e_smooth_span": "Smooth span curves (PCHIP) — interpolate hub→mid→tip with a shape-preserving cubic so mid wrap/sweep/skew don't put a sharp kink in the blade. Off = linear (historical).",
    "e_tip_round": "Rounds the blade TIP — tapers the chord over the outer span so the leading & trailing edges curve together, instead of a blunt straight tip edge. 0 = square.",
    "e_cylindrical_tip": "Cuts each blade tip to a cylinder at Tip radius so the outer tip face matches the fan-cover circle (constant OD). Off = legacy tips with LE/TE corners that bulge past Tip radius. Tip Round still petals the planform before the cut.",
    "e_tip_start": "Where the tip rounding begins (fraction of span). Lower = a longer, gentler rounded tip; higher = a small rounded cap near the very tip.",
    "e_winglet_span": "Where the WINGLET starts (fraction of span). Below this the blade is straight; beyond it the tip curls.",
    "e_winglet_sweep": "Winglet AXIAL bend (mm) — curls the tip forward/up out of the rotation plane (a real winglet). 0 = off.",
    "e_winglet_lean": "Winglet CIRCUMFERENTIAL curl (deg) — wraps the tip around the axis. 0 = off.",
    "e_shroud_thick": "Radial wall of a ring fused at the blade tips (mm). 0 = open tip. Grows the outer diameter by twice this amount.",
    "e_shroud_height": "How much of the tip chord the ring covers. 1 = full span. Below 1 the hoop starts at the trailing edge. BEM still treats a partial ring as an open tip.",
    "e_hub_radius": "Hub size (mm). Smaller hub = bigger flow annulus (more airflow/efficiency); must fit the model's hub limits.",
    "e_tip_radius": "Blade LENGTH / outer radius (mm). Shrink it to make an oversized blade fit the frame (tip diameter) or trim depth.",
    "e_hub_height": "Hub HEIGHT (mm). 0 = auto (just covers the blade roots — shortest). Raise it for a taller hub; it can't go below root coverage. Needs slack above the root span before Blade on hub can shift.",
    "e_blade_hub_z": "Where the blade roots sit on the hub (mm). 0 = centered. Positive = blades higher toward the intake (+Z), with more hub below — matches the real A12x25 which sits toward the top face. Negative = blades lower / toward the outlet. Clamped so roots stay inside the hub.",
    "e_blade_z": "Moves the plate blade up or down relative to the hub (mm). Positive is up (+Z). Negative is down, toward the hub bottom. 0 leaves the blade where it is. The hub does not move.",
    "e_hub_nose": "Nose height (mm) for the cone/dome hub profile. Adds a spinner on the intake side (increases depth — may go over-spec).",
    "e_hub_profile": "Hub intake cap shape: cylinder (flat face), cone (pointed spinner), or dome (rounded spinner). Set Hub nose > 0 mm for cone/dome.",
    "assess_preset": "Airflow resistance curve (static pressure load in Pa at 50 CFM): Case (8 Pa, open airflow), Heatsink (20 Pa, medium fin restriction), Radiator (35 Pa, high back-pressure).",
    "assess_material": "3D-print filament used for weight, blade-root spin stress, and print-sheet recommendations (PETG default; PLA+ is stiffer).",
    "fan_model": "Donor fan hub & frame envelope (motor shaft, cup diameter, frame bore, depth, RPM). Sets fit checks, Assess RPM/duct, and STL motor-cup subtraction.",
    "sweep_param": "Parameter to sweep across evenly spaced values from the current Design sliders. Each step runs a full CFD Assess (~30–40 min per step).",
    "sweep_steps": "Number of evenly spaced points along the Sweep range (2–12). Wall-clock time scales linearly with steps.",
    "seed_duty_cfm": "Target volumetric airflow (CFM) used to estimate initial stagger and camber magnitudes from Euler velocity triangles.",
    "seed_duty_pa": "Target static pressure rise (Pa) at the duty point for Seed from duty.",
    "seed_duty_rpm": "Shaft speed (RPM) at the duty point for Seed from duty.",
    "seed_duty_vortex": "Spanwise swirl distribution for Seed from duty: Free vortex (r·Cu = const, uniform axial flow) or Forced vortex (Cu ∝ r, higher tip loading).",
    "export_fit_hub": "Clamp hub radius and subtract the selected donor motor's rotor cup / shaft cavity on STL export so the hub mounts on the motor.",
    "export_fit_frame": "Clamp outer tip radius and axial depth to the selected donor frame bore and thickness on STL export.",
    "export_also_mirror": "Export both standard rotation (CW) and a mirror-image impeller (CCW) STL in one click.",
    "preview_motor_cup": "Show the subtracted donor motor cup inside the 3D Preview mesh. Slower Preview; off by default while iterating on blades.",
    "intake_overbuild": "Allow blades/hub to extend past the intake face (+Z) beyond the nominal frame depth. Flagged over-spec.",
    "intake_overbuild_mm": "Extra axial intake depth allowed when intake overbuild is enabled (mm).",
    "e_camber_pos": "Where max camber sits along the chord (0.2 = near LE, 0.6 = aft). Fraction of chord — not mm.",
    "e_thick_root": "Wall t/c at the hub (fraction of chord). Tapered mode only. Through-blade thickness, not LE→TE width.",
    "e_thick_mid": "Wall t/c at mid-span. Tapered mode only.",
    "e_thick_tip": "Wall t/c at the tip. Tapered mode only.",
    "e_thick_mm": "Wall thickness through the blade (mm), held constant root→tip. This is the thin dimension — not chord/width. Typical printed fan ~1.8–2.8 mm. Use Rounded plate; set LE/TE roundness ~0.2 (full LE bullnose fights uniform wall).",
    "e_thick_mode": "Uniform wall = same mm through the blade at every station. Tapered = independent t/c. Does not set LE→TE width — that is Chord.",
    "e_le_thick": "LEADING-EDGE control. NACA: thickness scale (1 = stock; >1 fattens the nose). "
        "Plate: LE roundness 0–1 (1 = full bullnose bead — fights uniform wall; ~0.2 = sharp). "
        "If left at 1 with plate, LE follows TE roundness. Click Preview after changing.",
    "e_te_thick": "TRAILING-EDGE control. NACA: thickness scale (1 = stock; <1 thins aft; >1 fattens). "
        "Plate: TE roundness 0–1 (1 = full bullnose, ~0.2 = sharp printable TE). "
        "Roundness does not close the wall. Use Back edge for that.",
    "e_le_face_root": "How thick the front edge stays at the hub, on a rounded plate. 1 = full wall. 0 = sharp. The middle of the blade stays the full wall.",
    "e_le_face_mid": "How thick the front edge stays at mid-span, on a rounded plate. 1 = full wall. 0 = sharp.",
    "e_le_face_tip": "How thick the front edge stays at the tip, on a rounded plate. 1 = full wall. 0 = sharp.",
    "e_te_face_root": "How thick the back edge stays at the hub, on a rounded plate. 1 = full wall. 0 = sharp.",
    "e_te_face_mid": "How thick the back edge stays at mid-span, on a rounded plate. 1 = full wall. 0 = sharp.",
    "e_te_face_tip": "How thick the back edge stays at the tip, on a rounded plate. 1 = full wall. 0 = sharp.",
    "e_section_family": "NACA = cambered airfoil with sharp LE/TE. Rounded plate = constant wall, tunable LE/TE roundness + camber (bows the blade face — the slight tip→hub curve). Wrap/lean still set the spanwise vortex planform.",
    "e_tip_notched": "Three boxy / skewed-rectangle bites cut into the outer trailing edge (close-ref A12x25 tip TE steps). Not spanwise owl serrations and not LE tubercles. Slows Preview — wait for it to finish after changing Sickle/Wrap.",
    "e_tip_notch_depth": "How deep each tip TE notch cuts toward mid-chord (mm). Stock ≈ 1.5 mm. Deeper = more staircase on the TE.",
    "e_spacing": "Uneven-but-balanced blade spacing to spread the blade-pass tone. 0 = evenly spaced.",
    "e_tub_amp": "Tubercle amplitude — bumpy leading edge (whale-fin), delays stall.",
    "e_tub_waves": "Number of tubercle bumps along the span.",
    "e_ser_amp": "Serration depth — sawtooth trailing edge (owl-wing), cuts edge noise.",
    "e_ser_waves": "Number of serration teeth.",
    "e_dim_amp": "Dimple depth — golf-ball-style surface texture.",
    "e_dim_rows": "Dimples along the chord.",
    "e_dim_cols": "Dimples along the span.",
    # Library → Leeway (Expert): how much the design may miss the motor / frame / weight / voltage.
    "lee_depth": (
        "Extra axial depth allowed past the frame (mm). 0 = must fit the frame depth. "
        "Raise only if your case has spare room behind the fan."
    ),
    "lee_overvolt": (
        "How many volts above nameplate the stress check may assume. 0 = nameplate only. "
        "Use a small value if the fan sometimes runs on a higher rail."
    ),
    "lee_tip": (
        "Extra tip radius allowed past the frame bore (mm). 0 = tip must clear the cover. "
        "Raise only for a known larger opening."
    ),
    "lee_weight": (
        "Extra mass allowed above the material limit (g). 0 = stay under the print-weight gate. "
        "Raise only if you accept a heavier part."
    ),
}

# Simple-mode hover text (#65). Keys that Simple shows on Design; Expert keeps CONTROL_DESC.
# Avoid: camber, stagger, NACA, t/c, PCHIP, chord (as jargon), LE/TE as bare acronyms.
CONTROL_DESC_SIMPLE = {
    "e_n_blades": "How many blades. More blades usually move more air, but can be louder.",
    "e_camber_root": "How scooped the blade face is near the hub. Zero is a flat paddle. Press Preview after changing.",
    "e_camber_mid": "How scooped the blade face is in the middle. Raise with tip scoop to match the white reference.",
    "e_camber_tip": "How scooped the blade face is at the tip — often the biggest match to the reference curve.",
    "e_camber_pos": "Where the deepest part of the scoop sits along the blade (near the front edge vs farther back).",
    "e_stagger_root": "Blade angle at the hub. Higher = more open for airflow; lower = blades overlap more for pressure.",
    "e_stagger_mid": "Blade angle in the middle of the span.",
    "e_stagger_tip": "Blade angle at the tip.",
    "e_chord_root": "How wide the blade is at the hub (front edge to back edge). Not how thick the plastic wall is.",
    "e_chord_mid": "How wide the blade is in the middle. Not wall thickness.",
    "e_chord_tip": "How wide the blade is at the tip. Raise this if the tip looks too skinny vs the reference.",
    "e_section_family": "Rounded plate = even wall, good for printed PC-fan blades. The other option is a knife-edge airfoil for Expert use.",
    "e_thick_mode": "Same wall thickness everywhere, or taper it from hub to tip.",
    "e_thick_mm": "How thick the plastic wall is through the blade (the thin dimension). Typical printed fans are about 2 mm.",
    "e_thick_root": "Wall thickness at the hub as a fraction of blade width.",
    "e_thick_mid": "Wall thickness at mid-span as a fraction of blade width.",
    "e_thick_tip": "Wall thickness at the tip as a fraction of blade width.",
    "e_le_thick": "How round or sharp the front edge is. Press Preview after changing.",
    "e_te_thick": "How round or sharp the back edge is. Press Preview after changing.",
    "e_le_face_root": "Front-edge thickness at the hub on a rounded plate. 1 = full wall, 0 = sharp.",
    "e_le_face_mid": "Front-edge thickness at mid-span. 1 = full wall, 0 = sharp.",
    "e_le_face_tip": "Front-edge thickness at the tip. 1 = full wall, 0 = sharp.",
    "e_te_face_root": "Back-edge thickness at the hub. 1 = full wall, 0 = sharp.",
    "e_te_face_mid": "Back-edge thickness at mid-span. 1 = full wall, 0 = sharp.",
    "e_te_face_tip": "Back-edge thickness at the tip. 1 = full wall, 0 = sharp.",
    "e_hub_radius": "Hub size. Smaller hub leaves more room for airflow; must still fit your fan model.",
    "e_tip_radius": "How far the blades reach (outer radius). Shrink to fit a smaller frame.",
    "e_hub_height": "Hub height. 0 = just tall enough to cover the blade roots.",
    "e_blade_hub_z": "Where the blades sit on the hub — up toward the intake or down toward the outlet.",
    "e_blade_z": "Moves a plate blade up or down on the hub. Positive is up. The hub stays put.",
    "e_hub_nose": "Adds a nose cone on the intake side in mm (makes the fan taller).",
    "e_hub_profile": "Shape of the center hub cap: flat cylinder, pointed cone, or rounded dome (uses Hub nose height).",
    "assess_preset": "How much airflow resistance (static pressure) the fan pushes against: Case (8 Pa, open), Heatsink (20 Pa, medium), or Radiator (35 Pa, tight fins).",
    "assess_material": "Plastic filament you plan to print with (sets weight, strength check, and print settings).",
    "fan_model": "Pick the donor fan frame and motor hub you are designing replacement blades for. Sets fit limits, fan speed, and the motor cutout for STL export.",
    "export_fit_hub": "Size the center hub and carve the motor socket so the printed blades fit your donor fan's motor.",
    "export_fit_frame": "Trim outer blade reach and height if needed so the exported STL clears your fan's frame.",
}

# Plain-language help for Fan Optimize Advanced search (and Assess flags Optimize reuses).
# Keys match state model names. Hover tooltips only — flag behavior is unchanged.
OPT_SEARCH_HELP = {
    "opt_trials": (
        "How many CFD designs to try. Each trial is a full mesh+solve (often tens of minutes). "
        "Start small (8). More trials ≈ better Pareto coverage, linear wall-clock cost."
    ),
    "opt_resume": (
        "Add new trials to the most recent runs/cockpit_opt_* run instead of starting a new one. "
        "The optimizer only learns from trials in the same run, so separate small runs each "
        "restart with random warm-up designs; continuing lets the trials add up. Risk: mixes "
        "settings if you changed hose/flags since the last batch. With no earlier Optimize run "
        "it continues the opened run."
    ),
    "opt_shroud": (
        "Also search designs with a plastic tip ring fused at the blade tips (kills tip leak). "
        "When to use: ducted / sealed-tip ideas. Cost: same CFD budget, slightly different geometry "
        "stamp. Risk: ring grows OD — tip radius is capped so it still fits the frame."
    ),
    "opt_stator": (
        "Replace the usual four-bar exit frame with a row of fixed guide vanes (straightens swirl). "
        "When to use: chasing pressure / efficiency after the rotor. Cost: same CFD count. "
        "Risk: can cut free CFM; mutually exclusive with stator+frame stack."
    ),
    "opt_stator_stack": (
        "Guide vanes first, then the four-bar frame a few mm downstream. When to use: mountable "
        "hardware that still needs OGVs. Cost: same CFD count. Risk: more blockage than stator alone; "
        "turns off plain stator."
    ),
    "opt_sickle": (
        "Forward-sweeps the leading edge in the rotation plane (scimitar / sickle shape). "
        "When to use: exploring tip loading / tone ideas. Cost: same CFD count. "
        "Risk: another geometry family — compare fairly against un-sickled runs."
    ),
    "opt_stepped": (
        "Adds a concentric step on the circular inlet casing (not on the blade). "
        "When to use: inlet-conditioning experiments. Cost: same CFD count. Risk: casing-only change."
    ),
    "opt_notched": (
        "Cuts three small bites into the trailing edge near the tip. When to use: tip-tone "
        "experiments. Cost: same CFD count. Risk: fixed recipe (not a free search variable); "
        "do not expect proven dB cuts."
    ),
    "opt_bem": (
        "RANKING-ONLY blade-element screen: skip CFD if predicted hose CFM is below ~32. "
        "Ranking only; coarse; can't separate close designs. "
        "When to use: large campaigns to burn fewer CFD hours. Never quote BEM beside CFD as equal."
    ),
    "opt_gp": (
        "Catalog Gaussian-process guess of free-delivery CFM: skip CFD when mean+uncertainty "
        "is below ~40 CFM. When to use: with a populated catalog. Cost: faster after a few scored "
        "points. Risk: weak early on; uncertain predictions still run CFD."
    ),
    "opt_gp_boost": (
        "With Catalog GP skip on: use a boosted-tree mean + GP uncertainty. When to use: richer "
        "catalog. Cost: tiny CPU overhead. Risk: needs scikit-learn or falls back to GP-only."
    ),
    "opt_gp_nn": (
        "With Catalog GP skip on: use a small neural net for the CFM mean + GP uncertainty "
        "(wins over Boost if both on). When to use: experimental surrogate. Cost: tiny. "
        "Risk: needs PyTorch or falls back to GP-only."
    ),
    "opt_search_rpm": (
        "Treat RPM as a searchable dial inside the fan’s PWM band (not fixed nameplate speed). "
        "When to use: PWM / thermal fans. Cost: wider search → more trials to cover well. "
        "Risk: compares apples-to-oranges vs fixed-RPM campaigns."
    ),
    "opt_rpm_min": "Lowest RPM Optuna may pick when Search RPM is on (PWM band floor).",
    "opt_rpm_max": "Highest RPM Optuna may pick when Search RPM is on (PWM band ceiling).",
    "assess_refine_op": (
        "Runs a third CFD at the real hose operating pressure instead of estimating load CFM "
        "from two points. Used by Assess and by Optimize. When to use: more honest load CFM. "
        "Cost: ~50% longer per design. Risk: still RANS, not a lab measurement."
    ),
    "assess_wall_ks": (
        "Models FDM print roughness (~0.1 mm sand grain) on impeller + frame/stator; casing "
        "stays smooth. Used by Assess and Optimize. When to use: an assumed 5 % print loss, not yet measured. "
        "Cost: same solve time. Risk: slightly lower predicted CFM vs smooth walls."
    ),
}
