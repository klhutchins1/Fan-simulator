"""Fan-tab models binder: fan-model readouts, fit checks, and the model manager (§13.9).

Readouts describe the selected fan model and whether the current editor geometry fits its
frame/hub/depth. The manager saves/deletes user fan models. Cross-domain: fit readouts call
``session.build_edit_params`` (editor); model changes refresh the library/results (core).
"""

from __future__ import annotations

import dataclasses

from fansim.cfd.domain import OPTIMIZER_TIP_GAP_MM
from fansim.cockpit.fan_helpers import _blade_max_dia
from fansim.cockpit.placement import frame_gap_note, impeller_z_extent
from fansim.fan_spec import (
    MotorMount,
    delete_user_fan_model,
    fan_spec_names,
    get_fan_spec,
    is_builtin,
    load_fan_models_dir,
    mount_min_hub_radius,
    save_user_fan_model,
)


def bind(session) -> None:
    state = session.state

    def _fan_model_items() -> list[dict[str, str]]:
        rows = []
        for k in fan_spec_names():
            try:
                spec = get_fan_spec(k)
                title = f"{spec.name} ({k})" if spec.name.lower() != k.lower() else spec.name
            except Exception:  # noqa: BLE001
                title = k
            rows.append({"title": title, "value": k})
        return rows

    def _model_readout():
        state.fan_model_items = _fan_model_items()
        s = get_fan_spec(state.fan_model)
        refs = (
            f" Published {s.ref_cfm:.0f} CFM / {s.ref_static_pa:.0f} Pa / {s.ref_noise_dba:.0f} dBA."
            if s.ref_cfm is not None
            else " (no published reference — exploratory model)."
        )
        tag = " [built-in ref, read-only]" if is_builtin(state.fan_model) else " [user model]"
        wt = f"≤{s.max_weight_g:.0f} g." if s.max_weight_g else ""
        state.model_info = (
            f"{s.name}{tag}: tip ≤{s.tip_dia_mm[1]:.0f} mm, depth ≤{s.depth_mm[1]:.0f} mm, "
            f"hub {s.hub_dia_mm[0]:.0f}-{s.hub_dia_mm[1]:.0f} mm, "
            f"{s.max_shaft_power_w:.2f} W shaft ({s.voltage_v:.0f} V×{s.max_current_a:.2f} A), "
            f"{wt}{refs}"
        )
        pub_simple = (
            f" · published {s.ref_cfm:.0f} CFM" if s.ref_cfm is not None else ""
        )
        state.model_info_simple = (
            f"{s.name} · fits blades up to {s.tip_dia_mm[1]:.0f} mm wide, "
            f"{s.depth_mm[1]:.0f} mm deep{pub_simple}."
        )

    def _hub_fit_readout():
        s = get_fan_spec(state.fan_model)
        need = mount_min_hub_radius(s)
        if need is None:
            state.hub_fit_info = f"{s.name}: no motor mount defined — hub size unconstrained."
            return
        cav = s.motor_mount.cavity_dia_mm
        cur = state.e_hub_radius
        if cur is None:
            state.hub_fit_info = f"Motor hub {cav:.1f} mm → this hub needs radius ≥ {need:.1f} mm."
            return
        cur = float(cur)
        state.hub_fit_info = (
            f"Motor hub {cav:.1f} mm → this hub needs radius ≥ {need:.1f} mm. "
            + (
                f"Current {cur:.1f} mm ✓ fits — cup will carve."
                if cur >= need
                else f"Current {cur:.1f} mm ✗ TOO SMALL, won't fit (raise Hub radius)."
            )
        )

    def _tip_fit_readout():
        s = get_fan_spec(state.fan_model)
        max_dia = s.tip_dia_mm[1]
        floor = float(OPTIMIZER_TIP_GAP_MM)
        if state.e_tip_radius is None:
            state.tip_fit_info = f"Frame ≤ {max_dia:.0f} mm dia (need ≥{floor:.1f} mm tip gap)."
            return
        try:
            dia = _blade_max_dia(session.build_edit_params())
        except Exception:  # noqa: BLE001
            dia = 2.0 * float(state.e_tip_radius)
        gap = max_dia / 2.0 - dia / 2.0
        note = frame_gap_note(dia, s)
        if note:
            state.tip_fit_info = (
                f"Frame ≤ {max_dia:.0f} mm → built tip dia {dia:.1f} mm "
                f"(gap {gap:.2f} mm) ✗ {note} — use Fit envelope."
            )
        elif dia > max_dia:
            state.tip_fit_info = (
                f"Frame ≤ {max_dia:.0f} mm → built tip dia {dia:.1f} mm "
                f"✗ over by {dia - max_dia:.1f} mm — use Fit envelope."
            )
        else:
            state.tip_fit_info = (
                f"Frame ≤ {max_dia:.0f} mm → built tip dia {dia:.1f} mm "
                f"(gap {gap:.2f} mm ≥ {floor:.1f} mm) ✓ fits."
            )

    def _depth_fit_readout():
        s = get_fan_spec(state.fan_model)
        max_d = s.depth_mm[1]
        if state.e_sweep_tip is None:
            state.depth_fit_info = f"Frame ≤ {max_d:.0f} mm deep."
            return
        try:
            d = impeller_z_extent(session.build_edit_params())
        except Exception:  # noqa: BLE001
            state.depth_fit_info = ""
            return
        state.depth_fit_info = (
            f"Frame ≤ {max_d:.0f} mm deep → impeller {d:.1f} mm "
            + (
                "✓ fits."
                if d <= max_d
                else f"✗ over by {d-max_d:.1f} mm — " + (
                    "turn off Allow intake overbuild (Fit & seed), then Fit envelope."
                    if getattr(state, "intake_overbuild", False)
                    else "use Fit envelope, or add Extra-depth leeway.")
            )
        )

    def reload_models():
        load_fan_models_dir()
        state.fan_models = fan_spec_names()
        _model_readout()
        _hub_fit_readout()
        _tip_fit_readout()
        _depth_fit_readout()
        session.refresh_library()
        session.refresh_items()
        session.refresh_figure()
        state.flush()

    def load_model_into_form(**_):
        s = get_fan_spec(state.fan_model)
        state.fm_key = "" if is_builtin(state.fan_model) else state.fan_model
        state.fm_tip_max = float(s.tip_dia_mm[1])
        state.fm_hub_min = float(s.hub_dia_mm[0])
        state.fm_hub_max = float(s.hub_dia_mm[1])
        state.fm_depth_max = float(s.depth_mm[1])
        state.fm_rpm = float(s.rpm)
        m = s.motor_mount
        state.fm_cav_dia = float(m.cavity_dia_mm) if m else 0.0
        state.fm_cav_depth = float(m.cavity_depth_mm) if m else 0.0
        state.fm_hub_h = float(getattr(m, "min_hub_height_mm", 0.0)) if m else 0.0
        state.fm_msg = (
            "Loaded a built-in — Save under a NEW name to make an editable copy."
            if is_builtin(state.fan_model)
            else f"Loaded user model '{state.fan_model}' — edit + Save."
        )
        state.flush()

    def save_model():
        key = (state.fm_key or "").strip().lower().replace(" ", "_")
        if not key:
            state.fm_msg = "⚠ Enter a model name first."
            state.flush()
            return
        base = get_fan_spec(state.fan_model)
        mount = None
        if float(state.fm_cav_dia) > 0:
            mount = MotorMount(
                cavity_dia_mm=float(state.fm_cav_dia),
                cavity_depth_mm=float(state.fm_cav_depth),
                rear_bore_dia_mm=(base.motor_mount.rear_bore_dia_mm if base.motor_mount else 0.0),
                shaft_dia_mm=(base.motor_mount.shaft_dia_mm if base.motor_mount else 0.0),
                min_hub_height_mm=float(state.fm_hub_h),
                grip_count=int(getattr(base.motor_mount, "grip_count", 0) or 0) if base.motor_mount else 0,
                grip_dia_mm=float(getattr(base.motor_mount, "grip_dia_mm", 2.4) or 2.4) if base.motor_mount else 2.4,
                grip_clearance_mm=float(getattr(base.motor_mount, "grip_clearance_mm", 0.35) or 0.35) if base.motor_mount else 0.35,
                grip_protrude_mm=float(getattr(base.motor_mount, "grip_protrude_mm", 0.35) or 0.35) if base.motor_mount else 0.35,
            )
        spec = dataclasses.replace(
            base,
            name=key.replace("_", " ").title(),
            tip_dia_mm=(base.tip_dia_mm[0], float(state.fm_tip_max)),
            hub_dia_mm=(float(state.fm_hub_min), float(state.fm_hub_max)),
            depth_mm=(base.depth_mm[0], float(state.fm_depth_max)),
            rpm=float(state.fm_rpm),
            motor_mount=mount,
            leeway_tip_dia_mm=0.0,
            leeway_depth_mm=0.0,
            leeway_weight_g=0.0,
            over_voltage_v=0.0,
        )
        try:
            path = save_user_fan_model(key, spec)
        except Exception as exc:  # noqa: BLE001
            state.fm_msg = f"⚠ Save failed: {exc}"
            state.flush()
            return
        state.fan_models = fan_spec_names()
        state.fan_model = key
        state.fm_msg = f"✓ Saved user model '{key}' → {path}"
        state.flush()

    def delete_model():
        key = state.fan_model
        try:
            ok = delete_user_fan_model(key)
        except Exception as exc:  # noqa: BLE001
            state.fm_msg = f"⚠ {exc}"
            state.flush()
            return
        state.fan_models = fan_spec_names()
        state.fan_model = "a12x25"
        state.fm_msg = f"{'✓ Deleted' if ok else '⚠ Not found:'} '{key}'."
        state.flush()

    @state.change("fan_model")
    def _on_model(**_):
        _model_readout()
        _hub_fit_readout()
        _tip_fit_readout()
        _depth_fit_readout()
        state.model_is_builtin = is_builtin(state.fan_model)
        session.refresh_library()
        session.refresh_items()
        session.refresh_figure()
        state.flush()

    session._model_readout = _model_readout
    session._hub_fit_readout = _hub_fit_readout
    session._tip_fit_readout = _tip_fit_readout
    session._depth_fit_readout = _depth_fit_readout
    session.reload_models = reload_models
    session.load_model_into_form = load_model_into_form
    session.save_model = save_model
    session.delete_model = delete_model
