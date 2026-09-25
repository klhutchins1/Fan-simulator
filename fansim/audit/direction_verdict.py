"""Audit #1, proof 3: verdict from the {as_built, flipped} x {spin -1, +1} free-air CFD matrix.

A 180° flip about X maps body rotation omega -> -omega, so each physical rotation sense appears
twice: once pumping +Z through the proper BCs (total-pressure inlet at -Z, static outlet at +Z) and
once pumping -Z (easier, biased BCs). Senses are compared only on their proper (+Z, positive CFM)
runs. The designed sense must win by ``margin`` on CFM and also on CFM per shaft watt, and must match
the geometric proof.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class MatrixRow:
    orientation: str  # "as_built" | "flipped"
    spin: int
    cfm: float
    converged: bool
    shaft_power_w: float
    moment_z_nm: float
    omega_signed: float


def body_sense(row: MatrixRow) -> int:
    if row.orientation not in ("as_built", "flipped"):
        raise ValueError(f"Invalid orientation: {row.orientation!r}")
    return row.spin if row.orientation == "as_built" else -row.spin


def _key(s: int) -> str:
    return f"{s:+d}"


def matrix_verdict(rows: list[MatrixRow], geometry_omega: int | None, *,
                   geometry_pump: int | None, margin: float = 0.20) -> dict:
    reasons: list[str] = []
    proper: dict[int, MatrixRow] = {}
    improper: dict[int, MatrixRow] = {}
    for sense in (+1, -1):
        mine = [r for r in rows if body_sense(r) == sense]
        pos = [r for r in mine if r.cfm > 0]
        neg = [r for r in mine if r.cfm <= 0]
        if len(pos) != 1 or len(neg) != 1:
            reasons.append(f"sense {_key(sense)}: expected one +Z and one -Z run, got "
                           f"{[(r.orientation, r.spin, r.cfm) for r in mine]}")
            continue
        proper[sense], improper[sense] = pos[0], neg[0]
    out = {
        "verdict": "INCONCLUSIVE", "designed_sense": None,
        "proper": {_key(s): r.cfm for s, r in proper.items()},
        "bc_bias_cfm": {_key(s): round(abs(improper[s].cfm) - proper[s].cfm, 3)
                        for s in proper if s in improper},
        "power_sign_ok": False,
        "recommended": None, "reasons": reasons,
    }
    if len(proper) != 2:
        return out
    # Check for non-finite values in proper runs
    for sense, row in proper.items():
        if not (math.isfinite(row.cfm) and math.isfinite(row.shaft_power_w) and math.isfinite(row.moment_z_nm)):
            reasons.append(f"sense {_key(sense)}: non-finite value in proper run "
                           f"(cfm={row.cfm}, power={row.shaft_power_w}, moment_z={row.moment_z_nm})")
            return out
    if not all(r.converged for r in proper.values()):
        reasons.append("a proper (+Z) run did not converge")
        return out
    out["power_sign_ok"] = all(r.moment_z_nm * r.omega_signed < 0 for r in proper.values())
    if not out["power_sign_ok"]:
        reasons.append("moment_z * omega >= 0 on a delivering run: fluid driving the rotor")
        return out
    win, lose = sorted(proper, key=lambda s: proper[s].cfm, reverse=True)
    w, lo = proper[win], proper[lose]
    if w.cfm < (1.0 + margin) * lo.cfm:
        reasons.append(f"CFM margin {w.cfm / lo.cfm - 1:.0%} < {margin:.0%}")
        return out
    if w.cfm / max(w.shaft_power_w, 1e-9) <= lo.cfm / max(lo.shaft_power_w, 1e-9):
        reasons.append("winner does not also win CFM per watt")
        return out
    out["designed_sense"] = win
    out["recommended"] = {"orientation": w.orientation, "spin": w.spin}
    if geometry_pump is None:
        reasons.append("geometric pump direction unknown")
        return out
    if geometry_omega is None:
        reasons.append("geometric proof inconclusive; CFD alone is not a verdict")
        return out
    # Check orientation against geometry prediction
    # As built, sense s pumps geometry_pump * geometry_omega * s in Z
    # The designed sense pumps +Z as built iff geometry_pump * geometry_omega * win > 0
    expected_orientation = "as_built" if geometry_pump * geometry_omega * win > 0 else "flipped"
    if w.orientation != expected_orientation:
        reasons.append(f"orientation mismatch: CFD says {w.orientation}, "
                       f"geometry predicts {expected_orientation}")
        return {"verdict": "FAIL", "designed_sense": win, "proper": out["proper"],
                "bc_bias_cfm": out["bc_bias_cfm"], "power_sign_ok": out["power_sign_ok"],
                "recommended": out["recommended"], "reasons": reasons}
    out["verdict"] = "PASS" if geometry_omega == win else "FAIL"
    if out["verdict"] == "FAIL":
        reasons.append(f"CFD says sense {_key(win)}, geometry says {_key(geometry_omega)}")
    return out
