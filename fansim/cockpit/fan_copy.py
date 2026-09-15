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
    "e_camber": "Mid-span blade curvature (legacy single slider alias). Prefer Camber root/mid/tip.",
    "e_camber_root": "Blade curvature at the hub. More camber turns the air harder (pressure); too much hurts efficiency.",
    "e_camber_mid": "Blade curvature at mid-span. Primary lift/pressure lever mid-blade.",
    "e_camber_tip": "Blade curvature at the tip. Often similar to mid; tip camber affects tip loading.",
    "e_stagger_root": "Blade PITCH angle at the hub. Higher = more axial (flow); lower = blades overlap (pressure).",
    "e_stagger_mid": "Blade PITCH angle at mid-span.",
    "e_stagger_tip": "Blade PITCH angle at the tip.",
    "e_chord_root": "Blade width at the hub. Wider = more area/solidity (pressure) but heavier, less efficient.",
    "e_chord_mid": "Blade width at mid-span.",
    "e_chord_tip": "Blade width at the tip.",
    "e_lean_mid": "Circumferential WRAP at mid-span — wraps blades so they overlap like a real fan.",
    "e_lean_tip": "Circumferential WRAP at the tip (0 = a flat radial paddle).",
    "e_sweep_mid": "Axial rake of the WHOLE mid section (mm, + toward outlet / +Z). Wider range for matching reference STLs.",
    "e_sweep_tip": "Axial rake of the WHOLE tip section (mm, + toward outlet / +Z).",
    "e_le_mid": "Rakes only the LEADING edge at mid-span (mm) — curves the LE line, trailing edge unchanged.",
    "e_le_tip": "Rakes only the LEADING edge at the tip (mm).",
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
    "e_hub_height": "Hub HEIGHT (mm). 0 = auto (just covers the blade roots — shortest). Raise it for a taller hub; it can't go below root coverage.",
    "e_hub_nose": "Nose height (mm) for the cone/dome hub profile. Adds a spinner on the intake side (increases depth — may go over-spec).",
    "e_camber_pos": "Where max camber sits along the chord (0.2 = near LE, 0.6 = aft). Fraction of chord — not mm.",
    "e_thick_root": "Max section thickness at the hub as a FRACTION of chord (0.08 ≈ 8% thick). Used in Tapered mode. Not mm.",
    "e_thick_mid": "Max section thickness at mid-span as a FRACTION of chord. Tapered mode only.",
    "e_thick_tip": "Max section thickness at the tip as a FRACTION of chord. Tapered mode only.",
    "e_thick_mm": "Absolute max section thickness (mm) held constant root→tip. Chord usually grows outward, so t/c drops toward the tip. Typical FDM fan wall ~1.2–2.5 mm.",
    "e_thick_mode": "Uniform wall = same thickness in mm at every station (usual for printed fans). Tapered = independent t/c root→mid→tip. Thickness does not create lift — camber/stagger do.",
    "e_le_thick": "LEADING-EDGE thickness scale (NACA only). 1 = stock; >1 fattens the nose; mid-chord stays near the span thickness. Click Preview after changing.",
    "e_te_thick": "TRAILING-EDGE thickness scale (NACA only). 1 = sharp stock; <1 thins aft; >1 fattens the aft section and adds a short printable TE blunt (experimental under high stagger — use Rounded plate for a true bullnose). Mid-chord stays near span thickness.",
    "e_section_family": "NACA = classic cambered airfoil. Rounded plate = constant thickness with full-round (bullnose) LE and TE — radius = half thickness, like a stadium section.",
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
        "Append new trials into the currently opened run folder instead of making a new "
        "runs/cockpit_opt_* folder. Use when continuing a campaign. Risk: mixes settings if you "
        "changed hose/flags since the last batch."
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
