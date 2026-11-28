"""Parse OpenFOAM postProcessing output into fan performance metrics.

Reads the ``forces`` (force/moment) and ``surfaceFieldValue`` (flow, inlet/outlet
pressure) function-object outputs and derives CFM, static-pressure rise, torque, shaft
power, and aerodynamic efficiency.
"""

from __future__ import annotations

import json
import math
import re
import warnings
from dataclasses import asdict, dataclass
from pathlib import Path

from fansim.physics.air import RHO_AMCA as RHO_AIR

# Exact NIST SP 811 international-foot conversion: 1 ft == 0.3048 m exact (#87).
CFM_PER_M3S = 60.0 / (0.3048**3)  # ft^3/min per m^3/s (~2118.880003289315)

# Solver/metrics generation stamped on every scored trial (optimize/study.py + cockpit Assess),
# so the catalog can tell which results are trustworthy. Bump when a change makes previously stored
# CFD numbers non-comparable; results with a lower/absent version are STALE (needs re-Assess).
#   1 (implicit / unstamped) — original: final-iteration-sample metrics + fixed coarse surface mesh.
#   2 (2026-09-18) — converged-tail-MEAN metrics (_tail_mean_row) + adaptive blade-wall mesh
#                    (openfoam_case.MeshResolution.for_blade). Free-air on the a12x25 refit moved
#                    from an under-read ~30 CFM to ~45+ CFM, so v1 objectives are not comparable.
#   3 (2026-09-25) — Audit #1 fix: rotor solved in its designed rotation (flipped 180° about X,
#                    spin −1; fansim/cfd/orientation.py); MRF zone fitted to the real rotor STL;
#                    convergence judged on tail-mean stability (oscillation reported separately).
#   4 (2026-09-27) — sealed round duct by default (was square slip-wall tunnel with open corners
#                    around the tips); casing corners sealed.
#   5 (2026-09-27) — short sealed frame ring (25 mm) around the rotor, slip box walls elsewhere;
#                    v4 full-length noSlip duct gave pipe friction.
#   6 (2026-10-20) — R1.7 print hub: validate/score/export grow min_hub_height below the blades.
#                    Auto-hub scores are a different trailing edge; do not migrate them.
#   7 (2026-11-27) — #86: AMCA 210 / ISO 5801 fan static pressure P_s = p_s2 - p_t1. On
#                    totalPressure inlets P_s = (p_out - p0_in) * rho (0 Pa at free delivery
#                    instead of +0.5*rho*|U_in|^2); on zeroGradient inlets with inlet_area_m2,
#                    P_s = (p_out - p_in) * rho - 0.5 * rho * (Q / A_in)^2. Aligns P_t = P_s + p_d2
#                    and both two-point fan-line endpoints on the same pressure convention.
CFD_VERSION = 7

TAIL_FRAC = 0.25  # fraction of the run treated as the converged tail (see convergence())

# Non-vanishing reference scale floors for relative tail-mean shift / oscillation (ASME V&V 20 /
# Roache 1998; #88). Above these floors the denominator is exact |mean|; near zero (shut-off flow,
# free-delivery pressure, stationary torque) the floor prevents 0/0 singularities.
FLOW_SCALE_FLOOR_M3S = 1e-4       # ~0.21 CFM (~0.35% of a 60 CFM fan)
PRESSURE_KIN_SCALE_FLOOR = 0.5    # m^2/s^2 (~0.6 Pa at rho=1.2)
TORQUE_SCALE_FLOOR_NM = 1e-4      # N*m (~1% of a 0.01 N*m fan)


def _all_data_rows(path: Path) -> list[list[float]]:
    """Every fully-numeric row of an OpenFOAM .dat file (vector parens stripped)."""
    rows: list[list[float]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Strip any OpenFOAM vector parentheses, then split on whitespace.
        fields = line.replace("(", " ").replace(")", " ").split()
        try:
            rows.append([float(x) for x in fields])
        except ValueError:
            continue
    if not rows:
        raise ValueError(f"no data rows in {path}")
    return rows


def _tail_mean_row(path: Path, tail_frac: float = TAIL_FRAC) -> list[float]:
    """Column-wise mean of the converged tail (last ``tail_frac``) of a .dat file.

    A steady RANS solve near stall settles into a small limit cycle rather than a fixed
    point; its meaningful value is the time-mean over that cycle, not the final-iteration
    phase sample. Reporting the tail mean makes oscillating solves reproducible run-to-run
    (two runs stopping at different cycle phases otherwise report different numbers). Uses
    the same tail window as :func:`convergence`. Rows whose column count differs from the
    last row are dropped defensively.
    """
    rows = _all_data_rows(path)
    ncol = len(rows[-1])
    rows = [r for r in rows if len(r) == ncol]
    tail = rows[max(1, int(len(rows) * (1.0 - tail_frac))):] or rows[-1:]
    return [sum(r[i] for r in tail) / len(tail) for i in range(ncol)]


def latest_pp_file(case_dir: Path, fo_name: str, filename: str) -> Path:
    """Newest postProcessing time-directory instance, sorted by numeric time (QA-39)."""
    candidates = list((Path(case_dir) / "postProcessing" / fo_name).glob(f"*/{filename}"))
    if not candidates:
        raise FileNotFoundError(f"missing postProcessing/{fo_name}/*/{filename}")

    def _time_key(path: Path) -> float:
        try:
            return float(path.parent.name)
        except ValueError:
            return float("-inf")

    return max(candidates, key=_time_key)


def _pp_file(case_dir: Path, fo_name: str, filename: str) -> Path:
    """Find the newest time-directory instance of a postProcessing file."""
    return latest_pp_file(case_dir, fo_name, filename)


@dataclass
class FanMetrics:
    """Derived fan-performance metrics at one operating point."""

    flow_m3s: float
    cfm: float
    static_pressure_rise_pa: float
    thrust_n: float
    torque_nm: float
    shaft_power_w: float
    air_power_w: float
    efficiency: float
    p_inlet_kin: float
    p_outlet_kin: float
    converged: bool = True
    # Tail-mean shift %: the two halves of the converged tail's mean, relative to the tail
    # mean (see convergence()). This is what `converged` judges. The raw peak-to-peak swing
    # of a limit-cycling solve is reported separately in oscillation_pct.
    flow_drift_pct: float = 0.0
    # Total (static+dynamic) efficiency when known; None until a caller sets it or a
    # future parse path computes ΔP_total. point_row passes this through as-is.
    eta_total: float | None = None
    # Signed fluid moment on the impeller about +Z (N·m). A fan doing work on the air has
    # moment_z_nm * omega_signed < 0. torque_nm stays |moment_z| for power.
    moment_z_nm: float = 0.0
    # Peak-to-peak flow over the converged tail as a % of its mean (pre-v3 "drift"). A thin-
    # blade steady RANS solve settles into a limit cycle rather than a fixed point; this is
    # the swing within that cycle, reported but not judged (see convergence()).
    oscillation_pct: float = 0.0
    # CROR only: downstream rotor's own moment about z (``moment_z_nm`` is then the net of both).
    moment_z_rear_nm: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _optional_pp_file(case_dir: Path, fo_name: str, filename: str) -> Path | None:
    """Newest postProcessing file if present, else ``None``."""
    try:
        return latest_pp_file(case_dir, fo_name, filename)
    except FileNotFoundError:
        return None


def _column_trajectory(path: Path, *, col: int, min_cols: int) -> list[float]:
    """Extract one numeric column across all valid rows of an OpenFOAM .dat file."""
    vals: list[float] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.replace("(", " ").replace(")", " ").split()
        if len(parts) < min_cols:
            continue
        try:
            vals.append(float(parts[col]))
        except ValueError:
            continue
    return vals


def _tail_slice(vals: list[float], tail_frac: float) -> list[float]:
    """Last ``tail_frac`` of a trajectory (empty if fewer than 4 total samples)."""
    if len(vals) < 4:
        return []
    return vals[max(1, int(len(vals) * (1.0 - tail_frac))):]


def _flow_trajectory(case_dir: Path) -> list[tuple[float, float]]:
    """(iteration, outlet flow) history from the outletFlow function object."""
    path = _pp_file(case_dir, "outletFlow", "surfaceFieldValue.dat")
    traj: list[tuple[float, float]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.replace("(", " ").replace(")", " ").split()
        if len(parts) < 2:
            continue
        try:
            traj.append((float(parts[0]), float(parts[-1])))
        except ValueError:
            continue
    return traj


def _tail_flows(case_dir: Path, tail_frac: float) -> list[float]:
    traj = _flow_trajectory(Path(case_dir))
    if len(traj) < 4:
        return []
    return [f for _, f in traj[max(1, int(len(traj) * (1.0 - tail_frac))):]]


def _half_mean_shift_pct(values: list[float], scale_floor: float) -> float:
    """Two-half tail-mean shift as % of ``max(|mean|, scale_floor)``."""
    h = len(values) // 2
    m1 = sum(values[:h]) / h
    m2 = sum(values[h:]) / (len(values) - h)
    mean = sum(values) / len(values)
    return abs(m2 - m1) / max(abs(mean), scale_floor) * 100.0


def convergence(case_dir: str | Path, tail_frac: float = TAIL_FRAC,
                tol_pct: float = 2.0) -> tuple[bool, float]:
    """Are all available QoI tail MEANS stable? Returns ``(converged, worst_shift_pct)``.

    Steady RANS on thin blades settles into a limit cycle rather than a fixed point. The
    reported metrics are tail means, so convergence judges those means across every available
    engineering QoI (ASME V&V 20-2009 / #88): mandatory ``outletFlow``, plus pressure rise
    (``outletP - inletP``) and rotor torque (``forces/moment.dat``, CROR ``forcesRear/moment.dat``)
    whenever present. Each QoI uses a non-vanishing physical scale floor so near-zero regimes
    (shut-off flow, free-delivery pressure) do not divide by zero. The flow swing itself is
    reported by :func:`oscillation_pct`.
    """
    if not (math.isfinite(tail_frac) and 0.0 < tail_frac <= 1.0):
        raise ValueError(f"tail_frac must be in (0, 1], got {tail_frac!r}")
    if not (math.isfinite(tol_pct) and tol_pct > 0.0):
        raise ValueError(f"tol_pct must be finite and > 0, got {tol_pct!r}")
    case_path = Path(case_dir)
    flows = _tail_flows(case_path, tail_frac)
    if len(flows) < 4:
        return (False, 999.0)
    shifts = [_half_mean_shift_pct(flows, FLOW_SCALE_FLOOR_M3S)]

    # Secondary QoI 1: pressure rise (outletP - inletP), closing the FIELD_U fixed-flow blind spot.
    p_in_path = _optional_pp_file(case_path, "inletP", "surfaceFieldValue.dat")
    p_out_path = _optional_pp_file(case_path, "outletP", "surfaceFieldValue.dat")
    if p_in_path is not None and p_out_path is not None:
        p_in_tail = _tail_slice(_column_trajectory(p_in_path, col=-1, min_cols=2), tail_frac)
        p_out_tail = _tail_slice(_column_trajectory(p_out_path, col=-1, min_cols=2), tail_frac)
        if len(p_in_tail) < 4 or len(p_out_tail) < 4:
            return (False, 999.0)
        n_p = min(len(p_in_tail), len(p_out_tail))
        dp_tail = [po - pi for po, pi in zip(p_out_tail[-n_p:], p_in_tail[-n_p:])]
        shifts.append(_half_mean_shift_pct(dp_tail, PRESSURE_KIN_SCALE_FLOOR))
    elif p_in_path is not None or p_out_path is not None:
        p_path = p_in_path if p_in_path is not None else p_out_path
        assert p_path is not None
        p_tail = _tail_slice(_column_trajectory(p_path, col=-1, min_cols=2), tail_frac)
        if len(p_tail) < 4:
            return (False, 999.0)
        shifts.append(_half_mean_shift_pct(p_tail, PRESSURE_KIN_SCALE_FLOOR))

    # Secondary QoI 2: rotor torque Mz (and CROR rear rotor torque when present).
    for fo_name in ("forces", "forcesRear"):
        m_path = _optional_pp_file(case_path, fo_name, "moment.dat")
        if m_path is not None:
            mz_tail = _tail_slice(_column_trajectory(m_path, col=3, min_cols=4), tail_frac)
            if len(mz_tail) < 4:
                return (False, 999.0)
            shifts.append(_half_mean_shift_pct(mz_tail, TORQUE_SCALE_FLOOR_NM))

    worst = max(shifts)
    return (worst < tol_pct, worst)


def oscillation_pct(case_dir: str | Path, tail_frac: float = TAIL_FRAC) -> float:
    """Peak-to-peak flow over the tail as a % of ``max(|mean|, FLOW_SCALE_FLOOR_M3S)``."""
    if not (math.isfinite(tail_frac) and 0.0 < tail_frac <= 1.0):
        raise ValueError(f"tail_frac must be in (0, 1], got {tail_frac!r}")
    flows = _tail_flows(Path(case_dir), tail_frac)
    if len(flows) < 4:
        return 999.0
    mean = sum(flows) / len(flows)
    return (max(flows) - min(flows)) / max(abs(mean), FLOW_SCALE_FLOOR_M3S) * 100.0


_RHO_INF_RE = re.compile(r"\brhoInf\s+([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*;")
_INLET_BLOCK_RE = re.compile(r"\binlet\s*\{([^}]*)\}", re.DOTALL)
_INLET_P0_RE = re.compile(r"\bp0\s+uniform\s+([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)")


def _case_meta_areas(case_dir: Path) -> tuple[float | None, float | None]:
    """Read ``(inlet_area_m2, outlet_area_m2)`` from ``constant/case_meta.json`` when present."""
    meta_path = case_dir / "constant" / "case_meta.json"
    if not meta_path.is_file():
        return None, None
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, None
    if not isinstance(meta, dict):
        return None, None

    def _pos(key: str) -> float | None:
        raw = meta.get(key)
        if raw is None:
            return None
        try:
            v = float(raw)
        except (TypeError, ValueError):
            return None
        return v if math.isfinite(v) and v > 0.0 else None

    return _pos("inlet_area_m2"), _pos("outlet_area_m2")


def _inlet_p_bc(case_dir: Path) -> tuple[str | None, float]:
    """Return ``(bc_type, p0_kin)`` from ``0/p``'s ``inlet`` block, or ``(None, 0.0)`` if absent."""
    p_path = case_dir / "0" / "p"
    if not p_path.is_file():
        return None, 0.0
    try:
        text = p_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None, 0.0
    m = _INLET_BLOCK_RE.search(text)
    if m is None:
        return None, 0.0
    body = m.group(1)
    if "totalPressure" in body:
        p0_m = _INLET_P0_RE.search(body)
        if p0_m is not None:
            try:
                p0 = float(p0_m.group(1))
            except ValueError:
                p0 = 0.0
            if math.isfinite(p0):
                return "totalPressure", p0
        return "totalPressure", 0.0
    if "zeroGradient" in body:
        return "zeroGradient", 0.0
    return None, 0.0


def _control_dict_rho_inf(case_dir: Path) -> float | None:
    """Read ``rhoInf`` from ``system/controlDict`` when present (OpenFOAM forces scaling)."""
    cd = case_dir / "system" / "controlDict"
    if not cd.is_file():
        return None
    try:
        text = cd.read_text(encoding="utf-8")
    except OSError:
        return None
    match = _RHO_INF_RE.search(text)
    if match is None:
        return None
    try:
        val = float(match.group(1))
    except ValueError:
        return None
    return val if math.isfinite(val) and val > 0.0 else None


def parse_fan_metrics(
    case_dir: str | Path,
    omega_rad_s: float,
    rho: float = RHO_AIR,
    *,
    outlet_area_m2: float | None = None,
) -> FanMetrics:
    """Parse OpenFOAM postProcessing outputs into :class:`FanMetrics`.

    Parameters
    ----------
    case_dir:
        OpenFOAM case directory containing ``postProcessing/{forces,outletFlow,inletP,outletP}``.
    omega_rad_s:
        Rotor angular speed magnitude [rad/s] (must be finite and non-negative).
        For counter-rotating (CROR) cases where ``postProcessing/forcesRear`` is present,
        ``torque_nm = |M_z,front| + |M_z,rear|`` and ``shaft_power_w = torque_nm * omega_rad_s``
        assume equal rotor speeds ``|omega_front| == |omega_rear| == omega_rad_s`` and that
        neither rotor is windmilling (checked separately by ``fansim.cfd.sanity._check_power_sign``).
    rho:
        Air density [kg/m^3] (must be finite and positive) used to scale kinematic pressures.
        OpenFOAM's ``forces`` functionObject bakes ``rhoInf`` from ``system/controlDict`` into
        ``force.dat`` / ``moment.dat``; a ``UserWarning`` is emitted if ``rho`` disagrees with
        ``controlDict``'s ``rhoInf`` (or ``RHO_AIR`` when absent).
    outlet_area_m2:
        Optional outlet patch area [m^2] used to populate ISO 5801 / AMCA 210 total efficiency
        ``eta_total``. When omitted, ``case_meta.json`` is consulted if present.

    Notes
    -----
    ``static_pressure_rise_pa`` follows ANSI/AMCA 210-16 §3.2 / ISO 5801:2017 §3.1.24 fan static
    pressure ``P_s = p_s2 - p_t1`` (``CFD_VERSION = 7``, #86):

    - ``totalPressure`` inlet in ``0/p``: ``P_s = (p_out - p0_in) * rho`` (``0 Pa`` at free
      delivery when ``p0 = 0``).
    - ``zeroGradient`` inlet in ``0/p`` with ``inlet_area_m2`` in ``case_meta.json``:
      ``P_s = (p_out - p_in) * rho - 0.5 * rho * (Q / A_in)^2``.
    - Fallback when ``0/p`` (or ``zeroGradient`` ``inlet_area_m2``) is absent: duct
      static-to-static ``(p_out - p_in) * rho``.

    ``eta_total`` uses ISO 5801 / AMCA 210 fan total pressure ``P_t = P_s + 0.5 * rho * (Q / A_out)^2``.
    """
    if not math.isfinite(omega_rad_s) or omega_rad_s < 0.0:
        raise ValueError(f"omega_rad_s must be finite and non-negative, got {omega_rad_s!r}")
    if not math.isfinite(rho) or rho <= 0.0:
        raise ValueError(f"rho must be finite and positive, got {rho!r}")
    if outlet_area_m2 is not None and (not math.isfinite(outlet_area_m2) or outlet_area_m2 <= 0.0):
        raise ValueError(f"outlet_area_m2 must be finite and positive, got {outlet_area_m2!r}")
    case_dir = Path(case_dir)

    rho_inf = _control_dict_rho_inf(case_dir)
    if rho_inf is not None and not math.isclose(rho, rho_inf, rel_tol=1e-6, abs_tol=1e-9):
        warnings.warn(
            f"parse_fan_metrics rho={rho:g} differs from system/controlDict "
            f"rhoInf={rho_inf:g}; OpenFOAM forces/moments keep rhoInf baked in "
            "while static_pressure_rise_pa uses rho",
            UserWarning,
            stacklevel=2,
        )
    elif rho_inf is None and not math.isclose(rho, RHO_AIR, rel_tol=1e-6, abs_tol=1e-9):
        warnings.warn(
            f"parse_fan_metrics rho={rho:g} differs from default RHO_AIR={RHO_AIR:g} "
            "and no system/controlDict rhoInf was found; ensure forces/moments "
            "were solved with the same rhoInf",
            UserWarning,
            stacklevel=2,
        )

    # Report the converged-tail MEAN of every metric, not the final-iteration sample:
    # near stall the steady solve limit-cycles, so a phase snapshot is not reproducible.
    moment = _tail_mean_row(_pp_file(case_dir, "forces", "moment.dat"))
    force = _tail_mean_row(_pp_file(case_dir, "forces", "force.dat"))
    # Layout: time, total(x,y,z), pressure(x,y,z), viscous(x,y,z).
    torque = abs(moment[3])  # total moment about z
    thrust = force[3]  # total force z
    moment_z = moment[3]
    moment_z_rear = None
    if (case_dir / "postProcessing" / "forcesRear").is_dir():
        # CROR: each rotor has its own motor and the two react in opposite senses, so the net
        # moment cancels. Shaft power is the sum of |M_z| * omega over the rotors (Audit #7).
        moment_r = _tail_mean_row(_pp_file(case_dir, "forcesRear", "moment.dat"))
        force_r = _tail_mean_row(_pp_file(case_dir, "forcesRear", "force.dat"))
        moment_z_rear = moment_r[3]
        torque = abs(moment[3]) + abs(moment_r[3])
        thrust = force[3] + force_r[3]
        moment_z = moment[3] + moment_r[3]

    flow = _tail_mean_row(_pp_file(case_dir, "outletFlow", "surfaceFieldValue.dat"))[-1]
    p_in = _tail_mean_row(_pp_file(case_dir, "inletP", "surfaceFieldValue.dat"))[-1]
    p_out = _tail_mean_row(_pp_file(case_dir, "outletP", "surfaceFieldValue.dat"))[-1]

    meta_a_in, meta_a_out = _case_meta_areas(case_dir)
    a_out = float(outlet_area_m2) if outlet_area_m2 is not None else meta_a_out
    bc_type, p0_in = _inlet_p_bc(case_dir)

    # Keep flow SIGNED: under a back-pressure beyond the fan's capability the flow reverses
    # (negative), which must read as a failure, not be masked by abs().
    # AMCA 210 / ISO 5801 fan static pressure P_s = p_s2 - p_t1 (CFD_VERSION 7, #86).
    if bc_type == "totalPressure":
        static_rise_pa = (p_out - p0_in) * rho
    elif bc_type == "zeroGradient" and meta_a_in is not None:
        static_rise_pa = (p_out - p_in) * rho - 0.5 * rho * (flow / meta_a_in) ** 2
    else:
        static_rise_pa = (p_out - p_in) * rho

    shaft_power = torque * omega_rad_s
    # Guard against double-negative (flow < 0 and static_rise_pa < 0) giving positive air power (#86).
    air_power = flow * static_rise_pa if flow > 0.0 else -abs(flow * static_rise_pa)
    efficiency = air_power / shaft_power if shaft_power > 1e-9 else 0.0
    converged, drift = convergence(case_dir)

    eta_total: float | None = None
    if a_out is not None and flow > 0.0 and shaft_power > 1e-9:
        dyn_out = 0.5 * rho * (flow / a_out) ** 2
        if bc_type == "totalPressure" or (bc_type == "zeroGradient" and meta_a_in is not None):
            p_total_pa = static_rise_pa + dyn_out
            eta_total = flow * p_total_pa / shaft_power
        elif bc_type is None:
            p_total_pa = p_out * rho + dyn_out
            eta_total = flow * p_total_pa / shaft_power

    return FanMetrics(
        flow_m3s=flow,
        cfm=flow * CFM_PER_M3S,
        static_pressure_rise_pa=static_rise_pa,
        thrust_n=thrust,
        torque_nm=torque,
        shaft_power_w=shaft_power,
        air_power_w=air_power,
        efficiency=efficiency,
        p_inlet_kin=p_in,
        p_outlet_kin=p_out,
        converged=converged,
        flow_drift_pct=drift,
        eta_total=eta_total,
        moment_z_nm=moment_z,
        moment_z_rear_nm=moment_z_rear,
        oscillation_pct=oscillation_pct(case_dir),
    )
