"""QA r13 Task D: screenshot Mixed/Volute/Prop/CROR in Simple vs Expert; record whether visible text differs. Usage: pwvenv python d_shots.py <out.json> <screens>"""
import json, sys
from playwright.sync_api import sync_playwright
OUT, SH = sys.argv[1], sys.argv[2]; R = {}
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True); pg = b.new_context(viewport={"width": 1366, "height": 768}).new_page()
    pg.goto("http://127.0.0.1:8080/", wait_until="networkidle"); pg.wait_for_timeout(6000)
    for tab in ("MIXED · PROXY", "VOLUTE · PROXY", "PROP · BEMT", "CROR · PROXY"):
        pg.locator(".v-tab", has_text=tab).first.click(); pg.wait_for_timeout(2500); t = {}
        for m in ("SIMPLE", "EXPERT"):
            pg.locator(".v-btn", has_text=m).first.click(); pg.wait_for_timeout(1000)
            t[m] = pg.locator(".v-main").first.inner_text()
            pg.screenshot(path=f"{SH}/d_{tab.split()[0].lower()}_{m.lower()}.png")
        R[tab] = {"identical_text": t["SIMPLE"] == t["EXPERT"], "n_lines": len(t["SIMPLE"].splitlines())}
    b.close()
json.dump(R, open(OUT, "w"), indent=1); print(R)
