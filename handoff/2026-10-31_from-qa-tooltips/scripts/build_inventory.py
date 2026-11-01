"""Join scan.json (AST widget scan) with the tooltip maps + image dir -> inventory.csv/json.

Status per control: IMAGE+TEXT (image tooltip), TEXT (text-only tooltip), NONE.
Helper widgets (slider/_slider/help_switch/_help_switch/help_select/_help_select) get their tooltip
inside fan_widgets.py from CONTROL_DESC / OPT_SEARCH_HELP / help_map and _IMG_URI (docs/control_images/e_*.png).
Action-row buttons are dict-driven (fan_tab_ui.py ~582-638) and added by hand.
"""
import csv, json, sys
sys.path.insert(0, "/workspace/fansim/repo-tt")
from fansim.cockpit.fan_copy import CONTROL_DESC, OPT_SEARCH_HELP, _IMG_URI
from fansim.cockpit.blade_copy import BLADE_DESC

d = json.load(open("/workspace/fansim/qa_tooltips/data/scan.json"))
HELPERS = {"slider", "_slider", "help_switch", "_help_switch", "help_select", "_help_select"}
ACTIONS = [  # fan_tab_ui.py action-row dicts + Reset; tab_shell.render_actions -> plain VBtn
    ("fan_tab_ui.py", 582, "VBtn(action)", "Preview (sec)", None),
    ("fan_tab_ui.py", 590, "VBtn(action)", "Assess (~15–30 min)", None),
    ("fan_tab_ui.py", 600, "VBtn(action)", "Optimize (hours)", None),
    ("fan_tab_ui.py", 610, "VBtn(action)", "⏹ Cancel opt", None),
    ("fan_tab_ui.py", 620, "VBtn(action)", "⏹ Cancel Assess", None),
    ("fan_tab_ui.py", 630, "VBtn(action)", "Randomize geometry", None),
    ("fan_tab_ui.py", 639, "VBtn", "Reset", None),
]


def area(r):
    f, ln = r["file"].split("/")[-1], r["line"]
    if f == "app.py":
        return "Header / tabs"
    if f == "tab_shell.py":
        return "Fan sub-tabs / action row"
    if f == "fan_widgets.py":
        return None  # helper internals, not a user control
    if f == "blade_editor.py":
        return "Prop+CROR shared shape panels"
    if f != "fan_tab_ui.py":
        return f.replace("_tab.py", "").capitalize() + " tab"
    for lo, hi, nm in [(1, 112, "Fan header"), (113, 225, "Fan › Results"), (226, 489, "Fan › Library"),
                       (490, 667, "Fan › Design (top)"), (668, 891, "Fan › Design › Geometry"),
                       (892, 1009, "Fan › Design › Assess & print"), (1010, 1118, "Fan › Design › Optimize"),
                       (1119, 1230, "Fan › Design › Fit & seed"), (1231, 1331, "Fan › Viewer"),
                       (1332, 1430, "Fan › Export"), (1431, 9999, "Fan › Results › Airflow")]:
        if lo <= ln <= hi:
            return nm


def mode(r):
    s = " ".join([r.get("own_v_show") or ""] + list(r.get("ancestor_show") or []))
    if "ui_mode === 'expert'" in s or r["file"].endswith(("mixed_tab.py", "volute_tab.py", "cror_tab.py")):
        return "Expert"
    if "ui_mode === 'simple'" in s or "ui_mode !== 'expert'" in s:
        return "Simple"
    return "Both"


rows = []
for r in d:
    a = area(r)
    if a is None:
        continue
    m = r["model"]
    m = m.strip("()',") if isinstance(m, str) else m
    text, img = (r.get("tooltip_text") or ""), None
    if r["widget"] in HELPERS and m:
        text = text or CONTROL_DESC.get(m) or OPT_SEARCH_HELP.get(m) or ""
        if "cylindrical_tip" in str(m) and r["file"].endswith("blade_editor.py"):
            text = BLADE_DESC.get("cylindrical_tip", "")
        if r["widget"] in ("slider", "_slider", "help_select", "_help_select"):
            text = r.get("tooltip_text") or CONTROL_DESC.get(m, "")
            if r["widget"] in ("slider", "_slider") and m in OPT_SEARCH_HELP and not text:
                text = ""
        img = f"docs/control_images/{m}.png" if m in _IMG_URI else None
    if m in ("opt_trials", "opt_rpm_min", "opt_rpm_max") and not text:
        text = OPT_SEARCH_HELP[m]  # manual VTooltip wraps, text via OPT_SEARCH_HELP[...] subscript
    st = "IMAGE+TEXT" if img else ("TEXT" if text else "NONE")
    rows.append(dict(file=r["file"].split("/")[-1], line=r["line"], area=a, mode=mode(r), widget=r["widget"],
                     label=r["label"], model=m, status=st, text=text, image=img or ""))
for f, ln, w, lab, m in ACTIONS:
    rows.append(dict(file=f, line=ln, area="Fan action row", mode="Both", widget=w, label=lab, model=m,
                     status="NONE", text="", image=""))
rows.sort(key=lambda x: (x["file"], x["line"]))
json.dump(rows, open("/workspace/fansim/qa_tooltips/data/inventory.json", "w"), indent=1, ensure_ascii=False)
with open("/workspace/fansim/qa_tooltips/data/inventory.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader(); w.writerows(rows)
from collections import Counter
print("total", len(rows), Counter(r["status"] for r in rows))
settings = [r for r in rows if r["model"]]
print("settings(with model)", len(settings), Counter(r["status"] for r in settings))
for a in sorted(set(r["area"] for r in rows)):
    sub = [r for r in rows if r["area"] == a]
    print(f"{a:34} {len(sub):3} {dict(Counter(r['status'] for r in sub))}")
