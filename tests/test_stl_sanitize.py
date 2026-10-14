"""QA-34: collapsed tessellation faces must not make a fused solid look multi-body."""
from __future__ import annotations

import numpy as np
import trimesh

from fansim.geometry.export import sanitize_stl, watertight_report


def _dirty_box(path):
    """Watertight box plus one collapsed triangle (2 unique vertices), like S5_0184's 7 slivers."""
    box = trimesh.creation.box(extents=(10.0, 10.0, 10.0))
    faces = np.vstack([box.faces, [0, 0, 1]])
    mesh = trimesh.Trimesh(vertices=box.vertices.copy(), faces=faces, process=False)
    mesh.export(str(path))
    return mesh


def test_collapsed_face_makes_k2_fail(tmp_path):
    stl = tmp_path / "dirty.stl"
    _dirty_box(stl)
    m = trimesh.load(str(stl), force="mesh", process=False)
    assert int((m.area_faces < 1e-9).sum()) >= 1
    assert not watertight_report(stl).ok


def test_sanitize_stl_drops_collapsed_faces(tmp_path):
    stl = tmp_path / "dirty.stl"
    _dirty_box(stl)
    sanitize_stl(stl)
    rep = watertight_report(stl)
    assert rep.ok
    assert rep.n_bodies == 1
    m = trimesh.load(str(stl), force="mesh")
    assert int((m.area_faces < 1e-9).sum()) == 0
    assert len(m.split(only_watertight=False)) == 1
