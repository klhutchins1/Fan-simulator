"""Drone-propeller model specs — the prop analog of fansim.fan_spec (the propeller archetype's
constraint layer). A PropSpec captures a real prop class: its diameter x pitch, blade count, the
motor-shaft mount (bore + adapter), the RPM envelope, and typical performance targets.

Props differ from cooling fans in ways the rest of the archetype must respect (see the DRONE backlog):
open air (no frame), THRUST/efficiency objectives (not CFM/static-P), very high RPM, and tip speeds
fast enough that COMPRESSIBILITY matters — `tip_mach` here flags that. Sizes/mounts follow the common
FPV standards (Gemfan/HQProp-class geometry; 5 mm T-mount with reducer rings is the 5-inch norm).

Performance numbers are TYPICAL static values on a matched motor, for sanity/validation targets, not
datasheet-exact — real thrust depends on the motor + battery. Geometry (dia/pitch/blades/shaft) is the
confident part. New props are new PropSpec entries (no engine change).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from fansim.physics.air import C0_AIR as C_AIR

MM_PER_IN = 25.4


@dataclass
class PropShaftMount:
    """How the prop mounts on the motor shaft. FPV standard: a 5 mm bore with reducer rings for
    smaller shafts, or a press-fit bore on micro props; some larger props are threaded."""
    shaft_dia_mm: float           # the motor shaft the prop drives onto (1.0/1.5/2/3/5 mm common)
    hub_bore_dia_mm: float        # the prop's center bore (>= shaft; adapter/reducer rings fill the gap)
    hub_dia_mm: float             # prop hub outer diameter
    style: str = "press-fit"      # "press-fit" | "T-mount" | "M5-thread"


@dataclass
class PropSpec:
    name: str
    diameter_in: float            # prop diameter, inches (the size that names the prop)
    pitch_in: float               # geometric pitch, inches (travel per rev, ideal)
    n_blades: int                 # 2-3 typical (4+ on some micro/cine)
    shaft: PropShaftMount
    rpm_max: float                # top of the usable RPM band
    material: str = "molded nylon/PC (glass/carbon-filled on premium)"
    ref_thrust_g: float | None = None    # ~static thrust near rpm_max on a matched motor (grams)
    ref_rpm: float | None = None
    ref_power_w: float | None = None
    notes: str = ""

    @property
    def diameter_mm(self) -> float:
        return self.diameter_in * MM_PER_IN

    @property
    def pitch_mm(self) -> float:
        return self.pitch_in * MM_PER_IN

    @property
    def pitch_ratio(self) -> float:
        """Pitch / diameter — the prop's 'aggressiveness' (higher = more speed, more current)."""
        return self.pitch_in / self.diameter_in

    def tip_speed_ms(self, rpm: float | None = None) -> float:
        rpm = self.rpm_max if rpm is None else rpm
        return math.pi * (self.diameter_mm / 1000.0) * rpm / 60.0

    def tip_mach(self, rpm: float | None = None) -> float:
        """Tip Mach number. > ~0.3 means compressibility is no longer negligible (fan MRF assumption
        breaks) — most FPV props exceed this at full throttle, so the CFD must account for it."""
        return self.tip_speed_ms(rpm) / C_AIR

    @property
    def ref_efficiency_g_per_w(self) -> float | None:
        if self.ref_thrust_g and self.ref_power_w:
            return round(self.ref_thrust_g / self.ref_power_w, 2)
        return None


# --- registry: common drone-prop classes (geometry confident; performance typical) ---
_REGISTRY: dict[str, PropSpec] = {
    # 5-inch freestyle/racing — the FPV mainstream (Gemfan 51466 / HQProp 5x4.3x3 class). 5 mm T-mount
    # with 1.5/2/3 mm reducer rings. On a 2207 ~1900 KV motor at 6S: ~1.8 kg static thrust near top.
    "fpv_5inch": PropSpec(
        name="FPV 5\" freestyle (5x4.3x3)", diameter_in=5.0, pitch_in=4.3, n_blades=3,
        shaft=PropShaftMount(shaft_dia_mm=5.0, hub_bore_dia_mm=5.0, hub_dia_mm=12.0, style="T-mount"),
        rpm_max=30000.0, ref_thrust_g=1850.0, ref_rpm=30000.0, ref_power_w=650.0,
        notes="tip goes transonic-ish at full throttle; reducer rings for 1.5/2/3 mm shafts"),

    # 3-inch cinewhoop / toothpick (Gemfan 3016 / HQ T3x2 class). 1.5 mm shaft press-fit, very high RPM.
    "cine_3inch": PropSpec(
        name="Cinewhoop 3\" (3x3x3)", diameter_in=3.0, pitch_in=3.0, n_blades=3,
        shaft=PropShaftMount(shaft_dia_mm=1.5, hub_bore_dia_mm=1.5, hub_dia_mm=7.0, style="press-fit"),
        rpm_max=42000.0, ref_thrust_g=650.0, ref_rpm=42000.0, ref_power_w=250.0,
        notes="ducted use common; 1404-1806 motors"),

    # 7-inch long-range / efficiency (Gemfan 7035 / HQ 7x4 class). Fewer blades, lower RPM, efficient.
    "longrange_7inch": PropSpec(
        name="Long-range 7\" (7x4x3)", diameter_in=7.0, pitch_in=4.0, n_blades=3,
        shaft=PropShaftMount(shaft_dia_mm=5.0, hub_bore_dia_mm=5.0, hub_dia_mm=14.0, style="T-mount"),
        rpm_max=20000.0, ref_thrust_g=1600.0, ref_rpm=20000.0, ref_power_w=350.0,
        notes="efficiency-oriented; 2806.5-2807 low-KV motors"),

    # 2-inch micro / whoop (Gemfan 2016 / HQ 2x2.5 class). Tiny 1.0-1.5 mm shaft, extreme RPM.
    "micro_2inch": PropSpec(
        name="Micro 2\" (2x2x4)", diameter_in=2.0, pitch_in=2.0, n_blades=4,
        shaft=PropShaftMount(shaft_dia_mm=1.5, hub_bore_dia_mm=1.5, hub_dia_mm=5.5, style="press-fit"),
        rpm_max=52000.0, ref_thrust_g=180.0, ref_rpm=52000.0, ref_power_w=90.0,
        notes="whoop/micro-quad; 1103-1303 motors"),
}


def get_prop_spec(name: str) -> PropSpec:
    if name not in _REGISTRY:
        raise KeyError(f"unknown prop model '{name}'; known: {sorted(_REGISTRY)}")
    return _REGISTRY[name]


def prop_spec_names() -> list[str]:
    return sorted(_REGISTRY)


def prop_spec_to_dict(spec: PropSpec) -> dict:
    from dataclasses import asdict
    return asdict(spec)


def prop_spec_from_dict(d: dict) -> PropSpec:
    d = dict(d)
    sh = d.get("shaft")
    if isinstance(sh, dict):
        d["shaft"] = PropShaftMount(**sh)
    return PropSpec(**d)
