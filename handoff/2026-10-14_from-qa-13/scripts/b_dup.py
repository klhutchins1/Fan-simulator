"""QA r13 Task B (PREREG_R13 02584e6): one real Preview of Stock, then capture all visible text (Simple + Expert,
Design + Results sub-tabs) for the duplicate catalog. Usage: pwvenv/bin/python b_dup.py <out.json> <screens_dir>"""
import json, sys, time
from playwright.sync_api import sync_playwright
OUT, SH = sys.argv[1], sys.argv[2]; R = {}
def st(pg, k):
    try: return pg.evaluate(f"() => window.trame.state.get('{k}')")
    except Exception as e: return f"ERR {e}"
def lines(pg):
    t = pg.locator(".v-main").first.inner_text() if pg.locator(".v-main").count() else pg.locator("body").inner_text()
    return [l.strip() for l in t.splitlines() if l.strip()]
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True); pg = b.new_context(viewport={"width": 1366, "height": 768}).new_page()
    pg.goto("http://127.0.0.1:8080/", wait_until="networkidle"); pg.wait_for_timeout(6000)
    R["before"] = lines(pg)
    pg.locator(".v-btn", has_text="PREVIEW").first.click(); t = time.monotonic(); pg.wait_for_timeout(2000)
    while st(pg, "preview_busy") and time.monotonic() - t < 600: pg.wait_for_timeout(2000)
    R["preview_s"] = round(time.monotonic() - t, 1); pg.wait_for_timeout(3000)
    R["state"] = {k: st(pg, k) for k in ("preview_msg", "assess_msg", "export_msg", "info_lines", "score_line", "flow_numbers", "flow_card", "ui_mode")}
    for m in ("SIMPLE", "EXPERT"):
        pg.locator(".v-btn", has_text=m).first.click(); pg.wait_for_timeout(800)
        for s in ("DESIGN", "RESULTS"):
            pg.locator(".v-tab", has_text=s).first.click(); pg.wait_for_timeout(1000)
            R[f"{m}_{s}"] = lines(pg); pg.screenshot(path=f"{SH}/b_{m.lower()}_{s.lower()}.png", full_page=True)
    b.close()
json.dump(R, open(OUT, "w"), indent=1, ensure_ascii=False, default=str)
print("preview_s", R["preview_s"], {k: len(v) for k, v in R.items() if isinstance(v, list)})
