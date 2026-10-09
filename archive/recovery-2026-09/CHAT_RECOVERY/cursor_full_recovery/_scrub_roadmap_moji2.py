"""Second-pass roadmap mojibake: decode remaining cp437-style sequences."""
from __future__ import annotations

import json
import re
from pathlib import Path

p = Path("docs/roadmap.md")
t = p.read_text(encoding="utf-8")

# Spot-check a few remainders by reconstructing UTF-8 from mojibake-as-cp437.
def via_cp437(s: str) -> str:
    try:
        return s.encode("cp437").decode("utf-8")
    except Exception as e:
        return f"ERR:{e}"


samples = [
    "Γê¥",
    "ΓëÑ",
    "┬░",
    "Γêê",
    "┬▒",
    "Γåö",
    "Γê₧",
    "Γåô",
    "Γåæ",
    "ΓùÅ",
    "Γùå",
    "r╠é",
    "ß╕₧",
    "┬╜",
    "┬│",
    "Γê¥RPM",
    "QΓê¥n",
    "VΓê₧",
    "thrustΓåönoise",
]
decoded = {s: via_cp437(s) for s in samples}

FIX2 = [
    ("Γê¥", "∝"),
    ("ΓëÑ", "≥"),
    ("┬░", "°"),
    ("Γêê", "∈"),
    ("┬▒", "±"),
    ("Γåö", "–"),  # verify via decode
    ("Γê₧", "∞"),
    ("Γåô", "↓"),
    ("Γåæ", "↑"),
    ("ΓùÅ", "△"),  # verify
    ("Γùå", "▲"),  # verify
    ("┬╜", "½"),
    ("┬│", "³"),
    ("W┬│", "W³"),  # if half already fixed separately
    # FW-H formula garble — rewrite whole known phrase if present
]

# Prefer decode-driven map from samples
for s, d in decoded.items():
    if d.startswith("ERR:"):
        continue
    if s in t and len(s) <= 4:
        FIX2.append((s, d))

# Deduplicate preserving order, longer first
seen: set[str] = set()
ordered: list[tuple[str, str]] = []
for a, b in sorted(FIX2, key=lambda x: -len(x[0])):
    if a not in seen and a != b:
        seen.add(a)
        ordered.append((a, b))

for a, b in ordered:
    t = t.replace(a, b)

# Hard fix the FW-H line if still garbled
bad_fwh = "p' = (r╠é · ß╕₧) / (4π cₜ r)"
good_fwh = "p' = (r̂ · Ḟ) / (4π c r)"
if bad_fwh in t:
    t = t.replace(bad_fwh, good_fwh)
# After partial fixes:
for alt in [
    "p' = (r̂ · ß╕₧) / (4π cₜ r)",
    "p' = (r╠é · Ḟ) / (4π cₜ r)",
    "p' = (r╠é · ß╕₧) / (4π c_t r)",
]:
    if alt in t:
        t = t.replace(alt, good_fwh)

# Fix smashed markdown on line ~307 if present
t = t.replace(
    "thrust–noise scatter.- [x] **4.3",
    "thrust–noise scatter.\n- [x] **4.3",
)
t = t.replace(
    "thrust-noise scatter.- [x] **4.3",
    "thrust–noise scatter.\n- [x] **4.3",
)

p.write_text(t, encoding="utf-8", newline="\n")

remain = []
for i, line in enumerate(t.splitlines(), 1):
    if re.search(r"[Γ┬╧╬├ÂÃß╠\u2500-\u257F]", line):
        remain.append({"line": i, "text": line[:220]})

Path("_moji_report2.json").write_text(
    json.dumps(
        {"decoded": decoded, "applied": ordered, "remain": remain},
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
print("remain", len(remain))
