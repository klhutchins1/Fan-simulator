"""Audit #1, proof 1 on the real rotors: Stock recipe STL + close-ref STL.

Checks (each True / False / None=unclear):
  real_handedness      chirality == REAL_FAN_CHIRALITY (model is not a mirror image of the real fan)
  motor_on_exhaust     motor_side == pump_sign (air leaves past the motor, like the real Noctua)
  tips_lead            tip_lead_sign == omega_sign (user-confirmed: real A12x25 tips lead the rotation)
  cfd_spin_matches     TestRig default spin == designed omega_sign (CFD turns it the designed way)
  cfd_pumps_plus_z     pump_sign == +1 (designed delivery matches the duct's inlet -Z -> outlet +Z)
  motor_rotation_consistent  chirality * motor_side == omega_sign (air leaves past motor; pump=motor_side, chi*pump=omega)
                       -- algebraically redundant with motor_on_exhaust whenever the proof is
                       CONCLUSIVE, since pump_sign == motor_side in that case and
                       chi == omega_sign * pump_sign identically; it adds no information beyond
                       motor_on_exhaust and real_handedness, but is kept as a cheap cross-check.

Usage:
    uv run python scripts/audit_direction_geometry.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import trimesh  # noqa: E402

from fansim.audit.direction import (  # noqa: E402
    REAL_FAN_CHIRALITY,
    motor_side,
    prove_direction,
    tip_lead_sign,
)
from fansim.cfd.domain import TestRig  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "validation" / "audits" / "direction_geometry.json"
STOCK_PARAMS = ROOT / "config" / "problems" / "a12x25_reference.yaml"
REF_STL = ROOT / "validation" / "reference" / "a12x25_impeller.stl"
STOCK_STL = ROOT / "runs" / "audit_direction" / "stock_impeller.stl"


def _stock_stl() -> Path:
    if not STOCK_STL.is_file():
        from fansim.geometry import build_impeller, export_stl
        from fansim.geometry.config import load_blade_params
        STOCK_STL.parent.mkdir(parents=True, exist_ok=True)
        export_stl(build_impeller(load_blade_params(STOCK_PARAMS)), STOCK_STL)
    return STOCK_STL


def _tri(a, b):
    return None if a is None or b is None else bool(a == b)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    spin_in_use = TestRig.__dataclass_fields__["spin"].default
    rotors = {}
    for name, path in (("stock", _stock_stl()), ("reference_stl", REF_STL)):
        mesh = trimesh.load(str(path), force="mesh")
        p = prove_direction(mesh)
        ms = motor_side(mesh)
        tl = tip_lead_sign(mesh)
        rotors[name] = {
            "stl": str(path.relative_to(ROOT)),
            "stl_sha256": _sha256(path),
            "omega_sign": p.omega_sign, "pump_sign": p.pump_sign, "chirality": p.chirality,
            "verdict": p.verdict, "note": p.note, "agreement": p.agreement,
            "n_sections": p.n_sections, "motor_side": ms, "tip_lead_sign": tl,
            "checks": {
                "real_handedness": _tri(p.chirality, REAL_FAN_CHIRALITY),
                "motor_on_exhaust": _tri(ms, p.pump_sign),
                "tips_lead": _tri(tl, p.omega_sign),
                "cfd_spin_matches": _tri(spin_in_use, p.omega_sign),
                "cfd_pumps_plus_z": _tri(p.pump_sign, 1),
                "motor_rotation_consistent": _tri(None if ms is None or p.chirality is None else p.chirality * ms, p.omega_sign),
            },
        }
        print(f"[{name}] {p.verdict}: rotate {p.omega_sign}, pump {p.pump_sign}, chi {p.chirality},"
              f" motor {ms} — {p.note}\n    checks {rotors[name]['checks']}", flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"rotors": rotors, "cfd_spin_in_use": spin_in_use}, indent=2) + "\n",
                   encoding="utf-8")
    print(f"-> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
