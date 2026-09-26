"""Leaf geometry helper: rotate a mesh 180 deg about X. Imports only trimesh + numpy.

Both ``fansim.cfd.orientation`` (the axial CFD orientation convention) and
``fansim.audit.direction`` (the mesh-only direction proof) need this same rotation, and neither
should have to import the other's domain to get it -- hence this leaf module.
"""

from __future__ import annotations

import numpy as np
import trimesh


def flip_about_x(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Proper 180° rotation about X (y → −y, z → −z): same rotor, turned over. Returns a copy."""
    m = mesh.copy()
    m.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1.0, 0.0, 0.0]))
    return m
