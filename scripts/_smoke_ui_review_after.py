"""Smoke verification for cockpit UI cohesion (Approach 1) — Playwright Chromium."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8083/"
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "build/ui_review_after")
OUT.mkdir(parents=True, exist_ok=True)

EXPECTED_TABS = ["Fan", "Mixed", "Volute", "Prop", "CROR"]


def visible_role_buttons(page, names: list[str]) -> list[dict]:
    """Collect visible buttons whose accessible name matches any of names (substring)."""
    buttons = page.get_by_role("button")
    n = buttons.count()
    found: list[dict] = []
    for i in range(n):
        btn = buttons.nth(i)
        try:
            if not btn.is_visible():
                continue
            text = (btn.inner_text() or "").strip().replace("\n", " ")
            if not text:
                continue
            for name in names:
                if name.lower() in text.lower():
                    box = btn.bounding_box()
                    if box:
                        found.append(
                            {
                                "text": text,
                                "x": box["x"],
                                "y": box["y"],
                                "w": box["width"],
                                "h": box["height"],
                            }
                        )
                    break
        except Exception:
            continue
    # Dedupe by text keeping leftmost/topmost
    by_text: dict[str, dict] = {}
    for f in found:
        key = f["text"]
        if key not in by_text or (f["y"], f["x"]) < (by_text[key]["y"], by_text[key]["x"]):
            by_text[key] = f
    return sorted(by_text.values(), key=lambda b: (round(b["y"] / 8), b["x"]))


def first_match(items: list[dict], *needles: str) -> dict | None:
    for item in items:
        t = item["text"].lower()
        if all(n.lower() in t for n in needles):
            return item
    for item in items:
        t = item["text"].lower()
        if any(n.lower() in t for n in needles):
            return item
    return None


def order_ok(ordered: list[dict | None]) -> tuple[bool, str]:
    present = [(i, b) for i, b in enumerate(ordered) if b is not None]
    if len(present) < 2:
        return False, f"too few matched buttons: {[b['text'] if b else None for b in ordered]}"
    xs = [b["x"] for _, b in present]
    ys = [b["y"] for _, b in present]
    # Same row (y within 40px): check left-to-right; else top-to-bottom then LTR
    same_row = max(ys) - min(ys) < 40
    if same_row:
        ok = all(xs[i] <= xs[i + 1] + 2 for i in range(len(xs) - 1))
        detail = " → ".join(f"{b['text']}@x={b['x']:.0f}" for _, b in present)
        return ok, detail
    # multi-row: sort by y then x should match intended order
    sorted_idx = sorted(range(len(present)), key=lambda k: (present[k][1]["y"], present[k][1]["x"]))
    ok = sorted_idx == list(range(len(present)))
    detail = " → ".join(f"{b['text']}@(x={b['x']:.0f},y={b['y']:.0f})" for _, b in present)
    return ok, detail


def click_top_tab(page, label: str) -> None:
    # Prefer role tab; fall back to text
    tab = page.get_by_role("tab", name=re.compile(rf"^{re.escape(label)}$"))
    if tab.count() == 0:
        tab = page.get_by_text(label, exact=True).first
    else:
        tab = tab.first
    tab.click()
    page.wait_for_timeout(800)


def main() -> int:
    report: dict = {"url": URL, "checks": {}, "screenshots": [], "notes": []}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1100})
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3500)

        # --- Tab order ---
        tabs = page.get_by_role("tab")
        tab_labels = []
        for i in range(tabs.count()):
            t = tabs.nth(i)
            if not t.is_visible():
                continue
            label = (t.inner_text() or "").strip()
            if label in EXPECTED_TABS or label in {"Design", "Results", "Library"}:
                tab_labels.append(label)
        top = [t for t in tab_labels if t in EXPECTED_TABS]
        # Keep first occurrence of each expected top tab in DOM order
        seen = set()
        top_unique = []
        for t in top:
            if t not in seen:
                seen.add(t)
                top_unique.append(t)
        tab_pass = top_unique == EXPECTED_TABS
        report["checks"]["tab_order"] = {
            "pass": tab_pass,
            "expected": EXPECTED_TABS,
            "actual": top_unique,
            "all_visible_tabs": tab_labels,
        }

        # --- Fan layout ---
        click_top_tab(page, "Fan")
        page.wait_for_timeout(1000)
        # Ensure Design subtab
        design = page.get_by_role("tab", name=re.compile(r"^Design$"))
        if design.count():
            design.first.click()
            page.wait_for_timeout(500)

        fan_shot = OUT / "01_fan_design.png"
        page.screenshot(path=str(fan_shot), full_page=False)
        report["screenshots"].append(str(fan_shot))

        # Controls left / viz right: Design tab (left) vs plotly / canvas (right)
        design_tab = page.get_by_role("tab", name=re.compile(r"^Design$")).first
        actions_hdr = page.get_by_text("Actions", exact=True).first
        preview_btn = page.get_by_role("button", name=re.compile(r"^Preview$")).first
        assess_btn = page.get_by_role("button", name=re.compile(r"^Assess$")).first

        # Find a large right-side viz container (vtk / plotly)
        viz_box = page.evaluate(
            """() => {
              const cands = [...document.querySelectorAll('canvas, .js-plotly-plot, .vtk-container, [class*="vtk"]')];
              let best = null;
              for (const el of cands) {
                const r = el.getBoundingClientRect();
                if (r.width < 200 || r.height < 200) continue;
                if (!best || r.width * r.height > best.w * best.h) {
                  best = {x: r.x, y: r.y, w: r.width, h: r.height, tag: el.tagName, cls: el.className};
                }
              }
              return best;
            }"""
        )

        dbox = design_tab.bounding_box() if design_tab.count() else None
        abox = actions_hdr.bounding_box() if actions_hdr.count() else None
        pbox = preview_btn.bounding_box() if preview_btn.count() else None
        asbox = assess_btn.bounding_box() if assess_btn.count() else None

        controls_left = False
        if dbox and viz_box:
            controls_left = dbox["x"] + dbox["width"] < viz_box["x"] + 40
        elif abox and viz_box:
            controls_left = abox["x"] < viz_box["x"]

        # Preview+Assess near top of controls (not buried): y should be above mid-viewport of left column
        near_top = False
        if pbox and asbox:
            near_top = pbox["y"] < 420 and asbox["y"] < 450 and abs(pbox["y"] - asbox["y"]) < 60
            if abox:
                # Actions header should appear before Modify design
                modify = page.get_by_text("Modify design", exact=False)
                if modify.count():
                    mbox = modify.first.bounding_box()
                    if mbox:
                        near_top = near_top and abox["y"] < mbox["y"]

        # Fan action order Preview → Assess → Export → Optimize
        fan_btns = visible_role_buttons(
            page, ["Preview", "Assess", "Export", "Optimize", "Reset", "Cancel"]
        )
        fan_order = [
            first_match(fan_btns, "Preview"),
            first_match(fan_btns, "Assess"),
            first_match(fan_btns, "Export"),
            first_match(fan_btns, "Optimize"),
        ]
        fan_order_pass, fan_order_detail = order_ok(fan_order)

        report["checks"]["fan_controls_left_viz_right"] = {
            "pass": bool(controls_left),
            "design_tab": dbox,
            "actions": abox,
            "preview": pbox,
            "assess": asbox,
            "viz": viz_box,
        }
        report["checks"]["fan_preview_assess_near_top"] = {
            "pass": bool(near_top),
            "preview_y": pbox["y"] if pbox else None,
            "assess_y": asbox["y"] if asbox else None,
            "actions_y": abox["y"] if abox else None,
        }
        report["checks"]["fan_action_order"] = {
            "pass": fan_order_pass,
            "detail": fan_order_detail,
            "buttons": fan_btns,
        }

        # --- Mixed ---
        click_top_tab(page, "Mixed")
        page.wait_for_timeout(1200)
        mixed_shot = OUT / "02_mixed.png"
        page.screenshot(path=str(mixed_shot), full_page=False)
        report["screenshots"].append(str(mixed_shot))

        mf_layout = page.evaluate(
            """() => {
              // Prefer vtk/canvas for 3D; plotly for plot
              const canvases = [...document.querySelectorAll('canvas')].map(el => {
                const r = el.getBoundingClientRect();
                return {x:r.x,y:r.y,w:r.width,h:r.height, kind:'canvas'};
              }).filter(b => b.w>180 && b.h>180);
              const plots = [...document.querySelectorAll('.js-plotly-plot')].map(el => {
                const r = el.getBoundingClientRect();
                return {x:r.x,y:r.y,w:r.width,h:r.height, kind:'plotly'};
              }).filter(b => b.w>180 && b.h>120);
              // On Mixed, right column should have 3D then plot stacked
              const rightish = (b) => b.x > window.innerWidth * 0.35;
              const c3 = canvases.filter(rightish).sort((a,b)=>a.y-b.y)[0] || canvases.sort((a,b)=>a.y-b.y)[0];
              const pl = plots.filter(rightish).sort((a,b)=>a.y-b.y)[0] || plots.sort((a,b)=>a.y-b.y)[0];
              return {canvas: c3 || null, plot: pl || null, nCanvas: canvases.length, nPlot: plots.length};
            }"""
        )
        mixed_3d_above = False
        if mf_layout.get("canvas") and mf_layout.get("plot"):
            mixed_3d_above = mf_layout["canvas"]["y"] < mf_layout["plot"]["y"]
        report["checks"]["mixed_3d_above_plot"] = {
            "pass": bool(mixed_3d_above),
            "layout": mf_layout,
        }

        mixed_btns = visible_role_buttons(
            page, ["Preview", "Assess", "Export", "Optimize", "CFD refine", "CFD"]
        )
        mixed_order = [
            first_match(mixed_btns, "Preview"),
            first_match(mixed_btns, "Assess"),
            first_match(mixed_btns, "Export"),
            first_match(mixed_btns, "Optimize"),
            first_match(mixed_btns, "CFD"),
        ]
        mixed_order_pass, mixed_order_detail = order_ok(mixed_order)
        report["checks"]["mixed_action_order"] = {
            "pass": mixed_order_pass,
            "detail": mixed_order_detail,
            "buttons": mixed_btns,
        }

        # --- Volute ---
        click_top_tab(page, "Volute")
        page.wait_for_timeout(1000)
        volute_shot = OUT / "03_volute.png"
        page.screenshot(path=str(volute_shot), full_page=False)
        report["screenshots"].append(str(volute_shot))
        volute_btns = visible_role_buttons(page, ["Preview", "Assess", "Export", "Optimize"])
        volute_order = [
            first_match(volute_btns, "Preview"),
            first_match(volute_btns, "Assess"),
            first_match(volute_btns, "Export"),
            first_match(volute_btns, "Optimize"),
        ]
        # Volute may not have Optimize — order among present
        present_vol = [b for b in volute_order if b]
        vol_pass, vol_detail = order_ok(volute_order if len(present_vol) >= 2 else present_vol + [None])
        if len(present_vol) < 2:
            vol_pass = len(present_vol) >= 1  # soft: at least buttons render
            vol_detail = f"present={[b['text'] for b in present_vol]}"
        report["checks"]["volute_action_order"] = {
            "pass": vol_pass,
            "detail": vol_detail,
            "buttons": volute_btns,
            "note": "Optimize may be N/A on Volute",
        }

        # --- Prop ---
        click_top_tab(page, "Prop")
        page.wait_for_timeout(1000)
        prop_shot = OUT / "04_prop.png"
        page.screenshot(path=str(prop_shot), full_page=False)
        report["screenshots"].append(str(prop_shot))
        prop_btns = visible_role_buttons(
            page, ["Analyze", "Preview", "Assess", "Export", "Optimize", "CFD"]
        )
        prop_order = [
            first_match(prop_btns, "Analyze") or first_match(prop_btns, "Preview"),
            first_match(prop_btns, "Assess"),
            first_match(prop_btns, "Export"),
            first_match(prop_btns, "Optimize"),
            first_match(prop_btns, "CFD"),
        ]
        prop_pass, prop_detail = order_ok(prop_order)
        report["checks"]["prop_action_order"] = {
            "pass": prop_pass,
            "detail": prop_detail,
            "buttons": prop_btns,
        }

        # --- CROR ---
        click_top_tab(page, "CROR")
        page.wait_for_timeout(1000)
        cror_shot = OUT / "05_cror.png"
        page.screenshot(path=str(cror_shot), full_page=False)
        report["screenshots"].append(str(cror_shot))
        cror_btns = visible_role_buttons(
            page, ["Preview", "Analyze", "Assess", "Export", "Optimize", "CFD", "Thin"]
        )
        cror_order = [
            first_match(cror_btns, "Optimize"),
            first_match(cror_btns, "CFD"),
        ]
        cror_pass, cror_detail = order_ok(cror_order)
        if first_match(cror_btns, "Optimize") is None:
            cror_pass = False
            cror_detail = "Optimize button not found"
        report["checks"]["cror_action_order"] = {
            "pass": cror_pass,
            "detail": cror_detail,
            "buttons": cror_btns,
            "note": "CROR is proxy-first; Optimize → CFD refine expected",
        }

        # Full-page Fan again for review pack
        click_top_tab(page, "Fan")
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / "01_fan_design_full.png"), full_page=True)
        report["screenshots"].append(str(OUT / "01_fan_design_full.png"))

        browser.close()

    report_path = OUT / "smoke_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))

    fails = [k for k, v in report["checks"].items() if not v.get("pass")]
    print("\n=== SUMMARY ===")
    for k, v in report["checks"].items():
        print(f"{'PASS' if v.get('pass') else 'FAIL'}: {k}")
    print(f"URL: {URL}")
    print(f"Report: {report_path}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
