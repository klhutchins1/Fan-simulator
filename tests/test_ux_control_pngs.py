"""Issue #100: rendered min/max control preview PNGs for Prop, Mixed, Volute, and CROR."""

from __future__ import annotations

import ast
import base64
import struct
from pathlib import Path

from fansim.cockpit.blade_editor import BLADE_SHAPE_KEYS
from fansim.cockpit.fan_copy import _CTRL_IMG_DIR, _IMG_URI
from fansim.cockpit.fan_widgets import resolve_tooltip

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_REPO_ROOT = Path(__file__).resolve().parents[1]
_COCKPIT_DIR = _REPO_ROOT / "fansim" / "cockpit"

_TAB_SLIDER_SOURCES: dict[str, tuple[str, tuple[str, ...]]] = {
    "p_": ("prop_tab.py", ("p_",)),
    "mf_": ("mixed_tab.py", ()),
    "volute_": ("volute_tab.py", ()),
    "cror_": ("cror_tab.py", ("cror_f_", "cror_r_")),
}


def _slider_models_in_tab(filename: str, shape_prefixes: tuple[str, ...]) -> set[str]:
    """Extract all slider model strings declared in a tab file (+ shared shape panels)."""
    tree = ast.parse((_COCKPIT_DIR / filename).read_text(encoding="utf-8"))
    models: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        name = fn.id if isinstance(fn, ast.Name) else (fn.attr if isinstance(fn, ast.Attribute) else "")
        if name not in ("_slider", "slider", "_shared_slider"):
            continue
        if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant) and isinstance(node.args[1].value, str):
            models.add(node.args[1].value)
        for kw in node.keywords:
            if kw.arg == "model" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                models.add(kw.value.value)
    # Shared shape-panel sliders from blade_editor.render_shape_panels
    for pref in shape_prefixes:
        for bare in BLADE_SHAPE_KEYS:
            if bare not in ("cylindrical_tip", "thick_mode"):
                models.add(f"{pref}{bare}")
    return models


def _png_dimensions(raw: bytes) -> tuple[int, int]:
    assert raw.startswith(_PNG_SIGNATURE), "missing PNG magic signature"
    assert len(raw) >= 24 and raw[12:16] == b"IHDR", "missing PNG IHDR chunk"
    return struct.unpack(">II", raw[16:24])


def test_img_uri_loads_all_four_tab_prefixes():
    for prefix in _TAB_SLIDER_SOURCES:
        keys = sorted(k for k in _IMG_URI if k.startswith(prefix))
        assert len(keys) >= 4, f"expected >= 4 rendered PNGs for {prefix}*, found {keys}"


def test_generated_tab_pngs_match_real_sliders_and_are_valid():
    for prefix, (tab_file, shape_prefixes) in _TAB_SLIDER_SOURCES.items():
        real_sliders = _slider_models_in_tab(tab_file, shape_prefixes)
        pngs = sorted(_CTRL_IMG_DIR.glob(f"{prefix}*.png"))
        assert len(pngs) >= 4, f"expected >= 4 PNG files for {prefix}* in {_CTRL_IMG_DIR}"

        for png_path in pngs:
            model = png_path.stem
            assert model in real_sliders, (
                f"{png_path.name} does not match any slider model in {tab_file}: "
                f"known={sorted(real_sliders)}"
            )
            raw = png_path.read_bytes()
            assert len(raw) > 1000, f"{png_path.name} looks unexpectedly tiny ({len(raw)} bytes)"
            w, h = _png_dimensions(raw)
            assert w >= 200 and h >= 100, f"{png_path.name} dimensions too small: {w}x{h}"

            assert model in _IMG_URI, f"{model} not loaded into _IMG_URI"
            uri = _IMG_URI[model]
            assert uri.startswith("data:image/png;base64,")
            decoded = base64.b64decode(uri.split(",", 1)[1])
            assert decoded == raw


def test_resolve_tooltip_returns_png_uri_for_all_generated_tab_controls():
    for prefix in _TAB_SLIDER_SOURCES:
        keys = sorted(k for k in _IMG_URI if k.startswith(prefix))
        assert keys, f"no loaded PNG keys for {prefix}*"
        for model in keys:
            simple, expert, uri = resolve_tooltip(model)
            assert expert, f"missing expert tooltip text for {model}"
            assert simple, f"missing simple tooltip text for {model}"
            assert uri == _IMG_URI[model], f"resolve_tooltip({model!r}) did not return loaded PNG URI"
            assert uri.startswith("data:image/png;base64,")
