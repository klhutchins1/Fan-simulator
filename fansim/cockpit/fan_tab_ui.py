"""Fan tab Trame UI (Design / Results / Library / Optimize panels).

Extracted from fan_tab.py (roadmap sec 13.9). Callbacks live in setup_fan_tab;
this module only builds widgets and binds ctrl.view_update / figure_update.
"""

from __future__ import annotations

from pathlib import Path

import sys

from fansim.cockpit.context import CockpitCtx
from fansim.cockpit.fan_copy import CONTROL_DESC, OPT_SEARCH_HELP
from fansim.cockpit.tab_shell import VTK_VIEW_STYLE, render_action_row
from fansim.cockpit.fan_widgets import help_select, help_switch, opt_section, slider
from fansim.cockpit.figures import filter_fitting_designs, scatter_figure
from fansim.fan_spec import published_scatter_point
from fansim.optimize.presets import assess_load

_RUNNING_TESTS = "pytest" in sys.modules

if _RUNNING_TESTS:
    pv = None  # type: ignore[assignment]
    plotter_ui = None  # type: ignore[assignment]
    html = None  # type: ignore[assignment]
    plotly_widgets = None  # type: ignore[assignment]
    v3 = None  # type: ignore[assignment]
else:
    import pyvista as pv
    from pyvista.trame.ui import plotter_ui
    from trame.widgets import html
    from trame.widgets import plotly as plotly_widgets
    from trame.widgets import vuetify3 as v3

# Local aliases matching the former fan_tab helpers
_slider = slider
_opt_section = opt_section
_help_switch = help_switch
_help_select = help_select


def render_fan_tab(ctx: CockpitCtx) -> None:
    """Build Fan UI (call inside layout content)."""
    state, ctrl = ctx.state, ctx.ctrl
    plotter = ctx.plotter
    busy_bar = ctx.busy_bar

    study_designs = ctx.study_designs or []  # type: ignore[attr-defined]
    user_designs = ctx.user_designs or []  # type: ignore[attr-defined]

    select = getattr(ctx, "fan_select")
    on_plotly_click = getattr(ctx, "fan_on_plotly_click")
    on_library_scale_to_hub = getattr(ctx, "fan_on_library_scale_to_hub")
    select_library_design = getattr(ctx, "fan_select_library_design")
    load_model_into_form = getattr(ctx, "fan_load_model_into_form")
    save_model = getattr(ctx, "fan_save_model")
    delete_model = getattr(ctx, "fan_delete_model")
    save_measurement = getattr(ctx, "fan_save_measurement")
    show_store_calibration = getattr(ctx, "fan_show_store_calibration")
    do_preview = getattr(ctx, "fan_do_preview")
    on_assess = getattr(ctx, "fan_on_assess")
    score_multi_point_bem = getattr(ctx, "fan_score_multi_point_bem")
    export_stl_current = getattr(ctx, "fan_export_stl_current")
    on_optimize_fan = getattr(ctx, "fan_on_optimize")
    cancel_optimize = getattr(ctx, "fan_cancel_optimize")
    cancel_assess = getattr(ctx, "fan_cancel_assess")
    on_sweep = getattr(ctx, "fan_on_sweep")
    cancel_sweep = getattr(ctx, "fan_cancel_sweep")
    cancel_airflow = getattr(ctx, "fan_cancel_airflow")
    on_fit_envelope = getattr(ctx, "fan_on_fit_envelope")
    on_scale_to_hub = getattr(ctx, "fan_on_scale_to_hub")
    seed_from_duty = getattr(ctx, "fan_seed_from_duty")
    randomize_geometry = getattr(ctx, "fan_randomize_geometry")
    randomize_features = getattr(ctx, "fan_randomize_features")

    hub_designs = getattr(ctx, "fan_hub_designs")
    active_spec = getattr(ctx, "fan_active_spec")

    def show_fan_about(**_):
        state.fan_ux_banner = True

    _action_busy = (
        "preview_busy || assess_busy || export_busy || opt_running || e_tip_radius == null"
    )

    with v3.VRow(no_gutters=True, v_show="active_tab === 'fan'"):
        with v3.VCol(cols=12):
            with v3.VRow(no_gutters=True, classes="align-center mb-2"):
                with v3.VCol(cols=4, classes="pr-1"):
                    v3.VSelect(
                        label="Fan model (hub)",
                        v_model=("fan_model",),
                        items=("fan_models",),
                        density="compact",
                        variant="outlined",
                        hide_details=True,
                    )
                with v3.VCol(cols=8, classes="pl-1"):
                    html.Div(
                        "{{ model_info }}",
                        classes="text-caption",
                        style="white-space: pre-line",
                    )

            with v3.VRow(no_gutters=True):
                # LEFT — controls
                with v3.VCol(cols=5, classes="pr-2"):
                    with v3.VTabs(v_model=("fan_subtab",), color="primary", classes="mb-3"):
                        v3.VTab("Design", value="design")
                        v3.VTab("Results", value="results")
                        v3.VTab("Library", value="library")

                    with html.Div(v_show="fan_subtab === 'results'"):
                        v3.VSwitch(
                            v_model=("fits_only",),
                            density="compact",
                            hide_details=True,
                            inset=True,
                            color="primary",
                            classes="ml-2 mb-1",
                            label="Fits this fan only",
                        )
                        html.Div(
                            "Hide scatter points whose built tip / depth / hub "
                            "do not fit the Fan model above. Turn off to show the "
                            "full opened-run set (including oversize blades).",
                            classes="text-caption text-medium-emphasis ml-2 mb-2",
                            v_show="ui_mode === 'expert'",
                        )
                        v3.VSwitch(
                            v_model=("declutter",),
                            density="compact",
                            hide_details=True,
                            inset=True,
                            color="primary",
                            classes="ml-2 mb-1",
                            label="Declutter (hide near-duplicates)",
                        )
                        v3.VSwitch(
                            v_model=("show_stock",),
                            density="compact",
                            hide_details=True,
                            inset=True,
                            color="primary",
                            classes="ml-2 mb-1",
                            label="Show stock (published)",
                        )
                        html.Div(
                            "Gold ✕ = datasheet free-air CFM with load CFM estimated "
                            "from the published P–Q line on the current Assess hose "
                            "(not OEM CFD). Click the ✕ to load the parametric stock "
                            "blade into Design (editable approximation) + 3-D preview.",
                            classes="text-caption text-medium-emphasis ml-2 mb-2",
                            v_show="ui_mode === 'expert'",
                        )
                        html.Div(
                            "Glossary — CFM: airflow volume. Pa: pressure. "
                            "Free = open delivery; load = against the hose ΔP. "
                            "Hub = motor barrel the blades sit on. "
                            "Preview = shape only (sec); Assess = one CFD; Optimize = many. "
                            "Plot: shape = which run (see legend) · ◆ = Assessed by you · ★ = best in "
                            "its run · gold ring = best overall (nothing beats it on free, load and "
                            "efficiency at once) · gold ✕ = stock datasheet. Dropdown ✪ = best overall.",
                            classes="text-caption text-medium-emphasis ml-2 mb-2",
                            v_show="ui_mode === 'expert'",
                        )
                        with v3.VCard(classes="mb-2 pa-3"):
                            v3.VSelect(
                                label="Design",
                                v_model=("selected_trial",),
                                items=("trial_items",),
                                density="compact",
                                variant="outlined",
                                hide_details=True,
                                update_modelValue=(select, "[$event]"),
                            )
                            html.Div(
                                "{{ line }}",
                                v_for="line in info_lines",
                                classes="text-body-2 mt-2",
                            )
                        hub_all = [d for d in hub_designs() if not d.extra.get("cfd_stale")]
                        if state.fits_only:
                            hub_all = filter_fitting_designs(hub_all, active_spec())
                        _load_pa0, _ = assess_load(str(state.assess_preset or "case"))
                        _stock0 = (
                            published_scatter_point(active_spec(), _load_pa0)
                            if state.show_stock
                            else None
                        )
                        with v3.VCard(style="height:640px;", classes="mb-2 pa-1"):
                            html.Div(
                                "CFM scatter — up and right is better (free vs load). "
                                "Click a point to load Design. Color = efficiency, shape = run "
                                "(legend), gold ring = best overall. Hover shows run + date.",
                                classes="text-caption text-medium-emphasis px-2 pt-1",
                                v_show="ui_mode === 'expert'",
                            )
                            html.Div(
                                "No scored designs yet — Assess one blade or open an Optimize "
                                "run to fill this plot. Gold ✕ (stock) still shows when enabled.",
                                classes="text-caption text-medium-emphasis px-2 py-4 text-center",
                                v_show="!trial_items || trial_items.length < 2",
                            )
                            fig_widget = plotly_widgets.Figure(
                                figure=scatter_figure(
                                    [d for d in hub_all if d in study_designs],
                                    [d for d in hub_all if d in user_designs],
                                    stock_ref=_stock0,
                                    opened_run=Path(ctx.run_dir).name,
                                ),
                                click=(on_plotly_click, "[$event?.points?.[0]?.customdata]"),
                                style="width:100%;",
                            )

                    with html.Div(v_show="fan_subtab === 'library'"):
                        with v3.VCard(classes="mb-2 pa-3"):
                            html.Div("{{ library_info }}", classes="text-caption mb-2")
                            html.Div(
                                "{{ library_leftover }}",
                                classes="text-caption mb-2",
                                v_if="library_leftover",
                            )
                            html.Div(
                                "{{ preview_msg }}",
                                classes="text-caption mt-2",
                                style="white-space: pre-line",
                            )
                            v3.VBtn(
                                "Scale to this hub",
                                color="primary",
                                size="small",
                                variant="outlined",
                                block=True,
                                classes="mb-2",
                                click=(on_library_scale_to_hub,),
                                disabled=("!library_sel",),
                            )
                            with v3.VList(density="compact", lines="two"):
                                with html.Div(v_for="it in library_items", key="it.value || it.caption"):
                                    with v3.VListSubheader(v_if="it.role === 'group'"):
                                        html.Div("{{ it.title }}")
                                        html.Div("{{ it.caption }}", classes="text-caption")
                                    with v3.VListItem(
                                        v_if="it.role === 'row'",
                                        disabled=("!it.clickable",),
                                        click=(select_library_design, "[it.value]"),
                                    ):
                                        v3.VListItemTitle("{{ it.title }}")
                                        v3.VListItemSubtitle("{{ it.subtitle }}")
                        with v3.VExpansionPanels(classes="mb-2", v_show="fan_subtab === 'library'"):
                            with v3.VExpansionPanel(title="Leeway (allow exceeding nominal → over-spec)"):
                                with v3.VExpansionPanelText():
                                    _slider("Tip past frame", "lee_tip", 0, 10, 0.5, unit="mm")
                                    _slider("Extra depth Z", "lee_depth", 0, 12, 0.5, unit="mm")
                                    _slider("Over-voltage", "lee_overvolt", 0, 12, 0.5, unit="V")
                                    _slider("Extra weight", "lee_weight", 0, 40, 1, unit="g")
                            with v3.VExpansionPanel(title="Manage fan models (add / edit / delete)"):
                                with v3.VExpansionPanelText():
                                    html.Div(
                                        "Built-in models are read-only references. Load one, tweak, "
                                        "then Save under a NEW name to make your own "
                                        "(editable + deletable).",
                                        classes="text-caption mb-2",
                                    )
                                    v3.VBtn(
                                        "Load selected model into form",
                                        size="x-small",
                                        variant="tonal",
                                        block=True,
                                        click=(load_model_into_form,),
                                        classes="mb-2",
                                    )
                                    v3.VTextField(
                                        label="Model name (new name = create)",
                                        v_model=("fm_key",),
                                        density="compact",
                                        variant="outlined",
                                        hide_details=True,
                                        classes="mb-2",
                                    )
                                    with v3.VRow(no_gutters=True):
                                        with v3.VCol(cols=6, classes="pr-1"):
                                            v3.VTextField(
                                                label="Max tip dia (mm)",
                                                v_model=("fm_tip_max",),
                                                type="number",
                                                density="compact",
                                                variant="outlined",
                                                hide_details=True,
                                                classes="mb-2",
                                            )
                                        with v3.VCol(cols=6, classes="pl-1"):
                                            v3.VTextField(
                                                label="Max depth (mm)",
                                                v_model=("fm_depth_max",),
                                                type="number",
                                                density="compact",
                                                variant="outlined",
                                                hide_details=True,
                                                classes="mb-2",
                                            )
                                    with v3.VRow(no_gutters=True):
                                        with v3.VCol(cols=6, classes="pr-1"):
                                            v3.VTextField(
                                                label="Hub dia min (mm)",
                                                v_model=("fm_hub_min",),
                                                type="number",
                                                density="compact",
                                                variant="outlined",
                                                hide_details=True,
                                                classes="mb-2",
                                            )
                                        with v3.VCol(cols=6, classes="pl-1"):
                                            v3.VTextField(
                                                label="Hub dia max (mm)",
                                                v_model=("fm_hub_max",),
                                                type="number",
                                                density="compact",
                                                variant="outlined",
                                                hide_details=True,
                                                classes="mb-2",
                                            )
                                    html.Div("Motor mount — 0 cavity = generic (no motor):", classes="text-caption")
                                    with v3.VRow(no_gutters=True):
                                        with v3.VCol(cols=4, classes="pr-1"):
                                            v3.VTextField(
                                                label="Cavity dia",
                                                v_model=("fm_cav_dia",),
                                                type="number",
                                                density="compact",
                                                variant="outlined",
                                                hide_details=True,
                                                classes="mb-2",
                                            )
                                        with v3.VCol(cols=4, classes="px-1"):
                                            v3.VTextField(
                                                label="Cavity depth",
                                                v_model=("fm_cav_depth",),
                                                type="number",
                                                density="compact",
                                                variant="outlined",
                                                hide_details=True,
                                                classes="mb-2",
                                            )
                                        with v3.VCol(cols=4, classes="pl-1"):
                                            v3.VTextField(
                                                label="Min hub H",
                                                v_model=("fm_hub_h",),
                                                type="number",
                                                density="compact",
                                                variant="outlined",
                                                hide_details=True,
                                                classes="mb-2",
                                            )
                                    with v3.VRow(no_gutters=True):
                                        with v3.VCol(cols=6, classes="pr-1"):
                                            v3.VBtn("💾 Save model", size="small", color="primary", block=True, click=(save_model,))
                                        with v3.VCol(cols=6, classes="pl-1"):
                                            v3.VBtn(
                                                "🗑 Delete",
                                                size="small",
                                                color="error",
                                                variant="tonal",
                                                block=True,
                                                click=(delete_model,),
                                                disabled=("model_is_builtin",),
                                            )
                                    html.Div("{{ fm_msg }}", classes="text-caption mt-2", style="white-space: pre-line")

                        with v3.VExpansionPanels(classes="mb-2", v_show="fan_subtab === 'library'"):
                            with v3.VExpansionPanel(title="Record measurement (physical)"):
                                with v3.VExpansionPanelText():
                                    html.Div(
                                        "Printed + tested a design? Enter what you measured — it's "
                                        "saved to validation/measurements/ tied to this design's sim "
                                        "numbers, and compared. (Select the design first.)",
                                        classes="text-caption mb-2",
                                    )
                                    with v3.VRow(no_gutters=True):
                                        with v3.VCol(cols=6, classes="pr-1"):
                                            v3.VTextField(
                                                label="Measured CFM",
                                                v_model=("meas_cfm",),
                                                type="number",
                                                density="compact",
                                                variant="outlined",
                                                hide_details=True,
                                                classes="mb-2",
                                            )
                                        with v3.VCol(cols=6, classes="pl-1"):
                                            v3.VTextField(
                                                label="Static Pa",
                                                v_model=("meas_static",),
                                                type="number",
                                                density="compact",
                                                variant="outlined",
                                                hide_details=True,
                                                classes="mb-2",
                                            )
                                    with v3.VRow(no_gutters=True):
                                        with v3.VCol(cols=6, classes="pr-1"):
                                            v3.VTextField(
                                                label="Noise dB(A)",
                                                v_model=("meas_noise",),
                                                type="number",
                                                density="compact",
                                                variant="outlined",
                                                hide_details=True,
                                                classes="mb-2",
                                            )
                                        with v3.VCol(cols=6, classes="pl-1"):
                                            v3.VTextField(
                                                label="RPM",
                                                v_model=("meas_rpm",),
                                                type="number",
                                                density="compact",
                                                variant="outlined",
                                                hide_details=True,
                                                classes="mb-2",
                                            )
                                    with v3.VRow(no_gutters=True):
                                        with v3.VCol(cols=5, classes="pr-1"):
                                            v3.VTextField(
                                                label="Material (printed)",
                                                v_model=("meas_material",),
                                                density="compact",
                                                variant="outlined",
                                                hide_details=True,
                                                classes="mb-2",
                                            )
                                        with v3.VCol(cols=4, classes="px-1"):
                                            v3.VSelect(
                                                label="Print type",
                                                v_model=("meas_print_type",),
                                                items=("meas_print_types",),
                                                density="compact",
                                                variant="outlined",
                                                hide_details=True,
                                                classes="mb-2",
                                            )
                                        with v3.VCol(cols=3, classes="pl-1"):
                                            v3.VTextField(
                                                label="Weight g",
                                                v_model=("meas_weight",),
                                                type="number",
                                                density="compact",
                                                variant="outlined",
                                                hide_details=True,
                                                classes="mb-2",
                                            )
                                    v3.VTextField(
                                        label="Instrument",
                                        v_model=("meas_instrument",),
                                        density="compact",
                                        variant="outlined",
                                        hide_details=True,
                                        classes="mb-2",
                                    )
                                    v3.VTextField(
                                        label="Notes",
                                        v_model=("meas_notes",),
                                        density="compact",
                                        variant="outlined",
                                        hide_details=True,
                                        classes="mb-2",
                                    )
                                    with v3.VRow(no_gutters=True, classes="mb-1"):
                                        with v3.VCol(cols=7, classes="pr-1"):
                                            v3.VBtn(
                                                "Save measurement",
                                                color="primary",
                                                size="small",
                                                block=True,
                                                click=(save_measurement,),
                                            )
                                        with v3.VCol(cols=5, classes="pl-1"):
                                            v3.VBtn(
                                                "Show store calibration",
                                                color="secondary",
                                                variant="outlined",
                                                size="small",
                                                block=True,
                                                click=(show_store_calibration,),
                                            )
                                    html.Div("{{ meas_msg }}", classes="text-caption mt-2", style="white-space: pre-line")

                    with html.Div(v_show="fan_subtab === 'design'"):
                        v3.VAlert(
                            "Design 3D-printable replacement blades for a PC cooling fan "
                            "(start: Noctua A12x25). Preview updates the shape in seconds; "
                            "Assess runs one CFD solve (~15–30 min); Optimize searches many "
                            "designs (hours). Export writes a print-ready STL. "
                            "Fan is CFD-checked — Mixed / Volute / Prop / CROR tabs are "
                            "faster estimates or proxies. Docs: README, docs/design-rules.md, "
                            "docs/a12x25-reference.md.",
                            type="info",
                            density="compact",
                            variant="tonal",
                            classes="mb-2",
                            closable=True,
                            v_model=("fan_ux_banner",),
                        )
                        with v3.VRow(no_gutters=True, classes="align-center mb-2"):
                            with v3.VCol(cols=10):
                                html.Div(
                                    "Start here: 1) Pick a design ↓  2) Preview (sec)  "
                                    "3) Assess (~15–30 min)  4) Optimize (hours, optional)  "
                                    "5) Export STL when happy.",
                                    classes="text-caption text-medium-emphasis",
                                )
                            with v3.VCol(cols=2, classes="text-right"):
                                v3.VBtn(
                                    "About",
                                    size="x-small",
                                    variant="tonal",
                                    click=(show_fan_about,),
                                )
                        with v3.VSelect(
                            # After Randomize / slider edits the geometry is no longer the selected
                            # design; say so on the dropdown itself (QA UI-20, §23.47). The label alone
                            # was too small: the shown VALUE must say it too (QA re-test).
                            label=("edited_stale ? '✎ Edited copy (not saved) — based on:' "
                                   ": 'Design (unlocks Preview / Assess / Export)'",),
                            base_color=("edited_stale ? 'warning' : undefined",),
                            color=("edited_stale ? 'warning' : 'primary'",),
                            v_model=("selected_trial",),
                            items=("trial_items",),
                            density="compact",
                            variant="outlined",
                            hide_details=True,
                            classes="mb-2",
                            update_modelValue=(select, "[$event]"),
                        ):
                            with v3.Template(v_slot_selection="{ item }"):
                                html.Span(
                                    "{{ edited_stale ? '✎ Edited copy of ' + item.title : item.title }}",
                                    classes=("edited_stale ? 'text-warning font-weight-medium' : ''",),
                                )
                        html.Div(
                            "Buttons stay disabled until a design is selected "
                            "(tip radius loaded). Use the reference entry or Results scatter.",
                            classes="text-caption text-medium-emphasis mb-2",
                            v_show="e_tip_radius == null",
                        )

                    with v3.VCard(classes="mb-2 pa-3", v_show="fan_subtab === 'design'"):
                        html.Div("Actions", classes="text-subtitle-2 mb-1")
                        html.Div(
                            "{{ assess_preset }} hose · {{ assess_material }} — "
                            "change under Assess & print below.",
                            classes="text-caption text-medium-emphasis mb-1",
                        )
                        html.Div(
                            "{{ intake_note }}",
                            v_show="intake_overbuild && intake_note && intake_note_warn",
                            classes="text-caption text-warning mb-1",
                        )
                        html.Div(
                            "{{ intake_note }}",
                            v_show="intake_overbuild && intake_note && !intake_note_warn",
                            classes="text-caption text-medium-emphasis mb-1",
                        )
                        v3.VAlert(
                            "{{ stale_msg }}",
                            v_if="edited_stale",
                            type="warning",
                            density="compact",
                            variant="tonal",
                            classes="mb-2",
                            style="white-space: pre-line",
                        )
                        render_action_row(
                            v3,
                            {
                                "preview": {
                                    "label": "Preview (sec)",
                                    "color": "primary",
                                    "size": "small",
                                    "click": (do_preview,),
                                    "loading": ("preview_busy",),
                                    "disabled": (_action_busy,),
                                },
                                "score": {
                                    "label": "Assess (~15–30 min)",
                                    "color": "success",
                                    "size": "small",
                                    "click": (on_assess,),
                                    "loading": ("assess_busy",),
                                    "disabled": (_action_busy,),
                                },
                                "optimize": {
                                    "label": "Optimize (hours)",
                                    "color": "success",
                                    "size": "small",
                                    "click": (on_optimize_fan,),
                                    "loading": ("opt_running",),
                                    "disabled": (
                                        "preview_busy || assess_busy || export_busy || opt_running",
                                    ),
                                },
                                "stop": [
                                    {
                                        "label": "⏹ Cancel opt",
                                        "size": "small",
                                        "color": "error",
                                        "variant": "tonal",
                                        "click": (cancel_optimize,),
                                        "disabled": ("!opt_running",),
                                    },
                                    {
                                        "label": "⏹ Cancel Assess",
                                        "size": "small",
                                        "color": "error",
                                        "variant": "tonal",
                                        "click": (cancel_assess,),
                                        "disabled": ("!assess_busy || opt_running",),
                                    },
                                ],
                                "randomize": {
                                    "label": "Randomize geometry",
                                    "size": "small",
                                    "variant": "tonal",
                                    "color": "secondary",
                                    "click": (randomize_geometry,),
                                },
                            },
                        )
                        v3.VBtn(
                            "Reset",
                            size="small",
                            variant="tonal",
                            click=(select, "[selected_trial]"),
                            classes="mt-1 mb-1",
                        )
                        html.Div("{{ preview_msg }}", classes="text-caption", style="white-space: pre-line")
                        v3.VAlert(
                            "{{ assess_msg }}",
                            v_if="assess_msg",
                            type="info",
                            density="compact",
                            variant="tonal",
                            classes="mt-1",
                            style="white-space: pre-line",
                        )
                        html.Div("{{ opt_msg }}", classes="text-caption mt-1", style="white-space: pre-line")
                        busy_bar("preview_busy", "assess_busy", "export_busy", "opt_running", color="success",
                                 value="preview_pct")

                    with v3.VExpansionPanels(
                        v_model=("fan_design_panels",),
                        multiple=True,
                        variant="accordion",
                        classes="mb-2",
                        v_show="fan_subtab === 'design'",
                    ):
                        with v3.VExpansionPanel(title="Geometry — modify design"):
                            with v3.VExpansionPanelText():
                                html.Div(
                                    "Hover any slider for a min/max picture + what it does.",
                                    classes="text-caption mb-1",
                                )
                                with v3.VExpansionPanels(variant="accordion", multiple=True):
                                    with v3.VExpansionPanel(title="Planform — blades & chord"):
                                        with v3.VExpansionPanelText():
                                            _slider("Blades", "e_n_blades", 5, 11, 1)
                                            _slider("Chord root", "e_chord_root", 14, 50, 0.5, unit="mm")
                                            _slider("Chord mid", "e_chord_mid", 14, 60, 0.5, unit="mm")
                                            _slider("Chord tip", "e_chord_tip", 14, 70, 0.5, unit="mm")
                                            html.Div(
                                                "Chord = LE→TE blade width (planform). Not wall thickness.",
                                                classes="text-caption mb-2",
                                            )
                                    with v3.VExpansionPanel(title="Pitch / twist — stagger"):
                                        with v3.VExpansionPanelText():
                                            _slider("Stagger root", "e_stagger_root", 15, 55, 1, unit="deg")
                                            _slider("Stagger mid", "e_stagger_mid", 15, 55, 1, unit="deg")
                                            _slider("Stagger tip", "e_stagger_tip", 15, 55, 1, unit="deg")
                                    with v3.VExpansionPanel(title="Airfoil — camber & thickness"):
                                        with v3.VExpansionPanelText():
                                            _help_select(
                                                "e_section_family",
                                                "Section family",
                                                items="section_family_items",
                                                help_map=CONTROL_DESC,
                                            )
                                            html.Div(
                                                "NACA = cambered airfoil (knife LE/TE). Rounded plate = "
                                                "constant wall, round LE, tunable TE + camber for the slight "
                                                "face curve — match printed PC-fan blades.",
                                                classes="text-caption mb-2",
                                            )
                                            _slider("Camber root", "e_camber_root", 0.0, 0.15, 0.005, unit="c/c")
                                            _slider("Camber mid", "e_camber_mid", 0.0, 0.15, 0.005, unit="c/c")
                                            _slider("Camber tip", "e_camber_tip", 0.0, 0.15, 0.005, unit="c/c")
                                            html.Div(
                                                "Camber = the scoop in the blade face (LE→TE curve). "
                                                "Raise tip/mid until the tip-on view matches the white reference. "
                                                "Not wrap/sickle — those move the planform, not the face scoop. Preview after changes.",
                                                classes="text-caption mb-2",
                                            )
                                            _slider("Camber position", "e_camber_pos", 0.2, 0.6, 0.05, unit="x/c")
                                            _help_select(
                                                "e_thick_mode",
                                                "Thickness span",
                                                items="thick_mode_items",
                                                help_map=CONTROL_DESC,
                                            )
                                            html.Div(
                                                "{{ thick_wall_readout }}",
                                                classes="text-caption mb-2",
                                            )
                                            _slider(
                                                "Wall thickness", "e_thick_mm", 0.8, 4.0, 0.1,
                                                unit="mm",
                                                disabled=("e_thick_mode !== 'uniform'",),
                                            )
                                            _slider(
                                                "Wall t/c root", "e_thick_root", 0.03, 0.15, 0.01,
                                                unit="t/c",
                                                disabled=("e_thick_mode === 'uniform'",),
                                            )
                                            _slider(
                                                "Wall t/c mid", "e_thick_mid", 0.03, 0.15, 0.01,
                                                unit="t/c",
                                                disabled=("e_thick_mode === 'uniform'",),
                                            )
                                            _slider(
                                                "Wall t/c tip", "e_thick_tip", 0.03, 0.15, 0.01,
                                                unit="t/c",
                                                disabled=("e_thick_mode === 'uniform'",),
                                            )
                                            html.Div(
                                                "Wall = the thin dimension through the blade (not LE→TE width). "
                                                "Uniform = same mm root→tip. Rounded plate keeps wall through "
                                                "the section (LE/TE from the roundness sliders); NACA knives the TE.",
                                                classes="text-caption mb-2",
                                            )
                                            _slider(
                                                "LE thick / roundness", "e_le_thick", 0.0, 2.0, 0.05,
                                                unit="×",
                                            )
                                            _slider(
                                                "TE thick / roundness", "e_te_thick", 0.0, 2.0, 0.05,
                                                unit="×",
                                            )
                                            html.Div(
                                                "NACA: LE/TE scales reshape nose/tail (1 = stock). TE>1 fattens "
                                                "the aft section. Plate: both sliders are edge roundness "
                                                "(1 = full bullnose, ~0.2 = sharp). "
                                                "Camber bows the plate face (slight tip→hub curve). Preview after changes.",
                                                classes="text-caption text-medium-emphasis mb-2",
                                            )
                                    with v3.VExpansionPanel(title="3-D shape — wrap, sweep, rake"):
                                        with v3.VExpansionPanelText():
                                            _help_switch(
                                                "e_smooth_span",
                                                "Smooth span curves",
                                                help_map=CONTROL_DESC,
                                                classes="mb-2",
                                            )
                                            _slider("Wrap mid", "e_lean_mid", 0, 30, 1, unit="deg")
                                            _slider("Wrap tip", "e_lean_tip", 0, 45, 1, unit="deg")
                                            _slider("Sweep mid", "e_sweep_mid", -10, 20, 0.5, unit="mm")
                                            _slider("Sweep tip", "e_sweep_tip", -8, 25, 0.5, unit="mm")
                                            _slider("LE curve mid", "e_le_mid", -12, 12, 0.5, unit="mm")
                                            _slider("LE curve tip", "e_le_tip", -12, 12, 0.5, unit="mm")
                                            _slider("Sickle mid", "e_le_skew_mid", 0, 12, 0.5, unit="mm")
                                            _slider("Sickle tip", "e_le_skew_tip", 0, 15, 0.5, unit="mm")
                                            _slider("Skew mid", "e_skew_mid", -20, 20, 0.5, unit="mm")
                                            _slider("Skew tip", "e_skew_tip", -25, 25, 0.5, unit="mm")
                                            html.Div("{{ depth_fit_info }}", classes="text-caption")
                                    with v3.VExpansionPanel(title="Tip — round & winglet"):
                                        with v3.VExpansionPanelText():
                                            _help_switch(
                                                "e_cylindrical_tip",
                                                "Cylindrical tip (match cover)",
                                                help_map=CONTROL_DESC,
                                            )
                                            _slider("Tip round", "e_tip_round", 0.0, 1.0, 0.05, unit="0–1")
                                            _slider("Tip round start", "e_tip_start", 0.5, 0.92, 0.02, unit="span")
                                            _help_switch(
                                                "e_tip_notched",
                                                "Tip TE notches (3 boxy bites)",
                                                help_map=CONTROL_DESC,
                                            )
                                            _slider(
                                                "Tip notch depth",
                                                "e_tip_notch_depth",
                                                0.5,
                                                3.0,
                                                0.1,
                                                unit="mm",
                                                disabled=("!e_tip_notched",),
                                            )
                                            html.Div(
                                                "Three boxy / skewed-rectangle bites on the outer trailing edge "
                                                "(stock A12x25 style). Not spanwise owl serrations.",
                                                classes="text-caption mb-2",
                                            )
                                            _slider("Winglet start", "e_winglet_span", 0.6, 0.95, 0.05, unit="span")
                                            _slider("Winglet sweep", "e_winglet_sweep", 0, 15, 0.5, unit="mm")
                                            _slider("Winglet lean", "e_winglet_lean", 0, 30, 1, unit="deg")
                                            _slider("Shroud thickness", "e_shroud_thick", 0, 3, 0.8, unit="mm")
                                            _slider(
                                                "Shroud height",
                                                "e_shroud_height",
                                                0,
                                                1,
                                                0.1,
                                                unit="span",
                                                disabled=("e_shroud_thick == 0",),
                                            )
                                            html.Div(
                                                "0 thickness = off. First thickness step is 0.8 mm (two walls); 1.6 mm is four walls. Height 1.0 covers the full tip; below 1.0 the hoop starts at the trailing edge and BEM still treats it as an open tip. A full ring (height 1.0) disables the winglet automatically — once the tip is fully covered a winglet only adds blockage.",
                                                classes="text-caption mb-1",
                                            )
                                    with v3.VExpansionPanel(title="Hub"):
                                        with v3.VExpansionPanelText():
                                            _slider("Hub radius", "e_hub_radius", 15, 35, 0.5, unit="mm")
                                            html.Div("{{ hub_fit_info }}", classes="text-caption mb-1")
                                            _slider("Tip radius / length", "e_tip_radius", 45, 59, 0.5, unit="mm")
                                            html.Div("{{ tip_fit_info }}", classes="text-caption mb-1")
                                            _slider(
                                                "Hub height (0=auto)", "e_hub_height", 0,
                                                "e_hub_height_max", 0.5, unit="mm",
                                            )
                                            _slider(
                                                "Blade on hub", "e_blade_hub_z", -8,
                                                "e_blade_hub_z_max", 0.5, unit="mm",
                                            )
                                            html.Div(
                                                "Blade on hub: + raises blades toward the intake (more hub below). "
                                                "Needs Hub height taller than the root span.",
                                                classes="text-caption mb-2",
                                            )
                                            v3.VSelect(
                                                label="Hub profile",
                                                v_model=("e_hub_profile",),
                                                items=("hub_profiles",),
                                                density="compact",
                                                variant="outlined",
                                                hide_details=True,
                                                classes="mb-3",
                                            )
                                            _slider(
                                                "Hub nose (cone/dome)", "e_hub_nose", 0,
                                                "e_hub_nose_max", 0.5, unit="mm",
                                            )
                                    with v3.VExpansionPanel(title="Spacing — tonal noise"):
                                        with v3.VExpansionPanelText():
                                            _slider("Uneven spacing", "e_spacing", 0.0, 0.6, 0.05, unit="0–1")
                                    with v3.VExpansionPanel(title="Features (bio-inspired)"):
                                        with v3.VExpansionPanelText():
                                            v3.VBtn(
                                                "🎲 Randomize features",
                                                size="x-small",
                                                variant="tonal",
                                                color="secondary",
                                                block=True,
                                                click=(randomize_features,),
                                                classes="mb-3",
                                            )
                                            _slider("Tubercle amp", "e_tub_amp", 0.0, 0.10, 0.01, unit="c")
                                            _slider("Tubercle waves", "e_tub_waves", 0, 8, 1)
                                            _slider("Serration amp", "e_ser_amp", 0.0, 0.06, 0.005, unit="c")
                                            _slider("Serration teeth", "e_ser_waves", 0, 12, 1)
                                            _slider("Dimple depth", "e_dim_amp", 0.0, 0.35, 0.05, unit="t")
                                            _slider("Dimple rows", "e_dim_rows", 0, 6, 1)
                                            _slider("Dimple cols", "e_dim_cols", 0, 6, 1)

                        with v3.VExpansionPanel(title="Assess & print"):
                            with v3.VExpansionPanelText():
                                html.Div(
                                    "Assess checks printability / stress (blade vibration is a warning), then runs "
                                    "CFD (~15–30 min) and reports free/load CFM. Rejected designs show "
                                    "what to change (usually fewer blades or thicker mid-blade).",
                                    classes="text-caption text-medium-emphasis mb-2",
                                )
                                v3.VSelect(
                                    label="Application (hose resistance)",
                                    v_model=("assess_preset",),
                                    items=("assess_preset_items",),
                                    density="compact",
                                    variant="outlined",
                                    hide_details=True,
                                    classes="mb-2",
                                )
                                html.Div(
                                    "Case ≈ open airflow (low Pa). Heatsink ≈ fins. "
                                    "Radiator ≈ high resistance. Sets the load CFM hose.",
                                    classes="text-caption text-medium-emphasis mb-2",
                                )
                                v3.VSelect(
                                    label="Print material (stress gate + vibration warning)",
                                    v_model=("assess_material",),
                                    items=("assess_material_items",),
                                    density="compact",
                                    variant="outlined",
                                    hide_details=True,
                                    classes="mb-2",
                                )
                                html.Div(
                                    "Used by Assess and Optimize. Pick PLA+ here before Optimize "
                                    "if that is what you print.",
                                    classes="text-caption text-medium-emphasis mb-2",
                                )
                                v3.VBtn(
                                    "Score multi-point BEM (ranking only)",
                                    size="small",
                                    variant="tonal",
                                    color="secondary",
                                    classes="mb-1",
                                    click=(score_multi_point_bem,),
                                    block=True,
                                )
                                html.Div(
                                    "{{ multi_point_msg }}",
                                    classes="text-caption mb-2",
                                    style="white-space: pre-line",
                                )
                                _opt_section(
                                    "Honesty / fidelity",
                                    "Also applied when you press Optimize (same hose + roughness).",
                                )
                                _help_switch(
                                    "assess_refine_op",
                                    "Third CFD at operating point (~50% longer)",
                                    classes="mb-2",
                                )
                                _help_switch(
                                    "assess_wall_ks",
                                    "FDM wall roughness (ks≈0.1 mm)",
                                    classes="mb-2",
                                )
                                with v3.VRow(no_gutters=True, classes="mt-2 align-center"):
                                    with v3.VCol(cols=6, classes="pr-1"):
                                        v3.VSelect(
                                            label="Sweep",
                                            v_model=("sweep_param",),
                                            items=("sweep_items",),
                                            density="compact",
                                            variant="outlined",
                                            hide_details=True,
                                        )
                                    with v3.VCol(cols=3, classes="px-1"):
                                        v3.VTextField(
                                            label="steps",
                                            v_model=("sweep_steps",),
                                            type="number",
                                            density="compact",
                                            variant="outlined",
                                            hide_details=True,
                                        )
                                    with v3.VCol(cols=3, classes="pl-1"):
                                        v3.VBtn(
                                            "Run",
                                            size="small",
                                            color="success",
                                            variant="tonal",
                                            click=(on_sweep,),
                                            disabled=("assess_busy",),
                                        )
                                with v3.VRow(
                                    v_if="sweep_active", no_gutters=True, classes="mt-2 align-center"
                                ):
                                    with v3.VCol(cols=9, classes="pr-2"):
                                        v3.VProgressLinear(
                                            model_value=("sweep_progress",),
                                            height=8,
                                            color="success",
                                            rounded=True,
                                        )
                                    with v3.VCol(cols=3):
                                        v3.VBtn(
                                            "⏹ Cancel",
                                            size="x-small",
                                            color="error",
                                            variant="tonal",
                                            block=True,
                                            click=(cancel_sweep,),
                                            disabled=("sweep_cancel",),
                                        )

                        with v3.VExpansionPanel(title="Optimize (hours · many CFD trials)"):
                            with v3.VExpansionPanelText():
                                html.Div(
                                    "Multi-objective CFD search. Reuses Application hose + Honesty "
                                    "above. Defaults: 8 trials. ◆ diamonds merge onto the Results "
                                    "plot. Hover switches for when-to-use / cost / risk.",
                                    classes="text-caption mb-2",
                                    style="white-space: pre-line",
                                )
                                with v3.VTooltip(location="end", open_delay=150, max_width=420):
                                    with v3.Template(v_slot_activator="{ props }"):
                                        v3.VTextField(
                                            v_bind="props",
                                            label="Trials",
                                            v_model=("opt_trials",),
                                            type="number",
                                            density="compact",
                                            variant="outlined",
                                            hide_details=True,
                                            classes="mb-2",
                                        )
                                    html.Div(OPT_SEARCH_HELP["opt_trials"], classes="text-caption")
                                _help_switch("opt_resume", "Continue the last Optimize run",
                                             classes="mb-0")
                                html.Div("{{ opt_resume_caption }}", classes="text-caption mb-2")
                                _opt_section(
                                    "Geometry stamps",
                                    "Optional part shapes stamped onto every trial "
                                    "(not free-form search knobs).",
                                )
                                _help_switch("opt_shroud", "Tip ring / shroud")
                                _help_switch("opt_stator", "Stator vanes")
                                _help_switch("opt_stator_stack", "Stator + frame stack")
                                _help_switch("opt_sickle", "Sickle leading edge")
                                _help_switch("opt_stepped", "Stepped inlet casing")
                                _help_switch("opt_notched", "Notched tip trailing edge")
                                _opt_section(
                                    "Speed-ups",
                                    "Skip hopeless CFD early. Faster campaigns; can miss "
                                    "borderline winners if floors are aggressive.",
                                )
                                _help_switch(
                                    "opt_bem",
                                    "BEM ranking screen — skip CFD below ~32 CFM",
                                )
                                _help_switch(
                                    "opt_gp",
                                    "Catalog GP skip below ~40 CFM free",
                                )
                                _help_switch(
                                    "opt_gp_boost",
                                    "Boost + GP mean",
                                )
                                _help_switch(
                                    "opt_gp_nn",
                                    "NN + GP mean",
                                )
                                _help_switch(
                                    "opt_surrogate_guided",
                                    "Surrogate-guided (DoE→NSGA on GP→verify top-k)",
                                )
                                _opt_section(
                                    "Operating point",
                                    "Fixed nameplate RPM unless you open the PWM band.",
                                )
                                _help_switch("opt_search_rpm", "Search RPM in PWM band")
                                with v3.VRow(
                                    v_show="opt_search_rpm", no_gutters=True, classes="mt-1 align-center"
                                ):
                                    with v3.VCol(cols=6, classes="pr-1"):
                                        with v3.VTooltip(location="end", open_delay=150, max_width=420):
                                            with v3.Template(v_slot_activator="{ props }"):
                                                v3.VTextField(
                                                    v_bind="props",
                                                    label="PWM RPM min",
                                                    v_model=("opt_rpm_min",),
                                                    type="number",
                                                    density="compact",
                                                    variant="outlined",
                                                    hide_details=True,
                                                )
                                            html.Div(OPT_SEARCH_HELP["opt_rpm_min"], classes="text-caption")
                                    with v3.VCol(cols=6, classes="pl-1"):
                                        with v3.VTooltip(location="end", open_delay=150, max_width=420):
                                            with v3.Template(v_slot_activator="{ props }"):
                                                v3.VTextField(
                                                    v_bind="props",
                                                    label="PWM RPM max",
                                                    v_model=("opt_rpm_max",),
                                                    type="number",
                                                    density="compact",
                                                    variant="outlined",
                                                    hide_details=True,
                                                )
                                            html.Div(OPT_SEARCH_HELP["opt_rpm_max"], classes="text-caption")
                                html.Div(
                                    "{{ opt_pwm_caption }}",
                                    v_show="opt_search_rpm",
                                    classes="text-caption mt-1 mb-1",
                                )
                                html.Div(
                                    "Noise ranking: use scripts/evaluate_noise.py (mic cal needed for absolute dB).",
                                    classes="text-caption mt-2 text-medium-emphasis",
                                    style="white-space: pre-line",
                                )

                        with v3.VExpansionPanel(title="Fit & seed"):
                            with v3.VExpansionPanelText():
                                v3.VSwitch(
                                    v_model=("intake_overbuild",),
                                    density="compact",
                                    hide_details=True,
                                    color="primary",
                                    inset=True,
                                    label="Allow intake overbuild (+Z)",
                                    classes="mb-1",
                                )
                                v3.VSlider(
                                    v_model=("intake_overbuild_mm",),
                                    min=0,
                                    max=20,
                                    step=1,
                                    label="Extra intake (mm)",
                                    thumb_label=True,
                                    density="compact",
                                    hide_details=True,
                                    classes="mb-1",
                                    disabled=("!intake_overbuild",),
                                )
                                html.Div(
                                    "Stock frame depth stays nominal; on = blades/hub may "
                                    "extend past the inlet (+Z) by Extra. Flagged over-spec "
                                    "vs datasheet depth. CFD duct still stock — won't drop "
                                    "into a stock frame.",
                                    classes="text-caption text-medium-emphasis mb-2",
                                )
                                html.Div(
                                    "Fit to the selected fan model before Preview/Assess when tip "
                                    "or depth is out of spec. Only changes Design sliders — Preview "
                                    "afterward. Seed from duty fills stagger/camber magnitudes from "
                                    "a CFM/Pa/RPM target (signs unchanged).",
                                    classes="text-caption mb-2",
                                )
                                with v3.VRow(no_gutters=True):
                                    with v3.VCol(cols=6, classes="pr-1"):
                                        v3.VBtn(
                                            "Fit envelope",
                                            size="small",
                                            variant="tonal",
                                            color="primary",
                                            block=True,
                                            click=(on_fit_envelope,),
                                            disabled=("e_tip_radius == null",),
                                        )
                                    with v3.VCol(cols=6, classes="pl-1"):
                                        v3.VBtn(
                                            "Scale to this hub",
                                            size="small",
                                            variant="tonal",
                                            color="primary",
                                            block=True,
                                            click=(on_scale_to_hub,),
                                            disabled=("e_tip_radius == null",),
                                        )
                                html.Div("{{ tip_fit_info }}", classes="text-caption mt-2")
                                html.Div("{{ hub_fit_info }}", classes="text-caption")
                                html.Div("{{ depth_fit_info }}", classes="text-caption mb-3")
                                html.Div("Seed from duty", classes="text-subtitle-2 mb-1")
                                with v3.VRow(no_gutters=True, classes="mb-1"):
                                    with v3.VCol(cols=4, classes="pr-1"):
                                        v3.VTextField(
                                            label="Target CFM",
                                            v_model=("seed_duty_cfm",),
                                            type="number",
                                            density="compact",
                                            variant="outlined",
                                            hide_details=True,
                                        )
                                    with v3.VCol(cols=4, classes="px-1"):
                                        v3.VTextField(
                                            label="ΔP (Pa)",
                                            v_model=("seed_duty_pa",),
                                            type="number",
                                            density="compact",
                                            variant="outlined",
                                            hide_details=True,
                                        )
                                    with v3.VCol(cols=4, classes="pl-1"):
                                        v3.VTextField(
                                            label="RPM",
                                            v_model=("seed_duty_rpm",),
                                            type="number",
                                            density="compact",
                                            variant="outlined",
                                            hide_details=True,
                                        )
                                v3.VSelect(
                                    label="Vortex",
                                    v_model=("seed_duty_vortex",),
                                    items=("seed_duty_vortex_items",),
                                    density="compact",
                                    variant="outlined",
                                    hide_details=True,
                                    classes="mb-2",
                                )
                                v3.VBtn(
                                    "Apply stagger/camber seed",
                                    size="small",
                                    variant="tonal",
                                    color="secondary",
                                    block=True,
                                    click=(seed_from_duty,),
                                    disabled=("e_tip_radius == null",),
                                    classes="mb-1",
                                )
                                html.Div(
                                    "{{ seed_duty_msg }}",
                                    classes="text-caption",
                                    style="white-space: pre-line",
                                )

                # RIGHT — viz
                with v3.VCol(cols=7):
                    with v3.VCard(classes="pa-2 mb-2"):
                        with v3.VRow(no_gutters=True, classes="align-center"):
                            with v3.VCol(cols=7):
                                v3.VSwitch(
                                    v_model=("highlight_spec",),
                                    density="compact",
                                    hide_details=True,
                                    color="error",
                                    inset=True,
                                    label="Highlight out-of-spec (red)",
                                )
                            with v3.VCol(cols=5):
                                v3.VSwitch(
                                    v_model=("show_envelope",),
                                    density="compact",
                                    hide_details=True,
                                    color="success",
                                    inset=True,
                                    label="Case envelope",
                                )
                        with v3.VRow(no_gutters=True, classes="align-center"):
                            with v3.VCol(cols=12):
                                v3.VSwitch(
                                    v_model=("show_dir_cues",),
                                    density="compact",
                                    hide_details=True,
                                    color="primary",
                                    inset=True,
                                    label="Rotation (CCW) + airflow (−Z) cues",
                                )
                        with v3.VRow(no_gutters=True, classes="align-center mt-1"):
                            with v3.VCol(cols=5, classes="pr-1"):
                                with v3.VBtnToggle(
                                    v_model=("glyph_mode",),
                                    density="compact",
                                    color="primary",
                                    mandatory=True,
                                    classes="mb-1",
                                ):
                                    v3.VBtn("Arrows on", value="on", size="small")
                                    v3.VBtn("Arrows off", value="off", size="small")
                            with v3.VCol(cols=4):
                                v3.VSelect(
                                    v_model=("glyph_density",),
                                    items=("glyph_density_items",),
                                    label="Arrow density",
                                    density="compact",
                                    hide_details=True,
                                    variant="underlined",
                                    disabled=("glyph_mode === 'off'",),
                                )
                            with v3.VCol(cols=3):
                                v3.VTextField(
                                    v_model=("glyph_scale",),
                                    label="Scale",
                                    type="number",
                                    density="compact",
                                    hide_details=True,
                                    variant="underlined",
                                    step="0.5",
                                    min="0.2",
                                    max="20",
                                    disabled=("glyph_mode === 'off'",),
                                )
                        # Collapsed: the legend paragraph pushed the 3-D view below the fold on
                        # short screens (1024x594, roadmap §23.22).
                        with v3.VExpansionPanels(variant="accordion", classes="mt-1"):
                            with v3.VExpansionPanel(title="Legend"):
                                with v3.VExpansionPanelText():
                                    html.Div(
                                        "Legend — orange impeller = editable design; white = stock "
                                        "reference overlay; red = past tip/depth spec; green = case "
                                        "envelope; blue arrows = CFD velocity (|U|, subsampled). "
                                        "Arrows need a scored case on disk (Assess / Optimize). "
                                        "Without CFD, the 3-D view is schematic geometry only. "
                                        "Use Arrows on/off on Design / Results / Library. "
                                        "Midplane PNGs live under Results when fields remain on disk "
                                        "(FRONT = inlet on the left).",
                                        classes="text-caption text-medium-emphasis",
                                    )
                        html.Div("{{ glyph_caption }}", classes="text-caption text-medium-emphasis mt-1")
                    with v3.VCard(style=VTK_VIEW_STYLE, classes="mb-2"):
                        view = plotter_ui(plotter)
                    # Print / export sits right under the viewer, with the switches that decide what
                    # Export writes (QA UI-24: they were ~2 screens below the Export button).
                    with v3.VCard(classes="pa-2 mb-2", v_show="fan_subtab === 'design'"):
                        with v3.VRow(no_gutters=True, classes="align-center"):
                            with v3.VCol(cols=8):
                                html.Div("Print / export", classes="text-subtitle-2")
                                html.Div(
                                    "Export STL writes a print-ready file: motor cup + grip pads carved "
                                    "into the hub, plus a mount/frame checklist.",
                                    classes="text-caption text-medium-emphasis",
                                )
                            with v3.VCol(cols=4, classes="text-right"):
                                v3.VBtn(
                                    "Export STL",
                                    size="small",
                                    color="primary",
                                    click=(export_stl_current,),
                                    loading=("export_busy",),
                                    disabled=(_action_busy,),
                                )
                        with v3.VRow(no_gutters=True, classes="mt-1"):
                            with v3.VCol(cols=6, classes="pr-1"):
                                v3.VSwitch(
                                    v_model=("export_fit_hub",),
                                    density="compact", hide_details=True, color="primary", inset=True,
                                    label="Fit hub to the motor",
                                )
                                v3.VSwitch(
                                    v_model=("export_fit_frame",),
                                    density="compact", hide_details=True, color="primary", inset=True,
                                    label="Fit tip + depth to the frame",
                                )
                            with v3.VCol(cols=6, classes="pl-1"):
                                v3.VSwitch(
                                    v_model=("export_also_mirror",),
                                    density="compact", hide_details=True, color="primary", inset=True,
                                    label="Also export the mirror-image fan (CW + CCW)",
                                )
                                v3.VSwitch(
                                    v_model=("preview_motor_cup",),
                                    density="compact", hide_details=True, color="primary", inset=True,
                                    label="Show the motor cup in Preview (slower)",
                                    disabled=("!cup_build_ok",),
                                )
                        html.Div("{{ memory_tier_note }}", classes="text-caption text-medium-emphasis mt-1")
                        html.Div("{{ export_msg }}", classes="text-caption mt-1", style="white-space: pre-line")
                        html.A(
                            "⬇ Download STL",
                            href=("export_download",),
                            download=True,
                            v_show="export_download",
                            classes="text-caption",
                        )
                    with v3.VCard(classes="mb-2 pa-3", v_show="fan_subtab === 'results'"):
                        html.Div("How the air moves", classes="text-subtitle-1 mb-1")
                        html.Div("{{ flow_overall }}", classes="text-body-2 font-weight-medium mb-2",
                                 v_show="flow_overall")
                        html.Div("{{ flow_msg }}", classes="text-caption text-medium-emphasis mb-2",
                                 v_show="flow_msg")
                        v3.VProgressLinear(indeterminate=True, height=3, color="primary",
                                           classes="mb-2", v_show="flow_busy")
                        with v3.VRow(v_for="row in flow_rows", key="row.key", dense=True,
                                     classes="mb-2 align-center"):
                            with v3.VCol(cols=12, md=4):
                                html.Div("{{ row.icon }} {{ row.title }}",
                                         classes="text-subtitle-2")
                                html.Div("{{ row.text }}", classes="text-body-2")
                            with v3.VCol(cols=6, md=4):
                                html.Div("This design", classes="text-caption")
                                html.Img(src=("row.img",), v_show="row.img",
                                         style="width:100%;cursor:zoom-in;border-radius:4px;",
                                         click="flow_zoom_src = row.img; flow_zoom = true")
                            with v3.VCol(cols=6, md=4):
                                html.Div("Stock", classes="text-caption")
                                html.Img(src=("row.stock_img",), v_show="row.stock_img",
                                         style="width:100%;cursor:zoom-in;border-radius:4px;",
                                         click="flow_zoom_src = row.stock_img; flow_zoom = true")
                        with html.Div(v_show="ui_mode === 'expert' && flow_numbers.length"):
                            html.Div("Technical detail, not reviewed for plain language",
                                     classes="text-caption text-disabled mt-2")
                            with html.Table(classes="text-caption"):
                                with html.Tr(v_for="n in flow_numbers", key="n.name"):
                                    html.Td("{{ n.name }}", classes="pr-4")
                                    html.Td("{{ n.design }}", classes="pr-4")
                                    html.Td("{{ n.stock }}")
                        with v3.VDialog(v_model=("flow_zoom",), max_width="1100"):
                            with v3.VCard(classes="pa-2", click="flow_zoom = false"):
                                html.Img(src=("flow_zoom_src",), style="width:100%;")
                    with v3.VCard(classes="mb-2 pa-2",
                                  v_show="fan_subtab === 'results' && ui_mode === 'expert'"):
                        html.Div("Duct airflow — slices, streamlines & spanwise", classes="text-subtitle-2 mb-1")
                        html.Div("Technical detail, not reviewed for plain language",
                                 classes="text-caption text-disabled mb-1")
                        html.Div(
                            "|U| / pressure midplane: cut through the duct center, flow left → "
                            "right (FRONT/inlet LEFT, OUTLET RIGHT); brighter = faster. "
                            "axial Uz: fan-face cut colored by axial velocity — blue = forward "
                            "delivery, red = reverse/recirculation (a stalled fan reads red). "
                            "streamlines: lines through the rotor colored by |U|. "
                            "spanwise: circumferentially averaged p0 / Uz / swirl / incidence vs "
                            "radius (where along the span free-air work is lost). "
                            "b2b Cp: blade-to-blade pressure coefficient at 3–5 span stations.",
                            classes="text-caption text-medium-emphasis mb-2",
                        )
                        with v3.VBtnToggle(
                            v_model=("airflow_field",),
                            density="compact",
                            color="primary",
                            classes="mb-2",
                            mandatory=True,
                        ):
                            v3.VBtn("|U| midplane", value="U", size="small")
                            v3.VBtn("pressure midplane", value="p", size="small")
                            v3.VBtn("axial Uz", value="uz", size="small")
                            v3.VBtn("streamlines", value="stream", size="small")
                            v3.VBtn("spanwise", value="span", size="small")
                            v3.VBtn("b2b Cp", value="b2b", size="small")
                        with v3.VRow(no_gutters=True, classes="align-center mb-1"):
                            with v3.VCol(cols=9):
                                html.Div(
                                    "{{ airflow_caption }}",
                                    classes="text-caption text-medium-emphasis",
                                )
                                html.Div(
                                    "{{ airflow_progress }}",
                                    classes="text-caption",
                                    v_show="airflow_progress",
                                )
                            with v3.VCol(cols=3, classes="text-right"):
                                v3.VBtn(
                                    "⏹ Cancel viz",
                                    size="small",
                                    variant="tonal",
                                    color="warning",
                                    disabled=("!airflow_busy",),
                                    click=(cancel_airflow,),
                                )
                        v3.VProgressLinear(
                            indeterminate=True,
                            color="primary",
                            height=3,
                            classes="mb-2",
                            v_show="airflow_busy",
                        )
                        html.Img(
                            src=("airflow_img_uri",),
                            v_show="airflow_img_uri",
                            style="width:100%;max-height:520px;object-fit:contain;"
                            "display:block;background:#fafafa;border-radius:4px;",
                        )

    # Bind Fan widget updaters onto ctrl (used by setup_fan_tab callbacks).
    ctrl.view_update = view.update
    ctrl.figure_update = fig_widget.update
