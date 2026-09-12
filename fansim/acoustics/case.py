# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Adapters that run the RANS noise proxies on a solved OpenFOAM case (compute-free post-process).

Reads the internal k/omega volume fields + cell volumes from a *reconstructed* OpenFOAM case and
feeds fansim.acoustics.proxies. The core integration (integrate_proudman_grid) works on any PyVista
grid and is unit-tested with a synthetic mesh; read_case is the thin OpenFOAM adapter.

NOTE on the pipeline: the optimizer currently runs decomposed (processor*/), reconstructs nothing,
and extracts scalar metrics from function objects -- so the volume fields are not on disk. To make
the Proudman/Curle proxy a *per-candidate* objective, run_solve needs a `reconstructPar -latestTime`
and to keep that time dir; then proudman_swl_from_case(case) returns a screening dB per design.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from fansim.acoustics.proxies import CMU, epsilon_from_komega, proudman_swl


def integrate_proudman_grid(grid, k_field: str = "k", omega_field: str = "omega",
                            epsilon_field: str | None = None) -> float:
    """Proudman broadband SWL [dB] from a PyVista grid carrying k and omega (or epsilon).

    Accepts cell or point data (point data is sampled to cells). Cell volumes are computed from the
    mesh. Solid/zero-volume cells are ignored. This is the tested core; read_case feeds it.
    """
    g = grid.point_data_to_cell_data() if k_field in grid.point_data else grid
    sized = g.compute_cell_sizes(length=False, area=False, volume=True)
    vols = np.asarray(sized.cell_data["Volume"], float)
    k = np.asarray(g.cell_data[k_field], float)
    if epsilon_field is not None and epsilon_field in g.cell_data:
        eps = np.asarray(g.cell_data[epsilon_field], float)
    else:
        eps = epsilon_from_komega(k, np.asarray(g.cell_data[omega_field], float), cmu=CMU)
    mask = vols > 0.0
    return proudman_swl(k[mask], eps[mask], vols[mask])


def read_case(case_dir: str | Path):
    """Load the latest-time internal mesh of a reconstructed OpenFOAM case as a PyVista grid.

    Writes a `.foam` stub if needed and uses PyVista's OpenFOAM reader. Raises a clear error if the
    case is still decomposed (only processor*/ present) -- reconstruct it first.
    """
    import pyvista as pv

    case_dir = Path(case_dir)
    times = [p.name for p in case_dir.iterdir() if p.is_dir() and p.name.replace(".", "", 1).isdigit()]
    nonzero = [t for t in times if float(t) > 0.0]
    if not nonzero:
        raise FileNotFoundError(
            f"{case_dir} has no reconstructed non-zero time dir (found {sorted(times)}). "
            "Run `reconstructPar -latestTime` first; the optimizer keeps only decomposed processor*/.")
    foam = case_dir / f"{case_dir.name}.foam"
    if not foam.exists():
        foam.write_text("")
    reader = pv.OpenFOAMReader(str(foam))
    reader.set_active_time_value(max(float(t) for t in nonzero))
    multi = reader.read()
    # the internal mesh is the first block ("internalMesh")
    return multi["internalMesh"] if "internalMesh" in multi.keys() else multi[0]


def proudman_swl_from_case(case_dir: str | Path) -> float:
    """Convenience: reconstructed OpenFOAM case -> Proudman broadband SWL [dB]. Relative metric."""
    return integrate_proudman_grid(read_case(case_dir))
