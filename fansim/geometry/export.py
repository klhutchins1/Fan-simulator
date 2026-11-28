"""Export impeller geometry and check mesh validity for downstream CFD/printing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:  # pragma: no cover
    import cadquery as cq

# K2 / QA-34: faces smaller than this (mm²) or with < 3 unique vertices are tessellation needles.
_DEGEN_AREA_MM2 = 1e-9


@dataclass
class WatertightReport:
    """Result of a manifold/watertightness check on an exported mesh."""

    watertight: bool
    n_vertices: int
    n_faces: int
    volume_mm3: float
    n_bodies: int
    bounds_mm: tuple[tuple[float, float, float], tuple[float, float, float]]
    mount_fits: bool | None = None   # motor-mount cavity carved (True) / hub too small (False) / N/A (None)
    mount_msg: str = ""

    @property
    def ok(self) -> bool:
        """Printable/meshable: a single watertight body with positive volume."""
        return self.watertight and self.n_bodies == 1 and self.volume_mm3 > 0.0


def sanitize_stl(path: str | Path) -> Path:
    """Drop collapsed / zero-area faces in place.

    Featured wrapped blades (QA-34 S5_0184) tessellate as one watertight solid plus one needle
    triangle per blade. ``fuse_impeller`` already saw 1 B-rep solid; the needles only exist in the
    mesh. Leaving them makes trimesh report extra bodies and Assess refuse a printable impeller.
    """
    import trimesh

    path = Path(path)
    mesh = trimesh.load(str(path), force="mesh", process=False)
    if not isinstance(mesh, trimesh.Trimesh) or len(mesh.faces) == 0:
        return path
    faces = np.asarray(mesh.faces)
    collapsed = (faces[:, 0] == faces[:, 1]) | (faces[:, 1] == faces[:, 2]) | (faces[:, 0] == faces[:, 2])
    tiny = np.asarray(mesh.area_faces) < _DEGEN_AREA_MM2
    keep = ~(collapsed | tiny)
    if bool(np.all(keep)):
        return path
    mesh.update_faces(keep)
    mesh.remove_unreferenced_vertices()
    mesh.export(str(path))
    return path


def export_stl(
    model: cq.Workplane, path: str | Path, tolerance: float = 0.05, angular_tolerance: float = 0.2
) -> Path:
    """Tessellate and write an STL. ``tolerance`` is the max chordal deviation in mm."""
    import cadquery as cq

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(
        model,
        str(path),
        exportType="STL",
        tolerance=tolerance,
        angularTolerance=angular_tolerance,
    )
    return sanitize_stl(path)


def export_step(model: cq.Workplane, path: str | Path, *, unit: str = "MM") -> Path:
    """Write a STEP (B-rep) file for Fusion / Onshape / FreeCAD (§20.1).

    No tessellation — CAD apps get the exact solid. ``unit`` is the STEP header unit.
    """
    import cadquery as cq

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(model, str(path), exportType="STEP", unit=unit)  # type: ignore[arg-type]
    return path


def watertight_report(path: str | Path) -> WatertightReport:
    """Load an STL with trimesh and report watertightness / body count."""
    import trimesh

    mesh = trimesh.load(str(path), force="mesh")
    bodies = mesh.split(only_watertight=False)
    lo, hi = mesh.bounds
    return WatertightReport(
        watertight=bool(mesh.is_watertight),
        n_vertices=len(mesh.vertices),
        n_faces=len(mesh.faces),
        volume_mm3=float(mesh.volume),
        n_bodies=len(bodies),
        bounds_mm=(tuple(map(float, lo)), tuple(map(float, hi))),
    )
