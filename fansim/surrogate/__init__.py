"""Surrogate tier: learn objective(design) from evaluated trials to pre-screen new designs cheaply.

A Gaussian process (self-contained numpy, no sklearn) is the starting surrogate the plan calls for;
FNO / neural-field operators (docs/bibliography.md sec.6) are the future upgrade for full flow fields.
"""

from fansim.surrogate.gp import GaussianProcess, design_matrix

__all__ = ["GaussianProcess", "design_matrix"]
