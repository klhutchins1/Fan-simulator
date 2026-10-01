"""Cockpit airflow viz bake + mesh LRU (§22.6 / §22.7 / §22.11).

Shared by Fan Assess (warm caches before select) and Fan Design select (lazy core
pack). Heavy views (streamlines / spanwise) stay on-demand.
"""

from __future__ import annotations

import logging
from collections import OrderedDict
from pathlib import Path
from threading import Lock

_log = logging.getLogger(__name__)

# Soft LRU of reconstructed UnstructuredGrids (§22.11). Cap keeps Windows RAM in check.
_MESH_LRU_MAX = 2
_MESH_LRU: OrderedDict[str, object] = OrderedDict()
_MESH_LOCK = Lock()


def clear_mesh_lru() -> None:
    """Drop cached OpenFOAM grids (tests)."""
    with _MESH_LOCK:
        _MESH_LRU.clear()


def _mesh_key(case_dir: Path) -> str:
    from fansim.cfd.glyphs import case_field_fingerprint

    return f"{case_dir.resolve()}::{case_field_fingerprint(case_dir)}"


def get_cached_mesh(case_dir: str | Path) -> object | None:
    """Return a process-cached ``read_case`` grid for this field set, or None."""
    case_dir = Path(case_dir)
    key = _mesh_key(case_dir)
    with _MESH_LOCK:
        mesh = _MESH_LRU.get(key)
        if mesh is not None:
            _MESH_LRU.move_to_end(key)
        return mesh


def put_cached_mesh(case_dir: str | Path, mesh) -> None:
    """Remember a reconstructed grid (LRU, max ``_MESH_LRU_MAX``)."""
    if mesh is None:
        return
    case_dir = Path(case_dir)
    key = _mesh_key(case_dir)
    with _MESH_LOCK:
        _MESH_LRU[key] = mesh
        _MESH_LRU.move_to_end(key)
        while len(_MESH_LRU) > _MESH_LRU_MAX:
            _MESH_LRU.popitem(last=False)


def load_case_mesh(
    case_dir: str | Path,
    *,
    runner_factory=None,
    image_ok=None,
    use_cache: bool = True,
):
    """Reconstruct if needed and ``read_case``, with optional LRU (§22.10 / §22.11)."""
    from fansim.acoustics.case import read_case
    from fansim.cfd.midplane import case_has_flow_fields, ensure_reconstructed

    case_dir = Path(case_dir)
    if use_cache:
        hit = get_cached_mesh(case_dir)
        if hit is not None:
            return hit
    if not case_has_flow_fields(case_dir):
        return None
    if not ensure_reconstructed(case_dir, runner_factory=runner_factory, image_ok=image_ok):
        return None
    mesh = read_case(case_dir)
    if use_cache:
        put_cached_mesh(case_dir, mesh)
    return mesh


def bake_cockpit_viz_core(
    case_dir: str | Path | None,
    *,
    runner_factory=None,
    image_ok=None,
    mesh=None,
    include_uz: bool = True,
) -> dict:
    """Build midplane (+ optional Uz) PNGs and glyph cloud. Fail-soft.

    Intended to run at the end of Assess (§22.6) so the first Results click is warm.
    Does **not** build streamlines / spanwise (lazy via §22.7).
    """
    out = {
        "available": False,
        "midplane": False,
        "uz": False,
        "glyphs": False,
        "caption": "Airflow not available for this design",
    }
    if case_dir is None:
        return out
    case_dir = Path(case_dir)
    if not case_dir.is_dir():
        return out

    try:
        if mesh is None:
            mesh = load_case_mesh(
                case_dir, runner_factory=runner_factory, image_ok=image_ok,
            )
        if mesh is None:
            return out

        from fansim.cfd.glyphs import ensure_velocity_glyphs
        from fansim.cfd.midplane import ensure_axial_uz_artifact, ensure_midplane_artifacts

        mid = ensure_midplane_artifacts(
            case_dir, mesh=mesh, runner_factory=runner_factory, image_ok=image_ok,
        )
        out["midplane"] = bool(mid.available)
        if include_uz:
            uz = ensure_axial_uz_artifact(
                case_dir, mesh=mesh, runner_factory=runner_factory, image_ok=image_ok,
            )
            out["uz"] = bool(uz.available)
        gly = ensure_velocity_glyphs(
            case_dir, mesh=mesh, runner_factory=runner_factory, image_ok=image_ok,
        )
        out["glyphs"] = bool(gly.available)
        out["available"] = out["midplane"] or out["glyphs"]
        if out["available"]:
            out["caption"] = "Core airflow viz ready"
        return out
    except Exception as exc:  # noqa: BLE001 — never break Assess
        _log.debug("bake_cockpit_viz_core %s: %s: %s", case_dir, type(exc).__name__, exc)
        return out


def bake_cockpit_viz_heavy(
    case_dir: str | Path | None,
    *,
    runner_factory=None,
    image_ok=None,
    mesh=None,
) -> dict:
    """Build streamlines + spanwise/b2b (on-demand / idle). Fail-soft."""
    out = {"available": False, "stream": False, "span": False}
    if case_dir is None:
        return out
    case_dir = Path(case_dir)
    if not case_dir.is_dir():
        return out
    try:
        if mesh is None:
            mesh = load_case_mesh(
                case_dir, runner_factory=runner_factory, image_ok=image_ok,
            )
        if mesh is None:
            return out
        from fansim.cfd.midplane import ensure_streamlines_artifact
        from fansim.cfd.spanwise import ensure_spanwise_artifacts

        stream = ensure_streamlines_artifact(
            case_dir, mesh=mesh, runner_factory=runner_factory, image_ok=image_ok,
        )
        span = ensure_spanwise_artifacts(
            case_dir, mesh=mesh, runner_factory=runner_factory, image_ok=image_ok,
        )
        out["stream"] = bool(stream.available)
        out["span"] = bool(span.available)
        out["available"] = out["stream"] or out["span"]
        return out
    except Exception as exc:  # noqa: BLE001
        _log.debug("bake_cockpit_viz_heavy %s: %s: %s", case_dir, type(exc).__name__, exc)
        return out
