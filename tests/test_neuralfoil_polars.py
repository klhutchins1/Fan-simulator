"""§20.2 NeuralFoil polar backend quality (skip if --extra neuralfoil missing)."""

from __future__ import annotations

import math

import pytest

from fansim.propeller.neuralfoil_polars import (
    ALPHA_DEG_MAX,
    ALPHA_DEG_MIN,
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
    assert ALPHA_DEG_MIN <= -20.0
    assert ALPHA_DEG_MAX >= 20.0
    # Clamped evaluation still returns a polar (not None) at the band edge.
    edge = section_neuralfoil(math.radians(ALPHA_DEG_MAX), 0.04, 1.0e5, thickness=0.06)
    assert edge is not None
