"""Compare cockpit slider min/max (fan_tab_ui.py _slider calls) vs generate_control_images.CONTROLS."""
import ast, json, sys, importlib.util
from pathlib import Path
REPO = Path(sys.argv[1] if len(sys.argv) > 1 else "/workspace/fansim/repo-tt")
src = (REPO / "fansim/cockpit/fan_tab_ui.py").read_text()
ui = {}
for n in ast.walk(ast.parse(src)):
    if isinstance(n, ast.Call) and getattr(n.func, "id", "") in ("_slider", "slider") and len(n.args) >= 4:
        try:
            lab, model = ast.literal_eval(n.args[0]), ast.literal_eval(n.args[1])
        except Exception:
            continue
        def v(a):
            try: return ast.literal_eval(a)
            except Exception: return ast.unparse(a)
        ui[model] = dict(label=lab, line=n.lineno, mn=v(n.args[2]), mx=v(n.args[3]))
# parse CONTROLS list literally from the generator (no heavy imports)
g = ast.parse((REPO / "scripts/generate_control_images.py").read_text())
gen = {}
for n in g.body:
    if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "CONTROLS":
        for i, e in enumerate(n.value.elts):
            row = ast.literal_eval(e)
            gen[row[0]] = dict(label=row[1], mn=row[3], mx=row[4], mode=row[5], line=e.lineno)
imgs = {p.stem for p in (REPO / "docs/control_images").glob("*.png")}
out = []
for m in sorted(set(ui) | set(gen)):
    u, gg = ui.get(m), gen.get(m)
    row = dict(model=m, ui=u, gen=gg, has_img=m in imgs)
    if u and gg:
        row["match"] = (u["mn"] == gg["mn"] and u["mx"] == gg["mx"])
    out.append(row)
json.dump(out, open("/workspace/fansim/qa_tooltips/data/range_check.json", "w"), indent=1)
for r in out:
    u, gg = r["ui"], r["gen"]
    print(f'{r["model"]:22} img={int(r["has_img"])} ui={(u["mn"],u["mx"]) if u else "-"!s:28} gen={(gg["mn"],gg["mx"]) if gg else "-"!s:20} {"" if r.get("match", True) else "MISMATCH"} {"L"+str(u["line"]) if u else ""}')
