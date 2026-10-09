"""Meanline seed from target duty: Cordier sizing, velocity triangles, loading gates (§20.4).

From target Q / ΔP / RPM produce:
  * dimensionless specific speed & diameter (Cordier / Balje form),
  * free- or forced-vortex triangles → per-station stagger & camber *magnitudes*,
  * cheap Lieblein diffusion-factor and de Haller ratio gates (no CFD).

**Freeze:** emit magnitudes only. Handedness and sign come from the existing editor /
geometry convention (apply with ``preserve_sign``).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from fansim.physics.air import RHO_AMCA

# Same factor as fansim.cfd.metrics.CFM_PER_M3S — kept local so this module stays CadQuery-free.
CFM_PER_M3S = 2118.882

# Classic cascade limits (Lieblein 1959; de Haller 1953). Ranking gates only.
DF_LIMIT = 0.60
DE_HALLER_LIMIT = 0.72

# UI-ish clamps matching Design sliders (magnitudes).
STAGGER_DEG_MIN = 15.0
STAGGER_DEG_MAX = 55.0
CAMBER_MIN = 0.0
CAMBER_MAX = 0.15

# Cordier optimal-line fit for mixed/axial machines (Balje / Cordier chart, SI form).
# δ_opt ≈ A · σ^B — used only as a sizing *hint*, not a hard design rule.
_CORDIER_A = 2.22
_CORDIER_B = -0.485


@dataclass(frozen=True)
class DutyPoint:
    """Target operating point in cockpit units."""

    cfm: float
    dp_pa: float
    rpm: float

    @property
    def q_m3s(self) -> float:
        return float(self.cfm) / CFM_PER_M3S

    @property
    def omega(self) -> float:
        return float(self.rpm) * 2.0 * math.pi / 60.0

    @property
    def specific_work(self) -> float:
        """Y = ΔP/ρ [J/kg]."""
        return float(self.dp_pa) / RHO_AMCA


def cfm_to_m3s(cfm: float) -> float:
    return float(cfm) / CFM_PER_M3S


def specific_speed(omega: float, q_m3s: float, specific_work: float) -> float:
    """Dimensionless specific speed σ = ω √Q / Y^(3/4) (Cordier / Balje SI form).

    Sources: Cordier (1953); Balje, *Turbomachines* (1981); Dixon & Hall §2.
    """
    y = float(specific_work)
    q = float(q_m3s)
    if y <= 0.0 or q < 0.0:
        raise ValueError("specific_work and q_m3s must be non-negative; Y > 0")
    return float(omega) * math.sqrt(q) / (y ** 0.75)


def specific_diameter(d_m: float, q_m3s: float, specific_work: float) -> float:
    """Dimensionless specific diameter δ = D · Y^(1/4) / √Q."""
    y = float(specific_work)
    q = float(q_m3s)
    if y <= 0.0 or q <= 0.0:
        raise ValueError("specific_work and q_m3s must be positive")
    return float(d_m) * (y ** 0.25) / math.sqrt(q)


def cordier_delta_opt(sigma: float) -> float:
    """Approximate Cordier optimal δ for a given σ (axial/mixed band)."""
    s = max(float(sigma), 1e-6)
    return _CORDIER_A * (s ** _CORDIER_B)


def suggest_tip_diameter_m(duty: DutyPoint) -> float:
    """Tip diameter from Cordier δ_opt(σ) at the duty (sizing hint)."""
    y = duty.specific_work
    q = duty.q_m3s
    if y <= 0.0 or q <= 0.0:
        raise ValueError("duty must have positive CFM and ΔP")
    sigma = specific_speed(duty.omega, q, y)
    delta = cordier_delta_opt(sigma)
    return delta * math.sqrt(q) / (y ** 0.25)


def axial_cz(q_m3s: float, hub_r_m: float, tip_r_m: float) -> float:
    """Uniform axial velocity through the annulus [m/s]."""
    if tip_r_m <= hub_r_m:
        raise ValueError("tip_r_m must exceed hub_r_m")
    area = math.pi * (tip_r_m * tip_r_m - hub_r_m * hub_r_m)
    if area <= 0.0:
        raise ValueError("annulus area must be positive")
    return float(q_m3s) / area


def solidity(n_blades: int, chord_m: float, r_m: float) -> float:
    """Cascade solidity σ = c / s with pitch s = 2πr / N.

    Not ``geometry.blade.blade_solidity``, which is the PROJECTED overlap measure c·cos(stagger)/s.
    """
    if r_m <= 0.0 or n_blades <= 0:
        raise ValueError("r_m and n_blades must be positive")
    pitch = 2.0 * math.pi * float(r_m) / float(n_blades)
    return float(chord_m) / pitch


def lieblein_df(w1: float, w2: float, delta_cu: float, sol: float) -> float:
    """Lieblein diffusion factor DF = (1 − W2/W1) + ΔCu / (2 σ W1).

    Source: Lieblein, Schwenk & Broderick, NACA RM E53A15 (1953) / Lieblein (1959).
    """
    w1a = max(float(w1), 1e-12)
    return (1.0 - float(w2) / w1a) + float(delta_cu) / (2.0 * max(float(sol), 1e-9) * w1a)


def de_haller_ratio(w1: float, w2: float) -> float:
    """de Haller ratio W2/W1 (limit typically ≥ 0.72).

    Source: de Haller, *Das Verhalten von Tragflügelgittern in Axialverdichtern* (1953).
    """
    return float(w2) / max(float(w1), 1e-12)


def camber_from_turning_rad(turning_rad: float, solidity: float = 1.0,
                            beta2_ax_deg: float = 0.0) -> float:
    """Max-camber fraction for a circular-arc section that turns the flow by ``turning_rad``.

    The blade must be cambered more than the flow turns, because the flow leaves the trailing
    edge with deviation δ. Carter's rule (Dixon & Hall, *Fluid Mechanics and Thermodynamics of
    Turbomachinery*, ch. 3): δ = m·θ/√σ with m = 0.23 + β2/500 (circular arc, max camber at
    mid-chord, β2 in degrees from axial), so the camber angle is θ = ε / (1 − m/√σ). A circular
    arc of camber angle θ has max camber (c/2)·tan(θ/4) ≈ θ/8.

    The old rule m = |ε|/4 assumed θ = 2ε, about twice the camber at σ ≈ 1 (QA 2026-10-08,
    roadmap §23.10). Only seeds the cockpit meanline recipe; CFD/BEM still score the design.
    """
    eps = abs(float(turning_rad))
    m_carter = 0.23 + abs(float(beta2_ax_deg)) / 500.0
    denom = max(1.0 - m_carter / math.sqrt(max(float(solidity), 1e-6)), 0.2)
    theta = eps / denom
    return min(max(0.5 * math.tan(theta / 4.0), CAMBER_MIN), CAMBER_MAX)


def stagger_from_disk_deg(beta1_ax_rad: float, beta2_ax_rad: float) -> float:
    """Metal stagger from the *rotation plane* (BladeParams convention).

    Relative flow angles are from axial; disk stagger = 90° − mean(β1, β2).
    Magnitudes only (always ≥ 0).
    """
    mean_ax = 0.5 * (float(beta1_ax_rad) + float(beta2_ax_rad))
    from_disk = 90.0 - math.degrees(mean_ax)
    return min(max(abs(from_disk), STAGGER_DEG_MIN), STAGGER_DEG_MAX)


def preserve_sign(current: float, magnitude: float) -> float:
    """Apply suggested magnitude without flipping the existing sign/handedness."""
    mag = abs(float(magnitude))
    if float(current) < 0.0:
        return -mag
    return mag


@dataclass
class StationTriangle:
    r_frac: float
    r_m: float
    u_mps: float
    cz_mps: float
    cu2_mps: float
    beta1_ax_deg: float
    beta2_ax_deg: float
    stagger_deg: float
    camber: float
    w1_mps: float
    w2_mps: float
    solidity: float
    df: float
    de_haller: float
    df_ok: bool
    de_haller_ok: bool


@dataclass
class MeanlineSeed:
    duty: DutyPoint
    vortex: str
    sigma: float
    delta: float
    delta_opt: float
    tip_d_suggest_m: float
    cz_mps: float
    stations: list[StationTriangle] = field(default_factory=list)
    note: str = (
        "§20.4 meanline seed — magnitudes only; Lieblein/de Haller are cheap gates, not CFD"
    )


def _cu2_distribution(
    vortex: str,
    *,
    y: float,
    omega: float,
    r_m: float,
    r_mid_m: float,
) -> float:
    """Exit swirl Cu2 [m/s] for axial inlet (Cu1=0), free or forced vortex."""
    if vortex == "free":
        # r·Cu = Y/ω = const → Cu2 = Y / U = Y / (ω r)
        return y / max(omega * r_m, 1e-12)
    if vortex == "forced":
        # Cu = λ r with λ from mid-radius Euler work: Y = ω λ r_mid²
        lam = y / max(omega * r_mid_m * r_mid_m, 1e-12)
        return lam * r_m
    raise ValueError(f"vortex must be 'free' or 'forced', got {vortex!r}")


def velocity_triangle_station(
    *,
    r_frac: float,
    r_m: float,
    omega: float,
    cz: float,
    cu2: float,
    chord_m: float,
    n_blades: int,
) -> StationTriangle:
    """One radius: relative angles, stagger/camber magnitudes, DF / de Haller."""
    u = omega * r_m
    # Relative speeds (axial inlet Cu1=0): Wθ1 = −U, Wθ2 = Cu2 − U
    w1 = math.hypot(cz, u)
    w_theta2 = cu2 - u
    w2 = math.hypot(cz, w_theta2)
    beta1 = math.atan2(u, max(cz, 1e-12))  # from axial, magnitude
    beta2 = math.atan2(abs(w_theta2), max(cz, 1e-12))
    turning = beta1 - beta2
    stag = stagger_from_disk_deg(beta1, beta2)
    sol = solidity(n_blades, chord_m, r_m)
    cam = camber_from_turning_rad(turning, sol, math.degrees(beta2))
    df = lieblein_df(w1, w2, abs(cu2), sol)
    dh = de_haller_ratio(w1, w2)
    return StationTriangle(
        r_frac=float(r_frac),
        r_m=float(r_m),
        u_mps=float(u),
        cz_mps=float(cz),
        cu2_mps=float(cu2),
        beta1_ax_deg=math.degrees(beta1),
        beta2_ax_deg=math.degrees(beta2),
        stagger_deg=stag,
        camber=cam,
        w1_mps=float(w1),
        w2_mps=float(w2),
        solidity=float(sol),
        df=float(df),
        de_haller=float(dh),
        df_ok=df <= DF_LIMIT,
        de_haller_ok=dh >= DE_HALLER_LIMIT,
    )


def seed_from_duty(
    duty: DutyPoint,
    *,
    hub_radius_mm: float,
    tip_radius_mm: float,
    n_blades: int,
    chord_root_mm: float,
    chord_mid_mm: float,
    chord_tip_mm: float,
    vortex: str = "free",
) -> MeanlineSeed:
    """Build Cordier numbers + per-station stagger/camber magnitudes and gates."""
    if duty.cfm <= 0.0 or duty.dp_pa <= 0.0 or duty.rpm <= 0.0:
        raise ValueError("duty CFM, ΔP, and RPM must be positive")
    hub_m = float(hub_radius_mm) / 1000.0
    tip_m = float(tip_radius_mm) / 1000.0
    y = duty.specific_work
    q = duty.q_m3s
    omega = duty.omega
    sigma = specific_speed(omega, q, y)
    delta = specific_diameter(2.0 * tip_m, q, y)
    delta_opt = cordier_delta_opt(sigma)
    tip_d_sug = suggest_tip_diameter_m(duty)
    cz = axial_cz(q, hub_m, tip_m)
    r_mid = 0.5 * (hub_m + tip_m)
    chords = {
        0.0: float(chord_root_mm) / 1000.0,
        0.5: float(chord_mid_mm) / 1000.0,
        1.0: float(chord_tip_mm) / 1000.0,
    }
    stations: list[StationTriangle] = []
    for rf, ch in chords.items():
        r = hub_m + rf * (tip_m - hub_m)
        cu2 = _cu2_distribution(vortex, y=y, omega=omega, r_m=r, r_mid_m=r_mid)
        stations.append(
            velocity_triangle_station(
                r_frac=rf,
                r_m=r,
                omega=omega,
                cz=cz,
                cu2=cu2,
                chord_m=ch,
                n_blades=int(n_blades),
            )
        )
    return MeanlineSeed(
        duty=duty,
        vortex=vortex,
        sigma=sigma,
        delta=delta,
        delta_opt=delta_opt,
        tip_d_suggest_m=tip_d_sug,
        cz_mps=cz,
        stations=stations,
    )


def format_meanline_seed(seed: MeanlineSeed) -> list[str]:
    """Human-readable cockpit lines."""
    d = seed.duty
    lines = [
        f"§20.4 seed @ {d.cfm:.0f} CFM / {d.dp_pa:.0f} Pa / {d.rpm:.0f} RPM "
        f"({seed.vortex}-vortex)",
        f"σ={seed.sigma:.3f}  δ={seed.delta:.3f}  δ_opt≈{seed.delta_opt:.3f}  "
        f"D_sug≈{1000.0 * seed.tip_d_suggest_m:.1f} mm  Cz={seed.cz_mps:.2f} m/s",
    ]
    for st in seed.stations:
        tag = {0.0: "root", 0.5: "mid", 1.0: "tip"}.get(st.r_frac, f"r{st.r_frac}")
        gates = []
        gates.append("DF✓" if st.df_ok else f"DF✗({st.df:.2f}>{DF_LIMIT})")
        gates.append("dH✓" if st.de_haller_ok else f"dH✗({st.de_haller:.2f}<{DE_HALLER_LIMIT})")
        lines.append(
            f"  {tag}: stagger {st.stagger_deg:.1f}°  camber {st.camber:.3f}  "
            f"σ_sol={st.solidity:.2f}  {' '.join(gates)}"
        )
    lines.append(seed.note)
    return lines


def station_magnitudes(seed: MeanlineSeed) -> dict[str, float]:
    """Flat stagger/camber magnitudes for root/mid/tip (always ≥ 0)."""
    by_rf = {st.r_frac: st for st in seed.stations}
    out: dict[str, float] = {}
    for rf, name in ((0.0, "root"), (0.5, "mid"), (1.0, "tip")):
        st = by_rf[rf]
        out[f"stagger_{name}"] = float(st.stagger_deg)
        out[f"camber_{name}"] = float(st.camber)
    return out
