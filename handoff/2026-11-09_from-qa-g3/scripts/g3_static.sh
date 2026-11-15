#!/bin/bash
# G3 static checks (PREREG 7e3e214). grep only, run from snapshot root.
echo "== G3-7 'honest' anywhere in fansim/ README docs/*.md (user-facing)"; grep -rn -i "honest" fansim --include=*.py | grep -v "^\s*#" ; grep -n -i "honest" README.md docs/*.md
echo "== G3-1 mixed_tab MRF/validated lines"; grep -n "MRF\|validated\|Experimental\|approximate" fansim/cockpit/mixed_tab.py
echo "== G3-2 volute_tab ranking/validated/converged/MRF lines"; grep -n -i "ranking only\|unvalidated\|converged\|MRF\|proxy\|±20" fansim/cockpit/volute_tab.py
echo "== G3-3 app.py tab labels"; grep -n "VTab(\|· estimate\|· experimental\|text=\"" fansim/cockpit/app.py
echo "== G3-6 fan_tab_ui intro (QA-57 :495)"; grep -n "faster estimates\|proxies\|honest" fansim/cockpit/fan_tab_ui.py
echo "== G3-5 README mixed/volute lines"; grep -n -i "mixed\|volute" README.md
