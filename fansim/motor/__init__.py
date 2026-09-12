# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Motor constraint layer: does the stock motor have the torque/power to drive a candidate?"""

from fansim.motor.envelope import (
    A12X25_MOTOR,
    EnvelopeCheck,
    MotorEnvelope,
    check_envelope,
)

__all__ = ["MotorEnvelope", "EnvelopeCheck", "check_envelope", "A12X25_MOTOR"]
