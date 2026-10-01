"""Fan Design slider tooltips / Optimize help (single source for Fan tab + widgets)."""

from __future__ import annotations

import base64
from pathlib import Path

_CTRL_IMG_DIR = Path(__file__).resolve().parents[2] / "docs" / "control_images"


def _load_control_images() -> dict:
    uris = {}
    if _CTRL_IMG_DIR.exists():
        for p in _CTRL_IMG_DIR.glob("e_*.png"):
            try:
                uris[p.stem] = "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()
            except Exception:  # noqa: BLE001
                pass
    return uris


_IMG_URI = _load_control_images()

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
    "e_hub_nose": "Nose height (mm) for the cone/dome hub profile. Adds a spinner on the intake side (increases depth — may go over-spec).",
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
        "Plate: TE roundness 0–1 (1 = full bullnose, ~0.2 = sharp printable TE).",
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
        "Not absolute CFM — ignores thickness/lean/wrap/LE-TE/plate; typically under-ranks CFD (~0.6×). "
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
    "opt_surrogate_guided": (
        "Pro loop: space-filling DoE → fit GP/boost/NN → NSGA-II on the surrogate → "
        "verify top-k (stub by default; CFD when Docker verify is on) → refit. "
        "Uses ensemble/GP spread as the acquisition signal. When to use: explore many "
        "designs cheaply before spending CFD. Cost: CPU for DoE+NSGA; CFD only on top-k "
        "if verify is enabled. Risk: surrogate can mis-rank early; verify is the honesty gate."
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
        "stays smooth. Used by Assess and Optimize. When to use: printed-part honesty. "
        "Cost: same solve time. Risk: slightly lower predicted CFM vs smooth walls."
    ),
}
