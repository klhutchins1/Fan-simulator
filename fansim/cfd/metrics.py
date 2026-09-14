# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Parse OpenFOAM postProcessing output into fan performance metrics.

Reads the ``forces`` (force/moment) and ``surfaceFieldValue`` (flow, inlet/outlet
pressure) function-object outputs and derives CFM, static-pressure rise, torque, shaft
power, and aerodynamic efficiency.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

CFM_PER_M3S = 2118.882  # ft^3/min per m^3/s
RHO_AIR = 1.2


def _last_data_row(path: Path) -> list[float]:
    """Return the numeric fields of the last non-comment row of an OpenFOAM .dat file."""
    last: list[float] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Strip any OpenFOAM vector parentheses, then split on whitespace.
        fields = line.replace("(", " ").replace(")", " ").split()
        try:
            last = [float(x) for x in fields]
        except ValueError:
            continue
    if last is None:
        raise ValueError(f"no data rows in {path}")
    return last


def _pp_file(case_dir: Path, fo_name: str, filename: str) -> Path:
    """Find the newest time-directory instance of a postProcessing file."""
    candidates = sorted((case_dir / "postProcessing" / fo_name).glob(f"*/{filename}"))
    if not candidates:
        raise FileNotFoundError(f"missing postProcessing/{fo_name}/*/{filename}")
    return candidates[-1]


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
    flow_drift_pct: float = 0.0
    # Total (static+dynamic) efficiency when known; None until a caller sets it or a
    # future parse path computes ΔP_total. point_row passes this through as-is.
    eta_total: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _flow_trajectory(case_dir: Path) -> list[tuple[float, float]]:
    """(iteration, outlet flow) history from the outletFlow function object."""
    path = _pp_file(case_dir, "outletFlow", "surfaceFieldValue.dat")
    traj: list[tuple[float, float]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.replace("(", " ").replace(")", " ").split()
        try:
            traj.append((float(parts[0]), float(parts[-1])))
        except (ValueError, IndexError):
            continue
    return traj


def convergence(case_dir: str | Path, tail_frac: float = 0.25,
                tol_pct: float = 2.0) -> tuple[bool, float]:
    """Is the integrated flow steady over the last ``tail_frac`` of iterations?

    Returns (converged, drift_pct). A steady RANS solve near stall can plateau its residuals
    while the integrated flow is still drifting (or flipping stall->attached); this catches
    that. drift_pct is the peak-to-peak flow range over the tail as a % of its mean.
    """
    traj = _flow_trajectory(Path(case_dir))
    if len(traj) < 4:
        return (False, 999.0)
    tail = traj[max(1, int(len(traj) * (1.0 - tail_frac))):]
    flows = [f for _, f in tail]
    mean = sum(flows) / len(flows)
    drift = (max(flows) - min(flows)) / (abs(mean) + 1e-12) * 100.0
    return (drift < tol_pct, drift)


def parse_fan_metrics(
    case_dir: str | Path, omega_rad_s: float, rho: float = RHO_AIR
) -> FanMetrics:
    case_dir = Path(case_dir)

    moment = _last_data_row(_pp_file(case_dir, "forces", "moment.dat"))
    force = _last_data_row(_pp_file(case_dir, "forces", "force.dat"))
    # Layout: time, total(x,y,z), pressure(x,y,z), viscous(x,y,z).
    torque = abs(moment[3])  # total moment about z
    thrust = force[3]  # total force z

    flow = _last_data_row(_pp_file(case_dir, "outletFlow", "surfaceFieldValue.dat"))[-1]
    p_in = _last_data_row(_pp_file(case_dir, "inletP", "surfaceFieldValue.dat"))[-1]
    p_out = _last_data_row(_pp_file(case_dir, "outletP", "surfaceFieldValue.dat"))[-1]

    # Keep flow SIGNED: under a back-pressure beyond the fan's capability the flow reverses
    # (negative), which must read as a failure, not be masked by abs().
    static_rise_pa = (p_out - p_in) * rho  # kinematic (m^2/s^2) -> Pa
    shaft_power = torque * omega_rad_s
    air_power = flow * static_rise_pa
    efficiency = air_power / shaft_power if shaft_power > 1e-9 else 0.0
    converged, drift = convergence(case_dir)

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
    )
