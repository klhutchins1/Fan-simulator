"""Whole-number checks for cockpit run-count fields (UI-39 Sweep steps, UI-40 Optimize trials).

Each returns ``(value, None)`` when the typed value is a whole number inside the range, else ``(None, message)``.
Nothing is clamped: a run must use exactly what the field shows, or refuse visibly.
"""

from __future__ import annotations

SWEEP_STEPS_RANGE = (2, 12)
OPT_TRIALS_RANGE = (2, 40)


def whole_in_range(raw, lo: int, hi: int, what: str, why: str = "") -> tuple[int | None, str | None]:
    text = "" if raw is None else str(raw).strip()
    try:
        val = float(text)
    except ValueError:
        val = None
    if val is None or val != val or not val.is_integer() or not lo <= val <= hi:
        tail = f" ({why})" if why else ""
        return None, f"⚠ {what} must be a whole number from {lo} to {hi}{tail}. Nothing was started."
    return int(val), None


def sweep_steps(raw):
    lo, hi = SWEEP_STEPS_RANGE
    return whole_in_range(raw, lo, hi, "Sweep steps", "each step is a full CFD Assess")


def opt_trials(raw):
    lo, hi = OPT_TRIALS_RANGE
    return whole_in_range(raw, lo, hi, "Optimize trials", "each trial is a full CFD solve")
