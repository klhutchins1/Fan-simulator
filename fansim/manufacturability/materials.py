"""FDM filament properties for the printer's supported materials.

Limited to what the user's printer can run: PLA, PLA+, PETG, ABS, TPU (no ASA / carbon- or
glass-filled). PETG is the default for fan blades (good stiffness + heat resistance near
warm case air); PLA is flagged for thermal creep; TPU is too flexible for a blade.

Values are representative FDM-part properties (not datasheet resin maxima); treat as
order-of-magnitude for the lightweight structural gate.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Material:
    name: str
    youngs_modulus_gpa: float
    yield_strength_mpa: float
    density_kg_m3: float
    heat_deflection_c: float  # ~temperature where it softens under load
    blade_suitable: bool = True
    note: str = ""


MATERIALS: dict[str, Material] = {
    "PLA": Material("PLA", 3.5, 60.0, 1240.0, 55.0, True,
                    "stiffest/cheapest but creeps ~55C near warm exhaust"),
    "PLA+": Material("PLA+", 3.0, 45.0, 1240.0, 60.0, True, "tougher PLA, still heat-limited"),
    "PETG": Material("PETG", 2.1, 50.0, 1270.0, 70.0, True, "default: stiffness + heat resistance"),
    "ABS": Material("ABS", 2.0, 40.0, 1040.0, 95.0, True, "heat-tolerant; needs an enclosure"),
    "TPU": Material("TPU", 0.02, 25.0, 1210.0, 60.0, False, "too flexible for a blade (excluded)"),
    "RESIN": Material("RESIN", 2.5, 50.0, 1100.0, 50.0, True,
                      "SLA/DLP; isotropic E (no FDM interlayer knockdown)"),
}

DEFAULT_MATERIAL = "PETG"
