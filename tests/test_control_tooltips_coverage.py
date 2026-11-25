"""New/Expert controls must ship with tooltip text (#56); geometry keys need image stems (#57)."""

from __future__ import annotations

from pathlib import Path

from fansim.cockpit.fan_copy import CONTROL_DESC, _CTRL_IMG_DIR, _IMG_URI


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
