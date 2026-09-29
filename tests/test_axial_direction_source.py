"""Roadmap 19.2: axial direction is derived (external) or pinned+cross-checked (builder)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fansim.audit.synthetic import cambered_blade_fan
from fansim.cfd.domain import TestRig as _Rig
from fansim.cfd.orientation import (
    AXIAL_BUILDER_DIRECTION,
    check_rotor_direction,
    prepare_axial_cfd,
)


def _rig(spin: int = -1) -> _Rig:
    return _Rig(duct_radius=0.056, tip_gap=0.0005, inlet_length=0.224, outlet_length=0.448,
                impeller_z_min=-0.003, impeller_z_max=0.003, mrf_z_min=-0.005, mrf_z_max=0.005,
                rpm=2000.0, inlet_velocity=2.0, spin=spin)


def _stl(tmp_path: Path, name: str, **kw) -> Path:
    p = tmp_path / f"{name}.stl"
    cambered_blade_fan(**kw).export(str(p))
    return p


STOCK = dict(stagger_deg=60.0, camber=0.06)      # omega +1, pump -1
FAN01 = dict(stagger_deg=-60.0, camber=-0.06)    # omega +1, pump +1
MIRRORED = dict(stagger_deg=-60.0, camber=0.06)  # omega -1, pump -1
FLAT = dict(camber=0.0)


def _meta(workdir: Path) -> dict:
    return json.loads((workdir / "direction_meta.json").read_text())


def test_builder_stock_handed(tmp_path):
    _, rig = prepare_axial_cfd(_stl(tmp_path, "s", **STOCK), _rig(spin=1), tmp_path)
    assert rig.spin == -1
    m = _meta(tmp_path)
    assert (m["orientation"], m["spin"], m["direction_source"], m["proof_verdict"]) == (
        "flipped", -1, "builder", "CONCLUSIVE")
    assert AXIAL_BUILDER_DIRECTION == ("flipped", -1)


def test_builder_inconclusive_flat_fan_uses_builder_direction(tmp_path):
    _, rig = prepare_axial_cfd(_stl(tmp_path, "f", **FLAT), _rig(spin=1), tmp_path, source="builder")
    assert rig.spin == -1
    m = _meta(tmp_path)
    assert (m["orientation"], m["proof_verdict"]) == ("flipped", "INCONCLUSIVE")


def test_builder_mirrored_raises(tmp_path):
    with pytest.raises(ValueError, match="cross-check"):
        prepare_axial_cfd(_stl(tmp_path, "m", **MIRRORED), _rig(), tmp_path, source="builder")


def test_external_fan01_handed_is_as_built_plus_one(tmp_path):
    stl, rig = prepare_axial_cfd(_stl(tmp_path, "e", **FAN01), _rig(), tmp_path, source="external")
    assert stl.is_file() and rig.spin == 1
    m = _meta(tmp_path)
    assert (m["orientation"], m["spin"], m["direction_source"]) == ("as_built", 1, "external")


def test_external_stock_handed_is_flipped_minus_one(tmp_path):
    _, rig = prepare_axial_cfd(_stl(tmp_path, "e2", **STOCK), _rig(spin=1), tmp_path,
                               source="external")
    assert rig.spin == -1 and _meta(tmp_path)["orientation"] == "flipped"


def test_external_flat_fan_raises(tmp_path):
    with pytest.raises(ValueError, match="pass orientation= and spin= explicitly"):
        prepare_axial_cfd(_stl(tmp_path, "x", **FLAT), _rig(), tmp_path, source="external")


def test_explicit_passthrough_no_proof(tmp_path):
    # Mirrored + flat would fail either derived mode; explicit override must not care.
    _, rig = prepare_axial_cfd(_stl(tmp_path, "p", **MIRRORED), _rig(), tmp_path,
                               source="external", orientation="as_built", spin=1)
    assert rig.spin == 1
    m = _meta(tmp_path)
    assert (m["direction_source"], m["orientation"], m["spin"], m["proof_verdict"]) == (
        "explicit", "as_built", 1, None)


def test_orientation_only_keeps_rig_spin(tmp_path):
    _, rig = prepare_axial_cfd(_stl(tmp_path, "o", **FLAT), _rig(spin=1), tmp_path,
                               orientation="flipped")
    assert rig.spin == 1 and _meta(tmp_path)["direction_source"] == "explicit"


def test_bad_source_and_spin(tmp_path):
    stl = _stl(tmp_path, "b", **STOCK)
    with pytest.raises(ValueError, match="source"):
        prepare_axial_cfd(stl, _rig(), tmp_path, source="magic")
    with pytest.raises(ValueError, match="spin"):
        prepare_axial_cfd(stl, _rig(), tmp_path, orientation="flipped", spin=0)


def test_check_rotor_direction(tmp_path):
    check_rotor_direction(_stl(tmp_path, "c1", **STOCK), +1)
    check_rotor_direction(_stl(tmp_path, "c2", **FLAT), +1)  # inconclusive passes
    with pytest.raises(ValueError, match="cross-check"):
        check_rotor_direction(_stl(tmp_path, "c3", **MIRRORED), +1)


def test_case_meta_records_direction(tmp_path):
    from fansim.cfd.openfoam_case import build_case

    stl, rig = prepare_axial_cfd(_stl(tmp_path, "cm", **STOCK), _rig(), tmp_path)
    case = build_case(tmp_path / "case", stl, rig, n_iters=5)
    meta = json.loads((case / "constant/case_meta.json").read_text())
    assert meta["direction_source"] == "builder"
    assert (meta["orientation"], meta["spin"], meta["proof_verdict"]) == (
        "flipped", -1, "CONCLUSIVE")
    # explicit dict wins over the sidecar
    case2 = build_case(tmp_path / "case2", stl, rig, n_iters=5,
                       direction_meta={"direction_source": "explicit", "orientation": "flipped",
                                       "spin": -1, "proof_verdict": None})
    assert json.loads((case2 / "constant/case_meta.json").read_text())["direction_source"] == "explicit"
