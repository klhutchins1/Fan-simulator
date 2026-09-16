"""Extract render_fan_tab into fan_tab_ui.py; dedupe widget helpers in fan_tab.py."""

from __future__ import annotations

from pathlib import Path

SRC = Path("fansim/cockpit/fan_tab.py")
UI = Path("fansim/cockpit/fan_tab_ui.py")

lines = SRC.read_text(encoding="utf-8").splitlines(True)
start = next(i for i, l in enumerate(lines) if l.startswith("def render_fan_tab"))
render = "".join(lines[start:])

header = '''"""Fan tab Trame UI (Design / Results / Library / Optimize panels).

Extracted from fan_tab.py (roadmap sec 13.9). Callbacks live in setup_fan_tab;
this module only builds widgets and binds ctrl.view_update / figure_update.
"""

from __future__ import annotations

import sys

from fansim.cockpit.context import CockpitCtx
from fansim.cockpit.fan_copy import CONTROL_DESC, OPT_SEARCH_HELP
from fansim.cockpit.fan_widgets import help_switch, opt_section, slider

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


'''

UI.write_text(header + render, encoding="utf-8")
print("wrote", UI, "render lines", len(render.splitlines()))

trimmed = lines[:start]
i0 = next(i for i, l in enumerate(trimmed) if l.startswith("def _slider"))
i1 = next(i for i, l in enumerate(trimmed) if l.startswith("def setup_fan_tab"))
new_mid = (
    "from fansim.cockpit.fan_widgets import help_switch, opt_section, slider\n"
    "\n"
    "# Back-compat names (setup may reference these; UI lives in fan_tab_ui)\n"
    "_slider = slider\n"
    "_opt_section = opt_section\n"
    "_help_switch = help_switch\n"
    "\n"
    "from fansim.cockpit.fan_tab_ui import render_fan_tab  # noqa: E402  — re-export for app.py\n"
    "\n"
)
# Drop unused fan_copy import from setup module if present — keep if still needed.
# setup_fan_tab body does not use CONTROL_DESC/OPT_SEARCH_HELP/IMG (render does).
head = "".join(trimmed[:i0])
head = head.replace(
    "from fansim.cockpit.fan_copy import CONTROL_DESC, OPT_SEARCH_HELP, _IMG_URI\n\n\n",
    "",
)
head = head.replace(
    "from fansim.cockpit.fan_copy import CONTROL_DESC, OPT_SEARCH_HELP, _IMG_URI\n\n",
    "",
)
head = head.replace(
    "from fansim.cockpit.fan_copy import CONTROL_DESC, OPT_SEARCH_HELP, _IMG_URI\n",
    "",
)

result = head + new_mid + "".join(trimmed[i1:])
SRC.write_text(result, encoding="utf-8")
print("fan_tab now", len(result.splitlines()), "lines")
