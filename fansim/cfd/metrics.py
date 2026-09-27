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
CFD_VERSION = 4

TAIL_FRAC = 0.25  # fraction of the run treated as the converged tail (see convergence())


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


def _last_data_row(path: Path) -> list[float]:
    """Return the numeric fields of the last non-comment row of an OpenFOAM .dat file."""
    return _all_data_rows(path)[-1]


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


def _tail_flows(case_dir: Path, tail_frac: float) -> list[float]:
    traj = _flow_trajectory(Path(case_dir))
    if len(traj) < 4:
        return []
    return [f for _, f in traj[max(1, int(len(traj) * (1.0 - tail_frac))):]]


def convergence(case_dir: str | Path, tail_frac: float = TAIL_FRAC,
                tol_pct: float = 2.0) -> tuple[bool, float]:
    """Is the integrated flow's tail MEAN stable? Returns (converged, mean_shift_pct).

    Steady RANS on thin blades settles into a limit cycle rather than a fixed point. The
    reported metrics are the tail mean, so convergence judges that mean: split the tail into
    two halves, and call it converged when their means agree within ``tol_pct`` of the tail
    mean. The swing itself is reported by :func:`oscillation_pct`.
    """
    flows = _tail_flows(Path(case_dir), tail_frac)
    if len(flows) < 4:
        return (False, 999.0)
    h = len(flows) // 2
    m1, m2 = sum(flows[:h]) / h, sum(flows[h:]) / (len(flows) - h)
    mean = sum(flows) / len(flows)
    shift = abs(m2 - m1) / (abs(mean) + 1e-12) * 100.0
    return (shift < tol_pct, shift)


def oscillation_pct(case_dir: str | Path, tail_frac: float = TAIL_FRAC) -> float:
    """Peak-to-peak flow over the tail as a % of its mean (the pre-v3 'drift')."""
    flows = _tail_flows(Path(case_dir), tail_frac)
    if len(flows) < 4:
        return 999.0
    mean = sum(flows) / len(flows)
    return (max(flows) - min(flows)) / (abs(mean) + 1e-12) * 100.0


def parse_fan_metrics(
    case_dir: str | Path, omega_rad_s: float, rho: float = RHO_AIR
) -> FanMetrics:
    case_dir = Path(case_dir)

    # Report the converged-tail MEAN of every metric, not the final-iteration sample:
    # near stall the steady solve limit-cycles, so a phase snapshot is not reproducible.
    moment = _tail_mean_row(_pp_file(case_dir, "forces", "moment.dat"))
    force = _tail_mean_row(_pp_file(case_dir, "forces", "force.dat"))
    # Layout: time, total(x,y,z), pressure(x,y,z), viscous(x,y,z).
    torque = abs(moment[3])  # total moment about z
    thrust = force[3]  # total force z

    flow = _tail_mean_row(_pp_file(case_dir, "outletFlow", "surfaceFieldValue.dat"))[-1]
    p_in = _tail_mean_row(_pp_file(case_dir, "inletP", "surfaceFieldValue.dat"))[-1]
    p_out = _tail_mean_row(_pp_file(case_dir, "outletP", "surfaceFieldValue.dat"))[-1]

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
        moment_z_nm=moment[3],
        oscillation_pct=oscillation_pct(case_dir),
    )
