"""Single source of air properties: room-temperature, sea-level air.

Two densities are deliberate. Fans and ducted CFD use AMCA 210 standard air (1.2 kg/m³, 20 °C,
101.325 kPa). Props and turbines use ISA sea level (1.225 kg/m³, 15 °C) to match the published data
they are compared against. Import from here; do not redefine locally
(``tests/audit/test_air_properties.py`` fails on new copies).
The guard catches module-level literal assignments (plain, annotated, and tuple); it does not catch computed values or other names.
"""

from __future__ import annotations

P0_PA = 101325.0      # sea-level static pressure, Pa
T_ROOM_K = 293.15     # 20 °C
R_AIR = 287.05        # specific gas constant of dry air, J/(kg·K)
GAMMA_AIR = 1.4       # ratio of specific heats

RHO_AMCA = 1.2        # kg/m³ — AMCA 210 standard air (fans, ducted CFD)
RHO_ISA = 1.225       # kg/m³ — ISA sea level (props, turbines, UIUC comparisons)
MU_AIR = 1.81e-5      # dynamic viscosity at 20 °C, Pa·s (Sutherland)
NU_AIR = 1.5e-5       # kinematic viscosity, m²/s (MU_AIR / RHO_AMCA ≈ 1.51e-5)
C0_AIR = 343.0        # speed of sound at 20 °C, m/s
