"""Map an Optuna trial to a BladeParams design vector (~10 dimensions).

Kept compact so a search is tractable: blade count, per-station stagger and chord, mid/tip
sweep, and global camber. Thickness is fixed to a printable profile unless extended DOFs are
enabled; optional bio-inspired features (tubercles, serrations, dimples) are sampled via
``suggest_features``.
"""

from __future__ import annotations

import dataclasses
import math
from pathlib import Path
from typing import Any

import numpy as np

from fansim.cfd.domain import OPTIMIZER_TIP_GAP_MM
from fansim.geometry.blade import (
    SHROUD_DEFAULT_MM,
    BladeParams,
    RadialStation,
    normalize_shroud_thick_mm,
    open_tip_rmax_mm,
    shroud_is_full,
)
from fansim.geometry.features import Features
from fansim.optimize.objective_keys import OBJECTIVE_NAMES

# Fixed printable thickness profile (fraction of chord), root -> tip. Chosen with the chord
# lower bound so the thinnest section (tip) stays above the ~0.8 mm min printable wall.
THICKNESS = (0.10, 0.08, 0.06)
CAMBER_POS = 0.4
MIN_CHORD = 14.0
MAX_CHORD = 40.0  # wide enough to reach realistic high-solidity (overlapping) blades


def suggest_features(trial) -> Features:
    """Sample a bio-inspired feature layer. Zero waves/amplitude => that feature is off,
    so the search can discover a smooth blade is best if features do not help."""
    return Features(
        tubercle_amp=trial.suggest_float("tubercle_amp", 0.0, 0.10),
        tubercle_waves=trial.suggest_int("tubercle_waves", 0, 8),
        serration_amp=trial.suggest_float("serration_amp", 0.0, 0.06),
        serration_waves=trial.suggest_int("serration_waves", 0, 12),
        dimple_amp=trial.suggest_float("dimple_amp", 0.0, 0.35),
        dimple_rows=trial.suggest_int("dimple_rows", 0, 6),
        dimple_cols=trial.suggest_int("dimple_cols", 0, 6),
    )


# Rules-guided bounds (from docs/design-rules.md). Each key: (lo, hi) for the guided search.
# Biases toward the data-driven recipe: high mid-stagger (flow+ eff+ noise-), wide tip chord
# (eff+ tone-), low camber (flow+ eff+), fewer blades (eff+ noise-), low mid-chord & mid-lean
# (both cut the noise-driving mid-solidity and the tone). Same param NAMES as the open search, so
# blade_from_flat / design-rule tooling are unchanged.
GUIDED = {
    "n_blades": (5, 11),         # was 5–8 (free-air); hose CFM needs OPEN's 5–11
    # R1.3 P0 (prereg 2026-11-25-r13-guided-wrap-bounds): floors low enough for Stock v3
    # under wrap (r14 C / r17 C). Stagger tip unchanged.
    "stagger_root": (19.5, 48.0),
    "stagger_mid": (27.2, 48.0),  # HIGH mid-stagger — the win-win-win lever
    "stagger_tip": (18.0, 38.0),
    "chord_root": (14.0, 34.0),
    "chord_mid": (14.0, 32.0),    # cap mid chord -> lower mid-solidity (noise driver)
    "chord_tip": (26.0, 40.0),    # WIDE tip chord — efficiency + quieter tone
    "sweep_mid": (0.0, 8.0),
    "sweep_tip": (0.0, 12.0),
    "lean_mid": (0.0, 12.0),      # low mid-lean -> lower blade-pass tone
    "lean_tip": (0.0, 45.0),
    "max_camber": (0.015, 0.06),  # was 0–0.06; P0 floor keeps Stock (0.0478) inside
}
OPEN = {
    # #127 (prereg 2026-11-26-search-space-bounds-127): OPEN is a strict superset of GUIDED.
    "n_blades": (5, 11), "stagger_root": (19.5, 48.0), "stagger_mid": (18.0, 48.0),
    "stagger_tip": (16.0, 38.0), "chord_root": (MIN_CHORD, MAX_CHORD),
    "chord_mid": (MIN_CHORD, MAX_CHORD), "chord_tip": (MIN_CHORD, MAX_CHORD),
    "sweep_mid": (-3.0, 8.0), "sweep_tip": (0.0, 12.0), "lean_mid": (0.0, 25.0),
    "lean_tip": (0.0, 45.0), "max_camber": (0.0, 0.06),
}
# Load-spreading recipe (guided + per-blade-loading cap). Keeps the flow/eff rules (high-ish
# mid-stagger, wide tip chord) but allows MORE blades and wider mid-chord so the search
# can meet a solidity floor -> lower per-blade loading -> quieter broadband at high flow. Pair with
# evaluate_candidate(min_sol_mid=..., min_sol_tip=...). Camber matches OPEN (hose scoring).
GUIDED_LC = {
    "n_blades": (7, 11),          # more blades: spread the load, cut per-blade loading
    "stagger_root": (22.0, 44.0),
    "stagger_mid": (28.0, 44.0),  # still high, but reachable with a solidity floor
    "stagger_tip": (18.0, 36.0),
    "chord_root": (18.0, 36.0),
    "chord_mid": (22.0, 40.0),    # wider mid chord keeps solidity up under high stagger
    "chord_tip": (26.0, 40.0),    # wide tip chord: efficiency + quieter tone
    "sweep_mid": (0.0, 8.0),
    "sweep_tip": (0.0, 12.0),
    "lean_mid": (0.0, 12.0),
    "lean_tip": (0.0, 45.0),
    "max_camber": (0.0, 0.06),    # was 0–0.02 (free-air); hose scoring uses OPEN's 0–0.06
}
BOUNDS = {"open": OPEN, "guided": GUIDED, "guided_lc": GUIDED_LC}

# Extra geometry DOFs promoted from the cockpit into the search when with_extended=True (space-
# independent). hub_radius fits the a12x25/delta hub-diameter limits; thin tips are still printability-
# gated. Off by default so existing runs stay comparable.
EXTENDED = {
    "hub_radius": (17.0, 28.0),
    # Default cap matches a12x25 frame (55.0 - 0.5 mm clearance, #127); explicit frame_half_mm /
    # max_tip_radius overrides this range for other frame sizes.
    "tip_radius": (48.0, 54.5),   # blade length (outer radius); tip dia = 2x, must fit the frame

    # Thickness biased THIN (down toward the printability floor): thicker blades are never
    # aerodynamically better and only add depth/weight. Lower bounds stay >= 0.80 mm at MIN_CHORD
    # (0.06 * 14.0 = 0.84 mm) for root and mid (#127).
    "thickness_root": (0.06, 0.11),
    "thickness_mid": (0.06, 0.09),
    "thickness_tip": (0.04, 0.07),
    "camber_pos": (0.30, 0.50),
}

# Winglet DOFs (opt-in via with_winglet). CFD study found a MILD winglet (~sweep 5 mm / lean 8 deg) buys
# ~4% airflow at flat efficiency; overdoing it is worse. Bounds cover the sweet spot + a little past it.
WINGLET = {"winglet_sweep": (0.0, 10.0), "winglet_lean": (0.0, 18.0)}


def _apply_spacing(bp: BladeParams, spread: float | None, seed: int | None) -> None:
    """Deterministically set a balanced uneven blade spacing on ``bp`` from (spread, seed)."""
    from fansim.geometry.blade import set_uneven_spacing

    sp = 0.0 if spread is None else float(spread)
    if sp <= 0.0:
        set_uneven_spacing(bp, spread=sp)
        return
    s = 0 if seed is None else int(seed)
    if s < 0:
        raise ValueError(f"spacing_seed must be >= 0, got {s}")
    set_uneven_spacing(bp, spread=sp, rng=np.random.default_rng(s))


def suggest_params(trial, with_features: bool = False, space: str = "open",
                   with_spacing: bool = False, with_extended: bool = False,
                   hub_radius_range: tuple[float, float] | None = None,
                   with_winglet: bool = False, max_tip_radius: float | None = None,
                   frame_half_mm: float | None = None,
                   with_shroud: bool = False) -> BladeParams:
    """Sample a BladeParams from an Optuna trial's search space.

    space: 'open' (full), 'guided' (data-driven recipe, docs/design-rules.md), or 'guided_lc'
    (guided + load-spreading bounds for a per-blade-loading cap). with_spacing adds an uneven
    blade-spacing DOF (spread + seed). with_extended adds hub radius, per-station thickness and
    camber position as search DOFs (else they stay at the fixed defaults). hub_radius_range forces
    the hub radius to be SAMPLED from that range (used by --mountable to keep the hub big enough to
    house the motor) — it overrides the extended hub bound and applies even without --extended.
    frame_half_mm caps tip_radius so the built envelope (ring included) leaves 0.5 mm to the frame."""
    if space not in BOUNDS:
        raise KeyError(f"unknown search space {space!r}; known: {sorted(BOUNDS)}")
    b = BOUNDS[space]
    if frame_half_mm is not None and float(frame_half_mm) <= 0.0:
        raise ValueError(f"frame_half_mm must be > 0, got {frame_half_mm}")
    if max_tip_radius is not None and float(max_tip_radius) <= 0.0:
        raise ValueError(f"max_tip_radius must be > 0, got {max_tip_radius}")
    n_blades = trial.suggest_int("n_blades", *b["n_blades"])

    # Realistic (low) stagger: wide high-solidity blades need low stagger to fit the 25 mm
    # depth and to make circumferential (pressure-generating) blades rather than axial paddles.
    stg_root = trial.suggest_float("stagger_root", *b["stagger_root"])
    stg_mid = trial.suggest_float("stagger_mid", *b["stagger_mid"])
    stg_tip = trial.suggest_float("stagger_tip", *b["stagger_tip"])

    ch_root = trial.suggest_float("chord_root", *b["chord_root"])
    ch_mid = trial.suggest_float("chord_mid", *b["chord_mid"])
    ch_tip = trial.suggest_float("chord_tip", *b["chord_tip"])

    sweep_mid = trial.suggest_float("sweep_mid", *b["sweep_mid"])
    sweep_tip = trial.suggest_float("sweep_tip", *b["sweep_tip"])

    # Circumferential wrap (lean) — the DOF that makes blades sweep/overlap like a real fan.
    lean_mid = trial.suggest_float("lean_mid", *b["lean_mid"])
    lean_tip = trial.suggest_float("lean_tip", *b["lean_tip"])

    camber = trial.suggest_float("max_camber", *b["max_camber"])

    # Extended geometry DOFs (opt-in): hub radius, per-station thickness, camber position.
    if with_extended:
        e = EXTENDED
        th_r = trial.suggest_float("thickness_root", *e["thickness_root"])
        th_m = trial.suggest_float("thickness_mid", *e["thickness_mid"])
        th_t = trial.suggest_float("thickness_tip", *e["thickness_tip"])
        cpos = trial.suggest_float("camber_pos", *e["camber_pos"])
    else:
        th_r, th_m, th_t, cpos = THICKNESS[0], THICKNESS[1], THICKNESS[2], CAMBER_POS
    hub = None
    hub_range = hub_radius_range or (EXTENDED["hub_radius"] if with_extended else None)
    if hub_range is not None:  # --mountable forces a hub big enough to house the motor
        hub_lo, hub_hi = float(hub_range[0]), float(hub_range[1])
        if hub_lo <= 0.0 or hub_lo > hub_hi:
            raise ValueError(f"invalid hub_radius_range {(hub_lo, hub_hi)}")
        hub = trial.suggest_float("hub_radius", hub_lo, hub_hi)

    stations = [
        RadialStation(0.0, ch_root, stg_root, th_r, camber, cpos, 0.0, 0.0, 0.0),
        RadialStation(0.5, ch_mid, stg_mid, th_m, camber, cpos, sweep_mid, 0.0, lean_mid),
        RadialStation(1.0, ch_tip, stg_tip, th_t, camber, cpos, sweep_tip, 0.0, lean_tip),
    ]
    hub_r = float(hub) if hub is not None else BladeParams.hub_radius

    # tip_radius: frame-aware cap from the real section-point bulge when frame_half_mm is set.
    # Else max_tip_radius / extended range / BladeParams default.
    if frame_half_mm is not None or max_tip_radius is not None:
        if frame_half_mm is not None:
            shroud = SHROUD_DEFAULT_MM if with_shroud else 0.0
            cap = tip_radius_cap_mm(stations, hub_r, frame_half_mm, shroud, n_blades)
            if max_tip_radius is not None:
                cap = min(cap, float(max_tip_radius))
        else:
            cap = float(max_tip_radius)  # type: ignore[arg-type]
        if cap <= hub_r:
            raise ValueError(
                f"tip_radius cap ({cap:.2f} mm) must exceed hub_radius ({hub_r:.2f} mm)"
            )
        lo = max(min(TIP_CAP_SEARCH_LO_MM, cap - 1.0), hub_r + 1e-3)
        lo = min(lo, cap)
        tip = trial.suggest_float("tip_radius", lo, cap)
    elif with_extended:
        tip = trial.suggest_float("tip_radius", *EXTENDED["tip_radius"])
    else:
        tip = None

    features = suggest_features(trial) if with_features else Features()
    kw = {}
    if hub is not None:
        kw["hub_radius"] = hub
    if tip is not None:
        kw["tip_radius"] = tip
    bp = BladeParams(n_blades=n_blades, stations=stations, features=features, **kw)
    # Durable record of what the sampled chords mean, for replaying this trial later
    # (``trial_attrs.chord_basis_for_trial``; trials without it predate the switch).
    bp.section_wrap = "cylinder"  # new axial designs: sections on their cylinders (roadmap 27.4)
    if hasattr(trial, "set_user_attr"):
        trial.set_user_attr("chord_basis", bp.chord_basis)
        trial.set_user_attr("section_wrap", bp.section_wrap)
    if with_shroud:                       # tip ring; search its TE-anchored height (recovery: 7.5)
        bp.shroud_thick_mm = SHROUD_DEFAULT_MM
        bp.shroud_height_frac = trial.suggest_float("shroud_height_frac", 0.30, 1.0)
        if hasattr(trial, "set_user_attr"):
            trial.set_user_attr("shroud_thick_mm", float(bp.shroud_thick_mm))
    if with_winglet:                      # curl the tip; §7.5: no winglet under a FULL ring
        wl_sweep = trial.suggest_float("winglet_sweep", *WINGLET["winglet_sweep"])
        wl_lean = trial.suggest_float("winglet_lean", *WINGLET["winglet_lean"])
        if not shroud_is_full(bp):
            from fansim.geometry.blade import apply_winglet
            apply_winglet(bp, sweep_add=wl_sweep, lean_add=wl_lean)
    if with_spacing:
        _apply_spacing(bp, trial.suggest_float("spacing_spread", 0.0, 0.6),
                       trial.suggest_int("spacing_seed", 0, 99999))
    return bp


# Full-recipe carriage (roadmap §23.1). The flat dict has root/mid/tip slots only, so a recipe with
# more stations (Stock: 7) was silently cut to 3. blade_to_flat now also stores the full station list
# plus the slot values it derived from it; blade_from_flat rebuilds every station and applies any
# slot EDIT as a delta interpolated (piecewise-linear in r_frac) between the root/mid/tip stations.
# Unedited -> the exact recipe; edited -> the recipe shifted the same way a 3-station edit would be.
FLAT_STATIONS = "stations"
FLAT_STATION_SLOTS = "station_slots"
FLAT_STATION_SLOT_R = "station_slot_r"
STATION_PAYLOAD_KEYS = (FLAT_STATIONS, FLAT_STATION_SLOTS, FLAT_STATION_SLOT_R)
_STATION_FIELDS = ("r_frac", "chord", "stagger_deg", "thickness", "max_camber", "camber_pos",
                   "sweep", "skew", "lean_deg", "le_sweep", "le_skew", "te_face", "le_face")
_STATION_DEFAULTS: dict[str, float] = {
    f.name: float(f.default)
    for f in dataclasses.fields(RadialStation)
    if f.default is not dataclasses.MISSING
}
# station field -> flat keys at (root, mid, tip); None = no slot (fixed at the recipe value)
_SLOT_KEYS = (
    ("chord", ("chord_root", "chord_mid", "chord_tip")),
    ("stagger_deg", ("stagger_root", "stagger_mid", "stagger_tip")),
    ("thickness", ("thickness_root", "thickness_mid", "thickness_tip")),
    ("max_camber", ("camber_root", "camber_mid", "camber_tip")),
    ("sweep", (None, "sweep_mid", "sweep_tip")),
    ("skew", (None, "skew_mid", "skew_tip")),
    ("lean_deg", (None, "lean_mid", "lean_tip")),
    ("le_sweep", ("le_sweep_root", "le_sweep_mid", "le_sweep_tip")),
    ("le_skew", ("le_skew_root", "le_skew_mid", "le_skew_tip")),
    ("te_face", ("te_face_root", "te_face_mid", "te_face_tip")),
    ("le_face", ("le_face_root", "le_face_mid", "le_face_tip")),
)


def _opt_float(p: dict, key: str, default: float) -> float:
    """Flat value, keeping a real 0. A missing key or None uses ``default``."""
    if key not in p or p[key] is None:
        return float(default)
    return float(p[key])


def _attr_float(obj: Any, name: str, default: float) -> float:
    """Attribute value as float, keeping a real 0. Missing or None uses ``default``."""
    val = getattr(obj, name, None)
    return float(default) if val is None else float(val)


def _slot_value(p: dict, key: str, original: float) -> float:
    """Flat value for a slot key with blade_from_flat's fallbacks (camber_* -> max_camber)."""
    if key in p and p[key] is not None:
        return float(p[key])
    if key.startswith("camber_") and p.get("max_camber") is not None:
        return float(p["max_camber"])
    return float(original)


def _stations_from_payload(p: dict) -> list[RadialStation]:
    """Every recipe station, with slot edits applied as interpolated deltas."""
    raw_stations = p[FLAT_STATIONS]
    slots = p.get(FLAT_STATION_SLOTS) or {}
    r_nodes_raw = p.get(FLAT_STATION_SLOT_R)
    r_nodes = [float(r) for r in r_nodes_raw] if r_nodes_raw is not None else []
    if slots and (len(r_nodes) != 3 or r_nodes[0] > r_nodes[1] or r_nodes[1] > r_nodes[2]):
        raise ValueError(
            f"{FLAT_STATION_SLOT_R} must be 3 non-decreasing r_frac values, got {r_nodes!r}"
        )
    out = []
    for raw in raw_stations:
        st = {k: float(raw[k]) for k in _STATION_FIELDS if k in raw and raw[k] is not None}
        r = st["r_frac"]
        if slots:
            for field_name, keys in _SLOT_KEYS:
                deltas = [
                    0.0 if k is None or k not in slots else _slot_value(p, k, slots[k]) - float(slots[k])
                    for k in keys
                ]
                if any(deltas):
                    base = st.get(field_name, _STATION_DEFAULTS.get(field_name, 0.0))
                    st[field_name] = base + float(np.interp(r, r_nodes, deltas))
            if "camber_pos" in slots:
                st["camber_pos"] = st.get("camber_pos", CAMBER_POS) + (
                    _slot_value(p, "camber_pos", slots["camber_pos"]) - float(slots["camber_pos"])
                )
        out.append(RadialStation(**st))
    return out


def blade_from_flat(p: dict, features: Features | None = None) -> BladeParams:
    """Rebuild a BladeParams from a flat param dict (inverse of suggest_params).

    Thickness (root/mid/tip), camber position and hub radius fall back to the fixed defaults when
    absent, so older param dicts (and the optimizer, which fixes them) still work; the cockpit can
    now override them.

    Camber: prefer ``camber_root`` / ``camber_mid`` / ``camber_tip``; else fall back to the single
    ``max_camber`` used by the optimizer (all three stations get that value).
    """
    if p.get(FLAT_STATIONS):                            # full recipe carried (§23.1)
        stations = _stations_from_payload(p)
    else:
        cpos = _opt_float(p, "camber_pos", CAMBER_POS)
        th_r = _opt_float(p, "thickness_root", THICKNESS[0])
        th_m = _opt_float(p, "thickness_mid", THICKNESS[1])
        th_t = _opt_float(p, "thickness_tip", THICKNESS[2])
        cam_fallback = _opt_float(p, "max_camber", 0.05)
        cam_r = _opt_float(p, "camber_root", cam_fallback)
        cam_m = _opt_float(p, "camber_mid", cam_fallback)
        cam_t = _opt_float(p, "camber_tip", cam_fallback)
        stations = [
            RadialStation(0.0, float(p["chord_root"]), float(p["stagger_root"]), th_r,
                          cam_r, cpos, 0.0, 0.0, 0.0,
                          le_sweep=_opt_float(p, "le_sweep_root", 0.0),
                          le_skew=_opt_float(p, "le_skew_root", 0.0),
                          te_face=_opt_float(p, "te_face_root", 1.0),
                          le_face=_opt_float(p, "le_face_root", 1.0)),
            RadialStation(0.5, float(p["chord_mid"]), float(p["stagger_mid"]), th_m,
                          cam_m, cpos, float(p["sweep_mid"]), _opt_float(p, "skew_mid", 0.0),
                          _opt_float(p, "lean_mid", 0.0),
                          le_sweep=_opt_float(p, "le_sweep_mid", 0.0),
                          le_skew=_opt_float(p, "le_skew_mid", 0.0),
                          te_face=_opt_float(p, "te_face_mid", 1.0),
                          le_face=_opt_float(p, "le_face_mid", 1.0)),
            RadialStation(1.0, float(p["chord_tip"]), float(p["stagger_tip"]), th_t,
                          cam_t, cpos, float(p["sweep_tip"]), _opt_float(p, "skew_tip", 0.0),
                          _opt_float(p, "lean_tip", 0.0),
                          le_sweep=_opt_float(p, "le_sweep_tip", 0.0),
                          le_skew=_opt_float(p, "le_skew_tip", 0.0),
                          te_face=_opt_float(p, "te_face_tip", 1.0),
                          le_face=_opt_float(p, "le_face_tip", 1.0)),
        ]
    kw: dict[str, object] = {}
    if p.get("root_embed") is not None:
        kw["root_embed"] = float(p["root_embed"])
    if p.get("hub_radius") is not None:
        kw["hub_radius"] = float(p["hub_radius"])
    if p.get("tip_radius") is not None:                  # blade LENGTH (outer radius) -- shrink to fit
        kw["tip_radius"] = float(p["tip_radius"])
    if _opt_float(p, "hub_height", 0.0) > 0.0:          # explicit hub height; <=0/absent = auto
        kw["hub_height_mm"] = float(p["hub_height"])
    if p.get("blade_hub_z") is not None:
        kw["blade_hub_z_mm"] = float(p["blade_hub_z"])
    elif p.get("blade_hub_z_mm") is not None:
        kw["blade_hub_z_mm"] = float(p["blade_hub_z_mm"])
    if p.get("blade_z") is not None:
        kw["blade_z_mm"] = float(p["blade_z"])
    elif p.get("blade_z_mm") is not None:
        kw["blade_z_mm"] = float(p["blade_z_mm"])
    if p.get("hub_profile"):                            # "cylinder" | "cone" | "dome"
        kw["hub_profile"] = str(p["hub_profile"])
    if _opt_float(p, "hub_nose", 0.0) > 0.0:            # nose height for cone/dome
        kw["hub_nose_mm"] = float(p["hub_nose"])
    bp = BladeParams(n_blades=int(p["n_blades"]), stations=stations,
                     features=features or Features(), **kw)
    # thread the later geometry knobs: shroud, section family, span interp, thickness bias
    shroud_t = _opt_float(p, "shroud_thick_mm", 0.0)
    if shroud_t > 0.0:
        bp.shroud_thick_mm = normalize_shroud_thick_mm(shroud_t)
    if p.get("shroud_height_frac") is not None:
        bp.shroud_height_frac = min(max(float(p["shroud_height_frac"]), 0.0), 1.0)
    if p.get("section_family"):
        bp.section_family = str(p["section_family"])
    span_interp = str(p.get("span_interp") or "").lower().strip()
    if span_interp in ("linear", "pchip"):
        bp.span_interp = span_interp
    if p.get("le_thick_scale") is not None:
        bp.le_thick_scale = float(p["le_thick_scale"])
    if p.get("te_thick_scale") is not None:
        bp.te_thick_scale = float(p["te_thick_scale"])
    if p.get("n_span") is not None:
        bp.n_span = max(4, int(p["n_span"]))
    if p.get("n_chord") is not None:
        bp.n_chord = max(8, int(p["n_chord"]))
    if p.get("cylindrical_tip") is not None:
        bp.cylindrical_tip = bool(p["cylindrical_tip"])
    if p.get("chord_basis"):                        # absent = "measured"; legacy saves are stamped "loft"
        bp.chord_basis = str(p["chord_basis"])
    # absent = "cylinder"; saves from before 27.4 are stamped "planar" (scripts/migrate_section_wrap.py)
    bp.section_wrap = str(p.get("section_wrap") or "cylinder")
    if (
        int(p.get("tip_notch_count", 0) or 0) > 0
        or p.get("notched_tips")
        or _opt_float(p, "tip_notch_depth_mm", 0.0) > 0.0
    ):
        # Notches are a FIXED recipe (on/off): apply_notched_tips stamps the canonical
        # count/depth. Do NOT override from the flat -- that silently reintroduced 1.2 mm
        # over the 1.5 mm recipe (test_fit_envelope_preserves_sickle_and_notch_keys).
        from fansim.geometry.blade import apply_notched_tips
        apply_notched_tips(bp)
    sickle_mm = _opt_float(p, "sickle_mm", 0.0)
    if sickle_mm > 0.0:
        from fansim.geometry.blade import apply_sickle
        apply_sickle(bp, sickle_mm)
    wl_sweep = _opt_float(p, "winglet_sweep", 0.0)
    wl_lean = _opt_float(p, "winglet_lean", 0.0)
    if (not shroud_is_full(bp)) and (wl_sweep or wl_lean):
        from fansim.geometry.blade import apply_winglet  # §7.5: no winglet under a full ring
        apply_winglet(bp, span_frac=_opt_float(p, "winglet_span", 0.85),
                      sweep_add=wl_sweep, lean_add=wl_lean)
    tip_round = _opt_float(p, "tip_round", 0.0)
    if tip_round > 0.0:                             # round the tip (taper chord over the outer span)
        # AFTER winglet: rounded tip keeps its curl
        from fansim.geometry.blade import apply_tip_shape
        apply_tip_shape(bp, tip_round=tip_round,
                        start_frac=_opt_float(p, "tip_round_start", 0.80))
    spread_val = _opt_float(p, "spacing_spread", 0.0)
    if spread_val > 0.0:                             # regenerate the same balanced pattern
        _apply_spacing(bp, p["spacing_spread"], p.get("spacing_seed", 0))
    elif p.get("blade_angles_deg") is not None:
        raw_angles = list(p["blade_angles_deg"])
        if len(raw_angles) == bp.n_blades:
            bp.blade_angles_deg = [float(a) for a in raw_angles]
    elif p.get("spacing_spread") is not None:
        _apply_spacing(bp, p["spacing_spread"], p.get("spacing_seed", 0))
    return bp


OBJECTIVE_DIRECTIONS = ("maximize",) * len(OBJECTIVE_NAMES)


# Walls this close (mm) count as one uniform wall. Was 0.12: v3 Stock's 2.47/2.51/2.47 mm read as
# uniform and the editor rewrote the recipe to one 2.48 mm wall (27.4). Designs made in uniform mode
# have walls equal up to t/c rounding (1e-4 x chord <= ~0.006 mm).
UNIFORM_WALL_TOL_MM = 0.02


def blade_to_flat(params: BladeParams) -> dict:
    """Flatten a ``BladeParams`` into the cockpit / ``blade_from_flat`` dict.

    The editor slots are root/mid/tip (stations nearest r/R 0, 0.5, 1). A recipe with more
    stations (e.g. 7-station Stock) also carries ``stations`` + the slot values it derived, so
    ``blade_from_flat`` rebuilds it exactly and applies slot edits across all stations (§23.1).

    Bio-features and post-loft stamps (winglet / tip-round / sickle / notches) are not
    reverse-engineered — start clean so the stock reference is editable from the yaml
    stations. Per-station camber is preserved as ``camber_root/mid/tip``; ``max_camber``
    stays mid for optimizer / older-UI compatibility.
    """
    st = sorted(params.stations, key=lambda s: s.r_frac)
    if len(st) < 3:
        raise ValueError(f"blade_to_flat needs ≥3 stations, got {len(st)}")

    def nearest(frac: float):
        return min(st, key=lambda s: abs(float(s.r_frac) - frac))

    root, mid, tip = nearest(0.0), nearest(0.5), nearest(1.0)
    cam_r, cam_m, cam_t = float(root.max_camber), float(mid.max_camber), float(tip.max_camber)
    th_r, th_m, th_t = float(root.thickness), float(mid.thickness), float(tip.thickness)
    cr, cm, ct = float(root.chord), float(mid.chord), float(tip.chord)
    # Absolute wall mm at each station — same rule as the cockpit uniform/tapered picker.
    ar, am, at = th_r * cr, th_m * cm, th_t * ct
    thick_mode = (
        "uniform"
        if max(ar, am, at) - min(ar, am, at) < UNIFORM_WALL_TOL_MM
        else "tapered"
    )
    thick_mm = round((ar + am + at) / 3.0, 2)
    flat: dict[str, Any] = dict(  # noqa: C408 - keyword form keeps the field list readable
        n_blades=int(params.n_blades),
        hub_radius=float(params.hub_radius),
        tip_radius=float(params.tip_radius),
        chord_root=cr, chord_mid=cm, chord_tip=ct,
        stagger_root=float(root.stagger_deg), stagger_mid=float(mid.stagger_deg),
        stagger_tip=float(tip.stagger_deg),
        camber_root=cam_r, camber_mid=cam_m, camber_tip=cam_t,
        max_camber=cam_m,
        camber_pos=float(mid.camber_pos),
        thickness_root=th_r, thickness_mid=th_m, thickness_tip=th_t,
        thick_mode=thick_mode,
        thick_mm=thick_mm,
        le_thick_scale=_attr_float(params, "le_thick_scale", 1.0),
        te_thick_scale=_attr_float(params, "te_thick_scale", 1.0),
        sweep_mid=float(mid.sweep), sweep_tip=float(tip.sweep),
        skew_mid=float(mid.skew), skew_tip=float(tip.skew),
        lean_mid=float(mid.lean_deg), lean_tip=float(tip.lean_deg),
        le_sweep_mid=float(mid.le_sweep), le_sweep_tip=float(tip.le_sweep),
        le_skew_mid=_attr_float(mid, "le_skew", 0.0),
        le_skew_tip=_attr_float(tip, "le_skew", 0.0),
        te_face_root=_attr_float(root, "te_face", 1.0),
        te_face_mid=_attr_float(mid, "te_face", 1.0),
        te_face_tip=_attr_float(tip, "te_face", 1.0),
        le_face_root=_attr_float(root, "le_face", 1.0),
        le_face_mid=_attr_float(mid, "le_face", 1.0),
        le_face_tip=_attr_float(tip, "le_face", 1.0),
        root_embed=float(params.root_embed),
        cylindrical_tip=bool(getattr(params, "cylindrical_tip", True)),
        chord_basis=str(getattr(params, "chord_basis", "measured") or "measured"),
        section_wrap=str(getattr(params, "section_wrap", "planar") or "planar"),
        hub_height=float(params.hub_height_mm or 0.0),
        blade_hub_z=_attr_float(params, "blade_hub_z_mm", 0.0),
        blade_z=_attr_float(params, "blade_z_mm", 0.0),
        hub_profile=str(params.hub_profile or "cylinder"),
        hub_nose=float(params.hub_nose_mm or 0.0),
        shroud_thick_mm=float(params.shroud_thick_mm or 0.0),
        shroud_height_frac=_attr_float(params, "shroud_height_frac", 1.0),
        span_interp=str(getattr(params, "span_interp", "linear") or "linear"),
        section_family=str(getattr(params, "section_family", "naca") or "naca"),
        n_span=int(getattr(params, "n_span", 18) or 18),
        n_chord=int(getattr(params, "n_chord", 60) or 60),
        tip_notch_count=int(getattr(params, "tip_notch_count", 0) or 0),
        tip_notch_depth_mm=float(getattr(params, "tip_notch_depth_mm", 0.0) or 0.0),
        notched_tips=bool(int(getattr(params, "tip_notch_count", 0) or 0) > 0),
        spacing_spread=0.0, spacing_seed=0,
        tip_round=0.0, tip_round_start=0.80,
        winglet_span=0.85, winglet_sweep=0.0, winglet_lean=0.0,
    )
    if params.blade_angles_deg is not None:
        flat["blade_angles_deg"] = [float(a) for a in params.blade_angles_deg]
    # The root/mid/tip slots lose information unless the recipe IS three stations at 0/0.5/1 with a
    # plain root (no sweep/skew/lean/le_sweep/le_skew) and uniform camber_pos. Otherwise carry it
    # all (§23.1).
    lossless = (
        len(st) == 3
        and [float(x.r_frac) for x in st] == [0.0, 0.5, 1.0]
        and not any(
            float(getattr(root, k))
            for k in ("sweep", "skew", "lean_deg", "le_sweep", "le_skew")
        )
        and float(root.camber_pos) == float(mid.camber_pos) == float(tip.camber_pos)
    )
    if not lossless:
        flat[FLAT_STATIONS] = [
            {k: float(getattr(x, k)) for k in _STATION_FIELDS} for x in st
        ]
        slot_keys = [k for _, keys in _SLOT_KEYS for k in keys if k is not None and k in flat]
        flat[FLAT_STATION_SLOTS] = {k: float(flat[k]) for k in slot_keys + ["camber_pos"]}
        flat[FLAT_STATION_SLOT_R] = [float(root.r_frac), float(mid.r_frac), float(tip.r_frac)]
    return flat


# Parametric stock recipes for scatter ✕ click → Design (not the OEM CAD).
STOCK_GEOMETRY_YAML = {
    "a12x25": "config/problems/a12x25_reference.yaml",
    "a12x25_approx": "config/problems/a12x25_approx.yaml",
}


OUTLINE_GEOMETRY_YAML = "config/problems/a12x25_outline.yaml"


def outline_blade_flat() -> dict:
    """The hub-26 plate whose front and back edges were set against the Noctua scan.

    Not the Stock button. Stock stays ``a12x25_reference.yaml``.
    """
    from fansim.geometry.config import load_blade_params

    root = Path(__file__).resolve().parents[2]
    path = root / OUTLINE_GEOMETRY_YAML
    if not path.is_file():
        raise FileNotFoundError(path)
    return blade_to_flat(load_blade_params(path))


def stock_blade_flat(fan_model: str = "a12x25") -> dict:
    """Load the parametric stock flat for ``fan_model``, or raise ``FileNotFoundError`` / ``KeyError``."""
    from fansim.geometry.config import load_blade_params

    key = str(fan_model or "a12x25")
    rel = STOCK_GEOMETRY_YAML.get(key)
    if rel is None:
        raise KeyError(f"no parametric stock geometry for fan model {key!r}")
    root = Path(__file__).resolve().parents[2]
    path = root / rel
    if not path.is_file():
        raise FileNotFoundError(path)
    return blade_to_flat(load_blade_params(path))


SICKLE_BOUNDS = (4.0, 12.0)   # tip le_skew mm

STATOR_BOUNDS = {
    "stator_stagger_deg": (35.0, 65.0),
    "stator_n_extra": (1, 4),
}

# Leftover clearance to the frame ID; single-sourced from fansim.cfd.domain.OPTIMIZER_TIP_GAP_MM.
TIP_CAP_CLEARANCE_MM = OPTIMIZER_TIP_GAP_MM
TIP_CAP_SEARCH_LO_MM = 48.0


def suggest_sickle(trial) -> float:
    """Sample tip sickle ``le_skew`` (mm) for a ``--sickle`` study."""
    lo, hi = SICKLE_BOUNDS
    return float(trial.suggest_float("sickle_mm", lo, hi))


def coprime_stator_extras(
    n_blades: int,
    bounds: tuple[int, int] | None = None,
) -> list[int]:
    """Vane offsets ``e`` in ``bounds`` with ``gcd(n_blades, n_blades + e) == 1`` (Tyler & Sofrin 1962)."""
    nb = int(n_blades)
    if nb < 2:
        raise ValueError(f"n_blades must be >= 2, got {n_blades!r}")
    b = STATOR_BOUNDS["stator_n_extra"] if bounds is None else bounds
    lo_e, hi_e = int(b[0]), int(b[1])
    return [e for e in range(lo_e, hi_e + 1) if math.gcd(nb, nb + e) == 1]


def suggest_stator(trial, *, n_blades: int | None = None) -> dict:
    """Sample stator stagger and vane-count offset for a ``--stator`` study.

    When ``n_blades`` is supplied, snaps the sampled offset to the nearest coprime value in
    ``STATOR_BOUNDS["stator_n_extra"]`` so ``gcd(B, B + n_extra) == 1`` (avoids simultaneous
    rotor–stator wake cutting and amplified cut-on BPF tones; #127) while keeping the Optuna
    parameter distribution fixed across trials.
    """
    lo_s, hi_s = STATOR_BOUNDS["stator_stagger_deg"]
    lo_e, hi_e = int(STATOR_BOUNDS["stator_n_extra"][0]), int(STATOR_BOUNDS["stator_n_extra"][1])
    stagger = trial.suggest_float("stator_stagger_deg", lo_s, hi_s)
    n_extra = trial.suggest_int("stator_n_extra", lo_e, hi_e)
    if n_blades is not None:
        coprime = coprime_stator_extras(n_blades, (lo_e, hi_e))
        if coprime and n_extra not in coprime:
            n_extra = min(coprime, key=lambda e: (abs(e - n_extra), -e))
    return {"stagger_deg": float(stagger), "n_extra": int(n_extra)}


def tip_radius_cap_mm(stations, hub_radius: float, frame_half_mm: float,
                      shroud_mm: float = 0.0, n_blades: int = 7,
                      cylindrical_tip: bool | None = None,
                      section_wrap: str = "cylinder",
                      features: Features | None = None,
                      winglet: tuple[float, float] | None = None,
                      sickle_mm: float = 0.0) -> float:
    """Largest tip_radius whose built envelope still leaves CLEARANCE to the frame.

    Same shrink as cockpit Fit (iterate open_tip_rmax_mm). No CadQuery.
    ``cylindrical_tip`` defaults to BladeParams (True); pass False to measure legacy bulge.
    ``section_wrap`` is the design's placement: new axial designs are wrapped (no LE/TE bulge past
    their radius); "planar" measures the legacy tangent-plane bulge.
    Optional ``features``, ``winglet=(sweep_add, lean_add)``, and ``sickle_mm`` are applied to
    cloned stations on each probe so active modifiers are accounted for without mutating caller
    inputs.
    """
    st_list = list(stations)
    if not st_list:
        raise ValueError("stations must be non-empty")
    hub_r = float(hub_radius)
    if hub_r < 0.0:
        raise ValueError(f"hub_radius must be >= 0, got {hub_r}")
    frame_half = float(frame_half_mm)
    if frame_half <= 0.0:
        raise ValueError(f"frame_half_mm must be > 0, got {frame_half}")
    shroud = float(shroud_mm or 0.0)
    if shroud < 0.0:
        raise ValueError(f"shroud_mm must be >= 0, got {shroud}")
    sickle = float(sickle_mm or 0.0)
    if sickle < 0.0:
        raise ValueError(f"sickle_mm must be >= 0, got {sickle}")
    # Outer built radius = open_tip_rmax_mm(probe) + shroud must stay <= frame_limit.
    frame_limit = frame_half - TIP_CAP_CLEARANCE_MM
    max_blade_r = frame_limit - shroud
    if max_blade_r <= hub_r:
        raise ValueError(
            f"frame_half_mm ({frame_half:.2f}) minus clearance/shroud leaves no span above "
            f"hub_radius ({hub_r:.2f})"
        )
    tr = max_blade_r
    min_tr = hub_r + 1e-3
    tip_kw = {}
    if cylindrical_tip is not None:
        tip_kw["cylindrical_tip"] = bool(cylindrical_tip)
    probe_features = features if features is not None else Features()
    needs_clone = winglet is not None or sickle > 0.0
    for _ in range(12):
        probe_stations = [dataclasses.replace(s) for s in st_list] if needs_clone else st_list
        probe = BladeParams(
            n_blades=int(n_blades), hub_radius=hub_r,
            tip_radius=tr, stations=probe_stations, section_wrap=section_wrap,
            features=probe_features, **tip_kw,
        )
        if winglet is not None and shroud == 0.0:
            from fansim.geometry.blade import apply_winglet
            apply_winglet(probe, sweep_add=float(winglet[0]), lean_add=float(winglet[1]))
        if sickle > 0.0:
            from fansim.geometry.blade import apply_sickle
            apply_sickle(probe, sickle)
        built = open_tip_rmax_mm(probe) + shroud
        if built <= frame_limit + 1e-9:
            return tr
        tr -= (built - frame_limit) + 0.15
        if tr < min_tr:
            return min_tr
    return tr
