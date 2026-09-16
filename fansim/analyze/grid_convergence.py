"""Grid Convergence Index (Roache 1994) — report discretization error from 3 mesh solutions.

The right way to say "the mesh is fine enough": from a coarse/medium/fine triplet, estimate the
observed order of convergence p, the Richardson-extrapolated (h->0) value, and a banded uncertainty
(GCI). Replaces eyeballing the 6/4/3 mm CFM trend in the grid-convergence scripts with a number.

Reference (docs/bibliography.md sec.4): Roache, P. J. (1994), J. Fluids Eng. 116, 405-413.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class GCIResult:
    p: float                 # observed order of convergence
    f_extrapolated: float    # Richardson value as h -> 0
    gci_fine_pct: float      # % uncertainty band on the FINE solution (f1)
    gci_medium_pct: float    # % uncertainty band on the medium solution (f2)
    asymptotic_ratio: float  # ~1.0 => solutions are in the asymptotic range
    converged: bool          # asymptotic_ratio within 10% of 1.0

    def __str__(self) -> str:
        return (f"GCI: p={self.p:.2f}, f(h->0)={self.f_extrapolated:.3f}, "
                f"GCI_fine={self.gci_fine_pct:.2f}%, asymptotic={self.asymptotic_ratio:.3f} "
                f"({'in' if self.converged else 'NOT in'} asymptotic range)")


def grid_convergence_index(h1: float, h2: float, h3: float,
                           f1: float, f2: float, f3: float,
                           safety_factor: float = 1.25) -> GCIResult:
    """Roache GCI from three grids (h1<h2<h3 = fine<medium<coarse) and their solution values.

    h* are representative cell sizes (e.g. base_cell in mm); f* the reported quantity (e.g. CFM).
    Handles unequal refinement ratios via the iterative order estimate. Raises ValueError on
    degenerate input (equal solutions, non-monotone ordering).
    """
    if not (h1 < h2 < h3):
        raise ValueError(f"need h1<h2<h3 (fine<medium<coarse); got {h1}, {h2}, {h3}")
    r21, r32 = h2 / h1, h3 / h2
    e21, e32 = f2 - f1, f3 - f2
    if e21 == 0.0 or e32 == 0.0:
        raise ValueError("solutions do not change between grids; order is undefined")
    s = math.copysign(1.0, e32 / e21)

    # iterate p:  p = |ln|e32/e21| + q(p)| / ln(r21),  q(p) = ln((r21^p - s)/(r32^p - s))
    p = math.log(abs(e32 / e21)) / math.log(r21)  # initial guess (q=0)
    for _ in range(100):
        q = math.log((r21**p - s) / (r32**p - s)) if r21 != r32 else 0.0
        p_new = abs(math.log(abs(e32 / e21)) + q) / math.log(r21)
        if abs(p_new - p) < 1e-10:
            p = p_new
            break
        p = p_new

    f_ext = f1 + (f1 - f2) / (r21**p - 1.0) if f1 != 0.0 or f2 != 0.0 else f1
    ea21 = abs((f1 - f2) / f1) if f1 != 0.0 else abs(f1 - f2)
    ea32 = abs((f2 - f3) / f2) if f2 != 0.0 else abs(f2 - f3)
    gci_fine = safety_factor * ea21 / (r21**p - 1.0)
    gci_med = safety_factor * ea32 / (r32**p - 1.0)
    # asymptotic-range check: GCI_23 / (r21^p * GCI_12) ~ 1
    asymptotic = (gci_med) / (r21**p * gci_fine) if gci_fine > 0 else float("inf")
    return GCIResult(
        p=p,
        f_extrapolated=f_ext,
        gci_fine_pct=100.0 * gci_fine,
        gci_medium_pct=100.0 * gci_med,
        asymptotic_ratio=asymptotic,
        converged=abs(asymptotic - 1.0) < 0.1,
    )
