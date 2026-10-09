"""Sim→print knockdown (roadmap §7.6 stage 1). No CFD."""

from __future__ import annotations

import pytest

from fansim.optimize.print_penalty import PRINT_K_CFM, PRINT_K_ETA, apply_print_penalty


def test_default_factors_scale_cfm_and_efficiency():
    cfm_free, cfm_load, eta, stamps = apply_print_penalty(100.0, 80.0, 40.0)
    assert cfm_free == pytest.approx(95.0)
    assert cfm_load == pytest.approx(76.0)
    assert eta == pytest.approx(36.8)
    assert stamps["cfm_free_cfd"] == 100.0
    assert stamps["cfm_load_cfd"] == 80.0
    assert stamps["efficiency_cfd"] == 40.0
    assert stamps["print_k_cfm"] == PRINT_K_CFM == pytest.approx(0.95)
    assert stamps["print_k_eta"] == PRINT_K_ETA == pytest.approx(0.92)


def test_print_penalty_off_is_identity():
    cfm_free, cfm_load, eta, stamps = apply_print_penalty(100.0, 80.0, 40.0, enabled=False)
    assert (cfm_free, cfm_load, eta) == (100.0, 80.0, 40.0)
    assert stamps == {}
