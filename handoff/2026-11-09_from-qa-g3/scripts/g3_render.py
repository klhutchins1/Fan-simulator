"""G3 re-check (PREREG 7e3e214) rendered checks on a headless cockpit with an empty run. Tab clicks + hovers only; no Assess/Sweep/
Optimize/Export/Randomize. Usage: pwenv/bin/python g3_render.py <out.json> <screens>"""
import json, os, re, sys
from playwright.sync_api import sync_playwright
URL = f"http://127.0.0.1:{os.environ.get('QA_PORT','8821')}/"; SH = sys.argv[2]; R = {"console_errors": [], "pageerrors": []}
EXP = "Experimental: not validated against published data"; MRF = "Assess runs MRF CFD (not validated against published data)"
VR = "ranking only, unvalidated (CFD not yet converged)"
def txt(pg): return pg.evaluate("() => document.body.innerText")
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True, args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": 1366, "height": 768})
    pg.on("console", lambda m: R["console_errors"].append(m.text[:200]) if m.type == "error" else None)
    pg.on("pageerror", lambda e: R["pageerrors"].append(str(e)[:200]))
    pg.goto(URL, wait_until="networkidle"); pg.wait_for_timeout(6000)
    for m in ("simple", "expert"):
        pg.locator(".v-btn", has_text=m.upper()).first.click(); pg.wait_for_timeout(1200)
        R[f"tabs_{m}"] = [t.strip() for t in pg.locator(".v-tab:visible").all_inner_texts()]
    t = txt(pg); R["fan_intro_honest"] = "honest" in t.lower(); R["fan_intro_line"] = [l for l in t.splitlines() if "faster estimates" in l][:1]
    for name, key in (("Mixed", "mixed"), ("Volute", "volute")):
        tab = pg.locator(".v-tab:visible", has_text=re.compile(rf"^\s*{name}", re.I)).first
        tab.hover(); pg.wait_for_timeout(900)
        ov = pg.locator(".v-overlay--active .v-overlay__content:visible")
        R[f"{key}_tab_tooltip"] = ov.last.inner_text()[:160] if ov.count() else None
        tab.click(); pg.wait_for_timeout(2500); pg.mouse.move(5, 5)
        for sub in ("DESIGN", "RESULTS"):
            s = pg.locator(".v-tab:visible", has_text=re.compile(rf"^\s*{sub}\s*$"))
            if s.count(): s.first.click(); pg.wait_for_timeout(1500)
            for _ in range(2):
                tt = pg.locator(".v-expansion-panel-title:visible")
                for i in range(tt.count()):
                    try:
                        if tt.nth(i).get_attribute("aria-expanded") == "false": tt.nth(i).click(); pg.wait_for_timeout(150)
                    except Exception: pass
            t = txt(pg)
            R[f"{key}_{sub.lower()}"] = {"experimental": EXP in t, "assess_mrf": MRF in t, "volute_rank": VR in t,
                                         "honest_lines": [l.strip()[:160] for l in t.splitlines() if "honest" in l.lower()],
                                         "mrf_lines": [l.strip()[:160] for l in t.splitlines() if "MRF" in l][:8]}
            pg.screenshot(path=f"{SH}/g3_{key}_{sub.lower()}_expert_1366.png", full_page=True)
    b.close()
json.dump(R, open(sys.argv[1], "w"), indent=1, ensure_ascii=False); print(json.dumps(R, indent=1, ensure_ascii=False))
