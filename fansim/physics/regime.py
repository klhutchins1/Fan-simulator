# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Map operating conditions -> (Reynolds, Mach, solver, turbulence model) with the reasoning.

Encodes *why* the axial-fan archetype uses incompressible steady RANS with k-omega SST, and when to
escalate to a transient LES/LBM tier -- so the choice is documented and travels to other archetypes
(a wind-turbine blade is high-Re incompressible; a propeller tip can approach compressible).
"""

from __future__ import annotations

from dataclasses import dataclass

NU_AIR = 1.5e-5     # kinematic viscosity of air, m^2/s
C0_AIR = 343.0      # speed of sound, m/s
RE_LAMINAR = 2000.0     # below ~this, treat as laminar
MACH_COMPRESSIBLE = 0.3  # above ~this, compressibility matters


@dataclass
class Regime:
    reynolds: float
    mach: float
    compressible: bool
    turbulence_model: str      # "laminar" | "k-omega SST" | ...
    solver: str                # steady solver recommendation
    transient_tier: str        # what to use for transient/acoustic questions
    note: str = ""


def classify_regime(length_m: float, velocity_ms: float, *, nu: float = NU_AIR,
                    c0: float = C0_AIR, need_acoustics: bool = False) -> Regime:
    """Classify a flow from a characteristic length and velocity.

    length_m: characteristic length (e.g. rotor diameter). velocity_ms: characteristic speed (e.g.
    blade tip speed). need_acoustics flags that noise/near-stall is wanted -> a transient tier.
    """
    re = velocity_ms * length_m / nu
    mach = velocity_ms / c0
    compressible = mach > MACH_COMPRESSIBLE
    turb = "laminar" if re < RE_LAMINAR else "k-omega SST"
    if compressible:
        solver, snote = "rhoSimpleFoam (compressible MRF)", "Mach>0.3: compressibility matters"
    else:
        solver, snote = "simpleFoam (incompressible MRF)", "low Mach: incompressible is adequate"
    transient = ("LES / LBM (FluidX3D) + FW-H" if need_acoustics
                 else "URANS/LES only if steady RANS won't converge (near stall)")
    return Regime(
        reynolds=re, mach=mach, compressible=compressible, turbulence_model=turb,
        solver=solver, transient_tier=transient,
        note=f"Re={re:.3g}, Ma={mach:.3g}; {snote}; "
             f"{'turbulent' if turb!='laminar' else 'laminar'} wall-bounded flow.")


def fan_regime(tip_speed_ms: float, diameter_m: float, need_acoustics: bool = False) -> Regime:
    """Convenience for an axial fan: diameter Reynolds + tip Mach."""
    return classify_regime(diameter_m, tip_speed_ms, need_acoustics=need_acoustics)
