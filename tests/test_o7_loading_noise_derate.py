"""O7 / #53: loading-noise proxy must use thrust at the motor-held RPM (affinity λ²).

Pre-reg: docs/validation/audits/2026-11-25-o7-loading-noise-derate-prereg.md
"""

from __future__ import annotations

from pathlib import Path

import pytest

from fansim.acoustics.loading import loading_proxy_from_rans, loading_proxy_operating
from fansim.optimize import objectives as obj


@pytest.mark.parametrize("derate", [1.0, 0.5, 0.8])
def test_operating_proxy_equals_rans_with_lambda2_thrust(derate):
    # P1
    n, thrust = 7, 0.07
    got = loading_proxy_operating(n, thrust, derate)
    want = loading_proxy_from_rans(n, thrust * derate * derate)
    assert got == pytest.approx(want, abs=1e-12)


def test_derate_one_matches_rated_proxy():
    # P2 — motor not limited: ranking unchanged
    assert loading_proxy_operating(9, 0.03, 1.0) == pytest.approx(
        loading_proxy_from_rans(9, 0.03), abs=1e-12
    )


def test_half_rpm_reduces_proxy():
    # P3 (O7 + #122) — λ=0.5 scales thrust by λ²=0.25 and strictly reduces predicted noise
    rated = loading_proxy_from_rans(7, 0.07)
    half = loading_proxy_operating(7, 0.07, 0.5)
    assert half < rated


def test_evaluate_candidate_applies_derate_after_motor_limit():
    # P4 — call site is after derate; no pre-derate loading_proxy_from_rans on rated thrust alone
    src = Path(obj.__file__).read_text(encoding="utf-8")
    assert "loading_proxy_operating" in src
    # The operating helper (or an equivalent λ² scale) must sit after derate is assigned.
    derate_at = src.index("derate = min(")
    call_at = src.index("loading_proxy_operating")
    assert call_at > derate_at
