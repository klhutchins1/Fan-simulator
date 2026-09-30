"""Pure-function tests for scripts/audit_direction_cfd.py: reverdict + STL binding (C1, I4).

Loaded via importlib (scripts/ is not a package). Importing it pulls in fansim.cfd transitively,
which is known to crash CPython at *interpreter teardown* on this machine -- irrelevant here since
we only judge the test outcomes recorded during the run, never the process exit code.
"""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "audit_direction_cfd.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("audit_direction_cfd_under_test", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mod():
    return _load_module()


def _row(orientation, spin, cfm, converged, power, mz, omega_signed):
    return {
        "orientation": orientation, "spin": spin, "cfm": cfm, "converged": converged,
        "shaft_power_w": power, "moment_z_nm": mz, "omega_signed": omega_signed,
    }


def test_production_spin_matches_test_rig_default(mod):
    from fansim.cfd.domain import TestRig
    assert mod.production_spin() == TestRig.__dataclass_fields__["spin"].default


_STOCK_V5 = Path(__file__).resolve().parents[2] / "docs" / "validation" / "audits" / "direction_cfd_stock_v5.json"


@pytest.mark.skipif(not _STOCK_V5.is_file(), reason="direction_cfd_stock_v5.json missing")
def test_stock_v5_direction_matrix_keeps_designed_ahead_of_reversed(mod):
    """Roadmap §19.3: permanent cheap reverse-rotation regression (no CFD).

    Locks the committed v5 Stock free-air matrix: designed body sense must beat reversed on |CFM|,
    and production (flipped, spin -1) must still be the convention recommendation. Re-run
    ``scripts/audit_direction_cfd.py --rotor stock`` only when deliberately refreshing evidence.
    """
    import json

    existing = json.loads(_STOCK_V5.read_text(encoding="utf-8"))
    out = mod.reverdict_payload(existing)
    v = out["verdict"]
    cv = out["convention_verdict"]
    assert v["verdict"] == "PASS", v
    proper = v["proper"]
    assert proper["+1"] > proper["-1"], proper
    # Clear margin so a soft drift still fails before it becomes ambiguous.
    assert proper["+1"] / proper["-1"] >= 1.3, proper
    assert cv["verdict"] == "PASS", cv
    assert cv["production"] == {"orientation": "flipped", "spin": -1}
    assert cv["recommended"] == {"orientation": "flipped", "spin": -1}

def test_reverdict_roundtrip_flags_convention_failure_when_recommendation_is_as_built(mod):
    # Production is now the FLIPPED setup (fansim.cfd.orientation.AXIAL_CFD_ORIENTATION), spin -1.
    # A matrix that recommends as_built means production is solving the reversed rotor: FAIL.
    spin = mod.production_spin()
    assert spin == -1
    rows = [
        _row("as_built", -1, 60.0, True, 0.5, 0.002, -209.44),
        _row("as_built", 1, -30.0, True, 0.5, -0.002, 209.44),
        _row("flipped", 1, -70.0, True, 0.5, -0.002, 209.44),
        _row("flipped", -1, 42.0, True, 0.5, 0.002, -209.44),
    ]
    existing = {
        "rotor": "stock", "rpm": 2000.0, "iters": 100, "mesh": {},
        "rows": rows, "geometry": {"omega_sign": spin, "pump_sign": 1},
    }
    out = mod.reverdict_payload(existing)
    assert out["verdict"]["verdict"] == "PASS"
    assert out["verdict"]["recommended"] == {"orientation": "as_built", "spin": spin}
    assert out["convention_verdict"]["verdict"] == "FAIL"
    assert out["convention_verdict"]["production"] == {"orientation": "flipped", "spin": spin}
    assert out["errors"] == []


def test_reverdict_roundtrip_recommends_flipped_matches_production(mod):
    # Requires production's spin default to be -1 (fansim/cfd/domain.py); this is Audit #1's own
    # convention and is pinned separately, so this test asserts the value it needs directly.
    spin = mod.production_spin()
    assert spin == -1
    # Designed sense's proper run is FLIPPED: production (flipped, -1) solves the designed rotor.
    rows = [
        _row("as_built", -1, -70.0, True, 0.5, 0.002, -209.44),
        _row("as_built", 1, -30.0, True, 0.5, -0.002, 209.44),
        _row("flipped", 1, 42.0, True, 0.5, -0.002, 209.44),
        _row("flipped", -1, 60.0, True, 0.5, 0.002, -209.44),
    ]
    existing = {
        "rotor": "stock", "rpm": 2000.0, "iters": 100, "mesh": {},
        "rows": rows, "geometry": {"omega_sign": 1, "pump_sign": -1},
    }
    out = mod.reverdict_payload(existing)
    assert out["verdict"]["verdict"] == "PASS"
    assert out["verdict"]["recommended"] == {"orientation": "flipped", "spin": -1}
    assert out["convention_verdict"]["verdict"] == "PASS"


def test_reverdict_tolerates_missing_convention_verdict_and_errors_keys(mod):
    spin = mod.production_spin()
    rows = [_row("as_built", spin, None, False, None, None, spin * 209.44)]
    existing = {"rows": rows, "geometry": {}}  # no "convention_verdict", no "errors"
    out = mod.reverdict_payload(existing)
    assert "convention_verdict" in out and "errors" in out
    assert out["verdict"]["verdict"] == "INCONCLUSIVE"


def test_stl_hash_mismatch_none_when_hash_matches(mod, tmp_path):
    stl = tmp_path / "rotor.stl"
    stl.write_bytes(b"some mesh bytes")
    sha = hashlib.sha256(stl.read_bytes()).hexdigest()
    assert mod.stl_hash_mismatch(stl, {"stl_sha256": sha}) is None


def test_stl_hash_mismatch_reports_stale_geometry(mod, tmp_path):
    stl = tmp_path / "rotor.stl"
    stl.write_bytes(b"new mesh bytes")
    msg = mod.stl_hash_mismatch(stl, {"stl_sha256": "0" * 64})
    assert msg is not None and "mismatch" in msg.lower()


def test_stl_hash_mismatch_reports_missing_hash_key(mod, tmp_path):
    stl = tmp_path / "rotor.stl"
    stl.write_bytes(b"mesh bytes")
    msg = mod.stl_hash_mismatch(stl, {})
    assert msg is not None and "missing stl_sha256" in msg
