"""Physics-regime classification: pick solver + turbulence model from the operating conditions."""

from fansim.physics.regime import Regime, classify_regime, fan_regime

__all__ = ["Regime", "classify_regime", "fan_regime"]
