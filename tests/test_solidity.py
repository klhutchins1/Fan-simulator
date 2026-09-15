"""Analytic solidity at hub_radius (§12.15)."""

from __future__ import annotations

import math

from fansim.geometry.blade import BladeParams, RadialStation, blade_solidity


def test_hub_solidity_uses_hub_radius_not_embed():
    # σ = N * c * cos(β) / (2 π r); stagger 0 → cos=1
    p = BladeParams(
        n_blades=7,
        hub_radius=20.0,
        tip_radius=50.0,
        root_embed=2.0,
        stations=[
            RadialStation(0.0, chord=20.0, stagger_deg=0.0, thickness=0.08),
            RadialStation(0.5, chord=20.0, stagger_deg=0.0, thickness=0.08),
            RadialStation(1.0, chord=20.0, stagger_deg=0.0, thickness=0.08),
        ],
    )
    sol = blade_solidity(p)
    expected = 7.0 * 20.0 / (2.0 * math.pi * 20.0)
    assert abs(sol["hub"] - expected) < 1e-9
    # Old bug used r = hub − embed → larger σ
    wrong = 7.0 * 20.0 / (2.0 * math.pi * 18.0)
    assert abs(sol["hub"] - wrong) > 0.01
