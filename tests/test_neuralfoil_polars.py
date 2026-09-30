"""§20.2 NeuralFoil polar backend quality (skip if --extra neuralfoil missing)."""

from __future__ import annotations

import math

import pytest

from fansim.propeller.neuralfoil_polars import (
    ALPHA_DEG_MAX,
    ALPHA_DEG_MIN,
    ALPHA_NF_MAX,
    ALPHA_NF_MIN,
    CD_MAX,
    STALL_ALPHA_DEG,
    neuralfoil_available,
    section_neuralfoil,
)

pytestmark = pytest.mark.skipif(
    not neuralfoil_available(), reason="needs uv sync --extra neuralfoil"
)


def test_neuralfoil_marks_stall_past_onset():
    attached = section_neuralfoil(math.radians(5.0), 0.04, 1.0e5, thickness=0.06)
    stalled = section_neuralfoil(math.radians(STALL_ALPHA_DEG + 2.0), 0.04, 1.0e5, thickness=0.06)
    assert attached is not None and stalled is not None
    assert attached[2] is False
    assert stalled[2] is True
    assert stalled[3] > 0.0  # cl_cap


def test_neuralfoil_alpha_band_wider_than_old_clamp():
    assert ALPHA_NF_MIN <= -20.0
    assert ALPHA_NF_MAX >= 20.0
    assert ALPHA_DEG_MIN <= -180.0
    assert ALPHA_DEG_MAX >= 180.0
    edge = section_neuralfoil(math.radians(ALPHA_NF_MAX), 0.04, 1.0e5, thickness=0.06)
    assert edge is not None


def test_neuralfoil_360_viterna_cd_peak_near_90():
    """Proven 360°: Cd asymptotes to CD_MAX at ±90°, not raw-NF near-zero drag."""
    pos = section_neuralfoil(math.radians(90.0), 0.04, 1.0e5, thickness=0.06)
    neg = section_neuralfoil(math.radians(-90.0), 0.04, 1.0e5, thickness=0.06)
    assert pos is not None and neg is not None
    assert abs(pos[0]) < 0.05
    assert abs(neg[0]) < 0.05
    assert abs(pos[1] - CD_MAX) < 0.05
    assert abs(neg[1] - CD_MAX) < 0.05
    assert pos[2] is True and neg[2] is True


def test_neuralfoil_360_finite_full_circle():
    """Finite Cl/Cd every 15° on (−180, 180]; Cd always positive."""
    for a in range(-180, 181, 15):
        row = section_neuralfoil(math.radians(float(a)), 0.04, 1.0e5, thickness=0.06)
        assert row is not None, a
        cl, cd, stalled, cl_cap = row
        assert math.isfinite(cl) and math.isfinite(cd), a
        assert cd > 0.0, a
        assert cl_cap > 0.0, a
        if abs(a) >= STALL_ALPHA_DEG:
            assert stalled is True, a


def test_neuralfoil_360_continuous_at_nf_band_edge():
    """Viterna match keeps Cl/Cd close when stepping just outside ±25°."""
    inside = section_neuralfoil(math.radians(ALPHA_NF_MAX), 0.04, 1.0e5, thickness=0.06)
    outside = section_neuralfoil(math.radians(ALPHA_NF_MAX + 1.0), 0.04, 1.0e5, thickness=0.06)
    assert inside is not None and outside is not None
    assert abs(outside[0] - inside[0]) < 0.15
    assert abs(outside[1] - inside[1]) < 0.15
