"""Unit tests for the RANS noise proxies (fansim.acoustics). No CFD required."""

import math

import numpy as np
import pytest

from fansim.acoustics import (
    curle_dpdt_estimate,
    curle_surface_swl,
    epsilon_from_komega,
    proudman_power_density,
    proudman_swl,
    sound_power_level,
    turbulent_mach,
)


def test_epsilon_from_komega():
    # epsilon = Cmu * k * omega
    assert epsilon_from_komega(2.0, 10.0, cmu=0.09) == pytest.approx(1.8)


def test_turbulent_mach():
    # M_t = sqrt(2k)/c0
    assert turbulent_mach(0.5, c0=343.0) == pytest.approx(math.sqrt(1.0) / 343.0)
    # zero/negative k clamps to 0 (no NaN)
    assert turbulent_mach(0.0) == 0.0
    assert turbulent_mach(-1.0) == 0.0


def test_proudman_power_density_formula():
    k, eps, rho, c0, alpha = 1.0, 2.0, 1.225, 343.0, 0.1
    mt = math.sqrt(2.0 * k) / c0
    expected = alpha * rho * eps * mt**5
    assert proudman_power_density(k, eps, rho, c0, alpha) == pytest.approx(expected)


def test_proudman_power_density_is_nonnegative_and_monotonic_in_k():
    # steep (M_t^5) growth with turbulence: more k -> strictly more power
    p_lo = proudman_power_density(0.5, 1.0)
    p_hi = proudman_power_density(2.0, 1.0)
    assert p_lo >= 0 and p_hi > p_lo


def test_sound_power_level():
    # 1e-6 W over 1e-12 ref = 60 dB
    assert sound_power_level(1e-6) == pytest.approx(60.0)
    assert sound_power_level(0.0) == float("-inf")


def test_proudman_swl_integrates_and_ranks():
    # two designs, same cells; the more-turbulent one must be louder
    vols = np.full(100, 1e-6)
    quiet = proudman_swl(np.full(100, 0.2), np.full(100, 0.5), vols)
    loud = proudman_swl(np.full(100, 1.0), np.full(100, 2.0), vols)
    assert loud > quiet
    assert math.isfinite(quiet)


def test_proxies_has_no_dead_arraylike_alias():
    from fansim.acoustics import proxies

    assert not hasattr(proxies, "ArrayLike")



def test_curle_surface_swl_and_estimate():
    areas = np.full(50, 2e-4)
    dpdt = curle_dpdt_estimate(np.full(50, 0.5), np.full(50, 100.0))  # (cp*rho*k)^2 * omega^2
    swl = curle_surface_swl(dpdt, areas)
    assert math.isfinite(swl)
    # doubling the fluctuation frequency raises the level
    dpdt2 = curle_dpdt_estimate(np.full(50, 0.5), np.full(50, 200.0))
    assert curle_surface_swl(dpdt2, areas) > swl


def test_arrays_and_scalars_interop():
    # functions accept both scalars and arrays
    assert np.ndim(proudman_power_density(np.ones(3), np.ones(3))) == 1
    assert np.ndim(proudman_power_density(1.0, 1.0)) == 0


def test_integrate_proudman_grid_ranks_turbulence():
    """The grid integrator (cell volumes + k/omega) must rank a more-turbulent field louder."""
    pv = pytest.importorskip("pyvista")
    from fansim.acoustics.case import integrate_proudman_grid

    g = pv.ImageData(dimensions=(11, 11, 11), spacing=(0.01, 0.01, 0.01))
    g.cell_data["omega"] = np.full(g.n_cells, 500.0)
    g.cell_data["k"] = np.full(g.n_cells, 0.3)
    quiet = integrate_proudman_grid(g)
    g.cell_data["k"] = np.full(g.n_cells, 1.5)
    loud = integrate_proudman_grid(g)
    assert loud > quiet
    assert math.isfinite(quiet)
