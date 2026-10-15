"""QA r13 Task D: static always-visible text-caption blocks in the other tabs (AST). Usage: python d_captions.py <src_dir> <out.json>"""
import ast, json, sys
from pathlib import Path
out = []
for f in ("mixed_tab.py", "prop_tab.py", "volute_tab.py", "cror_tab.py", "tab_shell.py"):
    src = (Path(sys.argv[1]) / f).read_text()
    for n in ast.walk(ast.parse(src)):
        if not isinstance(n, ast.Call): continue
        kw = {k.arg: k.value for k in n.keywords}
        c = kw.get("classes")
        if not (isinstance(c, ast.Constant) and "text-caption" in str(c.value)): continue
        if not n.args or not isinstance(n.args[0], ast.Constant) or not isinstance(n.args[0].value, str): continue
        s = n.args[0].value
        if "{{" in s: continue
        out.append({"file": f, "line": n.lineno, "chars": len(s), "v_show": ast.unparse(kw["v_show"]) if "v_show" in kw else None,
                    "v_if": ast.unparse(kw["v_if"]) if "v_if" in kw else None, "text": s})
json.dump(out, open(sys.argv[2], "w"), indent=1, ensure_ascii=False)
for o in out: print(o["file"], o["line"], o["chars"], o["v_show"] or o["v_if"] or "", o["text"][:70])
