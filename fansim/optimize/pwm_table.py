"""PWM duty ↔ RPM tables for PC fans (roadmap §2.5 leftovers).

Noctua NF-A12x25 PWM publishes 450–2000 RPM. Stage 1 uses a linear duty map
between those endpoints (honest approximation — real fans have a deadband and
soft start). Kv is a coarse estimate from no-load RPM / bus voltage.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PwmRpmTable:
    name: str
    rpm_min: float  # at ~0% usable PWM (idle floor)
    rpm_max: float  # at 100% duty
    voltage_v: float = 12.0

    def rpm_at_duty(self, duty_pct: float) -> float:
        d = min(max(float(duty_pct), 0.0), 100.0) / 100.0
        return float(self.rpm_min) + d * (float(self.rpm_max) - float(self.rpm_min))

    def duty_at_rpm(self, rpm: float) -> float:
        span = float(self.rpm_max) - float(self.rpm_min)
        if span <= 0:
            return 0.0
        d = (float(rpm) - float(self.rpm_min)) / span
        return min(max(d * 100.0, 0.0), 100.0)

    @property
    def kv_approx(self) -> float:
        """Rough Kv [RPM/V] from no-load ≈ rpm_max at bus voltage."""
        v = max(float(self.voltage_v), 1e-6)
        return float(self.rpm_max) / v


A12X25_PWM = PwmRpmTable(
    name="noctua_nf_a12x25_pwm",
    rpm_min=450.0,
    rpm_max=2000.0,
    voltage_v=12.0,
)

_TABLES = {
    "a12x25": A12X25_PWM,
    "noctua_nf_a12x25_pwm": A12X25_PWM,
}


def get_pwm_table(name: str = "a12x25") -> PwmRpmTable:
    if name not in _TABLES:
        raise KeyError(f"unknown PWM table '{name}'; known: {sorted(_TABLES)}")
    return _TABLES[name]


def make_pwm_table(
    rpm_min: float,
    rpm_max: float,
    *,
    name: str = "custom",
    voltage_v: float = 12.0,
) -> PwmRpmTable:
    """Build an editable PWM band (cockpit editor / ``--rpm-min`` / ``--rpm-max``)."""
    lo, hi = float(rpm_min), float(rpm_max)
    if lo < 0:
        raise ValueError(f"rpm_min must be >= 0 (got {lo})")
    if not (lo < hi):
        raise ValueError(f"rpm_min ({lo}) must be < rpm_max ({hi})")
    return PwmRpmTable(name=name, rpm_min=lo, rpm_max=hi, voltage_v=float(voltage_v))


def resolve_pwm_table(
    rpm_min: float | None = None,
    rpm_max: float | None = None,
    *,
    base: PwmRpmTable | None = None,
) -> PwmRpmTable:
    """A12x25 defaults, optionally overridden by editor / CLI bounds."""
    tab = base or A12X25_PWM
    if rpm_min is None and rpm_max is None:
        return tab
    return make_pwm_table(
        float(tab.rpm_min if rpm_min is None else rpm_min),
        float(tab.rpm_max if rpm_max is None else rpm_max),
        name=f"{tab.name}_edit",
        voltage_v=tab.voltage_v,
    )


def pwm_caption(table: PwmRpmTable | None = None) -> str:
    """One-line duty↔RPM honesty string for the cockpit PWM editor."""
    tab = table or A12X25_PWM
    mid = 0.5 * (tab.rpm_min + tab.rpm_max)
    return (
        f"Linear PWM map {tab.rpm_min:.0f}–{tab.rpm_max:.0f} RPM "
        f"(50% ≈ {mid:.0f}; Kv≈{tab.kv_approx:.0f} RPM/V from rpm_max/V). "
        f"Motor derate uses Kv no-load + I_max·V shaft cap. Not a deadband model."
    )


def suggest_rpm(trial, table: PwmRpmTable | None = None) -> float:
    """Optuna DOF: RPM within the PWM envelope (default A12x25 450–2000)."""
    tab = table or A12X25_PWM
    return float(trial.suggest_float("rpm", tab.rpm_min, tab.rpm_max))
