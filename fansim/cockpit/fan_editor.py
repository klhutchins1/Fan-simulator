"""Fan-tab editor binder: the geometry/feature form and edited-since-assessment tracking (§13.9).

Owns every ``state.e_*`` slider: seeding the form from a flat (``_init_editor``), serializing
it back (``edit_flat`` / ``edit_features`` / ``build_edit_params``), the Fit/Scale envelope
actions, randomizers, thickness-mode syncers, and the staleness signature (``sel_sig``).
Cross-domain: fit actions and staleness call the model fit-readouts (``session._*_fit_readout``).
"""

from __future__ import annotations

import random

from fansim.cockpit.placement import (
    effective_depth_max,
    fit_envelope,
    impeller_z_extent,
    intake_extra_mm,
    intake_overbuild_note,
    preview_changes,
    scale_to_hub,
)
from fansim.fan_spec import get_fan_spec
from fansim.geometry.blade import normalize_shroud_thick_mm, uniform_thickness_tc
from fansim.geometry.features import Features
from fansim.optimize.search_space import (
    FLAT_STATIONS,
    STATION_PAYLOAD_KEYS,
    UNIFORM_WALL_TOL_MM,
    blade_from_flat,
)

EDITOR_VARS = (
    "e_n_blades", "e_stagger_root", "e_stagger_mid", "e_stagger_tip",
    "e_chord_root", "e_chord_mid", "e_chord_tip", "e_sweep_mid", "e_sweep_tip",
    "e_camber_root", "e_camber_mid", "e_camber_tip", "e_camber", "e_camber_pos",
    "e_lean_mid", "e_lean_tip", "e_le_mid", "e_le_tip", "e_le_skew_mid", "e_le_skew_tip",
    "e_skew_mid", "e_skew_tip", "e_smooth_span", "e_winglet_span", "e_winglet_sweep",
    "e_winglet_lean", "e_shroud_thick", "e_shroud_height", "e_tip_round", "e_tip_start",
    "e_tip_notched", "e_tip_notch_depth", "e_cylindrical_tip", "e_chord_basis", "e_section_wrap", "e_hub_radius",
    "e_tip_radius", "e_hub_height", "e_blade_hub_z", "e_blade_z", "e_hub_profile", "e_hub_nose",
    "e_thick_mode", "e_thick_mm", "e_thick_root", "e_thick_mid", "e_thick_tip",
    "e_le_thick", "e_te_thick", "e_te_face_root", "e_te_face_mid", "e_te_face_tip",
    "e_le_face_root", "e_le_face_mid", "e_le_face_tip",
    "e_root_embed", "e_section_family", "e_spacing",
    "e_tub_amp", "e_tub_waves", "e_ser_amp", "e_ser_waves", "e_dim_amp",
    "e_dim_rows", "e_dim_cols",
)


def bind(session) -> None:
    state = session.state
    sel_sig = session.sel_sig

    # Full station recipe of the loaded design (e.g. 7-station Stock). The sliders only hold
    # root/mid/tip, so the recipe rides alongside and edit_flat() hands it back; blade_from_flat
    # applies slider edits across all stations (roadmap §23.1). Server-side only, not trame state.
    station_payload: list = [None]
    # Explicit uneven blade angles loaded from a flat (when e_spacing == 0); preserved across
    # unrelated slider edits until n_blades changes or e_spacing is raised (#127).
    angles_payload: list = [None]

    def _editor_busy() -> bool:
        """True while Preview/Assess/Export/Optimize own the mesh; ignore slider-mutating clicks."""
        return bool(
            getattr(state, "preview_busy", False)
            or getattr(state, "assess_busy", False)
            or getattr(state, "export_busy", False)
            or getattr(state, "opt_running", False)
        )

    def _set_station_payload(p: dict) -> None:
        if p.get(FLAT_STATIONS):
            station_payload[0] = {k: p[k] for k in STATION_PAYLOAD_KEYS if k in p}
        else:
            station_payload[0] = None
        raw_angles = p.get("blade_angles_deg")
        if raw_angles is not None:
            angles_payload[0] = [float(a) for a in raw_angles]
        else:
            angles_payload[0] = None

    def _init_editor(p: dict, feat: Features | None = None):
        feat = feat or Features()
        _set_station_payload(p)
        state.e_n_blades = int(p.get("n_blades", 7))
        state.e_stagger_root = float(p.get("stagger_root", 26.0))
        state.e_stagger_mid = float(p.get("stagger_mid", 26.0))
        state.e_stagger_tip = float(p.get("stagger_tip", 22.0))
        state.e_chord_root = float(p.get("chord_root", 34.0))
        state.e_chord_mid = float(p.get("chord_mid", 44.0))
        state.e_chord_tip = float(p.get("chord_tip", 38.0))
        _cam = float(p.get("max_camber", 0.05))
        state.e_camber_root = float(p.get("camber_root", _cam))
        state.e_camber_mid = float(p.get("camber_mid", _cam))
        state.e_camber_tip = float(p.get("camber_tip", _cam))
        state.e_camber = state.e_camber_mid
        state.e_sweep_mid = float(p.get("sweep_mid", 3.0))
        state.e_sweep_tip = float(p.get("sweep_tip", 5.0))
        state.e_lean_mid = float(p.get("lean_mid", 14.0))
        state.e_lean_tip = float(p.get("lean_tip", 26.0))
        state.e_le_mid = float(p.get("le_sweep_mid", 0.0))
        state.e_le_tip = float(p.get("le_sweep_tip", 0.0))
        _le_skew_mid = float(p.get("le_skew_mid", 0.0) or 0.0)
        _le_skew_tip = float(p.get("le_skew_tip", 0.0) or 0.0)
        _sickle = float(p.get("sickle_mm", 0.0) or 0.0)
        if _le_skew_mid == 0.0 and _le_skew_tip == 0.0 and _sickle > 0.0:
            _le_skew_tip = _sickle
            _le_skew_mid = 0.40 * _sickle
        state.e_le_skew_mid = _le_skew_mid
        state.e_le_skew_tip = _le_skew_tip
        state.e_skew_mid = float(p.get("skew_mid", 0.0))
        state.e_skew_tip = float(p.get("skew_tip", 0.0))
        state.e_smooth_span = (
            str(p.get("span_interp", "linear") or "linear").lower() == "pchip"
        )
        state.e_winglet_span = float(p.get("winglet_span", 0.85))
        state.e_winglet_sweep = float(p.get("winglet_sweep", 0.0))
        state.e_winglet_lean = float(p.get("winglet_lean", 0.0))
        state.e_shroud_thick = normalize_shroud_thick_mm(float(p.get("shroud_thick_mm", 0.0)))
        state.e_shroud_height = min(max(float(p.get("shroud_height_frac", 1.0)), 0.0), 1.0)
        state.e_tip_round = float(p.get("tip_round", 0.0))
        state.e_tip_start = float(p.get("tip_round_start", 0.80))
        state.e_tip_notched = bool(
            int(p.get("tip_notch_count", 0) or 0) > 0
            or p.get("notched_tips")
            or float(p.get("tip_notch_depth_mm", 0.0) or 0.0) > 0.0
        )
        state.e_tip_notch_depth = float(
            p.get("tip_notch_depth_mm", 1.5) or 1.5
        ) if state.e_tip_notched else 1.5
        _ct = p.get("cylindrical_tip", True)
        if isinstance(_ct, str):
            state.e_cylindrical_tip = _ct.strip().lower() not in (
                "0", "false", "no", "off", "",
            )
        else:
            state.e_cylindrical_tip = bool(_ct) if _ct is not None else True
        # Legacy (pre-37728b9) designs carry loft chords; keep that so they rebuild as scored.
        state.e_chord_basis = str(p.get("chord_basis") or "measured")
        state.e_section_wrap = str(p.get("section_wrap") or "cylinder")  # old saves are stamped planar
        state.e_hub_radius = float(p.get("hub_radius", 21.5))
        state.e_tip_radius = float(p.get("tip_radius", 56.5))
        state.e_hub_height = float(p.get("hub_height", 0.0))
        state.e_blade_hub_z = float(p.get("blade_hub_z", p.get("blade_hub_z_mm", 0.0)) or 0.0)
        state.e_blade_z = float(p.get("blade_z", p.get("blade_z_mm", 0.0)) or 0.0)
        state.e_hub_profile = str(p.get("hub_profile", "cylinder"))
        state.e_hub_nose = float(p.get("hub_nose", 0.0))
        state.e_thick_root = float(p.get("thickness_root", 0.10))
        state.e_thick_mid = float(p.get("thickness_mid", 0.08))
        state.e_thick_tip = float(p.get("thickness_tip", 0.06))
        cr = float(p.get("chord_root", state.e_chord_root or 34.0))
        cm = float(p.get("chord_mid", state.e_chord_mid or 44.0))
        ct = float(p.get("chord_tip", state.e_chord_tip or 38.0))
        # Absolute wall (mm) at each station — uniform mode means equal mm, not equal t/c.
        ar = state.e_thick_root * cr
        am = state.e_thick_mid * cm
        at = state.e_thick_tip * ct
        mode = str(p.get("thick_mode") or "").strip().lower()
        if mode in ("uniform", "tapered"):
            state.e_thick_mode = mode
        else:
            state.e_thick_mode = (
                "uniform"
                if abs(ar - am) < UNIFORM_WALL_TOL_MM and abs(am - at) < UNIFORM_WALL_TOL_MM
                else "tapered"
            )
        if p.get("thick_mm") is not None:
            try:
                state.e_thick_mm = round(float(p["thick_mm"]), 2)
            except Exception:  # noqa: BLE001
                state.e_thick_mm = round((ar + am + at) / 3.0, 2)
        else:
            state.e_thick_mm = round((ar + am + at) / 3.0, 2)
        # Refresh mm readout after load (Uniform preferred when walls already match).
        if state.e_thick_mode == "uniform":
            th_r, th_m, th_t = uniform_thickness_tc(
                float(state.e_thick_mm), cr, cm, ct,
            )
            state.e_thick_root = round(th_r, 4)
            state.e_thick_mid = round(th_m, 4)
            state.e_thick_tip = round(th_t, 4)
            state.thick_wall_readout = (
                f"Wall ≈ {float(state.e_thick_mm):.2f} mm at root/mid/tip "
                f"(t/c {th_r:.3f} / {th_m:.3f} / {th_t:.3f})"
            )
        else:
            state.thick_wall_readout = (
                f"Wall ≈ {ar:.2f} / {am:.2f} / {at:.2f} mm root/mid/tip"
            )
        state.e_le_thick = float(p.get("le_thick_scale", 1.0))
        state.e_te_thick = float(p.get("te_thick_scale", 1.0))
        state.e_te_face_root = float(p.get("te_face_root", 1.0) if p.get("te_face_root") is not None else 1.0)
        state.e_te_face_mid = float(p.get("te_face_mid", 1.0) if p.get("te_face_mid") is not None else 1.0)
        state.e_te_face_tip = float(p.get("te_face_tip", 1.0) if p.get("te_face_tip") is not None else 1.0)
        state.e_le_face_root = float(p.get("le_face_root", 1.0) if p.get("le_face_root") is not None else 1.0)
        state.e_le_face_mid = float(p.get("le_face_mid", 1.0) if p.get("le_face_mid") is not None else 1.0)
        state.e_le_face_tip = float(p.get("le_face_tip", 1.0) if p.get("le_face_tip") is not None else 1.0)
        state.e_root_embed = float(p.get("root_embed", 2.0) if p.get("root_embed") is not None else 2.0)
        _sf = str(p.get("section_family", "naca") or "naca").lower().strip()
        state.e_section_family = _sf if _sf in ("naca", "plate") else "naca"
        state.e_camber_pos = float(p.get("camber_pos", 0.4))
        state.e_spacing = float(p.get("spacing_spread", 0.0))
        state.e_tub_amp = float(p.get("tubercle_amp", feat.tubercle_amp))
        state.e_tub_waves = int(p.get("tubercle_waves", feat.tubercle_waves))
        state.e_ser_amp = float(p.get("serration_amp", feat.serration_amp))
        state.e_ser_waves = int(p.get("serration_waves", feat.serration_waves))
        state.e_dim_amp = float(p.get("dimple_amp", feat.dimple_amp))
        state.e_dim_rows = int(p.get("dimple_rows", feat.dimple_rows))
        state.e_dim_cols = int(p.get("dimple_cols", feat.dimple_cols))

    def edit_flat() -> dict:
        shroud = normalize_shroud_thick_mm(state.e_shroud_thick)
        if float(state.e_shroud_thick or 0.0) != shroud:
            state.e_shroud_thick = shroud
        if str(getattr(state, "e_thick_mode", "tapered")) == "uniform":
            th_r, th_m, th_t = uniform_thickness_tc(
                float(getattr(state, "e_thick_mm", 2.0) or 2.0),
                float(state.e_chord_root),
                float(state.e_chord_mid),
                float(state.e_chord_tip),
            )
        else:
            th_r = float(state.e_thick_root)
            th_m = float(state.e_thick_mid)
            th_t = float(state.e_thick_tip)
        return dict(
            n_blades=int(state.e_n_blades),
            stagger_root=state.e_stagger_root,
            stagger_mid=state.e_stagger_mid,
            stagger_tip=state.e_stagger_tip,
            chord_root=state.e_chord_root,
            chord_mid=state.e_chord_mid,
            chord_tip=state.e_chord_tip,
            sweep_mid=state.e_sweep_mid,
            sweep_tip=state.e_sweep_tip,
            camber_root=float(state.e_camber_root),
            camber_mid=float(state.e_camber_mid),
            camber_tip=float(state.e_camber_tip),
            max_camber=float(state.e_camber_mid),
            camber_pos=state.e_camber_pos,
            lean_mid=state.e_lean_mid,
            lean_tip=state.e_lean_tip,
            le_sweep_mid=state.e_le_mid,
            le_sweep_tip=state.e_le_tip,
            le_skew_mid=float(getattr(state, "e_le_skew_mid", 0.0) or 0.0),
            le_skew_tip=float(getattr(state, "e_le_skew_tip", 0.0) or 0.0),
            skew_mid=state.e_skew_mid,
            skew_tip=state.e_skew_tip,
            span_interp=("pchip" if bool(state.e_smooth_span) else "linear"),
            winglet_span=state.e_winglet_span,
            winglet_sweep=state.e_winglet_sweep,
            winglet_lean=state.e_winglet_lean,
            shroud_thick_mm=shroud,
            shroud_height_frac=min(max(float(state.e_shroud_height or 0.0), 0.0), 1.0),
            tip_round=state.e_tip_round,
            tip_round_start=state.e_tip_start,
            cylindrical_tip=bool(state.e_cylindrical_tip),
            chord_basis=str(getattr(state, "e_chord_basis", "measured") or "measured"),
            section_wrap=str(getattr(state, "e_section_wrap", "cylinder") or "cylinder"),
            notched_tips=bool(getattr(state, "e_tip_notched", False)),
            tip_notch_count=(3 if bool(getattr(state, "e_tip_notched", False)) else 0),
            tip_notch_depth_mm=(
                float(getattr(state, "e_tip_notch_depth", 1.5) or 1.5)
                if bool(getattr(state, "e_tip_notched", False))
                else 0.0
            ),
            hub_radius=state.e_hub_radius,
            tip_radius=state.e_tip_radius,
            hub_height=state.e_hub_height,
            blade_hub_z=float(getattr(state, "e_blade_hub_z", 0.0) or 0.0),
            blade_z=float(getattr(state, "e_blade_z", 0.0) or 0.0),
            hub_profile=state.e_hub_profile,
            hub_nose=state.e_hub_nose,
            thickness_root=th_r,
            thickness_mid=th_m,
            thickness_tip=th_t,
            thick_mode=str(getattr(state, "e_thick_mode", "tapered") or "tapered"),
            thick_mm=float(getattr(state, "e_thick_mm", 2.0) or 2.0),
            le_thick_scale=float(state.e_le_thick),
            te_thick_scale=float(state.e_te_thick),
            te_face_root=float(getattr(state, "e_te_face_root", 1.0)),
            te_face_mid=float(getattr(state, "e_te_face_mid", 1.0)),
            te_face_tip=float(getattr(state, "e_te_face_tip", 1.0)),
            le_face_root=float(getattr(state, "e_le_face_root", 1.0)),
            le_face_mid=float(getattr(state, "e_le_face_mid", 1.0)),
            le_face_tip=float(getattr(state, "e_le_face_tip", 1.0)),
            root_embed=float(getattr(state, "e_root_embed", 2.0)),
            section_family=str(state.e_section_family or "naca"),
            spacing_spread=state.e_spacing,
            spacing_seed=0,
            **(
                {"blade_angles_deg": list(angles_payload[0])}
                if (
                    angles_payload[0] is not None
                    and float(state.e_spacing or 0.0) <= 0.0
                    and len(angles_payload[0]) == int(state.e_n_blades)
                )
                else {}
            ),
            **(station_payload[0] or {}),
        )

    def _apply_editor_flat(flat: dict) -> None:
        # A complete design flat replaces the recipe; a partial update (no slot keys) keeps it.
        if FLAT_STATIONS in flat or ("chord_root" in flat and "stagger_mid" in flat):
            _set_station_payload(flat)
        mapping = {
            "n_blades": ("e_n_blades", int),
            "stagger_root": ("e_stagger_root", float),
            "stagger_mid": ("e_stagger_mid", float),
            "stagger_tip": ("e_stagger_tip", float),
            "chord_root": ("e_chord_root", float),
            "chord_mid": ("e_chord_mid", float),
            "chord_tip": ("e_chord_tip", float),
            "sweep_mid": ("e_sweep_mid", float),
            "sweep_tip": ("e_sweep_tip", float),
            "camber_root": ("e_camber_root", float),
            "camber_mid": ("e_camber_mid", float),
            "camber_tip": ("e_camber_tip", float),
            "max_camber": ("e_camber_mid", float),
            "camber_pos": ("e_camber_pos", float),
            "lean_mid": ("e_lean_mid", float),
            "lean_tip": ("e_lean_tip", float),
            "le_sweep_mid": ("e_le_mid", float),
            "le_sweep_tip": ("e_le_tip", float),
            "le_skew_mid": ("e_le_skew_mid", float),
            "le_skew_tip": ("e_le_skew_tip", float),
            "skew_mid": ("e_skew_mid", float),
            "skew_tip": ("e_skew_tip", float),
            "winglet_span": ("e_winglet_span", float),
            "winglet_sweep": ("e_winglet_sweep", float),
            "winglet_lean": ("e_winglet_lean", float),
            "shroud_thick_mm": ("e_shroud_thick", float),
            "shroud_height_frac": ("e_shroud_height", float),
            "tip_round": ("e_tip_round", float),
            "tip_round_start": ("e_tip_start", float),
            "tip_notch_depth_mm": ("e_tip_notch_depth", float),
            "hub_radius": ("e_hub_radius", float),
            "tip_radius": ("e_tip_radius", float),
            "hub_height": ("e_hub_height", float),
            "blade_hub_z": ("e_blade_hub_z", float),
            "blade_z": ("e_blade_z", float),
            "hub_profile": ("e_hub_profile", str),
            "hub_nose": ("e_hub_nose", float),
            "thickness_root": ("e_thick_root", float),
            "thickness_mid": ("e_thick_mid", float),
            "thickness_tip": ("e_thick_tip", float),
            "thick_mm": ("e_thick_mm", float),
            "le_thick_scale": ("e_le_thick", float),
            "te_thick_scale": ("e_te_thick", float),
            "te_face_root": ("e_te_face_root", float),
            "te_face_mid": ("e_te_face_mid", float),
            "te_face_tip": ("e_te_face_tip", float),
            "le_face_root": ("e_le_face_root", float),
            "le_face_mid": ("e_le_face_mid", float),
            "le_face_tip": ("e_le_face_tip", float),
            "root_embed": ("e_root_embed", float),
            "section_family": ("e_section_family", str),
            "spacing_spread": ("e_spacing", float),
        }
        for k, (sv, cast) in mapping.items():
            if k not in flat:
                continue
            v = flat.get(k)
            if v is None:
                continue
            try:
                setattr(state, sv, cast(v))
            except Exception:  # noqa: BLE001, S112
                continue
        if "thick_mode" in flat:
            mode = str(flat.get("thick_mode") or "").strip().lower()
            if mode in ("uniform", "tapered"):
                state.e_thick_mode = mode
        state.e_camber = float(getattr(state, "e_camber_mid", getattr(state, "e_camber", 0.05)))
        _sf = str(getattr(state, "e_section_family", "naca") or "naca").lower().strip()
        state.e_section_family = _sf if _sf in ("naca", "plate") else "naca"
        if "span_interp" in flat:
            state.e_smooth_span = str(flat.get("span_interp") or "linear").lower() == "pchip"
        if "cylindrical_tip" in flat:
            _ct = flat.get("cylindrical_tip")
            if isinstance(_ct, str):
                state.e_cylindrical_tip = _ct.strip().lower() not in (
                    "0", "false", "no", "off", "",
                )
            else:
                state.e_cylindrical_tip = bool(_ct) if _ct is not None else True
        if flat.get("chord_basis"):
            state.e_chord_basis = str(flat["chord_basis"])
        state.e_section_wrap = str(flat.get("section_wrap") or "cylinder")
        state.e_tip_notched = bool(
            int(flat.get("tip_notch_count", 0) or 0) > 0
            or flat.get("notched_tips")
            or float(flat.get("tip_notch_depth_mm", 0.0) or 0.0) > 0.0
        )
        if "tip_notch_depth_mm" in flat and float(flat.get("tip_notch_depth_mm") or 0) > 0:
            state.e_tip_notch_depth = float(flat["tip_notch_depth_mm"])

    def on_fit_envelope():
        if _editor_busy():
            return
        spec = session.active_spec()
        extra = intake_extra_mm(
            enabled=bool(getattr(state, "intake_overbuild", False)),
            extra_mm=float(getattr(state, "intake_overbuild_mm", 10.0) or 0.0),
        )
        max_d = effective_depth_max(spec, intake_extra=extra)
        res = fit_envelope(
            edit_flat(), spec, features=edit_features(), max_depth_mm=max_d,
        )
        _apply_editor_flat(res.flat)
        session._hub_fit_readout()
        session._tip_fit_readout()
        session._depth_fit_readout()
        state.edited_stale = True
        state.preview_msg = preview_changes(res.changes)
        state.flush()

    def _refresh_intake_slider_maxes(**_):
        extra = intake_extra_mm(
            enabled=bool(getattr(state, "intake_overbuild", False)),
            extra_mm=float(getattr(state, "intake_overbuild_mm", 10.0) or 0.0),
        )
        state.e_blade_hub_z_max = 8.0 + 0.5 * extra
        state.e_hub_height_max = 30.0 + extra
        state.e_hub_nose_max = 15.0 + 0.5 * extra

    state.change("intake_overbuild", "intake_overbuild_mm")(_refresh_intake_slider_maxes)
    _refresh_intake_slider_maxes()

    def _refresh_intake_note(**_):
        """Measured depth vs the stock frame while intake overbuild is on (not a static flag)."""
        extra = intake_extra_mm(
            enabled=bool(getattr(state, "intake_overbuild", False)),
            extra_mm=float(getattr(state, "intake_overbuild_mm", 10.0) or 0.0),
        )
        depth = None
        if extra > 0:
            try:
                depth = impeller_z_extent(session.build_edit_params())
            except Exception:  # noqa: BLE001 — readout only
                depth = None
        nominal = float(get_fan_spec(state.fan_model).depth_mm[1])
        state.intake_note, state.intake_note_warn = intake_overbuild_note(depth, nominal, extra)

    state.change("intake_overbuild", "intake_overbuild_mm", "fan_model", *EDITOR_VARS)(
        _refresh_intake_note)
    _refresh_intake_note()

    def on_scale_to_hub():
        if _editor_busy():
            return
        spec = session.active_spec()
        extra = intake_extra_mm(
            enabled=bool(getattr(state, "intake_overbuild", False)),
            extra_mm=float(getattr(state, "intake_overbuild_mm", 10.0) or 0.0),
        )
        max_d = effective_depth_max(spec, intake_extra=extra)
        res = scale_to_hub(
            edit_flat(), spec, features=edit_features(), max_depth_mm=max_d,
        )
        _apply_editor_flat(res.flat)
        session._hub_fit_readout()
        session._tip_fit_readout()
        session._depth_fit_readout()
        state.edited_stale = True
        state.preview_msg = preview_changes(res.changes)
        state.flush()

    def seed_from_duty():
        """§20.4: Cordier + velocity-triangle magnitudes → editor stagger/camber (signs kept)."""
        if _editor_busy():
            return
        try:
            from fansim.optimize.meanline import (
                DutyPoint,
                format_meanline_seed,
                preserve_sign,
                station_magnitudes,
            )
            from fansim.optimize.meanline import (
                seed_from_duty as _seed,
            )

            duty = DutyPoint(
                cfm=float(state.seed_duty_cfm),
                dp_pa=float(state.seed_duty_pa),
                rpm=float(state.seed_duty_rpm),
            )
            vortex = str(getattr(state, "seed_duty_vortex", "free") or "free")
            seed = _seed(
                duty,
                hub_radius_mm=float(state.e_hub_radius),
                tip_radius_mm=float(state.e_tip_radius),
                n_blades=int(state.e_n_blades),
                chord_root_mm=float(state.e_chord_root),
                chord_mid_mm=float(state.e_chord_mid),
                chord_tip_mm=float(state.e_chord_tip),
                vortex=vortex,
            )
            mags = station_magnitudes(seed)
            state.e_stagger_root = round(
                preserve_sign(float(state.e_stagger_root), mags["stagger_root"]), 1
            )
            state.e_stagger_mid = round(
                preserve_sign(float(state.e_stagger_mid), mags["stagger_mid"]), 1
            )
            state.e_stagger_tip = round(
                preserve_sign(float(state.e_stagger_tip), mags["stagger_tip"]), 1
            )
            state.e_camber_root = round(
                preserve_sign(float(state.e_camber_root), mags["camber_root"]), 3
            )
            state.e_camber_mid = round(
                preserve_sign(float(state.e_camber_mid), mags["camber_mid"]), 3
            )
            state.e_camber_tip = round(
                preserve_sign(float(state.e_camber_tip), mags["camber_tip"]), 3
            )
            state.e_camber = state.e_camber_mid
            state.edited_stale = True
            state.seed_duty_msg = "\n".join(format_meanline_seed(seed))
            state.preview_msg = (
                "Seeded stagger/camber magnitudes from duty (§20.4; signs/handedness kept). "
                "Press Preview."
            )
        except Exception as exc:  # noqa: BLE001
            state.seed_duty_msg = f"⚠ Seed from duty failed: {type(exc).__name__}: {exc}"
        state.flush()

    def edit_features() -> Features:
        tw = int(state.e_tub_waves) or (6 if state.e_tub_amp > 0 else 0)
        sw = int(state.e_ser_waves) or (8 if state.e_ser_amp > 0 else 0)
        dr = int(state.e_dim_rows) or (5 if state.e_dim_amp > 0 else 0)
        dc = int(state.e_dim_cols) or (5 if state.e_dim_amp > 0 else 0)
        return Features(
            tubercle_amp=state.e_tub_amp,
            tubercle_waves=tw,
            serration_amp=state.e_ser_amp,
            serration_waves=sw,
            dimple_amp=state.e_dim_amp,
            dimple_rows=dr,
            dimple_cols=dc,
        )

    def randomize_features():
        if _editor_busy():
            return
        on = {k: random.random() < 0.6 for k in ("tub", "ser", "dim")}
        if not any(on.values()):
            on[random.choice(("tub", "ser", "dim"))] = True
        state.e_tub_amp = round(random.uniform(0.02, 0.10), 3) if on["tub"] else 0.0
        state.e_tub_waves = random.randint(3, 8) if on["tub"] else 0
        state.e_ser_amp = round(random.uniform(0.015, 0.06), 3) if on["ser"] else 0.0
        state.e_ser_waves = random.randint(4, 12) if on["ser"] else 0
        state.e_dim_amp = round(random.uniform(0.10, 0.35), 2) if on["dim"] else 0.0
        state.e_dim_rows = random.randint(2, 6) if on["dim"] else 0
        state.e_dim_cols = random.randint(2, 6) if on["dim"] else 0
        active = ", ".join(k for k, v in on.items() if v)
        state.preview_msg = f"🎲 Randomized features ({active}). Press Preview to see it."
        state.flush()

    def randomize_geometry():
        import random as _r

        if _editor_busy():
            return
        state.library_parent_id = ""
        state.library_place_op = ""
        state.library_leftover = ""
        state.e_n_blades = _r.randint(5, 11)
        state.e_stagger_root = round(_r.uniform(18, 48), 1)
        state.e_stagger_mid = round(_r.uniform(18, 48), 1)
        state.e_stagger_tip = round(_r.uniform(16, 40), 1)
        state.e_chord_root = round(_r.uniform(16, 40), 1)
        state.e_chord_mid = round(_r.uniform(18, 50), 1)
        state.e_chord_tip = round(_r.uniform(20, 60), 1)
        state.e_chord_basis = "measured"  # freshly sampled chords are measured targets
        state.e_section_wrap = "cylinder"
        state.e_sweep_mid = round(_r.uniform(-8, 16), 1)
        state.e_sweep_tip = round(_r.uniform(-4, 20), 1)
        state.e_camber_root = round(_r.uniform(0.0, 0.06), 3)
        state.e_camber_mid = round(_r.uniform(0.0, 0.06), 3)
        state.e_camber_tip = round(_r.uniform(0.0, 0.06), 3)
        state.e_camber = state.e_camber_mid
        state.e_camber_pos = round(_r.uniform(0.3, 0.5), 2)
        state.e_lean_mid = round(_r.uniform(0, 25), 1)
        state.e_lean_tip = round(_r.uniform(0, 45), 1)
        state.e_le_mid = round(_r.uniform(-8, 8), 1)
        state.e_le_tip = round(_r.uniform(-8, 8), 1)
        state.e_le_skew_mid = round(_r.uniform(0, 6), 1)
        state.e_le_skew_tip = round(_r.uniform(0, 10), 1)
        state.e_skew_mid = round(_r.uniform(-4, 4), 1)
        state.e_skew_tip = round(_r.uniform(-4, 4), 1)
        wl = _r.random() < 0.4
        state.e_winglet_span = round(_r.uniform(0.75, 0.9), 2)
        state.e_winglet_sweep = round(_r.uniform(4, 12), 1) if wl else 0.0
        state.e_winglet_lean = round(_r.uniform(0, 20), 1) if wl else 0.0
        tipr = _r.random() < 0.5
        state.e_tip_round = round(_r.uniform(0.3, 0.9), 2) if tipr else 0.0
        state.e_tip_start = round(_r.uniform(0.7, 0.88), 2)
        state.e_hub_radius = round(_r.uniform(17, 28), 1)
        state.e_tip_radius = round(_r.uniform(48, 58), 1)
        state.e_thick_mode = "uniform"
        state.e_thick_mm = round(_r.uniform(1.2, 2.4), 1)
        th_r, th_m, th_t = uniform_thickness_tc(
            state.e_thick_mm, state.e_chord_root, state.e_chord_mid, state.e_chord_tip,
        )
        state.e_thick_root = round(th_r, 3)
        state.e_thick_mid = round(th_m, 3)
        state.e_thick_tip = round(th_t, 3)
        state.e_hub_profile = _r.choice(["cylinder", "cylinder", "cone", "dome"])
        state.e_hub_nose = (
            round(_r.uniform(3, 12), 1) if state.e_hub_profile != "cylinder" else 0.0
        )
        # Section shaping (previously left untouched — kept whatever was loaded).
        state.e_section_family = _r.choice(["naca", "naca", "plate"])
        state.e_le_thick = round(_r.uniform(0.6, 1.6), 2)
        state.e_te_thick = round(_r.uniform(0.6, 1.6), 2)
        state.e_te_face_root = round(_r.uniform(0.3, 1.0), 2)
        state.e_te_face_mid = round(_r.uniform(0.3, 1.0), 2)
        state.e_te_face_tip = round(_r.uniform(0.3, 1.0), 2)
        state.e_le_face_root = round(_r.uniform(0.3, 1.0), 2)
        state.e_le_face_mid = round(_r.uniform(0.3, 1.0), 2)
        state.e_le_face_tip = round(_r.uniform(0.3, 1.0), 2)
        state.e_smooth_span = _r.random() < 0.5
        state.e_cylindrical_tip = _r.random() < 0.65
        # Tip TE notches (on/off feature + its depth; depth stays at the 1.5 mm default when off).
        notched = _r.random() < 0.4
        state.e_tip_notched = notched
        state.e_tip_notch_depth = round(_r.uniform(0.8, 2.5), 1) if notched else 1.5
        # Tip shroud ring (off most of the time). Thickness snaps to the UI's 0.8 mm wall steps;
        # a full ring auto-disables the winglet downstream in blade_from_flat (§7.5).
        shroud = _r.random() < 0.3
        state.e_shroud_thick = _r.choice([0.8, 1.6]) if shroud else 0.0
        state.e_shroud_height = round(_r.uniform(0.3, 1.0), 1) if shroud else 1.0
        # Hub placement (0 hub height = auto sizing; blade_hub_z is clamped to fit by the builder,
        # so give it real room roughly half the time by setting an explicit taller hub).
        if _r.random() < 0.5:
            state.e_hub_height = round(_r.uniform(6, 16), 1)
            state.e_blade_hub_z = round(_r.uniform(-5, 5), 1)
        else:
            state.e_hub_height = 0.0
            state.e_blade_hub_z = round(_r.uniform(-4, 4), 1)
        # Uneven blade spacing (tonal-noise DOF; search-space band is 0.0–0.6).
        state.e_spacing = round(_r.uniform(0.0, 0.5), 2)
        state.preview_msg = (
            "🎲 Randomized geometry. Press Preview to see it (may be out-of-spec)."
        )
        state.flush()

    def build_edit_params():
        return blade_from_flat(edit_flat(), edit_features())

    def _feat_dict() -> dict:
        f = edit_features()
        return {
            "tubercle_amp": f.tubercle_amp,
            "tubercle_waves": f.tubercle_waves,
            "serration_amp": f.serration_amp,
            "serration_waves": f.serration_waves,
            "dimple_amp": f.dimple_amp,
            "dimple_rows": f.dimple_rows,
            "dimple_cols": f.dimple_cols,
        }

    def _editor_sig() -> dict:
        """Normalized signature of the current editor state (geometry + features)."""
        s = {**edit_flat(), **_feat_dict()}
        return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in s.items()}

    def _set_baseline():
        """Mark the current editor state as the assessed baseline (not stale)."""
        sel_sig[0] = _editor_sig()
        state.edited_stale = False
        state.stale_msg = ""
        state.export_msg = ""        # a "Saved …stl" line belongs to the previous design (§23.20)
        state.export_download = ""

    def _recompute_stale(**_):
        session._hub_fit_readout()
        session._tip_fit_readout()
        session._depth_fit_readout()
        if sel_sig[0] is None:
            return
        stale = _editor_sig() != sel_sig[0]
        if stale and not state.export_busy:
            state.export_msg = ""    # edited (e.g. Randomize): the last export no longer matches (§23.20)
            state.export_download = ""
        state.edited_stale = stale
        state.stale_msg = (
            "⚠ Edited since assessment — the shown CFM/efficiency are for the "
            "un-edited design. Press Assess to evaluate your changes."
            if stale
            else ""
        )

    state.change(*EDITOR_VARS)(_recompute_stale)

    @state.change("e_thick_mode")
    def _on_thick_mode(e_thick_mode=None, **_):
        mode = str(e_thick_mode if e_thick_mode is not None else getattr(state, "e_thick_mode", "tapered"))
        if mode == "uniform":
            # Prefer the Blade-thickness mm control; fall back to root wall if unset.
            mm = float(getattr(state, "e_thick_mm", 0.0) or 0.0)
            if mm < 0.8:
                mm = float(state.e_thick_root) * float(state.e_chord_root)
            state.e_thick_mm = round(max(mm, 0.8), 2)
            th_r, th_m, th_t = uniform_thickness_tc(
                state.e_thick_mm,
                float(state.e_chord_root),
                float(state.e_chord_mid),
                float(state.e_chord_tip),
            )
            state.e_thick_root = round(th_r, 4)
            state.e_thick_mid = round(th_m, 4)
            state.e_thick_tip = round(th_t, 4)
            state.thick_wall_readout = (
                f"Wall ≈ {state.e_thick_mm:.2f} mm at root/mid/tip "
                f"(t/c {th_r:.3f} / {th_m:.3f} / {th_t:.3f})"
            )
        else:
            # Keep the station t/c as they are. They were overwritten with UNIFORM-wall values here,
            # and loading a design fires this handler after _init_editor: the Stock Reference came
            # up with 2.36/2.36/2.36 mm walls instead of its tapered recipe and showed "Edited since
            # assessment" (roadmap §23.15). A manual Uniform -> Tapered switch needs no re-seed:
            # _sync_uniform_tc already keeps t/c equal to the uniform wall while Uniform is active.
            ar = float(state.e_thick_root) * float(state.e_chord_root)
            am = float(state.e_thick_mid) * float(state.e_chord_mid)
            at = float(state.e_thick_tip) * float(state.e_chord_tip)
            state.thick_wall_readout = (
                f"Wall ≈ {ar:.2f} / {am:.2f} / {at:.2f} mm root/mid/tip "
                f"(t/c sliders — tip was historically too thin at 3%)"
            )

    @state.change("e_thick_mm", "e_chord_root", "e_chord_mid", "e_chord_tip")
    def _sync_uniform_tc(**_):
        """Keep station t/c aligned with Blade thickness (mm) while Uniform is active."""
        if str(getattr(state, "e_thick_mode", "tapered") or "tapered") != "uniform":
            return
        mm = float(getattr(state, "e_thick_mm", 2.0) or 2.0)
        th_r, th_m, th_t = uniform_thickness_tc(
            mm,
            float(state.e_chord_root),
            float(state.e_chord_mid),
            float(state.e_chord_tip),
        )
        state.e_thick_root = round(th_r, 4)
        state.e_thick_mid = round(th_m, 4)
        state.e_thick_tip = round(th_t, 4)
        state.thick_wall_readout = (
            f"Wall ≈ {mm:.2f} mm at root/mid/tip "
            f"(t/c {th_r:.3f} / {th_m:.3f} / {th_t:.3f})"
        )

    @state.change("e_thick_root", "e_thick_mid", "e_thick_tip", "e_thick_mode")
    def _sync_tapered_wall_readout(**_):
        if str(getattr(state, "e_thick_mode", "tapered") or "tapered") == "uniform":
            return
        ar = float(state.e_thick_root) * float(state.e_chord_root)
        am = float(state.e_thick_mid) * float(state.e_chord_mid)
        at = float(state.e_thick_tip) * float(state.e_chord_tip)
        state.thick_wall_readout = (
            f"Wall ≈ {ar:.2f} / {am:.2f} / {at:.2f} mm root/mid/tip "
            f"(t/c sliders — tip was historically too thin at 3%)"
        )

    session._init_editor = _init_editor
    session.edit_flat = edit_flat
    session._apply_editor_flat = _apply_editor_flat
    session.on_fit_envelope = on_fit_envelope
    session.on_scale_to_hub = on_scale_to_hub
    session.seed_from_duty = seed_from_duty
    session.edit_features = edit_features
    session.randomize_features = randomize_features
    session.randomize_geometry = randomize_geometry
    session.build_edit_params = build_edit_params
    session._feat_dict = _feat_dict
    session._editor_sig = _editor_sig
    session._set_baseline = _set_baseline
    session._recompute_stale = _recompute_stale
