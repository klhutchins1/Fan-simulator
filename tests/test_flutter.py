"""Tests for the cantilever first-bending vs BPF gate."""

from __future__ import annotations

import math

import pytest

from fansim.geometry.blade import BladeParams
from fansim.structural.flutter import first_bending_hz, flutter_report


def test_default_petg_is_clear_of_bpf():
    r = flutter_report(BladeParams())
    assert r.ok
    assert r.f1_hz > 1.2 * r.bpf_hz


def test_tpu_high_rpm_can_fail():
    p = BladeParams()
    p.rpm = 30000.0
    r = flutter_report(p, material="TPU")
    assert r.ok is False
    assert "vibration" in r.reason.lower() or "blade-pass" in r.reason.lower()
    assert "fix:" in r.reason.lower()
    assert "blades" in r.reason.lower()


def test_resonance_message_suggests_blade_cap():
    from fansim.structural.flutter import max_blades_for_margin, resonance_user_message

    msg = resonance_user_message(
        f1_hz=384.0, bpf_hz=333.0, margin=1.15, min_margin=1.2,
        material="PETG", n_blades=10, rpm=2000.0,
    )
    assert "10 blades" in msg
    assert "Thickness mid" in msg
    assert max_blades_for_margin(384.0, 2000.0) == 9
    assert "<=9" in msg


def test_f1_scales_with_sqrt_modulus():
    p = BladeParams()
    petg = first_bending_hz(p, "PETG")
    tpu = first_bending_hz(p, "TPU")
    assert petg / tpu == pytest.approx(math.sqrt(2.1 / 0.02), rel=0.05)
