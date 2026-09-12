# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Tests for the Roache GCI (fansim.analyze.grid_convergence)."""

import pytest

from fansim.analyze import grid_convergence_index


def test_exact_second_order_series():
    """A synthetic f = f_inf - C*h^2 on h=1,2,4 must recover p=2, f_inf=100, asymptotic range."""
    finf, c = 100.0, 1.0
    f = lambda h: finf - c * h**2
    r = grid_convergence_index(1.0, 2.0, 4.0, f(1.0), f(2.0), f(4.0))
    assert r.p == pytest.approx(2.0, abs=1e-6)
    assert r.f_extrapolated == pytest.approx(100.0, abs=1e-6)
    assert r.gci_fine_pct > 0
    assert r.converged  # asymptotic_ratio ~ 1


def test_real_fan_grid_study():
    """Our actual A12x25 free-delivery study: 3/4/6 mm -> 59.6/57.7/56.8 CFM.

    Richardson extrapolation should land near the published ~60 CFM and flag a few-% fine-mesh GCI.
    """
    r = grid_convergence_index(3.0, 4.0, 6.0, 59.6, 57.7, 56.8)
    assert r.p > 0
    assert 59.0 < r.f_extrapolated < 63.0     # ~61 CFM as h->0, consistent with the +2% validation
    assert 1.0 < r.gci_fine_pct < 8.0         # the "~3-5% discretization error" quantified


def test_rejects_bad_ordering():
    with pytest.raises(ValueError):
        grid_convergence_index(4.0, 2.0, 1.0, 1.0, 2.0, 3.0)  # h not increasing


def test_rejects_flat_solutions():
    with pytest.raises(ValueError):
        grid_convergence_index(1.0, 2.0, 4.0, 50.0, 50.0, 50.0)
