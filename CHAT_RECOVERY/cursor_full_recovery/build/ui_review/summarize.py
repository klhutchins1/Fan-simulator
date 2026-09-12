import json
from pathlib import Path

f = json.loads(Path("build/ui_review/findings.json").read_text(encoding="utf-8"))
out = []
for k, v in f["tabs"].items():
    s = v["structure"]
    out.append(f"==== {k} ====")
    out.append(f"scroll {s['scrollHeight']} client {s['clientHeight']}")
    out.append("selected: " + str([t["text"] for t in s["tabs"] if t.get("selected")]))
    out.append("buttons:")
    for b in s["buttons"]:
        t = " ".join((b["text"] or "").split())
        if not t:
            continue
        u = t.upper()
        if any(x in u for x in ["FAN —", "PROPELLER —", "MIXED-FLOW", "VOLUTE —", "CROR —"]) and "OPTIMIZE" not in u:
            if len(t) > 12:
                continue
        if t in ("DESIGN", "RESULTS", "LIBRARY"):
            continue
        out.append(f"  [{'DIS' if b['disabled'] else 'OK '}] {t[:110]}")
    out.append("cards: " + str([(c.get("title") or "", c.get("top"), c.get("h")) for c in s["cards"]]))
    out.append("panels: " + str(s["panels"]))
    out.append("switches: " + str(s["switches"]))
    out.append("captions:")
    for c in s["captions"][:10]:
        out.append("  " + c[:170])
    for a in v["actions"]:
        keys = list(a.keys())
        if any(x in a for x in ("structure", "structure_after", "scrolled_structure")):
            ss = a.get("structure") or a.get("structure_after") or a.get("scrolled_structure")
            out.append(f"block {keys[0]}:")
            if isinstance(ss, dict):
                bt = []
                for b in ss.get("buttons", []):
                    t = " ".join((b.get("text") or "").split())
                    if t and len(t) > 2:
                        bt.append((t[:80], b.get("disabled")))
                out.append("  buttons=" + str(bt[:25]))
                out.append("  captions=" + str(ss.get("captions", [])[:8]))
                out.append(
                    "  titled_cards="
                    + str([(c.get("title"), c.get("top"), c.get("h")) for c in ss.get("cards", []) if c.get("title")])
                )
        else:
            out.append("action: " + str(a)[:400])
    out.append("")

Path("build/ui_review/summary.txt").write_text("\n".join(out), encoding="utf-8")
print("ok", len(out))
