# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Tests for the isolated (subprocess) impeller build used by the cockpit preview."""

import tempfile
from pathlib import Path

import pytest

from fansim.geometry.isolated import build_stl_isolated

SMOOTH = dict(n_blades=7, stagger_root=26, stagger_mid=26, stagger_tip=22,
              chord_root=34, chord_mid=44, chord_tip=38, max_camber=0.05,
              sweep_mid=3, sweep_tip=5, lean_mid=14, lean_tip=26)


def test_isolated_build_succeeds():
    out = Path(tempfile.mkdtemp()) / "iso.stl"
    p = build_stl_isolated(SMOOTH, {}, out, timeout=120)
    assert p.exists() and p.stat().st_size > 0


def test_isolated_build_bad_input_raises_not_crashes():
    # a broken param dict makes the worker exit non-zero; the caller gets a caught RuntimeError,
    # NOT a dead process -- which is the whole point (the cockpit server survives a bad edit).
    out = Path(tempfile.mkdtemp()) / "bad.stl"
    with pytest.raises(RuntimeError):
        build_stl_isolated({"n_blades": 7}, {}, out, timeout=60)
    assert not out.exists()


def test_isolated_build_times_out_gracefully():
    # an unreachably-short timeout must raise TimeoutError (not hang / not crash the caller)
    out = Path(tempfile.mkdtemp()) / "slow.stl"
    with pytest.raises(TimeoutError):
        build_stl_isolated(SMOOTH, {}, out, timeout=0.01)


def test_preview_build_is_fast_and_writes_volume_sidecar():
    # the fast preview path (non-fused) must build even a heavy FEATURED design well within a normal
    # timeout and write an accurate-volume sidecar for the weight check.
    import json

    feat = {"tubercle_amp": 0.06, "tubercle_waves": 6, "serration_amp": 0.04, "serration_waves": 8}
    out = Path(tempfile.mkdtemp()) / "preview.stl"
    p = build_stl_isolated({**SMOOTH, "n_blades": 9}, feat, out, timeout=90, preview=True)
    assert p.exists() and p.stat().st_size > 0
    meta = Path(str(out) + ".meta.json")
    assert meta.exists()
    assert json.loads(meta.read_text())["volume_mm3"] > 0


def test_preview_mesh_matches_fused_bounds():
    # the non-fused preview must have the same overall size as the real fused solid (same geometry),
    # so the envelope/depth spec check stays correct.
    import trimesh

    from fansim.geometry import build_impeller, export_stl
    from fansim.geometry.blade import build_impeller_preview
    from fansim.optimize.search_space import blade_from_flat

    params = blade_from_flat(SMOOTH)
    prev_mesh, vol = build_impeller_preview(params)
    assert vol > 0
    fused_stl = Path(tempfile.mkdtemp()) / "fused.stl"
    export_stl(build_impeller(params), fused_stl)
    fused = trimesh.load(str(fused_stl))
    # bounding boxes (dia + depth) agree within tessellation slop
    for a, b in zip(prev_mesh.bounds.ravel(), fused.bounds.ravel()):
        assert abs(a - b) < 1.5
