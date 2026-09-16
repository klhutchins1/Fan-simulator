"""Motor constraint layer: does the stock motor have the torque/power to drive a candidate?"""

from fansim.motor.envelope import (
    A12X25_MOTOR,
    EnvelopeCheck,
    MotorEnvelope,
    check_envelope,
)

__all__ = ["MotorEnvelope", "EnvelopeCheck", "check_envelope", "A12X25_MOTOR"]
