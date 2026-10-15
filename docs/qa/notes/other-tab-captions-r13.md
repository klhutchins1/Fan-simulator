# Other-tab caption inventory (round 13 Task D, filler): report only

Method: AST scan of `mixed_tab.py`, `prop_tab.py`, `volute_tab.py`, `cror_tab.py`, `tab_shell.py` for calls with
`classes` containing `text-caption` whose first argument is a literal string without `{{ }}` (`scripts/d_captions.py`,
`data/d_captions.json`). Captions passed some other way (e.g. `text=`) are not caught. Screens: `screens/d_*_{simple,expert}.png`.
**None of the four tabs respects `ui_mode`.** Each tab's visible text is identical in Simple and Expert (`data/d_shots.json`),
and none of the files mentions `ui_mode`.

Candidates for Expert-only next (always visible, explanatory, > 100 chars):

| file:line | chars | text (start) |
|---|---|---|
| prop_tab.py:1200 | 284 | "CFD refine checks top-N BEMT finalists for direction and sanity (Docke…" |
| mixed_tab.py:763 | 259 | "NSGA on free↔load CFM via the axial BEM stand-in. Not CFD. Assess stil…" |
| prop_tab.py:1357 | 198 | "From the best design of the last CFD refine (open-air MRF; flow patter…" |
| cror_tab.py:834 | 195 | "From the best design of the last CFD refine (dual-MRF). \|U\|/pressure m…" |
| volute_tab.py:782 | 176 | "Y=0 meridional cut of the sealed scroll (not the axial-duct wake crop)…" |
| volute_tab.py:587 | 167 | "90° discharge collector — not an A12x25 drop-in. Assess uses sealed-en…" (keep visible in Simple? it is a fit warning, so needs Kimball copy) |
| mixed_tab.py:877 | 160 | "From the last Assess (axial MRF duct, approximate for mixed-flow). \|U\|…" |
| cror_tab.py:706 | 129 | "Screen counter-rotating stacks for thrust, efficiency, and relative no…" |
| volute_tab.py:690 | 126 | "NSGA ranks impeller + scroll geometry. Assess for honest radial MRF CF…" |
| cror_tab.py:591 | 124 | "Edit front/rear planform, then Preview / Export / Optimize. Optimize i…" |
| prop_tab.py:962 | 122 | "Start here: pick size → tune blade → Analyze (~1 s) → Optimize (option…" (the Fan tab keeps its "Start here" in Simple, so keep this one too) |
| prop_tab.py:1111 | 117 | "Turn on Continue last prop study to append trials into the most recent…" |
| prop_tab.py:1106 | 94 | "Multi-objective BEMT search (~1 s/trial). CFD refine scores top-N fina…" |

Keep in Simple (short, actionable): the export-list lines (mixed 848/855, prop 1311/1325/1332, volute 746/753, cror 798/805)
and prop_tab.py:1073 "Pitch drives twist; expand inner panels…".
