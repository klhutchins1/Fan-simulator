"""Analysis utilities: turn raw study/CFD outputs into rigorous, reportable numbers."""

from fansim.analyze.grid_convergence import GCIResult, grid_convergence_index

__all__ = ["grid_convergence_index", "GCIResult"]
