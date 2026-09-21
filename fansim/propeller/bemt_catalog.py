"""Approximate dia×pitch BEMT static CT/CP and vendored UIUC PropDB fixtures (Track A A3)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fansim.geometry.blade import BladeParams
from fansim.prop_spec import PropShaftMount, PropSpec
from fansim.propeller.bemt import RHO_AIR, analyze
from fansim.propeller.geometry import prop_blade_params
from fansim.propeller.polar import nondim

ROOT = Path(__file__).resolve().parents[2]
UIUC_DIR = ROOT / "validation" / "reference" / "uiuc_propdb"
DEFAULT_UIUC_FIXTURE_ID = "apcsf_9x4.7_static"
BAND_REL_A3 = 0.35
MM_PER_IN = 25.4


def approximate_prop_blade(
    diameter_in: float, pitch_in: float, *, blade_count: int = 2
) -> BladeParams:
    dia_mm = float(diameter_in) * MM_PER_IN
    hub_dia_mm = max(0.15 * dia_mm, 8.0)
    shaft = PropShaftMount(
        shaft_dia_mm=5.0, hub_bore_dia_mm=5.0, hub_dia_mm=hub_dia_mm
    )
    spec = PropSpec(
        name=f"approx_{diameter_in}x{pitch_in}x{blade_count}",
        diameter_in=float(diameter_in),
        pitch_in=float(pitch_in),
        n_blades=int(blade_count),
        shaft=shaft,
        rpm_max=max(10000.0, float(diameter_in) * 2000.0),
    )
    return prop_blade_params(spec)


def bemt_static_ct_cp(
    diameter_in: float,
    pitch_in: float,
    *,
    rpm: float,
    blade_count: int = 2,
    rho: float = RHO_AIR,
) -> dict[str, Any]:
    blade = approximate_prop_blade(diameter_in, pitch_in, blade_count=blade_count)
    perf = analyze(blade, rpm=float(rpm), v_forward=0.0, rho=float(rho))
    d_m = float(diameter_in) * MM_PER_IN / 1000.0
    nd = nondim(
        perf.thrust_n,
        perf.power_w,
        rpm=float(rpm),
        diameter_m=d_m,
        v_inf=0.0,
        rho=float(rho),
    )
    return {
        "ct": float(nd["CT"]),
        "cp": float(nd["CP"]),
        "thrust_n": float(perf.thrust_n),
        "power_w": float(perf.power_w),
        "rpm": float(rpm),
        "diameter_in": float(diameter_in),
        "pitch_in": float(pitch_in),
        "blade_count": int(blade_count),
        "geometry_match": "approximate",
        "j": 0.0,
        "rho": float(rho),
    }


def load_uiuc_static_fixture(path_or_id: str | Path | None = None) -> dict[str, Any]:
    if path_or_id is None:
        path = UIUC_DIR / f"{DEFAULT_UIUC_FIXTURE_ID}.json"
    else:
        p = Path(path_or_id)
        path = (
            p
            if p.suffix.lower() == ".json" or p.is_file()
            else UIUC_DIR / f"{path_or_id}.json"
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in ("prop_id", "diameter_in", "pitch_in", "rpm", "ct", "cp"):
        if key not in data or data[key] is None:
            raise ValueError(f"UIUC fixture missing {key}: {path}")
    return data


def compare_bemt_to_static_witness(
    *,
    diameter_in: float,
    pitch_in: float,
    rpm: float,
    ct_w: float,
    cp_w: float,
    band_rel: float = BAND_REL_A3,
    source: str,
    prop_id: str,
    blade_count: int = 2,
) -> dict[str, Any]:
    bemt = bemt_static_ct_cp(
        diameter_in, pitch_in, rpm=rpm, blade_count=blade_count
    )
    ct_b, cp_b = float(bemt["ct"]), float(bemt["cp"])
    ct_w, cp_w = float(ct_w), float(cp_w)
    if ct_w <= 0.0 or cp_w <= 0.0:
        raise ValueError("witness ct/cp must be > 0")
    rel_ct = abs(ct_b - ct_w) / ct_w
    rel_cp = abs(cp_b - cp_w) / cp_w
    ok = rel_ct <= float(band_rel) and rel_cp <= float(band_rel)
    return {
        "pass": ok,
        "ct_bemt": ct_b,
        "cp_bemt": cp_b,
        "ct_w": ct_w,
        "cp_w": cp_w,
        "rel_err_ct": rel_ct,
        "rel_err_cp": rel_cp,
        "band_rel": float(band_rel),
        "geometry_match": "approximate",
        "source": source,
        "prop_id": prop_id,
        "rpm": float(rpm),
        "diameter_in": float(diameter_in),
        "pitch_in": float(pitch_in),
        "detail": (
            f"CT rel_err={rel_ct:.4f} CP rel_err={rel_cp:.4f} "
            f"band={band_rel} ({'PASS' if ok else 'FAIL'})"
        ),
    }


def _quorum_q6_apc() -> dict[str, Any] | None:
    """Task 3: BEMT vs PyThrust APC static CT/CP."""
    return None


def run_bemt_catalog_quorum(*, include_apc: bool = True) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    fx = load_uiuc_static_fixture()
    q7 = compare_bemt_to_static_witness(
        diameter_in=float(fx["diameter_in"]),
        pitch_in=float(fx["pitch_in"]),
        rpm=float(fx["rpm"]),
        ct_w=float(fx["ct"]),
        cp_w=float(fx["cp"]),
        source="uiuc_fixture",
        prop_id=str(fx["prop_id"]),
        blade_count=int(fx.get("blade_count", 2)),
    )
    checks.append({"id": "Q7", **q7})
    if include_apc:
        q6 = _quorum_q6_apc()
        if q6 is not None:
            checks.append(q6)
    all_pass = all(c.get("pass") is True for c in checks)
    return {"checks": checks, "all_pass": all_pass}
