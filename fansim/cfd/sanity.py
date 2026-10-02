"""Cheap physics and setup sanity checks over a finished CFD case.

Each check is individually SKIP-able (missing data never crashes the caller) and reports
PASS / WARN / FAIL / SKIP. These are report-only: the optimizer flags a sanity FAIL, it
never rejects a design over it (see ``docs/superpowers/plans/2026-09-27-cfd-sanity-checks.md``).

Data sources:
- ``constant/case_meta.json`` (patch areas, duct shape, rpm/spin) written by ``build_case``.
- ``postProcessing/inletFlow`` / ``outletFlow`` (sum(phi)), ``postProcessing/yPlus`` — the
  extra function objects from Task 1.
- ``logs/checkMesh.log``.
- :class:`fansim.cfd.metrics.FanMetrics`, parsed via ``parse_fan_metrics`` when not supplied.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import trimesh

from fansim.cfd.metrics import RHO_AIR, FanMetrics, _pp_file, _tail_mean_row, parse_fan_metrics
from fansim.physics.air import C0_AIR

_BORE_Z_TOL_M = 1e-3
_PLENUM_TOL_M = 1e-3

PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"
SKIP = "SKIP"

_STATUS_RANK = {SKIP: 0, PASS: 1, WARN: 2, FAIL: 3}


@dataclass(frozen=True)
class SanityCheck:
    name: str
    status: str
    value: float | None
    limit: str
    note: str


def _load_case_meta(case_dir: Path) -> dict | None:
    path = case_dir / "constant" / "case_meta.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _omega_from_case_meta(case_meta: dict | None) -> float | None:
    if not case_meta:
        return None
    if case_meta.get("omega_signed") is not None:
        try:
            return float(case_meta["omega_signed"])
        except (TypeError, ValueError):
            return None
    if "rpm" not in case_meta or "spin" not in case_meta:
        return None
    try:
        return float(case_meta["rpm"]) * float(case_meta["spin"]) * 2.0 * math.pi / 60.0
    except (TypeError, ValueError):
        return None


_OMEGA_RE = re.compile(r"omega\s+([-+\d.eE]+);")
_VERTEX_RE = re.compile(r"\(\s*([-+\d.eE]+)\s+([-+\d.eE]+)\s+([-+\d.eE]+)\s*\)")


def _infer_omega(case_dir: Path) -> float | None:
    """omega from constant/MRFProperties. None for dual-MRF files (ambiguous) or missing."""
    path = case_dir / "constant" / "MRFProperties"
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    matches = _OMEGA_RE.findall(text)
    if len(matches) != 1:
        return None
    try:
        return float(matches[0])
    except ValueError:
        return None


def _infer_box_half_width_and_zmax(case_dir: Path) -> tuple[float, float] | None:
    """(H, domain z_max) from the first 8 vertices of system/blockMeshDict."""
    path = case_dir / "system" / "blockMeshDict"
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"vertices\s*\(", text)
    if not m:
        return None
    matches = _VERTEX_RE.findall(text[m.end():])
    if len(matches) < 8:
        return None
    try:
        verts = [(float(x), float(y), float(z)) for x, y, z in matches[:8]]
    except ValueError:
        return None
    h = max(abs(v[0]) for v in verts)
    z_max = max(v[2] for v in verts)
    return h, z_max


def _infer_domain_z_min(case_dir: Path) -> float | None:
    """Domain z_min from the first 8 blockMeshDict vertices (None if unreadable)."""
    path = case_dir / "system" / "blockMeshDict"
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"vertices\s*\(", text)
    matches = _VERTEX_RE.findall(text[m.end():]) if m else []
    try:
        return min(float(z) for _, _, z in matches[:8]) if len(matches) >= 8 else None
    except ValueError:
        return None


def _load_mesh(path: Path) -> "trimesh.Trimesh | None":
    if not path.exists():
        return None
    try:
        return trimesh.load(str(path), force="mesh")
    except Exception:
        return None


def _infer_tip_radius_m(case_dir: Path) -> float | None:
    """99.5th percentile of impeller.stl vertex radius (metres)."""
    mesh = _load_mesh(case_dir / "constant" / "triSurface" / "impeller.stl")
    if mesh is None or len(mesh.vertices) == 0:
        return None
    verts = np.asarray(mesh.vertices)
    radii = np.sqrt(verts[:, 0] ** 2 + verts[:, 1] ** 2)
    return float(np.percentile(radii, 99.5))


def _infer_bore_radius_m(casing_mesh: "trimesh.Trimesh") -> float | None:
    """Min radial distance of casing.stl vertices at its inlet (z_min) end."""
    verts = np.asarray(casing_mesh.vertices)
    if verts.shape[0] == 0:
        return None
    z_min = verts[:, 2].min()
    ring = verts[np.abs(verts[:, 2] - z_min) <= _BORE_Z_TOL_M]
    if ring.shape[0] == 0:
        return None
    radii = np.sqrt(ring[:, 0] ** 2 + ring[:, 1] ** 2)
    return float(radii.min())


def _infer_case_meta(case_dir: Path) -> dict | None:
    """Best-effort ``case_meta``-shaped dict for a legacy case built before Task 1.

    Returns None when there isn't even enough geometry (blockMeshDict) to infer areas.
    Anything else missing (MRFProperties, casing/impeller STLs) degrades individual
    fields to None rather than failing the whole inference.
    """
    volute = case_dir / "constant" / "volute_domain.json"
    if volute.is_file():
        # Radial blower in a sealed scroll: +Z plenum inlet feeding the eye, +X outlet stub. The
        # axial-duct inference below would invent a uniform duct inlet, so leave the duct-only
        # fields out (inlet bookkeeping / duct shape SKIP) and keep what the volute records.
        try:
            vd = json.loads(volute.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            vd = {}
        # The recorded outlet_area_m2 is the stub's inner section, but the stub ends short of the
        # +X face, so the solver's outlet patch is the whole face (~10x larger on the default
        # volute). Energy bookkeeping must use the patch the BC sits on, measured from the mesh.
        try:
            from fansim.cfd.duct_area import inlet_patch_area_m2

            out_area = inlet_patch_area_m2(case_dir, patch="outlet")
        except Exception:  # noqa: BLE001 - no mesh yet: energy check SKIPs
            out_area = None
        return {
            "topology": vd.get("topology", "volute_radial"),
            "outlet_area_m2": out_area,
            "outlet_stub_area_m2": vd.get("outlet_area_m2"),
            "tip_radius_m": vd.get("mrf_radius_m"),   # MRF zone just outside the tip: Mach bound
            "omega_signed": _infer_omega(case_dir),
            "inferred": True,
        }

    box = _infer_box_half_width_and_zmax(case_dir)
    if box is None:
        return None
    h, domain_z_max = box

    omega_signed = _infer_omega(case_dir)
    casing_mesh = _load_mesh(case_dir / "constant" / "triSurface" / "casing.stl")
    has_casing = casing_mesh is not None
    outlet_area = (2.0 * h) ** 2

    if has_casing:
        # The bore is the inlet only if the casing reaches the inlet face; a short ring leaves
        # the full box face as the inlet.
        z_verts = np.asarray(casing_mesh.vertices)[:, 2]
        domain_z_min = _infer_domain_z_min(case_dir)
        at_inlet = domain_z_min is None or float(z_verts.min()) <= domain_z_min + _PLENUM_TOL_M
        r_bore = _infer_bore_radius_m(casing_mesh) if at_inlet else None
        inlet_area = (math.pi * r_bore ** 2 if r_bore is not None else None) if at_inlet             else outlet_area
        casing_z_max = float(z_verts.max())
        plenum = at_inlet and casing_z_max < domain_z_max - _PLENUM_TOL_M
    else:
        inlet_area = outlet_area
        plenum = False

    return {
        "duct_shape": "round" if has_casing else "square",
        "box_half_width_m": h,
        "inlet_area_m2": inlet_area,
        "outlet_area_m2": outlet_area,
        "casing": has_casing,
        "plenum": plenum,
        "tip_radius_m": _infer_tip_radius_m(case_dir),
        "omega_signed": omega_signed,
        "inferred": True,
    }


def _check_mass_balance(case_dir: Path) -> SanityCheck:
    limit = "<=1% PASS, <=5% WARN"
    try:
        q_in = _tail_mean_row(_pp_file(case_dir, "inletFlow", "surfaceFieldValue.dat"))[-1]
        q_out = _tail_mean_row(_pp_file(case_dir, "outletFlow", "surfaceFieldValue.dat"))[-1]
    except (FileNotFoundError, ValueError):
        return SanityCheck("mass_balance", SKIP, None, limit, "missing inletFlow/outletFlow postProcessing")
    if abs(q_out) < 1e-12:
        return SanityCheck("mass_balance", SKIP, None, limit, "outlet flow ~0, imbalance undefined")
    imbalance_pct = abs(q_in + q_out) / abs(q_out) * 100.0
    status = PASS if imbalance_pct <= 1.0 else WARN if imbalance_pct <= 5.0 else FAIL
    note = f"Q_in={q_in:.5f} Q_out={q_out:.5f} m3/s"
    return SanityCheck("mass_balance", status, imbalance_pct, limit, note)


def _check_energy_total(metrics: FanMetrics | None, case_meta: dict | None) -> SanityCheck:
    limit = "eta_total < 1 (Q>0)"
    if metrics is None or not case_meta or not case_meta.get("outlet_area_m2"):
        return SanityCheck("energy_total", SKIP, None, limit, "missing metrics or outlet_area_m2")
    if metrics.flow_m3s <= 0:
        # Reversed flow makes the inlet an outflow boundary: the totalPressure BC then
        # sets static p = p0 there, so the forward-flow inlet formula (and this
        # forward-flow-only efficiency) don't apply. Not FAIL-ing this avoided false
        # 99-29000% FAILs on back-pressured/reversed solves.
        return SanityCheck("energy_total", SKIP, None, limit, "Q<=0, check only applies to forward flow")
    if metrics.shaft_power_w <= 1e-9:
        return SanityCheck("energy_total", SKIP, None, limit, "shaft power ~0")
    a_out = float(case_meta["outlet_area_m2"])
    q = metrics.flow_m3s
    p_out_static_pa = metrics.p_outlet_kin * RHO_AIR
    dyn_out = 0.5 * RHO_AIR * (q / a_out) ** 2
    eta_total = q * (p_out_static_pa + dyn_out) / metrics.shaft_power_w
    status = PASS if eta_total < 1.0 else FAIL
    note = f"eta_total={eta_total:.3f}"
    return SanityCheck("energy_total", status, eta_total, limit, note)


def _dual_omegas(case_dir: Path | None) -> tuple[float, float] | None:
    """(omega_front, omega_rear) from a dual-MRF MRFProperties (MRF1 = upstream), else None."""
    if case_dir is None:
        return None
    path = Path(case_dir) / "constant" / "MRFProperties"
    if not path.exists():
        return None
    found = _OMEGA_RE.findall(path.read_text(encoding="utf-8", errors="replace"))
    if len(found) != 2:
        return None
    try:
        return float(found[0]), float(found[1])
    except ValueError:
        return None


def _check_power_sign(metrics: FanMetrics | None, omega_signed: float | None,
                      case_dir: Path | None = None) -> SanityCheck:
    limit = "Mz*omega < 0 (Q>0)"
    if metrics is not None and metrics.moment_z_rear_nm is not None:
        # CROR: the net moment cancels between counter-rotating rotors, so check each rotor
        # against its own zone omega (both must be doing work on the air).
        omegas = _dual_omegas(case_dir)
        if omegas is None:
            return SanityCheck("power_sign", SKIP, None, limit, "dual rotor: zone omegas unknown")
        if metrics.flow_m3s <= 0:
            return SanityCheck("power_sign", SKIP, None, limit,
                               "Q<=0, check only applies to forward flow")
        m_rear = float(metrics.moment_z_rear_nm)
        m_front = float(metrics.moment_z_nm) - m_rear
        p_front, p_rear = m_front * omegas[0], m_rear * omegas[1]
        status = PASS if (p_front < 0 and p_rear < 0) else FAIL
        note = (f"front Mz={m_front:.5f} omega={omegas[0]:.3f} ({p_front:.5f}); "
                f"rear Mz={m_rear:.5f} omega={omegas[1]:.3f} ({p_rear:.5f})")
        return SanityCheck("power_sign", status, max(p_front, p_rear), limit, note)
    if metrics is None or omega_signed is None:
        return SanityCheck("power_sign", SKIP, None, limit, "missing metrics or omega_signed")
    if metrics.flow_m3s <= 0:
        return SanityCheck("power_sign", SKIP, None, limit, "Q<=0, check only applies to forward flow")
    product = metrics.moment_z_nm * omega_signed
    status = PASS if product < 0 else FAIL
    note = f"Mz={metrics.moment_z_nm:.5f} omega={omega_signed:.3f} product={product:.5f}"
    return SanityCheck("power_sign", status, product, limit, note)


def _check_thrust_direction(metrics: FanMetrics | None) -> SanityCheck:
    limit = "Fz < 0 (Q>0)"
    if metrics is None:
        return SanityCheck("thrust_direction", SKIP, None, limit, "missing metrics")
    if metrics.flow_m3s <= 0:
        return SanityCheck("thrust_direction", SKIP, None, limit, "Q<=0, check only applies to forward flow")
    status = PASS if metrics.thrust_n < 0 else FAIL
    note = f"Fz={metrics.thrust_n:.5f} N, Q={metrics.flow_m3s:.5f} m3/s"
    return SanityCheck("thrust_direction", status, metrics.thrust_n, limit, note)


def _check_inlet_bookkeeping(metrics: FanMetrics | None, case_meta: dict | None) -> SanityCheck:
    limit = "<=5% PASS, <=15% WARN (Q>0)"
    if metrics is None or not case_meta or not case_meta.get("inlet_area_m2"):
        return SanityCheck("inlet_bookkeeping", SKIP, None, limit, "missing metrics or inlet_area_m2")
    if metrics.flow_m3s <= 0:
        # On reversed flow the inlet becomes an outflow boundary: its totalPressure BC
        # then sets static p = p0 there, so the expected -1/2 rho (Q/A)^2 inflow formula
        # doesn't apply (this gave false FAILs of 99-29000% before the guard).
        return SanityCheck("inlet_bookkeeping", SKIP, None, limit, "Q<=0, check only applies to forward flow")
    a_in = float(case_meta["inlet_area_m2"])
    q = metrics.flow_m3s
    expected_pa = -0.5 * RHO_AIR * (q / a_in) ** 2
    actual_pa = metrics.p_inlet_kin * RHO_AIR
    if abs(expected_pa) < 1e-9:
        return SanityCheck("inlet_bookkeeping", SKIP, None, limit, "expected inlet static ~0")
    rel_err_pct = abs(actual_pa - expected_pa) / abs(expected_pa) * 100.0
    status = PASS if rel_err_pct <= 5.0 else WARN if rel_err_pct <= 15.0 else FAIL
    note = f"p_in={actual_pa:.3f} Pa expected={expected_pa:.3f} Pa"
    return SanityCheck("inlet_bookkeeping", status, rel_err_pct, limit, note)


_NON_ORTHO_RE = re.compile(r"non-orthogonality\s+Max:\s*([\d.]+)", re.IGNORECASE)
_SKEWNESS_RE = re.compile(r"Max skewness\s*=\s*([\d.]+)", re.IGNORECASE)
_FAILED_COUNT_RE = re.compile(r"Failed\s+(\d+)\s+mesh checks", re.IGNORECASE)


def _check_mesh_quality(case_dir: Path) -> SanityCheck:
    limit = '"Mesh OK." PASS; skewness-only failures WARN; other failures FAIL'
    path = case_dir / "logs" / "checkMesh.log"
    if not path.exists():
        return SanityCheck("mesh_quality", SKIP, None, limit, "missing logs/checkMesh.log")
    text = path.read_text(encoding="utf-8", errors="replace")
    non_ortho = _NON_ORTHO_RE.search(text)
    skewness = _SKEWNESS_RE.search(text)
    detail = (
        f"max non-orthogonality={non_ortho.group(1) if non_ortho else 'n/a'}, "
        f"Max skewness={skewness.group(1) if skewness else 'n/a'}"
    )
    if "Mesh OK." in text:
        return SanityCheck("mesh_quality", PASS, None, limit, detail)

    # Failing checks are reported as "***<description>" lines, e.g.
    # " ***Max skewness = 4.257074, 1 highly skew faces detected which may impair..."
    star_lines = [line.strip() for line in text.splitlines() if line.strip().startswith("***")]
    if not star_lines:
        return SanityCheck("mesh_quality", WARN, None, limit, f"inconclusive checkMesh output; {detail}")

    count_match = _FAILED_COUNT_RE.search(text)
    failed_count = int(count_match.group(1)) if count_match else len(star_lines)

    if all("skew" in line.lower() for line in star_lines):
        note = f"{failed_count} highly skew faces (skewness only); {detail}"
        return SanityCheck("mesh_quality", WARN, None, limit, note)

    note = f"{failed_count} failed checks: {'; '.join(star_lines)}; {detail}"
    return SanityCheck("mesh_quality", FAIL, None, limit, note)


def _read_yplus_dat(path: Path) -> list[tuple[float, str, float, float, float]]:
    rows: list[tuple[float, str, float, float, float]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        try:
            time = float(parts[0])
            patch = parts[1]
            vmin, vmax, vavg = float(parts[2]), float(parts[3]), float(parts[4])
        except ValueError:
            continue
        rows.append((time, patch, vmin, vmax, vavg))
    return rows


def _check_y_plus(case_dir: Path) -> SanityCheck:
    # k-omega SST with the omega wall function blends viscous-sublayer and log-law behaviour:
    # y+ <= 5 (resolved wall, e.g. prism layers) and 30-300 (log-law) are both valid; the buffer
    # region 5-30 and y+ > 300 are where the wall treatment is least trustworthy.
    limit = "<=5 or 30-300"
    try:
        path = _pp_file(case_dir, "yPlus", "yPlus.dat")
    except FileNotFoundError:
        return SanityCheck("y_plus", SKIP, None, limit, "missing postProcessing/yPlus")
    rows = _read_yplus_dat(path)
    if not rows:
        return SanityCheck("y_plus", SKIP, None, limit, "no data rows in yPlus.dat")
    latest_time = max(r[0] for r in rows)
    impeller_rows = [r for r in rows if r[1] == "impeller" and r[0] == latest_time]
    if not impeller_rows:
        return SanityCheck("y_plus", SKIP, None, limit, "no impeller rows in yPlus.dat")
    avg = impeller_rows[-1][4]
    resolved = avg <= 5.0
    log_law = 30.0 <= avg <= 300.0
    status = PASS if (resolved or log_law) else WARN
    regime = "resolved" if resolved else ("log-law" if log_law else "buffer/over-range")
    note = (f"y+ avg={avg:.2f} ({regime}; min={impeller_rows[-1][2]:.2f} "
            f"max={impeller_rows[-1][3]:.2f})")
    return SanityCheck("y_plus", status, avg, limit, note)


def _check_regime(case_meta: dict | None, omega_signed: float | None) -> SanityCheck:
    limit = "tip Mach < 0.3"
    if not case_meta or not case_meta.get("tip_radius_m") or omega_signed is None:
        return SanityCheck("regime", SKIP, None, limit, "missing tip_radius_m or omega_signed")
    tip_mach = abs(omega_signed) * float(case_meta["tip_radius_m"]) / C0_AIR
    status = PASS if tip_mach < 0.3 else WARN
    note = f"tip Mach={tip_mach:.3f}"
    return SanityCheck("regime", status, tip_mach, limit, note)


def _check_converged(metrics: FanMetrics | None) -> SanityCheck:
    limit = "FanMetrics.converged"
    if metrics is None:
        return SanityCheck("converged", SKIP, None, limit, "missing metrics")
    status = PASS if metrics.converged else WARN
    note = f"flow_drift_pct={metrics.flow_drift_pct:.2f}%, oscillation_pct={metrics.oscillation_pct:.2f}%"
    return SanityCheck("converged", status, None, limit, note)


def _check_duct_shape(case_meta: dict | None) -> SanityCheck:
    limit = "ring/round PASS, square WARN"
    if not case_meta or "duct_shape" not in case_meta:
        return SanityCheck("duct_shape", SKIP, None, limit, "missing case_meta.json")
    shape = case_meta["duct_shape"]
    status = PASS if shape in ("ring", "round") else WARN
    note = f"{shape} (meta inferred)" if case_meta.get("inferred") else shape
    if shape == "round":
        note = f"{note}; full-length noSlip duct adds pipe friction; not free-air"
    return SanityCheck("duct_shape", status, None, limit, note)


def run_sanity(
    case_dir: str | Path,
    *,
    metrics: FanMetrics | None = None,
    omega_signed: float | None = None,
) -> list[SanityCheck]:
    """Run every cheap sanity check over a CFD case directory.

    Missing data (files, ``case_meta.json``, an unparseable metrics set) SKIPs the affected
    check rather than raising. ``metrics``/``omega_signed`` may be supplied by the caller
    (e.g. the optimizer, which has already parsed metrics); otherwise they are derived from
    the case itself.
    """
    case_dir = Path(case_dir)
    case_meta = _load_case_meta(case_dir)
    if case_meta is None:
        case_meta = _infer_case_meta(case_dir)
    if omega_signed is None:
        omega_signed = _omega_from_case_meta(case_meta)
    if metrics is None and omega_signed is not None:
        try:
            metrics = parse_fan_metrics(case_dir, omega_rad_s=abs(omega_signed))
        except (FileNotFoundError, ValueError, ZeroDivisionError):
            metrics = None

    return [
        _check_mass_balance(case_dir),
        _check_energy_total(metrics, case_meta),
        _check_power_sign(metrics, omega_signed, case_dir),
        _check_thrust_direction(metrics),
        _check_inlet_bookkeeping(metrics, case_meta),
        _check_mesh_quality(case_dir),
        _check_y_plus(case_dir),
        _check_regime(case_meta, omega_signed),
        _check_converged(metrics),
        _check_duct_shape(case_meta),
    ]


def overall(checks: list[SanityCheck]) -> str:
    """Worst status across ``checks``: FAIL > WARN > PASS; SKIP is ignored unless it's all there is."""
    if not checks:
        return SKIP
    non_skip = [c.status for c in checks if c.status != SKIP]
    if not non_skip:
        return SKIP
    return max(non_skip, key=lambda s: _STATUS_RANK[s])


def summarize(checks: list[SanityCheck]) -> str:
    """One line: overall status, then each WARN/FAIL check's headline detail."""
    status = overall(checks)
    parts = []
    for c in checks:
        if c.status not in (WARN, FAIL):
            continue
        if c.value is not None:
            parts.append(f"{c.name} {c.value:.3g} ({c.limit})")
        else:
            parts.append(f"{c.name} {c.note}")
    detail = "; ".join(parts) if parts else "no WARN/FAIL checks"
    return f"sanity {status}: {detail}"
