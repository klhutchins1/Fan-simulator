"""Static scan of cockpit UI controls: widget calls with label/v_model, enclosing v_show/tooltip context.
Usage: python scan_controls.py <repo> <out.json>"""
import ast, json, sys
from pathlib import Path
CTRL = {"VSlider", "VRangeSlider", "VTextField", "VSelect", "VSwitch", "VCheckbox", "VBtnToggle", "VRadioGroup", "VRadio",
        "VBtn", "VCombobox", "VAutocomplete", "VFileInput", "VChip", "VTab", "VExpansionPanelTitle", "VNumberInput", "VTextarea"}
HELPERS = {"slider", "_slider", "help_switch", "_help_switch", "help_select", "_help_select"}
def name_of(f):
    if isinstance(f, ast.Attribute): return f.attr
    if isinstance(f, ast.Name): return f.id
    return None
def s(node, src):
    if node is None: return None
    if isinstance(node, ast.Constant): return node.value
    if isinstance(node, ast.Tuple) and node.elts and isinstance(node.elts[0], ast.Constant): return "(" + str(node.elts[0].value) + ")"
    if isinstance(node, ast.JoinedStr): return ast.get_source_segment(src, node)
    return ast.get_source_segment(src, node)
def kw(call, k):
    for x in call.keywords:
        if x.arg == k: return x.value
class V(ast.NodeVisitor):
    def __init__(self, f, src): self.f, self.src, self.stack, self.out = f, src, [], []; self.fn = []
    def visit_FunctionDef(self, n): self.fn.append(n.name); self.generic_visit(n); self.fn.pop()
    def visit_With(self, n):
        ctx = []
        for it in n.items:
            c = it.context_expr
            if isinstance(c, ast.Call):
                ctx.append({"w": name_of(c.func), "v_show": s(kw(c, "v_show"), self.src), "v_if": s(kw(c, "v_if"), self.src),
                            "text": s(kw(c, "text"), self.src), "title": s(kw(c, "title"), self.src), "line": n.lineno})
                self.rec(c, with_=True)
        self.stack.append(ctx)
        for b in n.body: self.visit(b)
        self.stack.pop()
    def visit_Call(self, n):
        self.rec(n); self.generic_visit(n)
    def rec(self, c, with_=False):
        w = name_of(c.func)
        if w not in CTRL and w not in HELPERS: return
        if getattr(c, "_seen", False): return
        c._seen = True
        args = [s(a, self.src) for a in c.args]
        label = s(kw(c, "label"), self.src)
        model = s(kw(c, "v_model"), self.src)
        if w in ("slider", "_slider"):
            label, model = (args + [None, None])[:2]
        if w in ("help_switch", "_help_switch", "help_select", "_help_select"):
            model, label = (args + [None, None])[:2]
            label = label or s(kw(c, "label"), self.src)
        if label is None and args: label = args[0]
        flat = [x for ctx in self.stack for x in ctx]
        tips = [x for x in flat if x["w"] == "VTooltip"]
        shows = [x["v_show"] or x["v_if"] for x in flat if (x["v_show"] or x["v_if"])]
        self.out.append({"file": self.f, "line": c.lineno, "func": self.fn[-1] if self.fn else None, "widget": w,
                         "label": label, "model": model, "title_kw": s(kw(c, "title"), self.src),
                         "hint": s(kw(c, "hint"), self.src), "own_v_show": s(kw(c, "v_show"), self.src) or s(kw(c, "v_if"), self.src),
                         "disabled": s(kw(c, "disabled"), self.src), "click": s(kw(c, "click"), self.src),
                         "tooltip_text": tips[-1]["text"] if tips else None, "tooltip_line": tips[-1]["line"] if tips else None,
                         "ancestor_show": shows})
repo = Path(sys.argv[1]); out = []
for p in sorted((repo / "fansim/cockpit").glob("*.py")) + [repo / "fansim/ui_mode.py"]:
    if not p.exists(): continue
    src = p.read_text(); v = V(str(p.relative_to(repo)), src); v.visit(ast.parse(src)); out += v.out
json.dump(out, open(sys.argv[2], "w"), indent=1, default=str)
from collections import Counter
print(len(out), Counter(o["file"] for o in out)); print(Counter(o["widget"] for o in out))
