"""Trame busy chrome helpers (progress bar + elapsed ticker)."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Callable

from fansim.cockpit.busy import busy_caption


def make_busy_expr() -> Callable[..., str]:
    def busy_expr(*flags: str) -> str:
        return " || ".join(flags)
    return busy_expr


def make_busy_bar(v3: Any, busy_expr: Callable[..., str]) -> Callable[..., None]:
    def busy_bar(*flags: str, color: str = "primary", value: str | None = None) -> None:
        """``value``: a 0-100 state var; while it is > 0 the bar fills by stage instead of
        sweeping back and forth (the sweep read as "stuck", QA UI-4)."""
        stage = {"indeterminate": (f"!({value} > 0)",), "model_value": (value,)} if value else {
            "indeterminate": True}
        v3.VProgressLinear(
            **stage,
            height=6,
            color=color,
            rounded=True,
            classes="mt-2 mb-1",
            v_if=busy_expr(*flags),
        )
    return busy_bar


def make_spawn_busy_ticker(state: Any, asynchronous: Any) -> Callable[..., tuple]:
    def spawn_busy_ticker(
        *,
        action: str,
        msg_attr: str,
        busy_attr: str,
        note: str = "",
        hint_fn=None,
        interval: float = 1.0,
        skip_when=None,
    ):
        t0 = time.time()

        async def _tick():
            while bool(getattr(state, busy_attr)):
                if skip_when is not None and skip_when():
                    await asyncio.sleep(interval)
                    continue
                hint = hint_fn() if hint_fn else ""
                setattr(
                    state,
                    msg_attr,
                    busy_caption(action, time.time() - t0, hint=hint, note=note),
                )
                state.flush()
                await asyncio.sleep(interval)

        return asynchronous.create_task(_tick()), t0

    return spawn_busy_ticker
