"""New/Expert controls must ship with tooltip text (#56); geometry keys need image stems (#57)."""

from __future__ import annotations

import ast
from pathlib import Path

from fansim.cockpit.fan_copy import _CTRL_IMG_DIR, _IMG_URI, CONTROL_DESC

_REPO_ROOT = Path(__file__).resolve().parents[1]

# Controls where UI min=0 means "off / auto", so the min-vs-max illustration renders
# the smallest active value instead of 0. Upper bounds must still match the UI slider.
_ZERO_IS_AUTO_MIN = {
    "e_shroud_height",
    "e_le_thick",
    "e_te_thick",
    "e_tub_waves",
    "e_ser_waves",
    "e_dim_rows",
    "e_dim_cols",
}


def _literal_num(node: ast.AST) -> float | None:
    try:
        val = ast.literal_eval(node)
    except (ValueError, SyntaxError):
        return None
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        return float(val)
    return None


def test_control_image_bounds_match_fan_tab_sliders():
    """UI-35: tooltip image min/max ranges in generate_control_images.py must match fan_tab_ui.py."""
    ui_tree = ast.parse((_REPO_ROOT / "fansim/cockpit/fan_tab_ui.py").read_text(encoding="utf-8"))
    ui_sliders: dict[str, tuple[float, float]] = {}
    for node in ast.walk(ui_tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        name = fn.id if isinstance(fn, ast.Name) else (fn.attr if isinstance(fn, ast.Attribute) else "")
        if name != "_slider" or len(node.args) < 4:
            continue
        if not (isinstance(node.args[1], ast.Constant) and isinstance(node.args[1].value, str)):
            continue
        lo = _literal_num(node.args[2])
        hi = _literal_num(node.args[3])
        if lo is not None and hi is not None:
            ui_sliders[node.args[1].value] = (lo, hi)

    gen_tree = ast.parse(
        (_REPO_ROOT / "scripts/generate_control_images.py").read_text(encoding="utf-8")
    )
    controls_node = next(
        n.value
        for n in gen_tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "CONTROLS" for t in n.targets)
    )
    controls = ast.literal_eval(controls_node)

    mismatches: list[str] = []
    for row in controls:
        model, _label, _key, lo, hi, _mode, *_rest = row
        if model not in ui_sliders or not isinstance(lo, (int, float)) or not isinstance(hi, (int, float)):
            continue
        ui_lo, ui_hi = ui_sliders[model]
        if float(hi) != ui_hi:
            mismatches.append(f"{model}: hi script={hi} != ui={ui_hi}")
        if model not in _ZERO_IS_AUTO_MIN and float(lo) != ui_lo:
            mismatches.append(f"{model}: lo script={lo} != ui={ui_lo}")

    assert not mismatches, "Tooltip range drift (UI-35):\n" + "\n".join(mismatches)


def test_leeway_sliders_have_tooltips():
    for key in ("lee_tip", "lee_depth", "lee_overvolt", "lee_weight"):
        assert key in CONTROL_DESC, key
        assert len(CONTROL_DESC[key].strip()) > 20, key


def test_face_and_blade_z_keys_have_descriptions():
    for key in (
        "e_blade_z",
        "e_le_face_root",
        "e_le_face_mid",
        "e_le_face_tip",
        "e_te_face_root",
        "e_te_face_mid",
        "e_te_face_tip",
    ):
        assert key in CONTROL_DESC
        assert CONTROL_DESC[key].strip()


def test_control_image_dir_has_pngs_for_core_sliders():
    assert _CTRL_IMG_DIR.is_dir()
    assert len(_IMG_URI) >= 40
    assert (_CTRL_IMG_DIR / "e_n_blades.png").is_file()
    for stem in (
        "e_blade_z",
        "e_le_face_root",
        "e_le_face_mid",
        "e_le_face_tip",
        "e_te_face_root",
        "e_te_face_mid",
        "e_te_face_tip",
    ):
        assert (_CTRL_IMG_DIR / f"{stem}.png").is_file(), stem
        assert stem in _IMG_URI, stem
