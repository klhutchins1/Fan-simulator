"""Air is room-temperature sea-level air, derived from first principles, and nobody forks it."""

from __future__ import annotations

import ast
import math
import re
from pathlib import Path

import pytest

from fansim.physics import air

ROOT = Path(__file__).resolve().parents[2]
NAME_RE = re.compile(r"^(RHO(_AIR)?|NU(_AIR)?|MU(_AIR)?|C0(_AIR)?|C_SOUND|SPEED_OF_SOUND)$")

# Local copies that existed on 2026-09-24 (spec finding). Consolidating them is a later change;
# this list may only SHRINK. Values must still agree with fansim.physics.air.
KNOWN_COPIES = {
    ("fansim/acoustics/farfield.py", "C0_AIR"), ("fansim/acoustics/proxies.py", "RHO_AIR"),
    ("fansim/acoustics/proxies.py", "C0_AIR"), ("fansim/cfd/des_fwh.py", "RHO_AIR"),
    ("fansim/cfd/metrics.py", "RHO_AIR"), ("fansim/cfd/openfoam_case.py", "RHO_AIR"),
    ("fansim/cfd/openfoam_case.py", "NU_AIR"), ("fansim/fan_bem.py", "RHO_AIR"),
    ("fansim/fan_bem.py", "NU_AIR"), ("fansim/physics/regime.py", "NU_AIR"),
    ("fansim/physics/regime.py", "C0_AIR"), ("fansim/propeller/bemt.py", "RHO_AIR"),
    ("fansim/propeller/bemt.py", "NU_AIR"), ("fansim/propeller/noise.py", "C_SOUND"),
    ("fansim/propeller/power.py", "RHO_AIR"), ("fansim/wind_turbine/evaluate.py", "RHO_AIR"),
    ("scripts/evaluate_noise.py", "C0"), ("scripts/fan_noise_curle.py", "C0"), ("scripts/fan_noise_cv.py", "C0"),
}


def _air_constants_in(source: str) -> dict[str, float]:
    """Parse air constants from source code (plain, annotated, and tuple assignments)."""
    found: dict[str, float] = {}
    for node in ast.parse(source).body:
        # Plain assignment: RHO_AIR = 1.2
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, (int, float)):
            for t in node.targets:
                if isinstance(t, ast.Name) and NAME_RE.match(t.id):
                    found[t.id] = float(node.value.value)
        # Annotated assignment: RHO_AIR: float = 1.2
        elif isinstance(node, ast.AnnAssign) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, (int, float)):
            if isinstance(node.target, ast.Name) and NAME_RE.match(node.target.id):
                found[node.target.id] = float(node.value.value)
        # Tuple unpacking: RHO_AIR, NU_AIR = 1.2, 1.5e-5
        elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Tuple):
            for t in node.targets:
                if isinstance(t, ast.Tuple) and len(t.elts) == len(node.value.elts):
                    for name_node, val_node in zip(t.elts, node.value.elts):
                        if isinstance(name_node, ast.Name) and NAME_RE.match(name_node.id) \
                                and isinstance(val_node, ast.Constant) \
                                and isinstance(val_node.value, (int, float)):
                            found[name_node.id] = float(val_node.value)
    return found


def _module_level_air_constants() -> dict[tuple[str, str], float]:
    found: dict[tuple[str, str], float] = {}
    for top in ("fansim", "scripts"):
        for f in sorted((ROOT / top).rglob("*.py")):
            rel = f.relative_to(ROOT).as_posix()
            if rel == "fansim/physics/air.py":
                continue
            constants = _air_constants_in(f.read_text(encoding="utf-8"))
            for name, val in constants.items():
                found[(rel, name)] = val
    return found


def test_density_is_ideal_gas_at_room_conditions():
    rho = air.P0_PA / (air.R_AIR * air.T_ROOM_K)
    assert air.RHO_AMCA == pytest.approx(rho, rel=0.01)          # 1.204 at 20 °C
    assert air.RHO_ISA == pytest.approx(air.P0_PA / (air.R_AIR * 288.15), rel=0.01)


def test_speed_of_sound_is_ideal_gas():
    assert air.C0_AIR == pytest.approx(math.sqrt(air.GAMMA_AIR * air.R_AIR * air.T_ROOM_K), rel=0.005)


def test_viscosity_matches_sutherland_and_nu_is_mu_over_rho():
    t = air.T_ROOM_K
    mu = 1.458e-6 * t**1.5 / (t + 110.4)
    assert air.MU_AIR == pytest.approx(mu, rel=0.02)
    assert air.NU_AIR == pytest.approx(air.MU_AIR / air.RHO_AMCA, rel=0.03)


def test_not_water_not_mars():
    # Water: rho ~1000, nu ~1e-6, c ~1480. Mars surface: rho ~0.02, c ~240.
    assert 1.0 < air.RHO_AMCA < 1.3 and 1.0e-5 < air.NU_AIR < 2.0e-5 and 330 < air.C0_AIR < 350


def test_detector_catches_annotated_and_tuple_forms():
    # Test that the detector catches annotated and tuple assignment forms
    source = """
RHO_AIR: float = 1.2
NU_AIR, MU_AIR = 1.5e-5, 1.81e-5
C0_AIR = 1.2 * 2  # computed, should not be caught
IGNORED_VAR = 5.0
"""
    found = _air_constants_in(source)
    assert found == {"RHO_AIR": 1.2, "NU_AIR": 1.5e-5, "MU_AIR": 1.81e-5}
    assert "C0_AIR" not in found, "computed values should not be caught"
    assert "IGNORED_VAR" not in found, "non-air constants should not be caught"


def test_no_new_local_copies():
    new = set(_module_level_air_constants()) - KNOWN_COPIES
    assert not new, f"import these from fansim.physics.air instead of redefining: {sorted(new)}"


def test_existing_copies_agree_with_single_source():
    allowed = {
        "RHO": {air.RHO_AMCA, air.RHO_ISA}, "NU": {air.NU_AIR}, "MU": {air.MU_AIR},
        "C0": {air.C0_AIR}, "C_SOUND": {air.C0_AIR}, "SPEED_OF_SOUND": {air.C0_AIR},
    }
    bad = []
    for (rel, name), val in _module_level_air_constants().items():
        key = name.split("_AIR")[0]
        if val not in allowed[key]:
            bad.append(f"{rel}:{name}={val}")
    assert not bad, bad
