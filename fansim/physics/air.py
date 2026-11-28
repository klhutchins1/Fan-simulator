"""Single source of air properties: room-temperature, sea-level air.

Two densities are deliberate. Fans and ducted CFD use AMCA 210 standard air (1.2 kg/m³, 20 °C,
101.325 kPa). Props and turbines use ISA sea level (1.225 kg/m³, 15 °C) to match the published data
they are compared against. Import from here; do not redefine locally
(``tests/audit/test_air_properties.py`` fails on new copies).
The guard catches module-level literal assignments (plain, annotated, and tuple); it does not catch computed values or other names.
"""

from __future__ import annotations

import math

P0_PA = 101325.0      # sea-level static pressure, Pa
T_ROOM_K = 293.15     # 20 °C
T_ISA_K = 288.15      # 15 °C — ISA sea level (ISO 2533:1975)
R_AIR = 287.05        # specific gas constant of dry air, J/(kg·K)
GAMMA_AIR = 1.4       # ratio of specific heats

RHO_AMCA = 1.2        # kg/m³ — AMCA 210 standard air (fans, ducted CFD)
RHO_ISA = 1.225       # kg/m³ — ISA sea level (props, turbines, UIUC comparisons)
MU_AIR = 1.81e-5      # dynamic viscosity at 20 °C, Pa·s (Sutherland)
NU_AIR = MU_AIR / RHO_AMCA  # kinematic viscosity at 20 °C, m²/s (#48: one definition)
C0_AIR = 343.0        # speed of sound at 20 °C, m/s
MU_ISA = 1.7894e-5    # dynamic viscosity at 15 °C, Pa·s (ISO 2533:1975 / Sutherland)
NU_ISA = MU_ISA / RHO_ISA   # kinematic viscosity at 15 °C, m²/s (#112)
C0_ISA = math.sqrt(GAMMA_AIR * R_AIR * T_ISA_K)  # speed of sound at 15 °C, m/s (~340.29)
