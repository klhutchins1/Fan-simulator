"""r27 rendered checks (PREREG ef58906), headless cockpit, empty run. Mode buttons, tab clicks, panel expands and typing into
the Sweep steps / Trials boxes only. No Assess/Sweep/Optimize/Export/Randomize click. Usage: pwenv/bin/python r27_render.py <out.json> <screens>"""
import json, os, re, sys
from playwright.sync_api import sync_playwright
URL = f"http://127.0.0.1:{os.environ.get('QA_PORT','8827')}/"; SH = sys.argv[2]; R = {"console_errors": [], "pageerrors": []}
VR = "ranking only, unvalidated (CFD not yet converged)"
def txt(pg): return pg.evaluate("() => document.body.innerText")
def expand(pg):
    for _ in range(2):
        tt = pg.locator(".v-expansion-panel-title:visible")
        for i in range(tt.count()):
            try:
                if tt.nth(i).get_attribute("aria-expanded") == "false": tt.nth(i).click(); pg.wait_for_timeout(150)
            except Exception: pass
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True, args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": 1366, "height": 768})
    pg.on("console", lambda m: R["console_errors"].append(m.text[:200]) if m.type == "error" else None)
    pg.on("pageerror", lambda e: R["pageerrors"].append(str(e)[:200]))
    pg.goto(URL, wait_until="networkidle"); pg.wait_for_timeout(6000)
    for m in ("simple", "expert"):
        pg.locator(".v-btn", has_text=m.upper()).first.click(); pg.wait_for_timeout(1500)
        t = txt(pg)
        R[f"{m}_assess_intro"] = [l.strip()[:220] for l in t.splitlines() if "Assess runs" in l][:3]
        R[f"{m}_stale"] = {k: (k in t) for k in ("~2×", "0.6×", "3–5", "one CFD solve", "dB(A)")}
    expand(pg); pg.wait_for_timeout(800)
    t = txt(pg)
    labels = pg.evaluate("() => [...document.querySelectorAll('.v-field label, .v-label')].map(e => e.innerText.trim()).filter(Boolean)")
    R["expert_fan_labels_steps_trials"] = [l for l in labels if re.match(r"^(steps|trials)", l, re.I)]
    R["expert_fan_stale"] = {k: (k in t) for k in ("~2×", "0.6×", "3–5", "one CFD solve", "dB(A)")}
    pg.screenshot(path=f"{SH}/r27_fan_expert_expanded_1366.png", full_page=True)
    # B: type bad values (no Run click); read server state + visible error state
    for lab, key in (("steps", "sweep_steps"), ("Trials", "opt_trials")):
        f = pg.locator(".v-text-field:visible", has=pg.locator("label", has_text=re.compile(rf"^\s*{lab}", re.I))).first
        res = []
        if f.count():
            inp = f.locator("input").first
            for v in ("1e9", "100", "-5", ""):
                inp.fill(v); inp.blur(); pg.wait_for_timeout(500)
                res.append({"typed": v, "state": pg.evaluate(f"() => window.trame.state.get('{key}')"),
                            "field_error": "v-input--error" in (f.get_attribute("class") or ""),
                            "attrs": inp.evaluate("e => [e.min, e.max, e.step]")})
            inp.fill("4" if key == "sweep_steps" else "8"); inp.blur(); pg.wait_for_timeout(300)
        R[f"B_{key}"] = res
    # A: Volute tab text
    tab = pg.locator(".v-tab:visible", has_text=re.compile(r"^\s*Volute", re.I)).first
    tab.click(); pg.wait_for_timeout(2500)
    for sub in ("DESIGN", "RESULTS"):
        s = pg.locator(".v-tab:visible", has_text=re.compile(rf"^\s*{sub}\s*$"))
        if s.count(): s.first.click(); pg.wait_for_timeout(1500)
        expand(pg); t = txt(pg)
        R[f"A_volute_{sub.lower()}"] = {"assess_lines": [l.strip()[:200] for l in t.splitlines() if "Assess" in l][:6],
                                       "rank_label_lines": [l.strip()[:200] for l in t.splitlines() if VR in l][:6]}
        pg.screenshot(path=f"{SH}/r27_volute_{sub.lower()}_expert_1366.png", full_page=True)
    b.close()
json.dump(R, open(sys.argv[1], "w"), indent=1, ensure_ascii=False); print(json.dumps(R, indent=1, ensure_ascii=False))
