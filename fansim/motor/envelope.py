"""Motor torque-speed envelope — a candidate must be drivable by the target motor.

"On the Noctua" means reusing the stock motor/bearing, so a high-flow impeller that needs more shaft
power than the motor can deliver at the rated speed is *not buildable on that motor*, however good
its CFD numbers. This gates candidates on required shaft power (and torque) at the operating RPM.

The stock NF-A12x25 motor's mechanical output is not published directly: spec gives ~1.68 W max
*input* (electrical) at 2000 RPM. Shaft power = input * motor_efficiency; small BLDC fan motors run
~30-45%, so ~0.4 is the default assumption (documented, calibrate against a real motor via
validation/ingest.py). Many idealized parametric designs draw ~10 mN.m (~2 W shaft) -> they'd exceed
the stock motor and only run on a stronger one; this gate makes that explicit.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class MotorEnvelope:
    name: str
    rated_rpm: float
    max_input_power_w: float
    motor_efficiency: float = 0.40   # electrical->mechanical; assumption, calibrate with real data

    @property
    def rated_omega(self) -> float:
        return self.rated_rpm * 2.0 * math.pi / 60.0

    @property
    def max_shaft_power_w(self) -> float:
        return self.max_input_power_w * self.motor_efficiency

    @property
    def max_torque_nm(self) -> float:
        """Torque available at the rated speed (P = T * omega)."""
        return self.max_shaft_power_w / self.rated_omega


@dataclass
class EnvelopeCheck:
    feasible: bool
    power_margin: float      # max_shaft_power / required_shaft_power (>1 = fits, with headroom)
    required_shaft_power_w: float
    reason: str = ""


def check_envelope(shaft_power_w: float, envelope: MotorEnvelope,
                   torque_nm: float | None = None) -> EnvelopeCheck:
    """Feasible iff required shaft power <= the motor's shaft-power capability at rated speed.

    Operating at the rated RPM, shaft power is the binding limit; torque is reported/checked too.
    Returns the power margin (>=1 means it fits) and a reason when it doesn't.
    """
    cap = envelope.max_shaft_power_w
    req = float(shaft_power_w)
    margin = cap / req if req > 0 else float("inf")
    if req > cap:
        return EnvelopeCheck(False, margin, req,
                             f"needs {req:.2f} W shaft > motor {cap:.2f} W "
                             f"(margin {margin:.2f}x) on {envelope.name}")
    if torque_nm is not None and torque_nm > envelope.max_torque_nm:
        return EnvelopeCheck(False, margin, req,
                             f"needs {torque_nm*1e3:.1f} mN.m > motor {envelope.max_torque_nm*1e3:.1f} "
                             f"mN.m at {envelope.rated_rpm:.0f} RPM")
    return EnvelopeCheck(True, margin, req)


# stock NF-A12x25 PWM motor (see [[fan-sim-a12x25-specs]]); efficiency assumed, not published
A12X25_MOTOR = MotorEnvelope(name="Noctua NF-A12x25", rated_rpm=2000.0,
                             max_input_power_w=1.68, motor_efficiency=0.50)  # audit 2026-10-10
