"""Verdict rules for the flow report card (thresholds fixed in the spec, §24)."""

from __future__ import annotations

import math
from dataclasses import dataclass

from fansim.cfd.flow_report import FlowMetrics

ROW_KEYS = ("direction", "push", "spin", "dead", "noise")
TITLES = {"direction": "Air direction", "push": "Push along the blade", "spin": "Wasted spin",
          "dead": "Dead or blocked air", "noise": "Noise hint"}
ICONS = {"ok": "✓", "warn": "⚠", "bad": "✕", "na": "–"}

BACKFLOW_MARGIN = 0.02
BAND_TOL = 0.03  # mean push: 2σ of five Stock v3 repeats (27.3); five varied meshes gave 2.9 % (27.3b).
BAR_TOL = 0.08   # single bars: 2σ of Stock v3 on five varied meshes (roadmap 27.3b, Kimball 2026-10-16).
SWIRL_FACTOR = 1.10
DEAD_MARGIN = 0.02
TIP_FACTOR = 0.90
NOISE_MARGIN_DB = 0.5  # 2σ floor of the same five repeats; was 2.8 dB from that pair.
# Proudman is NOT judged (Kimball 2026-10-16): Stock alone read -13.7..+22.2 dB across five meshes (27.3b).
NOISE_JUDGED = False
NOISE_MESH_SPREAD_DB = 36  # max - min of Stock's Proudman SWL over the 27.3b meshes, rounded
# 27.3c: tip-speed + CFM hint is judged. 2σ on m1–m5 was 0.069 dB; floor 0.5.
HINT_MARGIN_DB = 0.5


@dataclass
class RowVerdict:
    key: str
    title: str
    status: str
    text: str
    better: bool | None
    bands: list[str] | None = None
    expert_only: bool = False


def _bad(x) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x))


def _pct(x: float) -> str:
    return f"{100.0 * x:.0f} %"


def _row(key, status, text, better=None, bands=None):
    return RowVerdict(key, TITLES[key], status, text, better, bands)


def _direction(d: FlowMetrics, s: FlowMetrics | None) -> RowVerdict:
    if d.net_reversed:
        return _row("direction", "bad",
                    "More air goes backwards than forwards: this fan is blowing the wrong way.", False)
    if _bad(d.backflow_frac):
        return _row("direction", "na", "Couldn't measure the air direction for this run.")
    if s is None:
        return _row("direction", "ok",
                    f"Air leaves out the back. {_pct(d.backflow_frac)} of the fan face flows backwards.")
    ok = d.backflow_frac <= s.backflow_frac + BACKFLOW_MARGIN + 1e-12
    text = (f"{_pct(d.backflow_frac)} of the fan face flows backwards "
            f"(Stock {_pct(s.backflow_frac)}). Less is better.")
    return _row("direction", "ok" if ok else "warn", text,
                better=d.backflow_frac < s.backflow_frac - BACKFLOW_MARGIN)


def _band_labels(d, s):
    labels = []
    for a, b in zip(d.band_dp0_pa, s.band_dp0_pa):
        if _bad(a) or _bad(b) or b == 0:
            labels.append("unknown")
        elif a > b * (1 + BAR_TOL):
            labels.append("stronger")
        elif a < b * (1 - BAR_TOL):
            labels.append("weaker")
        else:
            labels.append("similar")
    return labels


BARS_NOTE = "The bars show where along the blade; spin tilts them toward the tip, so read their shape loosely."


def _push(d, s):
    """Judged on the area-weighted mean push (Kimball 2026-10-12, roadmap 27.3 option b).

    Swirl alone shifts static pressure from hub to tip (radial equilibrium), so per-band labels made a
    swirly fan look hub-weak / tip-strong. That tilt cancels in the mean. Bands stay as a picture.
    """
    if s is None:
        return _row("push", "na", "No Stock comparison for the push along the blade.")
    labels = _band_labels(d, s)
    a, b = getattr(d, "mean_dp0_pa", None), getattr(s, "mean_dp0_pa", None)
    if _bad(a) or _bad(b) or b <= 0:
        return _row("push", "na", "Couldn't compare the overall push with Stock.", bands=labels)
    vs = f"({a:.1f} vs {b:.1f} Pa). {BARS_NOTE}"
    if a > b * (1 + BAND_TOL):
        return _row("push", "ok", f"Pushes about {_pct(a / b - 1)} harder than Stock overall {vs}",
                    better=True, bands=labels)
    if a < b * (1 - BAND_TOL):
        return _row("push", "warn", f"Pushes about {_pct(1 - a / b)} less than Stock overall {vs}",
                    better=False, bands=labels)
    return _row("push", "ok", f"Pushes about as hard as Stock overall {vs}", better=False, bands=labels)


def _spin(d, s):
    if s is None or _bad(d.swirl_frac) or _bad(s.swirl_frac):
        return _row("spin", "na", "Couldn't compare the spin in the outgoing air.")
    ok = d.swirl_frac <= s.swirl_frac * SWIRL_FACTOR + 1e-12
    text = (f"{_pct(d.swirl_frac)} of the outgoing air's energy is spin instead of forward flow "
            f"(Stock {_pct(s.swirl_frac)}). Less is better.")
    return _row("spin", "ok" if ok else "warn", text, better=d.swirl_frac < s.swirl_frac / SWIRL_FACTOR)


def _dead(d, s):
    vals = (d.dead_frac, d.tip_band_uz_ratio)
    if s is None or any(_bad(v) for v in vals) or _bad(s.dead_frac) or _bad(s.tip_band_uz_ratio):
        return _row("dead", "na", "Couldn't compare dead or blocked air.")
    dead_ok = d.dead_frac <= s.dead_frac + DEAD_MARGIN + 1e-12
    tip_ok = d.tip_band_uz_ratio >= s.tip_band_uz_ratio * TIP_FACTOR - 1e-12
    bits = [f"{_pct(d.dead_frac)} of the fan face has air that barely moves (Stock {_pct(s.dead_frac)})."]
    if not tip_ok:
        bits.append("Air near the blade tips is weak: likely leaking round the tips.")
    return _row("dead", "ok" if dead_ok and tip_ok else "warn", " ".join(bits),
                better=d.dead_frac < s.dead_frac - DEAD_MARGIN and tip_ok)


def _noise(d, s):
    hint_d = getattr(d, "noise_hint_db", None)
    hint_s = getattr(s, "noise_hint_db", None) if s is not None else None
    if hint_d is not None and hint_s is not None:
        delta = float(hint_d) - float(hint_s)
        if abs(delta) <= HINT_MARGIN_DB + 1e-12:
            text = ("About as loud as Stock from tip speed and airflow "
                    "(ranking only, not a microphone reading).")
            row = _row("noise", "ok", text, better=False)
        else:
            word = "quieter" if delta < 0 else "louder"
            text = (f"About {abs(delta):.1f} dB {word} than Stock from tip speed and airflow "
                    "(ranking only, not a microphone reading).")
            row = _row("noise", "ok" if delta < 0 else "warn", text,
                       better=delta < 0)
        row.expert_only = True
        return row
    if d.noise_swl_db is None:
        return _row("noise", "na", "No turbulence data in this run.")
    if s is None or s.noise_swl_db is None:
        return _row("noise", "na", "No Stock comparison for noise.")
    delta = d.noise_swl_db - s.noise_swl_db
    if not NOISE_JUDGED:
        text = (f"Not judged: on different meshes the same Stock fan's estimate moved by about "
                f"{NOISE_MESH_SPREAD_DB} dB, so this {delta:+.1f} dB difference is mostly mesh, not design.")
        row = _row("noise", "na", text)
        row.expert_only = True
        return row
    word = "quieter" if delta < 0 else "louder"
    text = (f"Rough estimate: about {abs(delta):.1f} dB {word} than Stock. "
            "Compare only; this is not a real sound measurement.")
    return _row("noise", "ok" if delta <= NOISE_MARGIN_DB + 1e-12 else "warn", text,
                better=delta < -NOISE_MARGIN_DB)


def judge(design: FlowMetrics, stock: FlowMetrics | None) -> list[RowVerdict]:
    return [_direction(design, stock), _push(design, stock), _spin(design, stock),
            _dead(design, stock), _noise(design, stock)]


def overall_line(rows: list[RowVerdict], compared: bool) -> str:
    if not compared:
        return "No Stock comparison for this run, so only the air direction is checked."
    shown = [r for r in rows if not r.expert_only]
    better = [r.title.lower() for r in shown if r.status == "ok" and r.better]
    worse = [r.title.lower() for r in shown if r.status in ("warn", "bad")]
    if not better and not worse:
        return "About the same as Stock on every check."
    parts = []
    if better:
        parts.append("Better than Stock at: " + ", ".join(better) + ".")
    if worse:
        parts.append("Worse at: " + ", ".join(worse) + ".")
    return " ".join(parts)
