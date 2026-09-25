"""geometry.stock_handedness: the Stock recipe rotor is built with the designed handedness.

Builds the actual Stock impeller (config/problems/a12x25_reference.yaml) with build_impeller +
export_stl, then runs it back through the same geometric proof used on the real STL. Slow (full
CadQuery build), so it is marked accordingly and run on demand rather than every audit pass.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import trimesh

from fansim.audit.direction import REAL_FAN_CHIRALITY, prove_direction, tip_lead_sign
from fansim.geometry import build_impeller, export_stl
from fansim.geometry.config import load_blade_params

_ROOT = Path(__file__).resolve().parents[2]
_STOCK_PARAMS = _ROOT / "config" / "problems" / "a12x25_reference.yaml"


@pytest.mark.slow
def test_stock_impeller_is_built_with_designed_handedness(tmp_path):
    params = load_blade_params(_STOCK_PARAMS)
    stl = tmp_path / "stock_impeller.stl"
    export_stl(build_impeller(params), stl)
    mesh = trimesh.load(str(stl), force="mesh")

    p = prove_direction(mesh)
    assert p.verdict == "CONCLUSIVE", p.note
    assert (p.omega_sign, p.pump_sign, p.chirality) == (+1, -1, -1)
    assert p.chirality == REAL_FAN_CHIRALITY

    assert tip_lead_sign(mesh) == +1
