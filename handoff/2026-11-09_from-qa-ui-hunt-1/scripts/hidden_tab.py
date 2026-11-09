"""ui-hunt-1: on an Expert-only tab (Mixed/Volute/CROR), switch to Simple. What tab is active and what is shown? No runs."""
import json, os, sys
from playwright.sync_api import sync_playwright
URL = f"http://127.0.0.1:{os.environ.get('QA_PORT','8812')}/"; R = {}
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True, args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": 1366, "height": 768}); pg.goto(URL, wait_until="networkidle"); pg.wait_for_timeout(5000)
    for t in ("mixed", "volute", "cror"):
        pg.evaluate("() => window.trame.state.set('ui_mode','expert')"); pg.wait_for_timeout(800)
        tabs = pg.locator(".v-tab:visible"); names = [x.strip() for x in tabs.all_inner_texts()]
        pg.locator(".v-tab:visible", has_text=t.upper() if t != "cror" else "CROR").first.click(); pg.wait_for_timeout(1500)
        a1 = pg.evaluate("() => window.trame.state.get('active_tab')")
        pg.locator(".v-btn", has_text="SIMPLE").first.click(); pg.wait_for_timeout(1500)
        txt = pg.evaluate("() => document.body.innerText")
        sel = pg.evaluate("() => [...document.querySelectorAll('.v-tab')].filter(e=>e.offsetParent).map(e=>[e.innerText.trim(), e.classList.contains('v-tab--selected')])")
        R[t] = {"active_after_click": a1, "active_after_simple": pg.evaluate("() => window.trame.state.get('active_tab')"), "visible_tabs_simple": sel,
                "body_head": txt[:260].replace("\n", " | ")}
        pg.screenshot(path=f"{sys.argv[2]}/10_{t}_then_simple_1366.png")
    pg.evaluate("() => window.trame.state.set('active_tab','fan')"); b.close()
json.dump(R, open(sys.argv[1], "w"), indent=1, ensure_ascii=False); print(json.dumps(R, indent=1, ensure_ascii=False))
