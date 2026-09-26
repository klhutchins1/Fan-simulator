"""Pure-function test for scripts/audit_direction_geometry.py's ``_cfd_frame`` (finding I2).

Loaded via importlib (scripts/ is not a package); we never call main() here, so this never
runs CFD or touches runs/audit_direction/ or docs/validation/audits/direction_geometry.json.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "audit_direction_geometry.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("audit_direction_geometry_under_test", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mod():
    return _load_module()


def test_cfd_frame_flipped_negates_sign(mod):
    # Designed omega +1, CFD copy flipped -> the CFD frame reads -1 (matches production spin).
    assert mod._cfd_frame(1, "flipped") == -1
    # Designed pump -1 (as-built delivery), CFD copy flipped -> the CFD frame reads +1
    # (matches the duct's inlet -Z -> outlet +Z convention).
    assert mod._cfd_frame(-1, "flipped") == 1


def test_cfd_frame_as_built_is_identity(mod):
    assert mod._cfd_frame(1, "as_built") == 1
    assert mod._cfd_frame(-1, "as_built") == -1


def test_cfd_frame_with_designed_and_as_built_orientation_both_false_vs_production():
    # From the finding: with (+1, "flipped") spin -1 matches and pump(-1) -> +1; with "as_built",
    # both give False when compared against production's spin=-1 / pump=+1 expectation.
    mod = _load_module()
    spin_in_use = -1
    assert (spin_in_use == mod._cfd_frame(1, "flipped")) is True
    assert (mod._cfd_frame(-1, "flipped") == 1) is True
    assert (spin_in_use == mod._cfd_frame(1, "as_built")) is False
    assert (mod._cfd_frame(-1, "as_built") == 1) is False


def test_cfd_frame_none_passthrough(mod):
    assert mod._cfd_frame(None, "flipped") is None
    assert mod._cfd_frame(None, "as_built") is None
