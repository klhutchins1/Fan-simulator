"""Spanwise + blade-to-blade CFD post-processing (roadmap §20.3).

TCAE-style Turbo Blade Post for ducted axial fans:
  * Circumferentially averaged total pressure, axial / swirl velocity, and
    incidence / deviation vs radius (exit / inlet planes).
  * Blade-to-blade static-pressure coefficient Cp at 3–5 span stations.

Built on the same reconstruct readiness as ``fansim.cfd.midplane`` so the Fan
cockpit can show these after Assess when volume fields are still on disk.
Primary diagnostic: *where* along the span free-air work (a12x25 gap) is lost.

OpenFOAM incompressible convention: ``p`` is kinematic (Pa / ρ). Total pressure
is ``p0 = p + 0.5 |U|^2``. Cp uses the same kinematic scaling.
"""

from __future__ import annotations

import json
import math
import threading
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from fansim.cfd.midplane import case_has_flow_fields, ensure_reconstructed
from fansim.physics.air import RHO_AMCA

_VIZ_SUBDIR = Path("postProcessing") / "cockpit_viz"
_SPANWISE_NAME = "spanwise_avg_v2.png"  # v2: blade-relative planes (27.3e)
_B2B_NAME = "b2b_cp_v1.png"
# Matplotlib Agg is not fully thread-safe with concurrent figure creation on Windows.
_PLOT_LOCK = threading.Lock()

# Default span fractions for blade-to-blade cuts (hub→tip). Five stations covers
# hub / mid / tip plus two intermediates without crowding the PNG.
DEFAULT_SPAN_STATIONS = (0.25, 0.40, 0.55, 0.70, 0.85)
DEFAULT_N_RADIAL = 28
DEFAULT_N_THETA = 72
DEFAULT_N_Z_B2B = 48
# Plane offsets (PLANE_Z_FRAC) and slab_half_width are single-sourced in fansim.cfd.flow_report.
# Radial half-width of the cylindrical shell for blade-to-blade, as frac of span.
_B2B_SHELL_FRAC = 0.035


@dataclass(frozen=True)
class SpanwiseProfile:
    """Circumferentially averaged profiles vs radius."""

    r_m: np.ndarray
    r_frac: np.ndarray
    p0_kin: np.ndarray
    u_axial: np.ndarray
    u_swirl: np.ndarray
    beta_in_deg: np.ndarray
    beta_ex_deg: np.ndarray
    incidence_deg: np.ndarray | None
    deviation_deg: np.ndarray | None
    metal_deg: np.ndarray | None
    hub_r_m: float
    tip_r_m: float
    omega: float
    z_in_m: float
    z_ex_m: float


@dataclass(frozen=True)
class BladeToBladeSlice:
    """Unrolled blade-to-blade Cp at one span station."""

    r_frac: float
    r_m: float
    theta_deg: np.ndarray
    z_m: np.ndarray
    cp: np.ndarray  # shape (n_z, n_theta); NaN where empty


@dataclass(frozen=True)
class SpanwiseArtifacts:
    """Paths to cached spanwise / blade-to-blade PNGs."""

    case_dir: Path
    spanwise_png: Path | None
    b2b_png: Path | None
    caption: str
    available: bool
    profile: SpanwiseProfile | None = None


def spanwise_artifact_path(case_dir: str | Path) -> Path:
    return Path(case_dir) / _VIZ_SUBDIR / _SPANWISE_NAME


def b2b_artifact_path(case_dir: str | Path) -> Path:
    return Path(case_dir) / _VIZ_SUBDIR / _B2B_NAME


def find_cached_spanwise(case_dir: str | Path) -> SpanwiseArtifacts | None:
    """Return artifacts when cached PNGs already exist on disk."""
    case_dir = Path(case_dir)
    span_png = spanwise_artifact_path(case_dir)
    b2b_png = b2b_artifact_path(case_dir)
    span = span_png if span_png.is_file() else None
    b2b = b2b_png if b2b_png.is_file() else None
    if span is None and b2b is None:
        return None
    cap = (
        "spanwise averages — p0 / Uz / swirl / incidence vs radius"
        if span
        else "blade-to-blade Cp — span stations"
    )
    return SpanwiseArtifacts(
        case_dir=case_dir,
        spanwise_png=span,
        b2b_png=b2b,
        caption=cap,
        available=True,
    )


# ---------------------------------------------------------------------------
# Case metadata helpers
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def load_case_radii_omega(case_dir: str | Path) -> tuple[float, float, float]:
    """``(hub_r_m, tip_r_m, omega_signed)`` from case_meta / design.json / defaults.

    Defaults (37.25 mm hub / 55 mm tip / 2000 RPM CCW) match the a12x25-class
    stock envelope so synthetic meshes without meta still produce plots.
    """
    case_dir = Path(case_dir)
    # Stock a12x25: hub Ø 37.25 mm → r = 0.018625 m; tip Ø 110 mm → r = 0.055 m.
    hub = 0.018625
    tip = 0.055
    omega = 2000.0 * 2.0 * math.pi / 60.0  # +ω (CCW from +Z) typical MRF sign after orientation

    meta = _load_json(case_dir / "constant" / "case_meta.json")
    if meta:
        if meta.get("hub_radius_m") is not None:
            try:
                hub = float(meta["hub_radius_m"])
            except (TypeError, ValueError):
                pass
        if meta.get("tip_radius_m") is not None:
            try:
                tip = float(meta["tip_radius_m"])
            except (TypeError, ValueError):
                pass
        if meta.get("omega_signed") is not None:
            try:
                omega = float(meta["omega_signed"])
            except (TypeError, ValueError):
                pass
        elif "rpm" in meta and "spin" in meta:
            try:
                omega = float(meta["rpm"]) * float(meta["spin"]) * 2.0 * math.pi / 60.0
            except (TypeError, ValueError):
                pass

    design = _load_json(case_dir / "design.json")
    if design:
        params = design.get("params") or {}
        if isinstance(params, dict):
            if params.get("hub_radius") is not None:
                try:
                    hub = float(params["hub_radius"]) * 1e-3  # mm → m
                except (TypeError, ValueError):
                    pass
            if params.get("tip_radius") is not None:
                try:
                    tip = float(params["tip_radius"]) * 1e-3
                except (TypeError, ValueError):
                    pass
            if params.get("rpm") is not None and meta is None:
                try:
                    rpm = float(params["rpm"])
                    omega = rpm * 2.0 * math.pi / 60.0
                except (TypeError, ValueError):
                    pass

    if tip <= hub:
        tip = hub + 0.01
    return hub, tip, omega


def metal_angle_from_stagger_deg(stagger_deg: float | np.ndarray) -> float | np.ndarray:
    """Metal angle from axial [deg].

    Recipe stagger is measured from the *circumferential* direction
    (0° = in the rotation plane, 90° = axial) — see ``section_compare``.
    Cascade metal angle from axial is therefore ``κ = 90 − stagger``.
    """
    return 90.0 - np.asarray(stagger_deg, dtype=float)


def load_metal_angles_deg(
    case_dir: str | Path,
    r_frac: np.ndarray,
) -> np.ndarray | None:
    """Interpolate metal angle κ(r) [deg from axial] from design.json stagger stations.

    Returns None when stagger root/mid/tip are unavailable.
    """
    design = _load_json(Path(case_dir) / "design.json")
    if not design:
        return None
    params = design.get("params") or {}
    if not isinstance(params, dict):
        return None
    keys = ("stagger_root", "stagger_mid", "stagger_tip")
    if not all(k in params for k in keys):
        # Single mid value is enough to paint a constant metal angle.
        if "stagger_mid" in params:
            try:
                k = metal_angle_from_stagger_deg(float(params["stagger_mid"]))
            except (TypeError, ValueError):
                return None
            return np.full(np.asarray(r_frac).shape, k, dtype=float)
        return None
    try:
        staggers = np.array(
            [float(params["stagger_root"]), float(params["stagger_mid"]), float(params["stagger_tip"])],
            dtype=float,
        )
    except (TypeError, ValueError):
        return None
    metal = metal_angle_from_stagger_deg(staggers)
    stations = np.array([0.0, 0.5, 1.0], dtype=float)
    return np.interp(np.asarray(r_frac, dtype=float), stations, metal)


# ---------------------------------------------------------------------------
# Field extraction / cylindrical kinematics
# ---------------------------------------------------------------------------


def _mesh_centers_up(mesh) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return ``(points, U, p)`` at cell centers. Raises if U is missing."""
    g = mesh
    if "U" in g.point_data and "U" not in g.cell_data:
        g = g.point_data_to_cell_data()
    if "U" not in g.cell_data and "U" not in g.point_data:
        raise KeyError("mesh has no U field")
    if hasattr(g, "cell_centers") and "U" in g.cell_data:
        centers = g.cell_centers()
        pts = np.asarray(centers.points, dtype=float)
        u = np.asarray(centers["U"], dtype=float)
        if "p" in centers.array_names or "p" in getattr(centers, "point_data", {}):
            p = np.asarray(centers["p"], dtype=float)
        elif "p" in g.cell_data:
            p = np.asarray(g.cell_data["p"], dtype=float)
            if p.shape[0] != pts.shape[0]:
                p = np.zeros(pts.shape[0], dtype=float)
        else:
            p = np.zeros(pts.shape[0], dtype=float)
    else:
        # Point-data fallback (PolyData / injected clouds).
        pts = np.asarray(g.points, dtype=float)
        src = g.point_data if "U" in g.point_data else g.cell_data
        u = np.asarray(src["U"], dtype=float)
        p = np.asarray(src["p"], dtype=float) if "p" in src else np.zeros(pts.shape[0])
    if u.ndim == 1:
        u = u.reshape(-1, 1)
    if u.shape[1] < 3:
        pad = np.zeros((u.shape[0], 3), dtype=float)
        pad[:, : u.shape[1]] = u
        u = pad
    p = np.asarray(p, dtype=float).reshape(-1)
    if p.shape[0] != pts.shape[0]:
        p = np.zeros(pts.shape[0], dtype=float)
    return pts, u, p


def cylindrical_velocity(pts: np.ndarray, u: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """``(r, u_axial, u_swirl)`` from Cartesian ``U``. Swirl is the θ-component."""
    x = pts[:, 0]
    y = pts[:, 1]
    r = np.sqrt(x * x + y * y)
    r_safe = np.maximum(r, 1e-12)
    u_ax = u[:, 2]
    # ê_θ = (−y/r, x/r, 0)
    u_th = (-u[:, 0] * y + u[:, 1] * x) / r_safe
    return r, u_ax, u_th


def relative_flow_angle_deg(
    u_axial: np.ndarray,
    u_swirl: np.ndarray,
    r: np.ndarray,
    omega: float,
) -> np.ndarray:
    """Relative flow angle β from axial [deg]: ``atan2(W_θ, W_z)``.

    ``W_θ = U_θ − ω r`` with ω along +Z (OpenFOAM MRF sign).
    """
    w_th = np.asarray(u_swirl, dtype=float) - float(omega) * np.asarray(r, dtype=float)
    w_z = np.asarray(u_axial, dtype=float)
    return np.degrees(np.arctan2(w_th, w_z))


def total_pressure_kin(p: np.ndarray, u: np.ndarray) -> np.ndarray:
    """Kinematic total pressure ``p + 0.5 |U|^2``."""
    mag2 = np.sum(np.asarray(u, dtype=float) ** 2, axis=1)
    return np.asarray(p, dtype=float) + 0.5 * mag2


def _blade_z(case_dir, hub_r):
    from fansim.cfd.flow_report_case import blade_z_extent
    return blade_z_extent(case_dir, hub_r=hub_r)


def _plane_mask(pts: np.ndarray, z0: float, half_dz: float) -> np.ndarray:
    return np.abs(pts[:, 2] - z0) <= half_dz


def circumferential_mean_vs_radius(
    pts: np.ndarray,
    values: dict[str, np.ndarray],
    *,
    hub_r: float,
    tip_r: float,
    n_radial: int = DEFAULT_N_RADIAL,
    z0: float | None = None,
    half_dz: float | None = None,
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Bin cell samples into radial rings; return ``(r_centers, {name: mean})``.

    When ``z0`` is set, only cells within ``half_dz`` of that plane contribute.
    Empty bins become NaN.
    """
    hub_r = float(hub_r)
    tip_r = float(tip_r)
    n_radial = max(3, int(n_radial))
    r = np.sqrt(pts[:, 0] ** 2 + pts[:, 1] ** 2)
    mask = (r >= hub_r) & (r <= tip_r)
    if z0 is not None:
        hz = float(half_dz) if half_dz is not None else max(0.02 * (tip_r - hub_r), 0.002)
        mask = mask & _plane_mask(pts, float(z0), hz)
    edges = np.linspace(hub_r, tip_r, n_radial + 1)
    centers = 0.5 * (edges[:-1] + edges[1:])
    out: dict[str, np.ndarray] = {k: np.full(n_radial, np.nan) for k in values}
    if not np.any(mask):
        return centers, out
    r_m = r[mask]
    idx = np.clip(np.digitize(r_m, edges) - 1, 0, n_radial - 1)
    for name, arr in values.items():
        a = np.asarray(arr, dtype=float).reshape(-1)[mask]
        for i in range(n_radial):
            sel = idx == i
            if np.any(sel):
                out[name][i] = float(np.mean(a[sel]))
    return centers, out


def compute_spanwise_profile(
    pts: np.ndarray,
    u: np.ndarray,
    p: np.ndarray,
    *,
    hub_r: float,
    tip_r: float,
    omega: float,
    metal_deg: np.ndarray | None = None,
    n_radial: int = DEFAULT_N_RADIAL,
    z_fan: float = 0.0,
    blade_z: tuple[float, float] | None = None,
) -> SpanwiseProfile:
    """Circumferential averages + incidence/deviation vs radius from point samples."""
    hub_r = float(hub_r)
    tip_r = float(tip_r)
    span = max(tip_r - hub_r, 1e-6)
    from fansim.cfd.flow_report import (  # same planes as the flow report card (27.3e)
        slab_centres,
        slab_half_width,
    )

    half_dz = slab_half_width(tip_r)
    z_in, z_ex = slab_centres(tip_r=tip_r, z_fan=z_fan, blade_z=blade_z)

    _r, u_ax, u_th = cylindrical_velocity(pts, u)
    p0 = total_pressure_kin(p, u)

    r_ex, ex = circumferential_mean_vs_radius(
        pts,
        {"p0": p0, "uz": u_ax, "uth": u_th},
        hub_r=hub_r, tip_r=tip_r, n_radial=n_radial, z0=z_ex, half_dz=half_dz,
    )
    r_in, inn = circumferential_mean_vs_radius(
        pts,
        {"uz": u_ax, "uth": u_th},
        hub_r=hub_r, tip_r=tip_r, n_radial=n_radial, z0=z_in, half_dz=half_dz,
    )
    # Prefer exit radii; fall back if exit plane was empty.
    r_m = r_ex
    if np.all(np.isnan(ex["p0"])) and not np.all(np.isnan(inn["uz"])):
        r_m = r_in
        ex = {
            "p0": circumferential_mean_vs_radius(
                pts, {"p0": p0}, hub_r=hub_r, tip_r=tip_r, n_radial=n_radial,
                z0=z_in, half_dz=half_dz,
            )[1]["p0"],
            "uz": inn["uz"],
            "uth": inn["uth"],
        }

    r_frac = (r_m - hub_r) / span
    beta_in = relative_flow_angle_deg(inn["uz"], inn["uth"], r_in, omega)
    beta_ex = relative_flow_angle_deg(ex["uz"], ex["uth"], r_m, omega)

    metal = None
    incidence = None
    deviation = None
    if metal_deg is not None:
        metal = np.asarray(metal_deg, dtype=float)
        if metal.shape != r_frac.shape:
            metal = np.interp(
                r_frac,
                np.linspace(0.0, 1.0, metal.shape[0]),
                metal,
            )
        incidence = beta_in - metal
        deviation = beta_ex - metal

    return SpanwiseProfile(
        r_m=r_m,
        r_frac=r_frac,
        p0_kin=ex["p0"],
        u_axial=ex["uz"],
        u_swirl=ex["uth"],
        beta_in_deg=beta_in,
        beta_ex_deg=beta_ex,
        incidence_deg=incidence,
        deviation_deg=deviation,
        metal_deg=metal,
        hub_r_m=hub_r,
        tip_r_m=tip_r,
        omega=float(omega),
        z_in_m=z_in,
        z_ex_m=z_ex,
    )


def compute_blade_to_blade_cp(
    pts: np.ndarray,
    p: np.ndarray,
    u: np.ndarray,
    *,
    hub_r: float,
    tip_r: float,
    r_frac: float,
    n_theta: int = DEFAULT_N_THETA,
    n_z: int = DEFAULT_N_Z_B2B,
    z_half_span: float | None = None,
    p_ref: float | None = None,
    u_ref: float | None = None,
) -> BladeToBladeSlice:
    """Unroll a thin cylindrical shell at ``r_frac`` onto (θ, z) and form Cp."""
    hub_r = float(hub_r)
    tip_r = float(tip_r)
    span = max(tip_r - hub_r, 1e-6)
    r0 = hub_r + float(r_frac) * span
    dr = max(_B2B_SHELL_FRAC * span, 0.001)
    r = np.sqrt(pts[:, 0] ** 2 + pts[:, 1] ** 2)
    shell = np.abs(r - r0) <= dr
    z_half = float(z_half_span) if z_half_span is not None else max(0.55 * tip_r, 0.01)
    shell = shell & (np.abs(pts[:, 2]) <= z_half)

    n_theta = max(8, int(n_theta))
    n_z = max(8, int(n_z))
    theta_edges = np.linspace(-math.pi, math.pi, n_theta + 1)
    z_edges = np.linspace(-z_half, z_half, n_z + 1)
    theta_c = np.degrees(0.5 * (theta_edges[:-1] + theta_edges[1:]))
    z_c = 0.5 * (z_edges[:-1] + z_edges[1:])
    cp = np.full((n_z, n_theta), np.nan)

    if u_ref is None:
        mag = np.linalg.norm(np.asarray(u, dtype=float), axis=1)
        u_ref = float(np.nanpercentile(mag[shell], 90.0)) if np.any(shell) else 1.0
        u_ref = max(u_ref, 0.5)
    dyn = 0.5 * float(u_ref) ** 2
    if p_ref is None:
        p_ref = float(np.nanmean(p[shell])) if np.any(shell) else 0.0

    if not np.any(shell):
        return BladeToBladeSlice(
            r_frac=float(r_frac), r_m=r0, theta_deg=theta_c, z_m=z_c, cp=cp,
        )

    th = np.arctan2(pts[shell, 1], pts[shell, 0])
    zz = pts[shell, 2]
    pp = np.asarray(p, dtype=float).reshape(-1)[shell]
    it = np.clip(np.digitize(th, theta_edges) - 1, 0, n_theta - 1)
    iz = np.clip(np.digitize(zz, z_edges) - 1, 0, n_z - 1)
    # Accumulate sums / counts
    sums: np.ndarray = np.zeros((n_z, n_theta), dtype=float)
    counts: np.ndarray = np.zeros((n_z, n_theta), dtype=float)
    for i in range(pp.shape[0]):
        sums[iz[i], it[i]] += pp[i]
        counts[iz[i], it[i]] += 1.0
    good = counts > 0
    p_mean = np.full_like(sums, np.nan)
    p_mean[good] = sums[good] / counts[good]
    cp[good] = (p_mean[good] - float(p_ref)) / dyn
    return BladeToBladeSlice(
        r_frac=float(r_frac), r_m=r0, theta_deg=theta_c, z_m=z_c, cp=cp,
    )


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------


def _save_fig(fig, path: Path) -> Path | None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(path), dpi=120, bbox_inches="tight", facecolor="white")
    return path if path.is_file() else None


def render_spanwise_png(
    case_dir: str | Path,
    profile: SpanwiseProfile,
    *,
    path: Path | None = None,
) -> Path | None:
    """Multi-panel line plot of circumferentially averaged profiles vs radius."""
    import matplotlib

    matplotlib.use("Agg", force=False)
    import matplotlib.pyplot as plt

    case_dir = Path(case_dir)
    out = path or spanwise_artifact_path(case_dir)
    r = profile.r_m * 1e3  # mm for readability
    has_inc = profile.incidence_deg is not None and np.any(np.isfinite(profile.incidence_deg))
    nrows = 3 if has_inc else 2

    with _PLOT_LOCK:
        fig, axes = plt.subplots(nrows, 2, figsize=(9.5, 2.6 * nrows), squeeze=False)
        try:
            ax = axes[0, 0]
            ax.plot(r, profile.p0_kin * RHO_AMCA, "C0-", lw=1.8)
            ax.set_ylabel("p0 [Pa]")
            ax.set_title("Total pressure (exit plane)")
            ax.grid(True, alpha=0.3)

            ax = axes[0, 1]
            ax.plot(r, profile.u_axial, "C1-", lw=1.8, label="Uz")
            ax.plot(r, profile.u_swirl, "C2-", lw=1.8, label="Uθ")
            ax.set_ylabel("m/s")
            ax.set_title("Axial / swirl (exit plane)")
            ax.legend(loc="best", fontsize=8)
            ax.grid(True, alpha=0.3)

            ax = axes[1, 0]
            ax.plot(r, profile.beta_in_deg, "C3-", lw=1.8, label="β inlet")
            ax.plot(r, profile.beta_ex_deg, "C4-", lw=1.8, label="β exit")
            if profile.metal_deg is not None:
                ax.plot(r, profile.metal_deg, "k--", lw=1.2, label="metal κ")
            ax.set_ylabel("deg")
            ax.set_title("Relative flow angle from axial")
            ax.legend(loc="best", fontsize=8)
            ax.grid(True, alpha=0.3)

            ax = axes[1, 1]
            # Tip-loss cue: drop in p0 relative to mid-span mean.
            mid = (profile.r_frac > 0.35) & (profile.r_frac < 0.65)
            ref = float(np.nanmean(profile.p0_kin[mid])) if np.any(mid) else float(np.nanmean(profile.p0_kin))
            drop = (profile.p0_kin - ref) * RHO_AMCA
            ax.plot(r, drop, "C0-", lw=1.8)
            ax.axhline(0.0, color="k", lw=0.6)
            ax.set_ylabel("Δp0 [Pa]")
            ax.set_title("p0 vs mid-span (tip loss cue)")
            ax.grid(True, alpha=0.3)

            if has_inc:
                ax = axes[2, 0]
                ax.plot(r, profile.incidence_deg, "C5-", lw=1.8)
                ax.axhline(0.0, color="k", lw=0.6)
                ax.set_ylabel("deg")
                ax.set_title("Incidence (β_in − κ)")
                ax.grid(True, alpha=0.3)

                ax = axes[2, 1]
                ax.plot(r, profile.deviation_deg, "C6-", lw=1.8)
                ax.axhline(0.0, color="k", lw=0.6)
                ax.set_ylabel("deg")
                ax.set_title("Deviation (β_ex − κ)")
                ax.grid(True, alpha=0.3)

            for row in axes:
                for a in row:
                    a.set_xlabel("radius [mm]")
            fig.suptitle(
                "Spanwise CFD averages — exit at "
                f"z={profile.z_ex_m * 1e3:.1f} mm, inlet at z={profile.z_in_m * 1e3:.1f} mm",
                fontsize=11,
            )
            fig.tight_layout(rect=(0, 0, 1, 0.96))
            written = _save_fig(fig, out)
        finally:
            plt.close(fig)
    return written


def render_b2b_png(
    case_dir: str | Path,
    slices: list[BladeToBladeSlice],
    *,
    path: Path | None = None,
) -> Path | None:
    """Row of blade-to-blade Cp contour plots at several span stations."""
    import matplotlib

    matplotlib.use("Agg", force=False)
    import matplotlib.pyplot as plt

    if not slices:
        return None
    case_dir = Path(case_dir)
    out = path or b2b_artifact_path(case_dir)
    n = len(slices)
    # Symmetric clim from finite Cp values.
    finite = np.concatenate([s.cp[np.isfinite(s.cp)] for s in slices]) if slices else np.array([])
    if finite.size:
        lim = float(np.percentile(np.abs(finite), 95.0))
        lim = max(lim, 0.2)
    else:
        lim = 1.0

    with _PLOT_LOCK:
        fig, axes = plt.subplots(1, n, figsize=(2.8 * n, 3.6), squeeze=False)
        try:
            last_im = None
            for i, slc in enumerate(slices):
                ax = axes[0, i]
                th: np.ndarray
                zz: np.ndarray
                th, zz = np.meshgrid(slc.theta_deg, slc.z_m * 1e3)
                last_im = ax.pcolormesh(
                    th, zz, slc.cp, shading="auto", cmap="RdBu_r",
                    vmin=-lim, vmax=lim,
                )
                ax.set_title(f"r/R={slc.r_frac:.2f}", fontsize=10)
                ax.set_xlabel("θ [deg]")
                if i == 0:
                    ax.set_ylabel("z [mm]")
            fig.suptitle("Blade-to-blade Cp (cyl. unroll)", fontsize=11)
            if last_im is not None:
                fig.colorbar(last_im, ax=axes.ravel().tolist(), fraction=0.025, pad=0.02,
                             label="Cp")
            fig.subplots_adjust(left=0.06, right=0.90, top=0.88, bottom=0.12, wspace=0.28)
            written = _save_fig(fig, out)
        finally:
            plt.close(fig)
    return written


# ---------------------------------------------------------------------------
# Public ensure / render entry points
# ---------------------------------------------------------------------------


def render_spanwise_artifacts(
    case_dir: str | Path,
    *,
    mesh=None,
    span_stations: tuple[float, ...] = DEFAULT_SPAN_STATIONS,
    n_radial: int = DEFAULT_N_RADIAL,
    force_stations: tuple[float, ...] | None = None,
) -> SpanwiseArtifacts:
    """Build spanwise + blade-to-blade PNGs from a reconstructed mesh.

    ``mesh`` may be injected for tests. When omitted, loads via
    ``fansim.acoustics.case.read_case``.
    """
    case_dir = Path(case_dir)
    unavailable = SpanwiseArtifacts(
        case_dir=case_dir, spanwise_png=None, b2b_png=None,
        caption="Spanwise post not available for this design", available=False,
    )

    if mesh is None:
        from fansim.acoustics.case import read_case

        mesh = read_case(case_dir)

    try:
        pts, u, p = _mesh_centers_up(mesh)
    except Exception:  # noqa: BLE001
        return unavailable
    if pts.shape[0] == 0:
        return unavailable

    hub_r, tip_r, omega = load_case_radii_omega(case_dir)
    # Prefer radii implied by the mesh annulus when meta is missing / mismatched.
    r_mesh = np.sqrt(pts[:, 0] ** 2 + pts[:, 1] ** 2)
    r_finite = r_mesh[np.isfinite(r_mesh) & (r_mesh > 1e-6)]
    if r_finite.size:
        r_lo = float(np.percentile(r_finite, 5.0))
        r_hi = float(np.percentile(r_finite, 98.0))
        # Only override when meta defaults look wildly off the mesh.
        if hub_r < 0.5 * r_lo or hub_r > tip_r:
            hub_r = max(0.15 * r_hi, r_lo * 0.5)
        if tip_r < 0.7 * r_hi or tip_r <= hub_r:
            tip_r = r_hi

    b = getattr(mesh, "bounds", None)
    if b is not None and float(b[4]) < 0.0 < float(b[5]):
        z_fan = 0.0
    else:
        z_fan = float(np.median(pts[:, 2]))

    stations = force_stations or span_stations
    # Drop stations outside [0, 1]; keep 3–5.
    stations = tuple(s for s in stations if 0.05 <= float(s) <= 0.95)[:5]
    if len(stations) < 3:
        stations = DEFAULT_SPAN_STATIONS

    # Metal angles are re-interpolated inside compute_spanwise_profile onto the
    # radial bin centers; seed with a unit-span probe so design.json stagger maps.
    metal_seed = load_metal_angles_deg(case_dir, np.linspace(0.0, 1.0, n_radial))

    profile = compute_spanwise_profile(
        pts, u, p,
        hub_r=hub_r, tip_r=tip_r, omega=omega,
        metal_deg=metal_seed, n_radial=n_radial, z_fan=z_fan,
        blade_z=_blade_z(case_dir, hub_r),
    )

    slices = [
        compute_blade_to_blade_cp(
            pts, p, u, hub_r=hub_r, tip_r=tip_r, r_frac=float(sf),
        )
        for sf in stations
    ]

    span_png = b2b_png = None
    try:
        span_png = render_spanwise_png(case_dir, profile)
    except Exception:  # noqa: BLE001
        span_png = None
    try:
        b2b_png = render_b2b_png(case_dir, slices)
    except Exception:  # noqa: BLE001
        b2b_png = None

    ok = span_png is not None or b2b_png is not None
    if span_png and b2b_png:
        cap = "spanwise averages + blade-to-blade Cp"
    elif span_png:
        cap = "spanwise averages — p0 / Uz / swirl / incidence vs radius"
    elif b2b_png:
        cap = "blade-to-blade Cp — span stations"
    else:
        cap = "Spanwise post not available for this design"
    return SpanwiseArtifacts(
        case_dir=case_dir,
        spanwise_png=span_png,
        b2b_png=b2b_png,
        caption=cap,
        available=ok,
        profile=profile if ok else None,
    )


def ensure_spanwise_artifacts(
    case_dir: str | Path | None,
    *,
    runner_factory=None,
    image_ok=None,
    mesh=None,
    force: bool = False,
) -> SpanwiseArtifacts:
    """Find or build spanwise / blade-to-blade PNGs (fail-soft, mirrors midplane)."""
    unavailable = SpanwiseArtifacts(
        case_dir=Path(case_dir) if case_dir else Path("."),
        spanwise_png=None,
        b2b_png=None,
        caption="Spanwise post not available for this design",
        available=False,
    )
    if case_dir is None:
        return unavailable
    case_dir = Path(case_dir)
    if not case_dir.is_dir():
        return unavailable

    if not force:
        cached = find_cached_spanwise(case_dir)
        if cached is not None and cached.spanwise_png is not None:
            return cached

    if mesh is None:
        if not case_has_flow_fields(case_dir):
            return unavailable
        if not ensure_reconstructed(case_dir, runner_factory=runner_factory, image_ok=image_ok):
            return unavailable

    try:
        return render_spanwise_artifacts(case_dir, mesh=mesh)
    except Exception:  # noqa: BLE001 — viz must never break Assess
        return unavailable
