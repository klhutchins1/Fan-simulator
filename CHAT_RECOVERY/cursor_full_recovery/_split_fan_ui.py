"""Split render_fan_tab into fan_ui.py; slim fan_tab to setup + re-export."""
from __future__ import annotations

from pathlib import Path

tab = Path("fansim/cockpit/fan_tab.py")
lines = tab.read_text(encoding="utf-8").splitlines(True)
start = next(i for i, l in enumerate(lines) if l.startswith("def render_fan_tab"))
render = "".join(lines[start:])
setup = "".join(lines[:start])

hdr = '''"""Fan tab Trame layout (Design / Results / Library)."""
from __future__ import annotations

import sys

from fansim.cockpit.context import CockpitCtx
from fansim.cockpit.fan_copy import CONTROL_DESC, OPT_SEARCH_HELP
from fansim.cockpit.fan_widgets import _help_switch, _opt_section, _slider
from fansim.cockpit.score_caption import score_caption

_RUNNING_TESTS = "pytest" in sys.modules
if _RUNNING_TESTS:
    plotter_ui = None  # type: ignore[assignment]
    html = None  # type: ignore[assignment]
    plotly_widgets = None  # type: ignore[assignment]
    v3 = None  # type: ignore[assignment]
else:
    from pyvista.trame.ui import plotter_ui
    from trame.widgets import html
    from trame.widgets import plotly as plotly_widgets
    from trame.widgets import vuetify3 as v3


'''

Path("fansim/cockpit/fan_ui.py").write_text(hdr + render, encoding="utf-8", newline="\n")

setup2 = setup.replace(
    "from fansim.cockpit.fan_viz import bind_fan_viz\n",
    "from fansim.cockpit.fan_ui import render_fan_tab\n"
    "from fansim.cockpit.fan_viz import bind_fan_viz\n",
)
for drop in (
    "from fansim.cockpit.fan_copy import CONTROL_DESC, OPT_SEARCH_HELP\n",
    "from fansim.cockpit.fan_widgets import _help_switch, _opt_section, _slider\n",
):
    setup2 = setup2.replace(drop, "")

tab.write_text(
    setup2.rstrip() + "\n\n__all__ = [\"setup_fan_tab\", \"render_fan_tab\"]\n",
    encoding="utf-8",
    newline="\n",
)
print("fan_tab", setup2.count("\n") + 1, "fan_ui", (hdr + render).count("\n") + 1)
