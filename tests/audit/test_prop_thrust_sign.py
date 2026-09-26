"""Prop thrust sign comes from geometry; a wrong sign is reported, never flipped away."""

from __future__ import annotations

import pytest

from fansim.audit.synthetic import cambered_blade_fan
from fansim.propeller.calibrate import normalize_metrics_sign
from fansim.propeller.direction import chirality_hint_from_name, prop_direction


def _stl(tmp_path, **kw):
    p = tmp_path / "prop.stl"
    cambered_blade_fan(n_blades=2, r_hub=6.0, r_tip=60.0, chord=15.0, **kw).export(str(p))
    return p


def test_correct_sign_is_positive_thrust_and_ok():
    out = normalize_metrics_sign({"thrust_n": -0.5}, spin=-1)
    assert out["thrust_sign_ok"] is True and out["thrust_n"] == pytest.approx(0.5)
    assert out["thrust_n_raw"] == -0.5 and "thrust_sign_error" not in out


def test_wrong_sign_is_flagged_not_flipped():
    out = normalize_metrics_sign({"thrust_n": 0.5}, spin=-1)
    assert out["thrust_sign_ok"] is False and "thrust_sign_error" in out
    assert out["thrust_n"] == pytest.approx(-0.5)   # reported as negative thrust, not masked
    assert out["spin"] == -1 and "spin_recommended" not in out


def test_chirality_hint():
    assert chirality_hint_from_name("obj_2_ccw.stl") == -1
    assert chirality_hint_from_name("obj_8_cw.stl") == 1
    assert chirality_hint_from_name("prop.stl") is None


def test_direction_from_geometry(tmp_path):
    # Synthetic oracle: stagger 60, camber > 0 designs omega +1 pumping -Z as built (chirality -1).
    d = prop_direction(_stl(tmp_path, stagger_deg=60.0, camber=0.06))
    assert (d.orientation, d.spin, d.chirality, d.source) == ("flipped", -1, -1, "geometry")
    d2 = prop_direction(_stl(tmp_path, stagger_deg=60.0, camber=-0.06))  # omega -1, pumps +Z
    assert (d2.orientation, d2.spin) == ("as_built", -1)


def test_label_disagreeing_with_geometry_raises(tmp_path):
    with pytest.raises(ValueError, match="chirality"):
        prop_direction(_stl(tmp_path, stagger_deg=60.0, camber=0.06), name_hint="x_cw.stl")


def test_inconclusive_geometry_raises(tmp_path):
    with pytest.raises(ValueError, match="INCONCLUSIVE"):
        prop_direction(_stl(tmp_path, stagger_deg=60.0, camber=0.0))
