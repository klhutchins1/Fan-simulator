"""Shared cockpit session handle passed into tab setup/render."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass
class CockpitCtx:
    server: Any
    state: Any
    ctrl: Any
    run_dir: Path
    runs_root: Path
    plotter: Any
    busy_bar: Callable[..., None]
    busy_expr: Callable[..., str]
    spawn_busy_ticker: Callable[..., tuple]

    # Non-Fan VTK plotters — None until first Mixed/Volute/Prop/CROR visit (§12.3 / §14.6).
    prop_plotter: Any = None
    mf_plotter: Any = None
    volute_plotter: Any = None
    cror_plotter: Any = None

    # Optional Fan session fields (populated by the cockpit shell before `setup_fan_tab`).
    study_name: str | None = None
    study_designs: Any | None = None
    user_designs: Any | None = None
    by_trial: Any | None = None
    next_id: Any | None = None
    assess_dir: Path | None = None
