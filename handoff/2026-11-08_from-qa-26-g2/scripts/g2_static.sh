#!/bin/bash
# QA r26 G2 static checks (PREREG_R26_G2 414177a). grep only; run from the snapshot root.
echo "== K3 README required phrases"; for p in "Noise outputs are not validated" "blade-pass tone frequency is exact" "rpm × blades" "estimates for exploration only"; do printf '%s: ' "$p"; grep -c "$p" README.md; done
echo "== K3 README forbidden phrases (expect 0)"; for p in "tone + relative ranking are usable" "relative dB(A) ranking" "relative dB(A)"; do printf '%s: ' "$p"; grep -c "$p" README.md; done
echo "== K3 README noise/dB lines"; grep -n -i "noise\|dB(A)\|dBA" README.md
echo "== K5 fan_flow_report dB-ish (expect none)"; grep -n "dB-ish" fansim/cockpit/fan_flow_report.py || echo none
echo "== K5 a12x25-reference noise lines"; grep -n -i "noise\|dB(A)\|ranks designs" docs/a12x25-reference.md
echo "== K4 fan_tab_ui Optimize noise text"; grep -n "Noise ranking\|absolute dB\|evaluate_noise" fansim/cockpit/fan_tab_ui.py
echo "== K4 cockpit-wide dB(A)/dBA hits (all fansim/cockpit)"; grep -rn "dB(A)\|dBA" fansim/cockpit --include=*.py
echo "== K2 where expert_only is consumed"; grep -rn "expert_only" fansim/cockpit --include=*.py
echo "== info: scripts/ + docs/design-rules.md dB(A)/dBA count"; grep -rln "dB(A)\|dBA" scripts | wc -l; grep -n "dB(A)" docs/design-rules.md
