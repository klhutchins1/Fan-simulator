"""Export impeller geometry and check mesh validity for downstream CFD/printing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cadquery as cq
import trimesh


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


def export_stl(
    model: cq.Workplane, path: str | Path, tolerance: float = 0.05, angular_tolerance: float = 0.2
) -> Path:
    """Tessellate and write an STL. ``tolerance`` is the max chordal deviation in mm."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(
        model,
        str(path),
        exportType="STL",
        tolerance=tolerance,
        angularTolerance=angular_tolerance,
    )
    return path


def watertight_report(path: str | Path) -> WatertightReport:
    """Load an STL with trimesh and report watertightness / body count."""
    mesh = trimesh.load(str(path), force="mesh")
    bodies = mesh.split(only_watertight=False)
    lo, hi = mesh.bounds
    return WatertightReport(
        watertight=bool(mesh.is_watertight),
        n_vertices=int(len(mesh.vertices)),
        n_faces=int(len(mesh.faces)),
        volume_mm3=float(mesh.volume),
        n_bodies=int(len(bodies)),
        bounds_mm=(tuple(map(float, lo)), tuple(map(float, hi))),
    )
