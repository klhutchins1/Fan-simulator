# EXTRACTED-FROM-CURSOR-TRANSCRIPT 2026-09-12
# source: agent-transcripts/9f43d5b7...jsonl write@217 + 1 later StrReplace
# NOT verified against lost E: tree — re-check before deleting RECOVERED-FROM-CHAT peers.

"""Application load presets for the fan optimizer (roadmap §3.1).

Each preset sets the CFD load-point so ``cfm_load`` is airflow against a real
application impedance. NSGA-II still maximizes (cfm_free, cfm_load, efficiency);
the load-point is what changes which Pareto members win.

    case      8 Pa   free-air / case dump
    heatsink 20 Pa   CPU/GPU cooler
    radiator  35 Pa  liquid-cooling radiator

An explicit ``load_pa`` always wins over the preset's default.
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_LOAD_PA = 1.0  # mild free-air; historical optimizer default


@dataclass(frozen=True)
class ApplicationPreset:
    name: str
    load_pa: float
    summary: str


PRESETS: dict[str, ApplicationPreset] = {
    "case": ApplicationPreset("case", 8.0, "free-air / case dump (~5–15 Pa)"),
    "heatsink": ApplicationPreset("heatsink", 20.0, "CPU/GPU heatsink (~10–30 Pa)"),
    "radiator": ApplicationPreset("radiator", 35.0, "radiator (~20–40 Pa)"),
}


def resolve_load(preset: str | None = None, load_pa: float | None = None
                 ) -> tuple[float, str | None]:
    """Return ``(load_pa, preset_name)``.

    * neither set → historical 1 Pa free-air default
    * preset only → that application's load
    * ``load_pa`` set → that value (overrides the preset's default)
    """
    name: str | None = None
    if preset is not None:
        if preset not in PRESETS:
            known = ", ".join(sorted(PRESETS))
            raise ValueError(f"unknown preset {preset!r}; expected one of: {known}")
        name = preset
    if load_pa is not None:
        return float(load_pa), name
    if name is not None:
        return PRESETS[name].load_pa, name
    return DEFAULT_LOAD_PA, None


def assess_preset_items() -> list[dict]:
    """VSelect items for cockpit Assess: legacy 1 Pa plus the three application hoses."""
    items = [{"title": "1 Pa (legacy)", "value": "legacy"}]
    titles = {"case": "Case", "heatsink": "Heatsink", "radiator": "Radiator"}
    for name, preset in PRESETS.items():
        title = f"{titles.get(name, name.capitalize())} {preset.load_pa:g} Pa"
        items.append({"title": title, "value": name})
    return items


def assess_load(preset: str) -> tuple[float, str]:
    """``(load_pa, label)`` for an Assess picker value. ``legacy`` is 1 Pa."""
    key = (preset or "legacy").strip()
    if key == "legacy":
        return DEFAULT_LOAD_PA, "1 Pa (legacy)"
    pa, name = resolve_load(preset=key)
    return pa, f"{name} {pa:g} Pa @ 50 CFM"
