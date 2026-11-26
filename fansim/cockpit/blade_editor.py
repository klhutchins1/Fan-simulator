"""Shared BladeParams Design editor helpers (roadmap §14.2).

Maps a state prefix (``p_``, ``cror_f_``, ``cror_r_``) to the shared flat vocabulary
used by Prop / CROR Design panels. Does not own Fan ``e_*`` names.
"""

from __future__ import annotations

from typing import Any, Callable

from fansim.cockpit.blade_copy import BLADE_DESC

# Flat keys that are shared across BladeParams-based Design editors.
BLADE_SHAPE_KEYS = (
    "thickness_root", "thickness_mid", "thickness_tip",
    "camber_root", "camber_mid", "camber_tip",
    "camber_pos",
    "sweep_mid", "sweep_tip",
    "lean_mid", "lean_tip",
    "le_sweep_mid", "le_sweep_tip",
    "le_skew_mid", "le_skew_tip",
    "tip_round", "tip_round_start",
    "cylindrical_tip",
    "thick_mode", "thick_mm",
)

_DEFAULTS: dict[str, Any] = {
    "thickness_root": 0.09, "thickness_mid": 0.06, "thickness_tip": 0.04,
    "camber_root": 0.04, "camber_mid": 0.04, "camber_tip": 0.04,
    "camber_pos": 0.4,
    "sweep_mid": 0.0, "sweep_tip": 3.0,
    "lean_mid": 0.0, "lean_tip": 0.0,
    "le_sweep_mid": 0.0, "le_sweep_tip": 0.0,
    "le_skew_mid": 0.0, "le_skew_tip": 0.0,
    "tip_round": 0.0, "tip_round_start": 0.80,
    "cylindrical_tip": True,
    "thick_mode": "tapered", "thick_mm": 1.5,
}


def state_key(prefix: str, flat_key: str) -> str:
    return f"{prefix}{flat_key}"


def init_shape_state(state, prefix: str, flat: dict | None = None) -> None:
    """Set ``state.{prefix}{key}`` from flat / defaults."""
    flat = flat or {}
    for key in BLADE_SHAPE_KEYS:
        sk = state_key(prefix, key)
        if key == "cylindrical_tip":
            raw = flat.get(key, _DEFAULTS[key])
            if isinstance(raw, str):
                setattr(state, sk, raw.strip().lower() not in ("0", "false", "no", "off", ""))
            else:
                setattr(state, sk, bool(raw) if raw is not None else True)
        elif key == "thick_mode":
            mode = str(flat.get(key, _DEFAULTS[key]) or "tapered").lower()
            setattr(state, sk, mode if mode in ("uniform", "tapered") else "tapered")
        else:
            setattr(state, sk, float(flat.get(key, _DEFAULTS[key])))


def shape_flat_from_state(state, prefix: str) -> dict[str, Any]:
    """Collect shared shape keys from state into an unprefixed flat dict."""
    out: dict[str, Any] = {}
    for key in BLADE_SHAPE_KEYS:
        sk = state_key(prefix, key)
        val = getattr(state, sk, _DEFAULTS[key])
        if key == "cylindrical_tip":
            out[key] = bool(val)
        elif key == "thick_mode":
            mode = str(val or "tapered").lower()
            out[key] = mode if mode in ("uniform", "tapered") else "tapered"
        else:
            out[key] = float(val)
    # Legacy single camber for older consumers.
    out["camber"] = float(out["camber_mid"])
    return out


def apply_shape_flat_to_state(state, prefix: str, flat: dict) -> None:
    """Load a flat (possibly partial / legacy) into prefixed state keys."""
    merged = dict(_DEFAULTS)
    if "camber" in flat and "camber_mid" not in flat:
        c = float(flat["camber"])
        merged["camber_root"] = c
        merged["camber_mid"] = c
        merged["camber_tip"] = c
    for key in BLADE_SHAPE_KEYS:
        if key in flat and flat[key] is not None:
            merged[key] = flat[key]
    init_shape_state(state, prefix, merged)


def render_shape_panels(
    *,
    prefix: str,
    slider: Callable[..., None],
    help_switch: Callable[..., None] | None = None,
    v3=None,
    html=None,
    title_3d: str = "3-D shape — sweep, wrap, sickle",
    title_thick: str = "Thickness & camber",
    title_tip: str = "Tip",
) -> None:
    """Render shared expansion panels. Callers supply their slider helper."""
    if v3 is None or html is None:
        return
    p = prefix

    def _lab(bare: str, label: str) -> str:
        # Prefer bare-key tooltip via model name lookup in tab-local CONTROL maps.
        return label

    with v3.VExpansionPanels(variant="accordion", class_="mb-2"):
        with v3.VExpansionPanel(title=title_thick):
            with v3.VExpansionPanelText():
                slider(
                    _lab("thick_mm", "Uniform wall"),
                    f"{p}thick_mm",
                    0.8,
                    3.0,
                    0.1,
                    unit="mm",
                    disabled=(f"{p}thick_mode !== 'uniform'",),
                )
                html.Div(
                    "Choose Uniform wall above to set thickness in mm, or Tapered to set hub-to-tip wall ratios below.",
                    classes="text-caption text-medium-emphasis mb-1",
                )
                slider(
                    "t/c root",
                    f"{p}thickness_root",
                    0.03,
                    0.14,
                    0.005,
                    unit="t/c",
                    simple_label="Wall ratio root",
                    simple_unit="ratio",
                    disabled=(f"{p}thick_mode === 'uniform'",),
                )
                slider(
                    "t/c mid",
                    f"{p}thickness_mid",
                    0.02,
                    0.12,
                    0.005,
                    unit="t/c",
                    simple_label="Wall ratio mid",
                    simple_unit="ratio",
                    disabled=(f"{p}thick_mode === 'uniform'",),
                )
                slider(
                    "t/c tip",
                    f"{p}thickness_tip",
                    0.02,
                    0.10,
                    0.005,
                    unit="t/c",
                    simple_label="Wall ratio tip",
                    simple_unit="ratio",
                    disabled=(f"{p}thick_mode === 'uniform'",),
                )
                slider("Scoop root", f"{p}camber_root", 0.0, 0.06, 0.005, unit="c/c", simple_unit="0–0.06")
                slider("Scoop mid", f"{p}camber_mid", 0.0, 0.06, 0.005, unit="c/c", simple_unit="0–0.06")
                slider("Scoop tip", f"{p}camber_tip", 0.0, 0.06, 0.005, unit="c/c", simple_unit="0–0.06")
                slider("Scoop pos", f"{p}camber_pos", 0.25, 0.55, 0.01, unit="x/c", simple_unit="front→back")
        with v3.VExpansionPanel(title=title_3d):
            with v3.VExpansionPanelText():
                slider("Sweep mid", f"{p}sweep_mid", -4, 10, 0.5, unit="mm")
                slider("Sweep tip", f"{p}sweep_tip", -2, 14, 0.5, unit="mm")
                slider("LE curve mid", f"{p}le_sweep_mid", -8, 8, 0.5, unit="mm", simple_label="Front edge curve mid")
                slider("LE curve tip", f"{p}le_sweep_tip", -8, 8, 0.5, unit="mm", simple_label="Front edge curve tip")
                slider("Sickle mid", f"{p}le_skew_mid", 0, 10, 0.5, unit="mm", simple_label="Curved front edge mid")
                slider("Sickle tip", f"{p}le_skew_tip", 0, 14, 0.5, unit="mm", simple_label="Curved front edge tip")
                slider("Wrap mid", f"{p}lean_mid", 0, 20, 1, unit="deg")
                slider("Wrap tip", f"{p}lean_tip", 0, 25, 1, unit="deg")
        with v3.VExpansionPanel(title=title_tip):
            with v3.VExpansionPanelText():
                if help_switch is not None:
                    help_switch(
                        f"{p}cylindrical_tip",
                        "Cylindrical tip",
                        help_map={f"{p}cylindrical_tip": BLADE_DESC["cylindrical_tip"]},
                    )
                slider("Tip round", f"{p}tip_round", 0.0, 1.0, 0.05, unit="0–1")
                slider("Tip round start", f"{p}tip_round_start", 0.5, 0.95, 0.02, unit="span")
