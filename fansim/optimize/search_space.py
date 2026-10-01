"""Map an Optuna trial to a BladeParams design vector (~10 dimensions).

Kept compact so a search is tractable: blade count, per-station stagger and chord, mid/tip
sweep, and global camber. Thickness is fixed to a printable profile. Feature-layer
parameters (tubercles, serrations, dimples) are added here once the feature library lands.
"""

from __future__ import annotations

from pathlib import Path

from fansim.geometry.blade import (BladeParams, RadialStation, shroud_is_full,
    open_tip_rmax_mm, SHROUD_DEFAULT_MM, normalize_shroud_thick_mm)
from fansim.geometry.features import Features

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
    "stagger_root": (24.0, 48.0),
    "stagger_mid": (32.0, 48.0),  # HIGH mid-stagger — the win-win-win lever
    "stagger_tip": (18.0, 38.0),
    "chord_root": (14.0, 34.0),
    "chord_mid": (14.0, 32.0),    # cap mid chord -> lower mid-solidity (noise driver)
    "chord_tip": (26.0, 40.0),    # WIDE tip chord — efficiency + quieter tone
    "sweep_mid": (0.0, 8.0),
    "sweep_tip": (0.0, 12.0),
    "lean_mid": (0.0, 12.0),      # low mid-lean -> lower blade-pass tone
    "lean_tip": (0.0, 45.0),
    "max_camber": (0.0, 0.06),    # was 0–0.02 (free-air); hose scoring uses OPEN's 0–0.06
}
OPEN = {
    "n_blades": (5, 11), "stagger_root": (20.0, 48.0), "stagger_mid": (18.0, 42.0),
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
    "tip_radius": (48.0, 58.0),   # blade length (outer radius); tip dia = 2x, must fit the frame

    # Thickness biased THIN (down toward the printability floor): thicker blades are never
    # aerodynamically better and only add depth/weight. The opt_extended run showed a generous upper
    # range (0.14) gated 21/30 trials on depth/weight -- so cap near/below the fixed defaults.
    "thickness_root": (0.06, 0.11),
    "thickness_mid": (0.05, 0.09),
    "thickness_tip": (0.04, 0.07),
    "camber_pos": (0.30, 0.50),
}

# Winglet DOFs (opt-in via with_winglet). CFD study found a MILD winglet (~sweep 5 mm / lean 8 deg) buys
# ~4% airflow at flat efficiency; overdoing it is worse. Bounds cover the sweet spot + a little past it.
WINGLET = {"winglet_sweep": (0.0, 10.0), "winglet_lean": (0.0, 18.0)}


def _apply_spacing(bp: BladeParams, spread: float, seed) -> None:
    """Deterministically set a balanced uneven blade spacing on ``bp`` from (spread, seed)."""
    import numpy as np

    from fansim.geometry.blade import set_uneven_spacing
    set_uneven_spacing(bp, spread=float(spread), rng=np.random.default_rng(int(seed)))


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
    b = BOUNDS[space]
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
        hub = trial.suggest_float("hub_radius", *hub_range)

    stations = [
        RadialStation(0.0, ch_root, stg_root, th_r, camber, cpos, 0.0, 0.0, 0.0),
        RadialStation(0.5, ch_mid, stg_mid, th_m, camber, cpos, sweep_mid, 0.0, lean_mid),
        RadialStation(1.0, ch_tip, stg_tip, th_t, camber, cpos, sweep_tip, 0.0, lean_tip),
    ]
    hub_r = float(hub) if hub is not None else BladeParams.hub_radius

    # tip_radius: frame-aware cap from the real section-point bulge when frame_half_mm is set.
    # Else max_tip_radius / extended range / BladeParams default.
    if frame_half_mm is not None:
        shroud = SHROUD_DEFAULT_MM if with_shroud else 0.0
        cap = tip_radius_cap_mm(stations, hub_r, frame_half_mm, shroud, n_blades)
        lo = min(TIP_CAP_SEARCH_LO_MM, cap - 1.0)
        if lo >= cap:
            lo = cap - 0.5
        tip = trial.suggest_float("tip_radius", lo, cap)
    elif max_tip_radius is not None:
        tip = trial.suggest_float("tip_radius", min(48.0, max_tip_radius - 1.0), max_tip_radius)
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
    if hasattr(trial, "set_user_attr"):
        trial.set_user_attr("chord_basis", bp.chord_basis)
    if with_shroud:                       # tip ring; search its TE-anchored height (recovery: 7.5)
        bp.shroud_thick_mm = SHROUD_DEFAULT_MM
        bp.shroud_height_frac = trial.suggest_float("shroud_height_frac", 0.30, 1.0)
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


def blade_from_flat(p: dict, features: Features | None = None) -> BladeParams:
    """Rebuild a BladeParams from a flat param dict (inverse of suggest_params).

    Thickness (root/mid/tip), camber position and hub radius fall back to the fixed defaults when
    absent, so older param dicts (and the optimizer, which fixes them) still work; the cockpit can
    now override them.

    Camber: prefer ``camber_root`` / ``camber_mid`` / ``camber_tip``; else fall back to the single
    ``max_camber`` used by the optimizer (all three stations get that value).
    """
    cpos = float(p.get("camber_pos", CAMBER_POS))
    th_r = float(p.get("thickness_root", THICKNESS[0]))
    th_m = float(p.get("thickness_mid", THICKNESS[1]))
    th_t = float(p.get("thickness_tip", THICKNESS[2]))
    cam_fallback = float(p.get("max_camber", 0.05))
    cam_r = float(p.get("camber_root", cam_fallback))
    cam_m = float(p.get("camber_mid", cam_fallback))
    cam_t = float(p.get("camber_tip", cam_fallback))
    stations = [
        RadialStation(0.0, p["chord_root"], p["stagger_root"], th_r,
                      cam_r, cpos, 0.0, 0.0, 0.0,
                      le_sweep=p.get("le_sweep_root", 0.0),
                      le_skew=p.get("le_skew_root", 0.0)),
        RadialStation(0.5, p["chord_mid"], p["stagger_mid"], th_m,
                      cam_m, cpos, p["sweep_mid"], p.get("skew_mid", 0.0),
                      p.get("lean_mid", 0.0), le_sweep=p.get("le_sweep_mid", 0.0),
                      le_skew=p.get("le_skew_mid", 0.0)),
        RadialStation(1.0, p["chord_tip"], p["stagger_tip"], th_t,
                      cam_t, cpos, p["sweep_tip"], p.get("skew_tip", 0.0),
                      p.get("lean_tip", 0.0), le_sweep=p.get("le_sweep_tip", 0.0),
                      le_skew=p.get("le_skew_tip", 0.0)),
    ]
    kw: dict[str, object] = {}
    if "hub_radius" in p:
        kw["hub_radius"] = float(p["hub_radius"])
    if "tip_radius" in p:                               # blade LENGTH (outer radius) -- shrink to fit
        kw["tip_radius"] = float(p["tip_radius"])
    if float(p.get("hub_height", 0.0)) > 0.0:           # explicit hub height; <=0/absent = auto
        kw["hub_height_mm"] = float(p["hub_height"])
    if "blade_hub_z" in p or "blade_hub_z_mm" in p:
        kw["blade_hub_z_mm"] = float(p.get("blade_hub_z", p.get("blade_hub_z_mm", 0.0)) or 0.0)
    if p.get("hub_profile"):                            # "cylinder" | "cone" | "dome"
        kw["hub_profile"] = str(p["hub_profile"])
    if float(p.get("hub_nose", 0.0)) > 0.0:             # nose height for cone/dome
        kw["hub_nose_mm"] = float(p["hub_nose"])
    bp = BladeParams(n_blades=int(p["n_blades"]), stations=stations,
                     features=features or Features(), **kw)
    # thread the later geometry knobs (recovery): shroud, section family, span interp, thickness bias
    if float(p.get("shroud_thick_mm", 0.0)) > 0.0:
        bp.shroud_thick_mm = normalize_shroud_thick_mm(float(p["shroud_thick_mm"]))
    if "shroud_height_frac" in p:
        bp.shroud_height_frac = min(max(float(p["shroud_height_frac"]), 0.0), 1.0)
    if p.get("section_family"):
        bp.section_family = str(p["section_family"])
    if p.get("span_interp") in ("linear", "pchip"):
        bp.span_interp = str(p["span_interp"])
    if "le_thick_scale" in p:
        bp.le_thick_scale = float(p["le_thick_scale"])
    if "te_thick_scale" in p:
        bp.te_thick_scale = float(p["te_thick_scale"])
    if "n_span" in p:
        bp.n_span = max(4, int(p["n_span"]))
    if "n_chord" in p:
        bp.n_chord = max(8, int(p["n_chord"]))
    if "cylindrical_tip" in p:
        bp.cylindrical_tip = bool(p["cylindrical_tip"])
    if p.get("chord_basis"):                        # absent = "measured"; legacy saves are stamped "loft"
        bp.chord_basis = str(p["chord_basis"])
    if (
        int(p.get("tip_notch_count", 0) or 0) > 0
        or p.get("notched_tips")
        or float(p.get("tip_notch_depth_mm", 0.0) or 0.0) > 0.0
    ):
        # Notches are a FIXED recipe (on/off): apply_notched_tips stamps the canonical
        # count/depth. Do NOT override from the flat -- that silently reintroduced 1.2 mm
        # over the 1.5 mm recipe (test_fit_envelope_preserves_sickle_and_notch_keys).
        from fansim.geometry.blade import apply_notched_tips
        apply_notched_tips(bp)
    if float(p.get("sickle_mm", 0.0)) > 0.0:
        from fansim.geometry.blade import apply_sickle
        apply_sickle(bp, float(p["sickle_mm"]))
    if (not shroud_is_full(bp)) and (
            float(p.get("winglet_sweep", 0.0)) or float(p.get("winglet_lean", 0.0))):
        from fansim.geometry.blade import apply_winglet   # §7.5: no winglet under a full ring
        apply_winglet(bp, span_frac=float(p.get("winglet_span", 0.85)),
                      sweep_add=float(p.get("winglet_sweep", 0.0)),
                      lean_add=float(p.get("winglet_lean", 0.0)))
    if float(p.get("tip_round", 0.0)) > 0.0:        # round the tip (taper chord over the outer span)
        from fansim.geometry.blade import apply_tip_shape   # AFTER winglet: rounded tip keeps its curl
        apply_tip_shape(bp, tip_round=float(p["tip_round"]),
                        start_frac=float(p.get("tip_round_start", 0.80)))
    if "spacing_spread" in p:                       # regenerate the same balanced pattern
        _apply_spacing(bp, p["spacing_spread"], p.get("spacing_seed", 0))
    return bp


OBJECTIVE_NAMES = ("cfm_free", "cfm_load", "efficiency")
OBJECTIVE_DIRECTIONS = ("maximize", "maximize", "maximize")


# --- spliced from transcript edit-history (recovery 2026-09-12) ---
def blade_to_flat(params: BladeParams) -> dict:
    """Flatten a 3-station ``BladeParams`` into the cockpit / ``blade_from_flat`` dict.

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
        if abs(ar - am) < 0.12 and abs(am - at) < 0.12
        else "tapered"
    )
    thick_mm = round((ar + am + at) / 3.0, 2)
    flat = dict(
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
        le_thick_scale=float(getattr(params, "le_thick_scale", 1.0) or 1.0),
        te_thick_scale=float(getattr(params, "te_thick_scale", 1.0) or 1.0),
        sweep_mid=float(mid.sweep), sweep_tip=float(tip.sweep),
        skew_mid=float(mid.skew), skew_tip=float(tip.skew),
        lean_mid=float(mid.lean_deg), lean_tip=float(tip.lean_deg),
        le_sweep_mid=float(mid.le_sweep), le_sweep_tip=float(tip.le_sweep),
        le_skew_mid=float(getattr(mid, "le_skew", 0.0) or 0.0),
        le_skew_tip=float(getattr(tip, "le_skew", 0.0) or 0.0),
        cylindrical_tip=bool(getattr(params, "cylindrical_tip", True)),
        chord_basis=str(getattr(params, "chord_basis", "measured") or "measured"),
        hub_height=float(params.hub_height_mm or 0.0),
        blade_hub_z=float(getattr(params, "blade_hub_z_mm", 0.0) or 0.0),
        hub_profile=str(params.hub_profile or "cylinder"),
        hub_nose=float(params.hub_nose_mm or 0.0),
        shroud_thick_mm=float(params.shroud_thick_mm or 0.0),
        shroud_height_frac=float(params.shroud_height_frac or 1.0),
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
    return flat


# Parametric stock recipes for scatter ✕ click → Design (not the OEM CAD).
STOCK_GEOMETRY_YAML = {
    "a12x25": "config/problems/a12x25_reference.yaml",
    "a12x25_approx": "config/problems/a12x25_approx.yaml",
}


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


# --- spliced STATOR_BOUNDS (recovery) ---
STATOR_BOUNDS = {
    "stator_stagger_deg": (35.0, 65.0),
    "stator_n_extra": (1, 4),
}


# --- RECONSTRUCTED 2026-09-12 (never captured in any transcript; from test contract; VERIFY) ---
TIP_CAP_CLEARANCE_MM = 0.5  # leftover to the frame ID; matches OPTIMIZER_TIP_GAP_MM
TIP_CAP_SEARCH_LO_MM = 48.0


# --- spliced suggest_sickle (recovery) ---
def suggest_sickle(trial) -> float:
    """Sample tip sickle ``le_skew`` (mm) for a ``--sickle`` study."""
    lo, hi = SICKLE_BOUNDS
    return float(trial.suggest_float("sickle_mm", lo, hi))


# --- spliced suggest_stator (recovery) ---
def suggest_stator(trial) -> dict:
    """Sample stator stagger and vane-count offset for a ``--stator`` study."""
    lo_s, hi_s = STATOR_BOUNDS["stator_stagger_deg"]
    lo_e, hi_e = STATOR_BOUNDS["stator_n_extra"]
    stagger = trial.suggest_float("stator_stagger_deg", lo_s, hi_s)
    n_extra = trial.suggest_int("stator_n_extra", lo_e, hi_e)
    return {"stagger_deg": float(stagger), "n_extra": int(n_extra)}


# --- spliced tip_radius_cap_mm (recovery) ---
def tip_radius_cap_mm(stations, hub_radius: float, frame_half_mm: float,
                      shroud_mm: float = 0.0, n_blades: int = 7,
                      cylindrical_tip: bool | None = None) -> float:
    """Largest tip_radius whose built envelope still leaves CLEARANCE to the frame.

    Same shrink as cockpit Fit (iterate open_tip_rmax_mm). No CadQuery.
    ``cylindrical_tip`` defaults to BladeParams (True); pass False to measure legacy bulge.
    """
    shroud = float(shroud_mm or 0.0)
    allowed = float(frame_half_mm) - shroud - TIP_CAP_CLEARANCE_MM
    tr = allowed
    tip_kw = {}
    if cylindrical_tip is not None:
        tip_kw["cylindrical_tip"] = bool(cylindrical_tip)
    for _ in range(12):
        probe = BladeParams(
            n_blades=int(n_blades), hub_radius=float(hub_radius),
            tip_radius=tr, stations=list(stations),
            **tip_kw,
        )
        built = open_tip_rmax_mm(probe) + shroud
        if built <= allowed:
            return tr
        tr -= (built - allowed) + 0.15
        if tr < 20.0:
            return 20.0
    return tr
