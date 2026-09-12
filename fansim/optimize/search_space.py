# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Map an Optuna trial to a BladeParams design vector (~10 dimensions).

Kept compact so a search is tractable: blade count, per-station stagger and chord, mid/tip
sweep, and global camber. Thickness is fixed to a printable profile. Feature-layer
parameters (tubercles, serrations, dimples) are added here once the feature library lands.
"""

from __future__ import annotations

from fansim.geometry.blade import BladeParams, RadialStation
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
    "n_blades": (5, 8),          # fewer blades: quieter + more efficient
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
    "max_camber": (0.0, 0.02),    # keep camber low
}
OPEN = {
    "n_blades": (5, 11), "stagger_root": (20.0, 48.0), "stagger_mid": (18.0, 42.0),
    "stagger_tip": (16.0, 38.0), "chord_root": (MIN_CHORD, MAX_CHORD),
    "chord_mid": (MIN_CHORD, MAX_CHORD), "chord_tip": (MIN_CHORD, MAX_CHORD),
    "sweep_mid": (-3.0, 8.0), "sweep_tip": (0.0, 12.0), "lean_mid": (0.0, 25.0),
    "lean_tip": (0.0, 45.0), "max_camber": (0.0, 0.06),
}
# Load-spreading recipe (guided + per-blade-loading cap). Keeps the flow/eff rules (high-ish
# mid-stagger, wide tip chord, low camber) but allows MORE blades and wider mid-chord so the search
# can meet a solidity floor -> lower per-blade loading -> quieter broadband at high flow. Pair with
# evaluate_candidate(min_sol_mid=..., min_sol_tip=...).
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
    "max_camber": (0.0, 0.02),
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
                   with_winglet: bool = False, max_tip_radius: float | None = None) -> BladeParams:
    """Sample a BladeParams from an Optuna trial's search space.

    space: 'open' (full), 'guided' (data-driven recipe, docs/design-rules.md), or 'guided_lc'
    (guided + load-spreading bounds for a per-blade-loading cap). with_spacing adds an uneven
    blade-spacing DOF (spread + seed). with_extended adds hub radius, per-station thickness and
    camber position as search DOFs (else they stay at the fixed defaults). hub_radius_range forces
    the hub radius to be SAMPLED from that range (used by --mountable to keep the hub big enough to
    house the motor) — it overrides the extended hub bound and applies even without --extended."""
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
    # tip_radius (blade LENGTH): frame-aware when max_tip_radius is given, so the BUILT tip diameter
    # lands inside the frame instead of getting gated (the built dia bulges ~4 mm past 2*tip_radius, so
    # the caller passes frame_max/2 minus a margin). Else the extended range, else the fixed default.
    if max_tip_radius is not None:
        tip = trial.suggest_float("tip_radius", min(48.0, max_tip_radius - 1.0), max_tip_radius)
    elif with_extended:
        tip = trial.suggest_float("tip_radius", *EXTENDED["tip_radius"])
    else:
        tip = None
    hub_range = hub_radius_range or (EXTENDED["hub_radius"] if with_extended else None)
    if hub_range is not None:  # --mountable forces a hub big enough to house the motor
        hub = trial.suggest_float("hub_radius", *hub_range)

    stations = [
        RadialStation(0.0, ch_root, stg_root, th_r, camber, cpos, 0.0, 0.0, 0.0),
        RadialStation(0.5, ch_mid, stg_mid, th_m, camber, cpos, sweep_mid, 0.0, lean_mid),
        RadialStation(1.0, ch_tip, stg_tip, th_t, camber, cpos, sweep_tip, 0.0, lean_tip),
    ]
    features = suggest_features(trial) if with_features else Features()
    kw = {}
    if hub is not None:
        kw["hub_radius"] = hub
    if tip is not None:
        kw["tip_radius"] = tip
    bp = BladeParams(n_blades=n_blades, stations=stations, features=features, **kw)
    if with_winglet:                      # curl the tip (CFD: mild winglet ~+4% airflow, flat eff)
        from fansim.geometry.blade import apply_winglet
        apply_winglet(bp, sweep_add=trial.suggest_float("winglet_sweep", *WINGLET["winglet_sweep"]),
                      lean_add=trial.suggest_float("winglet_lean", *WINGLET["winglet_lean"]))
    if with_spacing:
        _apply_spacing(bp, trial.suggest_float("spacing_spread", 0.0, 0.6),
                       trial.suggest_int("spacing_seed", 0, 99999))
    return bp


def blade_from_flat(p: dict, features: Features | None = None) -> BladeParams:
    """Rebuild a BladeParams from a flat param dict (inverse of suggest_params).

    Thickness (root/mid/tip), camber position and hub radius fall back to the fixed defaults when
    absent, so older param dicts (and the optimizer, which fixes them) still work; the cockpit can
    now override them."""
    cpos = float(p.get("camber_pos", CAMBER_POS))
    th_r = float(p.get("thickness_root", THICKNESS[0]))
    th_m = float(p.get("thickness_mid", THICKNESS[1]))
    th_t = float(p.get("thickness_tip", THICKNESS[2]))
    stations = [
        RadialStation(0.0, p["chord_root"], p["stagger_root"], th_r,
                      p["max_camber"], cpos, 0.0, 0.0, 0.0),
        RadialStation(0.5, p["chord_mid"], p["stagger_mid"], th_m,
                      p["max_camber"], cpos, p["sweep_mid"], p.get("skew_mid", 0.0),
                      p.get("lean_mid", 0.0), le_sweep=p.get("le_sweep_mid", 0.0)),
        RadialStation(1.0, p["chord_tip"], p["stagger_tip"], th_t,
                      p["max_camber"], cpos, p["sweep_tip"], p.get("skew_tip", 0.0),
                      p.get("lean_tip", 0.0), le_sweep=p.get("le_sweep_tip", 0.0)),
    ]
    kw = {}
    if "hub_radius" in p:
        kw["hub_radius"] = float(p["hub_radius"])
    if "tip_radius" in p:                               # blade LENGTH (outer radius) -- shrink to fit
        kw["tip_radius"] = float(p["tip_radius"])
    if float(p.get("hub_height", 0.0)) > 0.0:           # explicit hub height; <=0/absent = auto
        kw["hub_height_mm"] = float(p["hub_height"])
    if p.get("hub_profile"):                            # "cylinder" | "cone" | "dome"
        kw["hub_profile"] = str(p["hub_profile"])
    if float(p.get("hub_nose", 0.0)) > 0.0:             # nose height for cone/dome
        kw["hub_nose_mm"] = float(p["hub_nose"])
    bp = BladeParams(n_blades=int(p["n_blades"]), stations=stations,
                     features=features or Features(), **kw)
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
    stations. Mid-span camber is used for the single editor camber slider.
    """
    st = sorted(params.stations, key=lambda s: s.r_frac)
    if len(st) < 3:
        raise ValueError(f"blade_to_flat needs ≥3 stations, got {len(st)}")

    def nearest(frac: float):
        return min(st, key=lambda s: abs(float(s.r_frac) - frac))

    root, mid, tip = nearest(0.0), nearest(0.5), nearest(1.0)
    flat = dict(
        n_blades=int(params.n_blades),
        hub_radius=float(params.hub_radius),
        tip_radius=float(params.tip_radius),
        chord_root=float(root.chord), chord_mid=float(mid.chord), chord_tip=float(tip.chord),
        stagger_root=float(root.stagger_deg), stagger_mid=float(mid.stagger_deg),
        stagger_tip=float(tip.stagger_deg),
        max_camber=float(mid.max_camber),
        camber_pos=float(mid.camber_pos),
        thickness_root=float(root.thickness), thickness_mid=float(mid.thickness),
        thickness_tip=float(tip.thickness),
        sweep_mid=float(mid.sweep), sweep_tip=float(tip.sweep),
        skew_mid=float(mid.skew), skew_tip=float(tip.skew),
        lean_mid=float(mid.lean_deg), lean_tip=float(tip.lean_deg),
        le_sweep_mid=float(mid.le_sweep), le_sweep_tip=float(tip.le_sweep),
        le_skew_mid=float(getattr(mid, "le_skew", 0.0) or 0.0),
        le_skew_tip=float(getattr(tip, "le_skew", 0.0) or 0.0),
        hub_height=float(params.hub_height_mm or 0.0),
        hub_profile=str(params.hub_profile or "cylinder"),
        hub_nose=float(params.hub_nose_mm or 0.0),
        shroud_thick_mm=float(params.shroud_thick_mm or 0.0),
        shroud_height_frac=float(params.shroud_height_frac or 1.0),
        span_interp=str(getattr(params, "span_interp", "linear") or "linear"),
        spacing_spread=0.0, spacing_seed=0,
        tip_round=0.0, tip_round_start=0.80,
        winglet_span=0.85, winglet_sweep=0.0, winglet_lean=0.0,
    )
    return flat


SICKLE_BOUNDS = (4.0, 12.0)   # tip le_skew mm
