"""Cockpit Home / Start tab: plain-language overview, 4 choices, workflow, and honesty summary.

Shown on launch so first-time users immediately see what the app does, where to start,
and what is validated vs experimental before diving into sliders.
"""

from __future__ import annotations

import sys

from fansim.cockpit.context import CockpitCtx
from fansim.cockpit.diagrams import visual_guide_cards
from fansim.cockpit.experimental import EXPERIMENTAL_LABEL

HOME_TAB = "home"

_RUNNING_TESTS = "pytest" in sys.modules

if _RUNNING_TESTS:
    html = None  # type: ignore[assignment]
    v3 = None  # type: ignore[assignment]
else:
    from trame.widgets import html
    from trame.widgets import vuetify3 as v3


def home_choices() -> list[dict[str, str]]:
    """Four primary start-page actions (plain English, no jargon)."""
    return [
        {
            "key": "fan",
            "title": "Design a PC fan",
            "badge": "Airflow checked",
            "subtitle": (
                "Start from a Noctua A12x25-class blade, tune the shape in 3-D, "
                "check airflow, and export a print-ready STL."
            ),
            "cta": "Open Fan designer",
            "color": "primary",
        },
        {
            "key": "prop",
            "title": "Design a propeller",
            "badge": "Fast estimate (~1 s)",
            "subtitle": (
                "Tune a 2–4 blade drone propeller with instant thrust and efficiency "
                "estimates, then export a printable STL."
            ),
            "cta": "Open Propeller designer",
            "color": "primary",
        },
        {
            "key": "saved",
            "title": "Open a saved design",
            "badge": "Results & Library",
            "subtitle": (
                "Compare previously scored blades on the airflow chart or load a saved "
                "design onto your fan hub."
            ),
            "cta": "Browse saved designs",
            "color": "secondary",
        },
        {
            "key": "accuracy",
            "title": "How accuracy is checked",
            "badge": "Honest limits",
            "subtitle": (
                "See which numbers are checked against published fan and propeller tests, "
                "and which tools are still experimental."
            ),
            "cta": "Read accuracy guide",
            "color": "secondary",
        },
    ]


def home_steps() -> list[dict[str, str]]:
    """Short 4-step 'how it works' flow."""
    return [
        {
            "num": "1",
            "title": "Pick a starting blade",
            "detail": "Stock Noctua A12x25 fan or a common drone propeller size.",
        },
        {
            "num": "2",
            "title": "Preview in 3-D (seconds)",
            "detail": "Adjust blade count, angle, width, and scoop; check that it fits the frame.",
        },
        {
            "num": "3",
            "title": "Check airflow",
            "detail": "Fan Assess runs real CFD (~30–40 min in Docker). Propeller Analyze takes ~1 s.",
        },
        {
            "num": "4",
            "title": "Export STL & print",
            "detail": "Download a print-ready STL with motor mount cavity and print checklist.",
        },
    ]


def home_validated_items() -> list[dict[str, str]]:
    """What is checked against published data (plain language)."""
    return [
        {
            "title": "PC-fan airflow (Fan tab)",
            "detail": (
                "Full CFD method checked against published PC fans near free air "
                "(−0.5 % on Noctua A12x25; +8.1 % on lt120 at 6.85 Pa). "
                "Loaded airflow ranks designs well, though absolute values under load can read ~25 % high. "
                "Cockpit Assess uses a faster screening mesh for comparing designs."
            ),
        },
        {
            "title": "Propeller fast estimate (Prop tab)",
            "detail": (
                "Fast (~1 s) blade-element estimate checked against UIUC wind-tunnel propeller data. "
                "Best for comparing blade shapes, thrust, and efficiency."
            ),
        },
    ]


def home_experimental_items() -> list[dict[str, str]]:
    """What is NOT validated (plain language; never include a pass mark)."""
    return [
        {
            "title": "Noise & blade vibration",
            "detail": (
                "Estimates for exploration only. Blade-pass tone frequency (RPM × blades) is exact, "
                "but loudness levels and vibration checks are not validated against lab measurements."
            ),
        },
        {
            "title": "Mixed-flow, Volute, Prop CFD & CROR (Expert mode)",
            "detail": (
                f"{EXPERIMENTAL_LABEL} Switch to Expert in the top bar to explore these tabs "
                "or multi-design Optimize runs."
            ),
        },
    ]


def setup_home_tab(ctx: CockpitCtx) -> None:
    """Seed Home state and bind routing handlers onto ``ctx``."""
    state = ctx.state

    state.home_tagline = (
        "Design 3D-printable PC cooling fans and drone propellers, check how much air "
        "they move, and export print-ready STL files."
    )
    state.home_choices = home_choices()
    state.home_steps = home_steps()
    state.home_validated_items = home_validated_items()
    state.home_experimental_items = home_experimental_items()
    state.home_diagrams = visual_guide_cards()
    state.home_accuracy_open = False

    def home_go_fan(**_):
        state.active_tab = "fan"
        state.fan_subtab = "design"
        state.flush()

    def home_go_prop(**_):
        state.active_tab = "propeller"
        state.prop_subtab = "design"
        state.flush()

    def home_go_saved(**_):
        state.active_tab = "fan"
        n_scored = int(getattr(state, "n_scored_designs", 0) or 0)
        state.fan_subtab = "results" if n_scored >= 1 else "library"
        state.flush()

    def home_toggle_accuracy(**_):
        state.home_accuracy_open = not bool(getattr(state, "home_accuracy_open", False))
        state.flush()

    def home_choose(key: str = "", **_):
        if key == "fan":
            home_go_fan()
        elif key == "prop":
            home_go_prop()
        elif key == "saved":
            home_go_saved()
        elif key == "accuracy":
            home_toggle_accuracy()

    ctx.home_go_fan = home_go_fan  # type: ignore[attr-defined]
    ctx.home_go_prop = home_go_prop  # type: ignore[attr-defined]
    ctx.home_go_saved = home_go_saved  # type: ignore[attr-defined]
    ctx.home_toggle_accuracy = home_toggle_accuracy  # type: ignore[attr-defined]
    ctx.home_choose = home_choose  # type: ignore[attr-defined]


def render_home_tab(ctx: CockpitCtx) -> None:
    """Render the Home start page inside the cockpit layout."""
    if html is None or v3 is None:
        return

    home_choose = ctx.home_choose

    with html.Div(
        v_show=f"active_tab === '{HOME_TAB}'",
        style="max-width: 1180px; margin: 0 auto;",
    ):
        # Hero card
        with v3.VCard(classes="pa-4 mb-3", variant="tonal", color="primary"):
            html.Div("Welcome to Fan Simulator", classes="text-h5 font-weight-bold mb-1")
            html.Div("{{ home_tagline }}", classes="text-body-1")
            html.Div(
                "{{ cfd_readiness }}",
                classes="text-caption mt-2",
                v_show="cfd_readiness",
            )

        # 4 big start choices
        with v3.VRow(dense=True, classes="mb-3"):
            with v3.VCol(
                v_for="c in home_choices",
                key="c.key",
                cols=12,
                sm=6,
                md=3,
            ):
                with v3.VCard(
                    classes="pa-3 d-flex flex-column justify-space-between",
                    style="height: 100%; cursor: pointer;",
                    variant="outlined",
                    click=(home_choose, "[c.key]"),
                ):
                    with html.Div():
                        with html.Div(classes="d-flex justify-space-between align-center mb-1"):
                            html.Div("{{ c.title }}", classes="text-subtitle-1 font-weight-bold")
                        v3.VChip(
                            "{{ c.badge }}",
                            size="x-small",
                            variant="tonal",
                            color=("c.color",),
                            classes="mb-2",
                        )
                        html.Div(
                            "{{ c.subtitle }}",
                            classes="text-body-2 text-medium-emphasis mb-3",
                        )
                    v3.VBtn(
                        "{{ c.cta }}",
                        color=("c.color",),
                        variant="tonal",
                        size="small",
                        block=True,
                        click_stop=(home_choose, "[c.key]"),
                    )

        # Expandable accuracy + visual concept guide (toggled by choice #4)
        with v3.VCard(classes="pa-4 mb-3", variant="outlined", v_show="home_accuracy_open"):
            with html.Div(classes="d-flex justify-space-between align-center mb-2"):
                html.Div("How accuracy is checked & key blade terms", classes="text-h6")
                v3.VBtn(
                    "Hide",
                    size="x-small",
                    variant="text",
                    click="home_accuracy_open = false",
                )
            html.Div(
                "Scores shown in the cockpit reflect airflow simulations adjusted for the fan's "
                "motor power limit and an assumed 5 % 3D-printed surface roughness knockdown. "
                "Because the Stock reference blade is rebuilt from a parametric recipe (about 5 % "
                "lower airflow than a molded Noctua A12x25), compare your blade against Stock in "
                "the same test rather than chasing raw datasheet numbers.",
                classes="text-body-2 mb-3",
            )
            html.Div(
                "Visual guide — what the main blade controls mean:",
                classes="text-subtitle-2 mb-2",
            )
            with v3.VRow(dense=True):
                with v3.VCol(
                    v_for="dg in home_diagrams",
                    key="dg.key",
                    cols=12,
                    sm=6,
                    md=3,
                ):
                    with v3.VCard(classes="pa-2", variant="flat", style="background:#f8fafc;"):
                        html.Img(
                            src=("dg.src",),
                            alt=("dg.title",),
                            style="width:100%;display:block;border-radius:4px;",
                        )
                        html.Div("{{ dg.caption }}", classes="text-caption mt-1 text-medium-emphasis")
            html.Div(
                "More detail in the repo docs: docs/VALIDATION.md, docs/validation/scoreboard.md, "
                "docs/how-scores-are-computed.md, and docs/design-rules.md.",
                classes="text-caption text-medium-emphasis mt-2",
            )

        # How it works (4-step flow)
        with v3.VCard(classes="pa-3 mb-3", variant="outlined"):
            html.Div("How it works", classes="text-subtitle-1 font-weight-bold mb-2")
            with v3.VRow(dense=True):
                with v3.VCol(
                    v_for="st in home_steps",
                    key="st.num",
                    cols=12,
                    sm=6,
                    md=3,
                ):
                    with html.Div(classes="pa-1"):
                        html.Div(
                            "{{ st.num }}. {{ st.title }}",
                            classes="text-subtitle-2 font-weight-medium",
                        )
                        html.Div("{{ st.detail }}", classes="text-caption text-medium-emphasis")

        # Validated vs Experimental (plain language, side by side)
        with v3.VRow(dense=True):
            with v3.VCol(cols=12, md=6):
                with v3.VCard(classes="pa-3", variant="outlined", style="height: 100%;"):
                    html.Div(
                        "Checked against published data",
                        classes="text-subtitle-1 font-weight-bold mb-2 text-success",
                    )
                    with html.Div(
                        v_for="item in home_validated_items",
                        key="item.title",
                        classes="mb-2",
                    ):
                        html.Div("{{ item.title }}", classes="text-subtitle-2")
                        html.Div("{{ item.detail }}", classes="text-caption text-medium-emphasis")
            with v3.VCol(cols=12, md=6):
                with v3.VCard(classes="pa-3", variant="outlined", style="height: 100%;"):
                    html.Div(
                        "Experimental (not validated)",
                        classes="text-subtitle-1 font-weight-bold mb-2 text-warning",
                    )
                    with html.Div(
                        v_for="item in home_experimental_items",
                        key="item.title",
                        classes="mb-2",
                    ):
                        html.Div("{{ item.title }}", classes="text-subtitle-2")
                        html.Div("{{ item.detail }}", classes="text-caption text-medium-emphasis")
