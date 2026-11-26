"""Verdict rules for the flow report card (thresholds fixed in the spec, §24)."""

from __future__ import annotations

import math
from dataclasses import dataclass

from fansim.cfd.flow_report import FlowMetrics

ROW_KEYS = ("direction", "push", "spin", "dead", "noise")
TITLES = {"direction": "Air direction", "push": "Push along the blade", "spin": "Wasted spin",
          "dead": "Dead or blocked air", "noise": "Noise hint"}
ICONS = {"ok": "✓", "warn": "⚠", "bad": "✕", "na": "–"}

# Flow report v4 (blade-relative planes, 27.3e): 2σ of Stock v3 on five varied meshes, Kimball 2026-10-17 (R0.2).
BAND_TOL = 0.06  # mean push: 5.7 % (was 0.03 at v3 planes)
BAR_TOL = 0.12   # single bars (was 0.08 at v3 planes)
# R0.3: two-run scatter = max(existing margin, ceil(√2 × 2σ)) on v4 Stock meshes.
CLOSE_BAND = 0.08          # mean push, relative
CLOSE_BACKFLOW = 0.02      # abs
CLOSE_SWIRL_REL = 0.10     # never tighten the 1.10 factor
CLOSE_DEAD = 0.02          # abs, never tighten
CLOSE_TIP_REL = 0.15       # tip/mean Uz, relative
NOISE_MARGIN_DB = 0.5  # 2σ floor of the same five repeats; was 2.8 dB from that pair.
# Proudman is NOT judged (Kimball 2026-10-16): Stock alone read -13.7..+22.2 dB across five meshes (27.3b).
NOISE_JUDGED = False
NOISE_MESH_SPREAD_DB = 36  # max - min of Stock's Proudman SWL over the 27.3b meshes, rounded
# 27.3c / R0.4: the tip-speed + CFM hint is never judged (it restates CFM at fixed rpm/tip).
# 2σ on m1–m5 was 0.069 dB; floor kept at 0.5 if judging is ever restored.
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
    return x is None or (isinstance(x, float) and not math.isfinite(x))


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
    if _bad(s.backflow_frac):
        return _row("direction", "na", "Couldn't compare the air direction with Stock.")
    delta = d.backflow_frac - s.backflow_frac
    text = (f"{_pct(d.backflow_frac)} of the fan face flows backwards "
            f"(Stock {_pct(s.backflow_frac)}). Less is better.")
    if abs(delta) <= CLOSE_BACKFLOW + 1e-12:
        return _row("direction", "na", f"Too close to call. {text}")
    return _row("direction", "ok" if delta < 0 else "warn", text, better=delta < 0)


def _band_labels(d, s):
    labels = []
    for a, b in zip(d.band_dp0_pa, s.band_dp0_pa):
        if _bad(a) or _bad(b) or b == 0:
            labels.append("unknown")
        elif a > b + BAR_TOL * abs(b):
            labels.append("stronger")
        elif a < b - BAR_TOL * abs(b):
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
    rel = a / b - 1.0
    if abs(rel) <= CLOSE_BAND + 1e-12:
        return _row("push", "na", f"Too close to call. {vs}", bands=labels)
    if rel > 0:
        return _row("push", "ok", f"Pushes about {_pct(rel)} harder than Stock overall {vs}",
                    better=True, bands=labels)
    return _row("push", "warn", f"Pushes about {_pct(-rel)} less than Stock overall {vs}",
                better=False, bands=labels)


def _spin(d, s):
    if s is None or _bad(d.swirl_frac) or _bad(s.swirl_frac):
        return _row("spin", "na", "Couldn't compare the spin in the outgoing air.")
    text = (f"{_pct(d.swirl_frac)} of the outgoing air's energy is spin instead of forward flow "
            f"(Stock {_pct(s.swirl_frac)}). Less is better.")
    if s.swirl_frac <= 0:
        return _row("spin", "na", text)
    rel = d.swirl_frac / s.swirl_frac - 1.0
    if abs(rel) <= CLOSE_SWIRL_REL + 1e-12:
        return _row("spin", "na", f"Too close to call. {text}")
    return _row("spin", "ok" if rel < 0 else "warn", text, better=rel < 0)


def _dead(d, s):
    vals = (d.dead_frac, d.tip_band_uz_ratio)
    if s is None or any(_bad(v) for v in vals) or _bad(s.dead_frac) or _bad(s.tip_band_uz_ratio):
        return _row("dead", "na", "Couldn't compare dead or blocked air.")
    bits = [f"{_pct(d.dead_frac)} of the fan face has air that barely moves (Stock {_pct(s.dead_frac)})."]
    dead_delta = d.dead_frac - s.dead_frac
    tip_comparable = s.tip_band_uz_ratio > 0
    tip_rel = (d.tip_band_uz_ratio / s.tip_band_uz_ratio - 1.0) if tip_comparable else None
    worse_dead = dead_delta > CLOSE_DEAD + 1e-12
    worse_tip = tip_rel is not None and tip_rel < -CLOSE_TIP_REL - 1e-12
    better_dead = dead_delta < -CLOSE_DEAD - 1e-12
    better_tip = tip_rel is not None and tip_rel > CLOSE_TIP_REL + 1e-12
    if not tip_comparable:
        bits.append("Couldn't compare tip airflow with Stock.")
    elif worse_tip:
        bits.append("Air near the blade tips is weak: likely leaking round the tips.")
    elif better_tip:
        bits.append("Air near the blade tips is stronger than Stock.")
    extra = " ".join(bits)
    if worse_dead or worse_tip:
        return _row("dead", "warn", extra, better=False)
    if better_dead or better_tip:
        return _row("dead", "ok", extra, better=True)
    if not tip_comparable:
        return _row("dead", "na", extra)
    return _row("dead", "na", f"Too close to call. {extra}")


def _noise(d, s):
    # R0.4 / G2: the hint restates CFM at fixed rpm/tip. Never ✓/⚠/better.
    g2 = ("Scales with tip speed and airflow only; this is not a comparison of "
          "how quiet the design is.")
    hint_d = getattr(d, "noise_hint_db", None)
    hint_s = getattr(s, "noise_hint_db", None) if s is not None else None
    if not _bad(hint_d):
        if not _bad(hint_s):
            text = f"Hint {float(hint_d):.1f} (Stock {float(hint_s):.1f}). {g2}"
        else:
            text = f"Hint {float(hint_d):.1f}. {g2}"
        row = _row("noise", "na", text)
        row.expert_only = True
        return row
    if _bad(d.noise_swl_db):
        return _row("noise", "na", "No turbulence data in this run.")
    if s is None or _bad(s.noise_swl_db):
        row = _row("noise", "na", "No Stock comparison for noise.")
        row.expert_only = True
        return row
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
        direction = next((r for r in rows if r.key == "direction"), None)
        if direction is not None and direction.status == "bad":
            return (
                "No Stock comparison for this run, and the air direction check failed: "
                "this fan is blowing the wrong way."
            )
        return "No Stock comparison for this run, so only the air direction is checked."
    shown = [r for r in rows if not r.expert_only]
    better = [r.title.lower() for r in shown if r.status == "ok" and r.better]
    worse = [r.title.lower() for r in shown if r.status in ("warn", "bad")]
    if not better and not worse:
        compared_rows = [
            r for r in shown
            if r.status != "na" or r.text.startswith("Too close to call")
        ]
        if not compared_rows:
            return "Couldn't compare this run with Stock: no checks had comparable data."
        if len(compared_rows) < len(shown):
            return "About the same as Stock on the comparable checks."
        return "About the same as Stock on every check."
    parts = []
    if better:
        parts.append("Better than Stock at: " + ", ".join(better) + ".")
    if worse:
        parts.append("Worse at: " + ", ".join(worse) + ".")
    return " ".join(parts)
