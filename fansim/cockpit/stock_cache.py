"""Cached parametric Stock preview STL so gold-✕ does not rebuild every click."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Runtime cache for the parametric Stock preview mesh (gold ✕). This is a rebuildable cache,
# NOT tracked reference data — it lives under a gitignored dir so a stock preview (in the app
# or a test) never rewrites anything in git. Tests redirect it to a tmp dir (tests/conftest.py).
# The trusted geometry/CFD golden is the separate validation/reference/a12x25_impeller.stl.
STOCK_CACHE_DIR = ROOT / ".cache" / "stock"


def stock_cache_paths(fan_model: str = "a12x25") -> tuple[Path, Path]:
    key = str(fan_model or "a12x25").strip().lower().replace(" ", "_")
    stl = STOCK_CACHE_DIR / f"{key}_stock_parametric.stl"
    meta = Path(str(stl) + ".meta.json")
    return stl, meta


def stock_fingerprint(flat: dict, *, preview: bool = True) -> str:
    """Stable hash of the geometry knobs that affect the Stock preview mesh."""
    keys = (
        "n_blades", "hub_radius", "tip_radius", "hub_height", "hub_nose", "hub_profile",
        "blade_hub_z",
        "chord_root", "chord_mid", "chord_tip",
        "stagger_root", "stagger_mid", "stagger_tip",
        "sweep_mid", "sweep_tip", "lean_mid", "lean_tip",
        "skew_mid", "skew_tip", "le_sweep_mid", "le_sweep_tip",
        "le_skew_mid", "le_skew_tip", "sickle_mm",
        "max_camber", "camber_root", "camber_mid", "camber_tip", "camber_pos",
        "thickness_root", "thickness_mid", "thickness_tip", "thick_mode", "thick_mm",
        "le_thick_scale", "te_thick_scale",
        "te_face_root", "te_face_mid", "te_face_tip",
        "le_face_root", "le_face_mid", "le_face_tip",
        "section_family", "span_interp",
        "n_span", "n_chord",
        "shroud_thick_mm", "shroud_height_frac",
        "tip_round", "tip_round_start", "cylindrical_tip", "chord_basis", "section_wrap",
        "tip_notch_count", "tip_notch_depth_mm", "notched_tips",
        "root_embed", "spacing_spread", "spacing_seed",
    )
    payload = {k: flat.get(k) for k in keys}
    # 0 and a missing key hash the same, so today's outline and Stock caches stay valid.
    try:
        blade_z = float(flat.get("blade_z", flat.get("blade_z_mm", 0.0)) or 0.0)
    except (TypeError, ValueError):
        blade_z = 0.0
    if blade_z != 0.0:
        payload["blade_z"] = blade_z
    payload["_preview"] = bool(preview)
    # Dense stock preview (full loft) must not hit a coarse screen-loft cache entry.
    payload["_preview_dense"] = True
    # Bump when the builder's geometry changes so stale cached STLs rebuild. 3 = revert the
    # bad +Z motor relocation back to the −Z-cup original (2026-09-17). 4 = airfoil LE now leads
    # (chordwise placement was back-to-front; 2026-09-29). 5 = Stock recipe v2 promoted
    # (section refit to the close-ref STL; 2026-09-29).
    payload["_geom_version"] = 5
    blob = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


def stock_cache_hit(fan_model: str, flat: dict, *, preview: bool = True) -> Path | None:
    stl, meta = stock_cache_paths(fan_model)
    if not stl.is_file() or not meta.is_file():
        return None
    try:
        data = json.loads(meta.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    if data.get("fingerprint") != stock_fingerprint(flat, preview=preview):
        return None
    return stl


def write_stock_cache_meta(fan_model: str, flat: dict, *, preview: bool = True) -> Path:
    stl, meta = stock_cache_paths(fan_model)
    meta.parent.mkdir(parents=True, exist_ok=True)
    meta.write_text(
        json.dumps(
            {
                "fan_model": fan_model,
                "fingerprint": stock_fingerprint(flat, preview=preview),
                "preview": bool(preview),
                "stl": stl.name,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return meta
