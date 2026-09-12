# app.py — ALL read windows captured in Claude transcripts (real fragments of the GROWN file)

Line numbers shift between windows (file was edited). These are real code slices of the
~2377-line app.py to cross-check/patch the copy you recover from Cursor. Ordered by time.


================================================================================
## window @ 2026-08-26T22:03:38  (lines 1-30)

1	"""Trame design cockpit: browse the design space, click/select a design, view its 3D model.
2	
3	Layout: an interactive Plotly scatter of the evaluated designs (left) beside a live PyVista
4	3D view of the selected impeller and its metrics (right). Selecting a point in the plot -- or
5	via the dropdown -- loads that design's model. This is the foundation for the tweak-and-rerun
6	loop (parameter editor + regression sweep) added next.
7	"""
8	
9	from __future__ import annotations
10	
11	from pathlib import Path
12	
13	import plotly.graph_objects as go
14	import pyvista as pv
15	from pyvista.trame.ui import plotter_ui
16	from trame.app import get_server
17	from trame.ui.vuetify3 import SinglePageLayout
18	from trame.widgets import html
19	from trame.widgets import plotly as plotly_widgets
20	from trame.widgets import vuetify3 as v3
21	
22	from fansim.cockpit.data import feasible_designs, load_designs
23	
24	pv.OFF_SCREEN = True
25	
26	
27	def scatter_figure(designs) -> go.Figure:
28	    xs = [d.objectives["cfm_free"] for d in designs]
29	    ys = [d.objectives["cfm_load"] for d in designs]
30	    cs = [d.objectives["efficiency"] for d in designs]

================================================================================
## window @ 2026-08-26T22:03:41  (lines 55-145)

55	    designs = feasible_designs(load_designs(run_dir, study_name))
56	    by_trial = {d.trial: d for d in designs}
57	    if not designs:
58	        raise SystemExit(f"No feasible designs found in {run_dir}")
59	
60	    server = get_server(client_type="vue3")
61	    state, ctrl = server.state, server.controller
62	
63	    plotter = pv.Plotter()
64	    plotter.background_color = "white"
65	    plotter.add_axes()
66	
67	    state.trial_items = [
68	        {"title": f"trial {d.trial}"
69	                  + ("  ★" if d.is_pareto else ""), "value": d.trial}
70	        for d in sorted(designs, key=lambda d: -d.objectives["cfm_load"])
71	    ]
72	    state.selected_trial = None
73	    state.info_lines = ["Select a design (click a point or use the dropdown)."]
74	    figure = scatter_figure(designs)
75	
76	    def select(trial: int | None):
77	        print(f"[cockpit] select({trial!r})", flush=True)
78	        if trial is None:
79	            return
80	        d = by_trial.get(int(trial))
81	        if d is None:
82	            return
83	        plotter.clear_actors()
84	        if d.has_model:
85	            plotter.add_mesh(pv.read(str(d.stl_path)), color="lightsteelblue",
86	                             smooth_shading=True)
87	            plotter.reset_camera()
88	        o, p = d.objectives, d.params
89	        state.selected_trial = int(trial)
90	        state.info_lines = [
91	            f"Trial {d.trial}   {d.extra.get('n_blades')} blades"
92	            + ("   ★ Pareto" if d.is_pareto else ""),
93	            f"CFM free {o['cfm_free']:.1f}   CFM load {o['cfm_load']:.1f}"
94	            f"   efficiency {o['efficiency']:.1f}%",
95	            f"stagger r/m/t {p.get('stagger_root',0):.0f}/{p.get('stagger_mid',0):.0f}"
96	            f"/{p.get('stagger_tip',0):.0f}   camber {p.get('max_camber',0):.3f}",
97	            f"chord r/m/t {p.get('chord_root',0):.1f}/{p.get('chord_mid',0):.1f}"
98	            f"/{p.get('chord_tip',0):.1f}   sweep m/t {p.get('sweep_mid',0):.1f}"
99	            f"/{p.get('sweep_tip',0):.1f}",
100	        ]
101	        try:
102	            ctrl.view_update()
103	        except Exception:
104	            pass
105	
106	    @state.change("selected_trial")
107	    def _on_dropdown(selected_trial=None, **_):
108	        select(selected_trial)
109	
110	    def on_plotly_click(event=None):
111	        pts = (event or {}).get("points") or []
112	        if pts and pts[0].get("customdata") is not None:
113	            state.selected_trial = int(pts[0]["customdata"])
114	
115	    with SinglePageLayout(server) as layout:
116	        layout.title.set_text("Fan-simulator Cockpit")
117	        with layout.content:
118	            with v3.VContainer(fluid=True, classes="pa-2"):
119	                with v3.VRow(no_gutters=True):
120	                    with v3.VCol(cols=6, classes="pr-2"):
121	                        plotly_widgets.Figure(
122	                            figure=figure,
123	                            click=(on_plotly_click, "[$event]"),
124	                            style="width:100%;",
125	                        )
126	                    with v3.VCol(cols=6):
127	                        with v3.VCard(classes="mb-2 pa-3"):
128	                            v3.VSelect(
129	                                label="Design",
130	                                v_model=("selected_trial",),
131	                                items=("trial_items",),
132	                                density="compact", variant="outlined",
133	                                hide_details=True,
134	                                update_modelValue=(select, "[$event]"),
135	                            )
136	                            html.Div(
137	                                "{{ line }}",
138	                                v_for="line in info_lines",
139	                                classes="text-body-2 mt-2",
140	                            )
141	                        with v3.VCard(style="height:520px;"):
142	                            view = plotter_ui(plotter)
143	    ctrl.view_update = view.update
144	    return server
145

================================================================================
## window @ 2026-08-27T14:12:58  (lines 120-239)

120	
121	    def refresh_items():
122	        alld = sorted(study_designs + user_designs,
123	                      key=lambda d: -d.objectives["cfm_load"])
124	        state.trial_items = [_label(d) for d in alld]
125	
126	    state.selected_trial = None
127	    state.info_lines = ["Select a design (click a point or use the dropdown)."]
128	    state.preview_msg = "Select a design, then edit and press Preview geometry."
129	    state.assess_msg = ""
130	    state.assess_busy = False
131	    state.sweep_param = "max_camber"
132	    state.sweep_steps = 3
133	    refresh_items()
134	
135	    preview_stl = Path(tempfile.gettempdir()) / "fansim_cockpit_preview.stl"
136	
137	    def refresh_figure():
138	        fig = scatter_figure(study_designs, user_designs)
139	        if hasattr(ctrl, "figure_update"):
140	            ctrl.figure_update(fig)
141	
142	    def _init_editor(p: dict, feat: Features | None = None):
143	        """Load the parameter-editor sliders from a design's params + features."""
144	        feat = feat or Features()
145	        state.e_n_blades = int(p.get("n_blades", 7))
146	        state.e_stagger_root = float(p.get("stagger_root", 50.0))
147	        state.e_stagger_mid = float(p.get("stagger_mid", 40.0))
148	        state.e_stagger_tip = float(p.get("stagger_tip", 30.0))
149	        state.e_chord_root = float(p.get("chord_root", 20.0))
150	        state.e_chord_mid = float(p.get("chord_mid", 22.0))
151	        state.e_chord_tip = float(p.get("chord_tip", 18.0))
152	        state.e_camber = float(p.get("max_camber", 0.02))
153	        state.e_sweep_mid = float(p.get("sweep_mid", 2.0))
154	        state.e_sweep_tip = float(p.get("sweep_tip", 6.0))
155	        state.e_tub_amp = feat.tubercle_amp
156	        state.e_tub_waves = feat.tubercle_waves
157	        state.e_ser_amp = feat.serration_amp
158	        state.e_ser_waves = feat.serration_waves
159	        state.e_dim_amp = feat.dimple_amp
160	        state.e_dim_rows = feat.dimple_rows
161	        state.e_dim_cols = feat.dimple_cols
162	
163	    _init_editor({})
164	
165	    def edit_flat() -> dict:
166	        return dict(
167	            n_blades=int(state.e_n_blades),
168	            stagger_root=state.e_stagger_root, stagger_mid=state.e_stagger_mid,
169	            stagger_tip=state.e_stagger_tip, chord_root=state.e_chord_root,
170	            chord_mid=state.e_chord_mid, chord_tip=state.e_chord_tip,
171	            sweep_mid=state.e_sweep_mid, sweep_tip=state.e_sweep_tip,
172	            max_camber=state.e_camber,
173	        )
174	
175	    def edit_features() -> Features:
176	        return Features(
177	            tubercle_amp=state.e_tub_amp, tubercle_waves=int(state.e_tub_waves),
178	            serration_amp=state.e_ser_amp, serration_waves=int(state.e_ser_waves),
179	            dimple_amp=state.e_dim_amp, dimple_rows=int(state.e_dim_rows),
180	            dimple_cols=int(state.e_dim_cols),
181	        )
182	
183	    def build_edit_params():
184	        return blade_from_flat(edit_flat(), edit_features())
185	
186	    def do_preview():
187	        params = build_edit_params()
188	        printable = check_printability(params)
189	        if not printable.printable:
190	            state.preview_msg = f"⚠ Not printable: {printable.reason}"
191	            return
192	        state.preview_msg = "Building preview geometry…"
193	        try:
194	            export_stl(build_impeller(params), preview_stl)
195	        except Exception as exc:  # loft / boolean failure on an extreme edit
196	            state.preview_msg = f"⚠ Geometry failed: {type(exc).__name__}"
197	            return
198	        plotter.clear_actors()
199	        plotter.add_mesh(pv.read(str(preview_stl)), color="darkorange",
200	                         smooth_shading=True)
201	        plotter.reset_camera()
202	        feats = "features ON" if params.features.active else "smooth"
203	        state.preview_msg = (f"Preview (orange): {params.n_blades} blades, "
204	                             f"camber {state.e_camber:.3f}, {feats} — geometry only, "
205	                             f"not yet evaluated. Use 'Assess' to run CFD.")
206	        try:
207	            ctrl.view_update()
208	        except Exception:
209	            pass
210	
211	    # --- Assess (run CFD) + Sweep (regression over one parameter) ---
212	    SWEEP_OPTIONS = [
213	        ("camber", "flat", "max_camber", 0.0, 0.06),
214	        ("blades", "flat", "n_blades", 5.0, 11.0),
215	        ("stagger tip", "flat", "stagger_tip", 20.0, 50.0),
216	        ("sweep tip", "flat", "sweep_tip", 0.0, 15.0),
217	        ("tubercle amp", "tub", "tubercle_amp", 0.0, 0.10),
218	        ("serration amp", "ser", "serration_amp", 0.0, 0.06),
219	        ("dimple depth", "dim", "dimple_amp", 0.0, 0.35),
220	    ]
221	    state.sweep_items = [o[0] for o in SWEEP_OPTIONS]
222	
223	    def _feat_dict() -> dict:
224	        f = edit_features()
225	        return dict(tubercle_amp=f.tubercle_amp, tubercle_waves=f.tubercle_waves,
226	                    serration_amp=f.serration_amp, serration_waves=f.serration_waves,
227	                    dimple_amp=f.dimple_amp, dimple_rows=f.dimple_rows,
228	                    dimple_cols=f.dimple_cols)
229	
230	    def _blocking_eval(params, workdir):
231	        return evaluate_candidate(params, workdir, procs=8, base_cell=0.006, iters=500)
232	
233	    async def _assess(params, flat, label):
234	        tid = next_id[0]
235	        next_id[0] += 1
236	        workdir = assess_dir / f"design_{tid}"
237	        loop = asyncio.get_running_loop()
238	        result = await loop.run_in_executor(None, _blocking_eval, params, workdir)
239	        if not result.feasible:

================================================================================
## window @ 2026-08-27T14:13:57  (lines 400-454)

400	                        )
401	                    with v3.VCol(cols=6):
402	                        with v3.VCard(classes="mb-2 pa-3"):
403	                            v3.VSelect(
404	                                label="Design",
405	                                v_model=("selected_trial",),
406	                                items=("trial_items",),
407	                                density="compact", variant="outlined",
408	                                hide_details=True,
409	                                update_modelValue=(select, "[$event]"),
410	                            )
411	                            html.Div(
412	                                "{{ line }}",
413	                                v_for="line in info_lines",
414	                                classes="text-body-2 mt-2",
415	                            )
416	                        with v3.VCard(classes="mb-2 pa-3"):
417	                            html.Div("Modify design", classes="text-subtitle-2 mb-1")
418	                            with v3.VExpansionPanels(variant="accordion", multiple=True):
419	                                with v3.VExpansionPanel(title="Geometry"):
420	                                    with v3.VExpansionPanelText():
421	                                        _slider("Blades", "e_n_blades", 5, 11, 1)
422	                                        _slider("Camber (curve)", "e_camber", 0.0, 0.06, 0.005)
423	                                        _slider("Stagger root", "e_stagger_root", 15, 70, 1)
424	                                        _slider("Stagger mid", "e_stagger_mid", 15, 70, 1)
425	                                        _slider("Stagger tip", "e_stagger_tip", 15, 70, 1)
426	                                        _slider("Chord root", "e_chord_root", 10, 28, 0.5)
427	                                        _slider("Chord mid", "e_chord_mid", 10, 28, 0.5)
428	                                        _slider("Chord tip", "e_chord_tip", 10, 28, 0.5)
429	                                        _slider("Sweep mid", "e_sweep_mid", -3, 8, 0.5)
430	                                        _slider("Sweep tip", "e_sweep_tip", 0, 15, 0.5)
431	                                with v3.VExpansionPanel(title="Features (bio-inspired)"):
432	                                    with v3.VExpansionPanelText():
433	                                        _slider("Tubercle amp", "e_tub_amp", 0.0, 0.10, 0.01)
434	                                        _slider("Tubercle waves", "e_tub_waves", 0, 8, 1)
435	                                        _slider("Serration amp", "e_ser_amp", 0.0, 0.06, 0.005)
436	                                        _slider("Serration teeth", "e_ser_waves", 0, 12, 1)
437	                                        _slider("Dimple depth", "e_dim_amp", 0.0, 0.35, 0.05)
438	                                        _slider("Dimple rows", "e_dim_rows", 0, 6, 1)
439	                                        _slider("Dimple cols", "e_dim_cols", 0, 6, 1)
440	                            with v3.VRow(no_gutters=True, classes="mt-2"):
441	                                v3.VBtn("Preview geometry", color="primary", size="small",
442	                                        click=(do_preview,), classes="mr-2",
443	                                        disabled=("assess_busy",))
444	                                v3.VBtn("Reset", size="small", variant="tonal",
445	                                        click=(select, "[selected_trial]"))
446	                            html.Div("{{ preview_msg }}", classes="text-caption mt-2")
447	                        with v3.VCard(classes="mb-2 pa-3"):
448	                            html.Div("Assess & sweep (runs CFD)",
449	                                     classes="text-subtitle-2 mb-1")
450	                            v3.VBtn("Assess this design", color="success", size="small",
451	                                    block=True, click=(on_assess,),
452	                                    loading=("assess_busy",), disabled=("assess_busy",))
453	                            with v3.VRow(no_gutters=True, classes="mt-2 align-center"):
454	                                with v3.VCol(cols=6, classes="pr-1"):

================================================================================
## window @ 2026-08-28T01:56:06  (lines 419-458)

419	                                with v3.VExpansionPanel(title="Geometry"):
420	                                    with v3.VExpansionPanelText():
421	                                        _slider("Blades", "e_n_blades", 5, 11, 1)
422	                                        _slider("Camber (curve)", "e_camber", 0.0, 0.06, 0.005)
423	                                        _slider("Stagger root", "e_stagger_root", 15, 55, 1)
424	                                        _slider("Stagger mid", "e_stagger_mid", 15, 55, 1)
425	                                        _slider("Stagger tip", "e_stagger_tip", 15, 55, 1)
426	                                        _slider("Chord root", "e_chord_root", 14, 42, 0.5)
427	                                        _slider("Chord mid", "e_chord_mid", 14, 42, 0.5)
428	                                        _slider("Chord tip", "e_chord_tip", 14, 42, 0.5)
429	                                        _slider("Wrap mid (deg)", "e_lean_mid", 0, 30, 1)
430	                                        _slider("Wrap tip (deg)", "e_lean_tip", 0, 45, 1)
431	                                        _slider("Sweep mid", "e_sweep_mid", -3, 8, 0.5)
432	                                        _slider("Sweep tip", "e_sweep_tip", 0, 15, 0.5)
433	                                with v3.VExpansionPanel(title="Features (bio-inspired)"):
434	                                    with v3.VExpansionPanelText():
435	                                        _slider("Tubercle amp", "e_tub_amp", 0.0, 0.10, 0.01)
436	                                        _slider("Tubercle waves", "e_tub_waves", 0, 8, 1)
437	                                        _slider("Serration amp", "e_ser_amp", 0.0, 0.06, 0.005)
438	                                        _slider("Serration teeth", "e_ser_waves", 0, 12, 1)
439	                                        _slider("Dimple depth", "e_dim_amp", 0.0, 0.35, 0.05)
440	                                        _slider("Dimple rows", "e_dim_rows", 0, 6, 1)
441	                                        _slider("Dimple cols", "e_dim_cols", 0, 6, 1)
442	                            with v3.VRow(no_gutters=True, classes="mt-2"):
443	                                v3.VBtn("Preview geometry", color="primary", size="small",
444	                                        click=(do_preview,), classes="mr-2",
445	                                        loading=("preview_busy",),
446	                                        disabled=("preview_busy || assess_busy",))
447	                                v3.VBtn("Reset", size="small", variant="tonal",
448	                                        click=(select, "[selected_trial]"))
449	                            html.Div("{{ preview_msg }}", classes="text-caption mt-2")
450	                        with v3.VCard(classes="mb-2 pa-3"):
451	                            html.Div("Assess & sweep (runs CFD)",
452	                                     classes="text-subtitle-2 mb-1")
453	                            v3.VBtn("Assess this design", color="success", size="small",
454	                                    block=True, click=(on_assess,),
455	                                    loading=("assess_busy",), disabled=("assess_busy",))
456	                            with v3.VRow(no_gutters=True, classes="mt-2 align-center"):
457	                                with v3.VCol(cols=6, classes="pr-1"):
458	                                    v3.VSelect(label="Sweep", v_model=("sweep_param",),

================================================================================
## window @ 2026-08-28T02:00:13  (lines 143-192)

143	    def _init_editor(p: dict, feat: Features | None = None):
144	        """Load the parameter-editor sliders from a design's params + features."""
145	        feat = feat or Features()
146	        state.e_n_blades = int(p.get("n_blades", 7))
147	        state.e_stagger_root = float(p.get("stagger_root", 26.0))
148	        state.e_stagger_mid = float(p.get("stagger_mid", 26.0))
149	        state.e_stagger_tip = float(p.get("stagger_tip", 22.0))
150	        state.e_chord_root = float(p.get("chord_root", 34.0))
151	        state.e_chord_mid = float(p.get("chord_mid", 44.0))
152	        state.e_chord_tip = float(p.get("chord_tip", 38.0))
153	        state.e_camber = float(p.get("max_camber", 0.05))
154	        state.e_sweep_mid = float(p.get("sweep_mid", 3.0))
155	        state.e_sweep_tip = float(p.get("sweep_tip", 5.0))
156	        state.e_lean_mid = float(p.get("lean_mid", 14.0))  # circumferential WRAP (deg)
157	        state.e_lean_tip = float(p.get("lean_tip", 26.0))
158	        state.e_tub_amp = feat.tubercle_amp
159	        state.e_tub_waves = feat.tubercle_waves
160	        state.e_ser_amp = feat.serration_amp
161	        state.e_ser_waves = feat.serration_waves
162	        state.e_dim_amp = feat.dimple_amp
163	        state.e_dim_rows = feat.dimple_rows
164	        state.e_dim_cols = feat.dimple_cols
165	
166	    _init_editor({})
167	
168	    def edit_flat() -> dict:
169	        return dict(
170	            n_blades=int(state.e_n_blades),
171	            stagger_root=state.e_stagger_root, stagger_mid=state.e_stagger_mid,
172	            stagger_tip=state.e_stagger_tip, chord_root=state.e_chord_root,
173	            chord_mid=state.e_chord_mid, chord_tip=state.e_chord_tip,
174	            sweep_mid=state.e_sweep_mid, sweep_tip=state.e_sweep_tip,
175	            max_camber=state.e_camber,
176	            lean_mid=state.e_lean_mid, lean_tip=state.e_lean_tip,
177	        )
178	
179	    def edit_features() -> Features:
180	        # A feature needs BOTH amplitude and a count to be visible; if the user raises only the
181	        # amplitude slider, auto-fill a sensible count so it actually shows up.
182	        tw = int(state.e_tub_waves) or (6 if state.e_tub_amp > 0 else 0)
183	        sw = int(state.e_ser_waves) or (8 if state.e_ser_amp > 0 else 0)
184	        dr = int(state.e_dim_rows) or (5 if state.e_dim_amp > 0 else 0)
185	        dc = int(state.e_dim_cols) or (5 if state.e_dim_amp > 0 else 0)
186	        return Features(
187	            tubercle_amp=state.e_tub_amp, tubercle_waves=tw,
188	            serration_amp=state.e_ser_amp, serration_waves=sw,
189	            dimple_amp=state.e_dim_amp, dimple_rows=dr, dimple_cols=dc,
190	        )
191	
192	    def build_edit_params():

================================================================================
## window @ 2026-08-28T02:00:47  (lines 58-67)

58	def _slider(label: str, model: str, mn: float, mx: float, step: float):
59	    """Compact labelled slider bound to a state variable (used in the editor panel)."""
60	    v3.VSlider(
61	        v_model=(model,), min=mn, max=mx, step=step, label=label,
62	        thumb_label=True, density="compact", hide_details=True, classes="mb-1",
63	    )
64	
65	
66	def scatter_figure(study_designs, user_designs=()) -> go.Figure:
67	    def trace(designs, name, symbol_pareto, symbol_plain, line):

================================================================================
## window @ 2026-08-28T04:02:21  (lines 200-254)

200	        )
201	
202	    def edit_features() -> Features:
203	        # A feature needs BOTH amplitude and a count to be visible; if the user raises only the
204	        # amplitude slider, auto-fill a sensible count so it actually shows up.
205	        tw = int(state.e_tub_waves) or (6 if state.e_tub_amp > 0 else 0)
206	        sw = int(state.e_ser_waves) or (8 if state.e_ser_amp > 0 else 0)
207	        dr = int(state.e_dim_rows) or (5 if state.e_dim_amp > 0 else 0)
208	        dc = int(state.e_dim_cols) or (5 if state.e_dim_amp > 0 else 0)
209	        return Features(
210	            tubercle_amp=state.e_tub_amp, tubercle_waves=tw,
211	            serration_amp=state.e_ser_amp, serration_waves=sw,
212	            dimple_amp=state.e_dim_amp, dimple_rows=dr, dimple_cols=dc,
213	        )
214	
215	    def build_edit_params():
216	        return blade_from_flat(edit_flat(), edit_features())
217	
218	    def _build_preview_stl(params):
219	        """Blocking geometry build (runs off the event loop)."""
220	        export_stl(build_impeller(params), preview_stl)
221	
222	    def do_preview():
223	        # Async so the "Generating…" indicator shows while the (7-35 s) geometry build runs;
224	        # a synchronous build would freeze the UI with no feedback until it finished.
225	        if state.preview_busy or state.assess_busy:
226	            return
227	        params = build_edit_params()
228	        printable = check_printability(params)
229	        if not printable.printable:
230	            state.preview_msg = f"⚠ Not printable: {printable.reason}"
231	            return
232	
233	        async def task():
234	            state.preview_busy = True
235	            state.preview_msg = "⏳ Generating geometry… (a few seconds)"
236	            state.flush()
237	            loop = asyncio.get_running_loop()
238	            try:
239	                await loop.run_in_executor(None, _build_preview_stl, params)
240	            except Exception as exc:  # loft / boolean failure on an extreme edit
241	                state.preview_msg = f"⚠ Geometry failed: {type(exc).__name__}"
242	                state.preview_busy = False
243	                state.flush()
244	                return
245	            plotter.clear_actors()
246	            plotter.add_mesh(pv.read(str(preview_stl)), color="darkorange",
247	                             smooth_shading=True)
248	            plotter.reset_camera()
249	            feats = "features ON" if params.features.active else "smooth"
250	            state.preview_msg = (f"Preview (orange): {params.n_blades} blades, "
251	                                 f"camber {state.e_camber:.3f}, {feats} — geometry only, "
252	                                 f"not yet evaluated. Use 'Assess' to run CFD.")
253	            state.preview_busy = False
254	            try:

================================================================================
## window @ 2026-08-28T04:19:05  (lines 284-323)

284	    def _feat_dict() -> dict:
285	        f = edit_features()
286	        return dict(tubercle_amp=f.tubercle_amp, tubercle_waves=f.tubercle_waves,
287	                    serration_amp=f.serration_amp, serration_waves=f.serration_waves,
288	                    dimple_amp=f.dimple_amp, dimple_rows=f.dimple_rows,
289	                    dimple_cols=f.dimple_cols)
290	
291	    def _blocking_eval(params, workdir):
292	        return evaluate_candidate(params, workdir, procs=8, base_cell=0.006, iters=500)
293	
294	    async def _assess(params, flat, label):
295	        tid = next_id[0]
296	        next_id[0] += 1
297	        workdir = assess_dir / f"design_{tid}"
298	        loop = asyncio.get_running_loop()
299	        result = await loop.run_in_executor(None, _blocking_eval, params, workdir)
300	        if not result.feasible:
301	            state.assess_msg = f"{label}: rejected — {result.reason}"
302	            state.flush()
303	            return None
304	        stl = workdir / "impeller.stl"
305	        d = Design(
306	            trial=tid, params=dict(flat),
307	            objectives={"cfm_free": result.cfm_free, "cfm_load": result.cfm_load,
308	                        "efficiency": result.efficiency},
309	            feasible=True, is_pareto=False,
310	            stl_path=stl if stl.exists() else None,
311	            extra={"n_blades": params.n_blades, "source": "user"},
312	        )
313	        user_designs.append(d)
314	        by_trial[tid] = d
315	        refresh_items()
316	        refresh_figure()
317	        state.flush()
318	        return d
319	
320	    def on_assess():
321	        if state.assess_busy:
322	            return
323	        params, flat = build_edit_params(), edit_flat()

================================================================================
## window @ 2026-08-28T04:19:20  (lines 320-349)

320	    def on_assess():
321	        if state.assess_busy:
322	            return
323	        params, flat = build_edit_params(), edit_flat()
324	
325	        async def task():
326	            state.assess_busy = True
327	            state.assess_msg = "Running CFD on your design… (~4 min)"
328	            state.flush()
329	            d = await _assess(params, flat, "Assess")
330	            if d:
331	                o = d.objectives
332	                state.assess_msg = (f"Done ◆#{d.trial}: free {o['cfm_free']:.1f}  "
333	                                    f"load {o['cfm_load']:.1f}  eff {o['efficiency']:.1f}%"
334	                                    f"  (added to plot)")
335	                state.selected_trial = d.trial
336	            state.assess_busy = False
337	            state.flush()
338	
339	        asynchronous.create_task(task())
340	
341	    def on_sweep():
342	        if state.assess_busy:
343	            return
344	        import numpy as np
345	
346	        opt = next((o for o in SWEEP_OPTIONS if o[0] == state.sweep_param), SWEEP_OPTIONS[0])
347	        label, kind, field, mn, mx = opt
348	        base_flat, base_feat = edit_flat(), _feat_dict()
349	        steps = max(2, int(state.sweep_steps))

================================================================================
## window @ 2026-08-28T05:30:04  (lines 386-421)

386	    def select(trial: int | None):
387	        print(f"[cockpit] select({trial!r})", flush=True)
388	        if trial is None:
389	            return
390	        d = by_trial.get(int(trial))
391	        if d is None:
392	            return
393	        plotter.clear_actors()
394	        if d.has_model:
395	            plotter.add_mesh(pv.read(str(d.stl_path)), color="lightsteelblue",
396	                             smooth_shading=True)
397	            plotter.reset_camera()
398	        o, p = d.objectives, d.params
399	        state.selected_trial = int(trial)
400	        state.info_lines = [
401	            f"Trial {d.trial}   {d.extra.get('n_blades')} blades"
402	            + ("   ★ Pareto" if d.is_pareto else ""),
403	            f"CFM free {o['cfm_free']:.1f}   CFM load {o['cfm_load']:.1f}"
404	            f"   efficiency {o['efficiency']:.1f}%",
405	            f"stagger r/m/t {p.get('stagger_root',0):.0f}/{p.get('stagger_mid',0):.0f}"
406	            f"/{p.get('stagger_tip',0):.0f}   camber {p.get('max_camber',0):.3f}",
407	            f"chord r/m/t {p.get('chord_root',0):.1f}/{p.get('chord_mid',0):.1f}"
408	            f"/{p.get('chord_tip',0):.1f}   sweep m/t {p.get('sweep_mid',0):.1f}"
409	            f"/{p.get('sweep_tip',0):.1f}",
410	        ]
411	        _init_editor(p)  # load the editor sliders from the selected design
412	        state.preview_msg = "Edit the sliders below, then press Preview geometry."
413	        try:
414	            ctrl.view_update()
415	        except Exception:
416	            pass
417	
418	    @state.change("selected_trial")
419	    def _on_dropdown(selected_trial=None, **_):
420	        select(selected_trial)
421

================================================================================
## window @ 2026-08-28T14:20:33  (lines 128-139)

128	def build_server(run_dir: str | Path, study_name: str | None = None):
129	    run_dir = Path(run_dir)
130	    study_designs = feasible_designs(load_designs(run_dir, study_name))
131	    user_designs: list[Design] = []
132	    by_trial = {d.trial: d for d in study_designs}
133	    if not study_designs:
134	        raise SystemExit(f"No feasible designs found in {run_dir}")
135	    assess_dir = run_dir / "cockpit_assess"
136	    next_id = [9000]  # ids for user-assessed designs (distinct from study trials)
137	
138	    server = get_server(client_type="vue3")
139	    state, ctrl = server.state, server.controller

================================================================================
## window @ 2026-08-28T14:21:03  (lines 334-353)

334	                    dimple_cols=f.dimple_cols)
335	
336	    def _blocking_eval(params, workdir):
337	        return evaluate_candidate(params, workdir, procs=8, base_cell=0.006, iters=500)
338	
339	    async def _assess(params, flat, label):
340	        tid = next_id[0]
341	        next_id[0] += 1
342	        workdir = assess_dir / f"design_{tid}"
343	        loop = asyncio.get_running_loop()
344	        result = await loop.run_in_executor(None, _blocking_eval, params, workdir)
345	        if not result.feasible:
346	            state.assess_msg = f"{label}: rejected — {result.reason}"
347	            state.flush()
348	            return None
349	        stl = workdir / "impeller.stl"
350	        d = Design(
351	            trial=tid, params=dict(flat),
352	            objectives={"cfm_free": result.cfm_free, "cfm_load": result.cfm_load,
353	                        "efficiency": result.efficiency},

================================================================================
## window @ 2026-08-28T14:21:06  (lines 354-365)

354	            feasible=True, is_pareto=False,
355	            stl_path=stl if stl.exists() else None,
356	            extra={"n_blades": params.n_blades, "source": "user"},
357	        )
358	        user_designs.append(d)
359	        by_trial[tid] = d
360	        refresh_items()
361	        refresh_figure()
362	        state.flush()
363	        return d
364	
365	    def on_assess():

================================================================================
## window @ 2026-08-28T14:37:59  (lines 343-387)

343	        loop = asyncio.get_running_loop()
344	        result = await loop.run_in_executor(None, _blocking_eval, params, workdir)
345	        if not result.feasible:
346	            state.assess_msg = f"{label}: rejected — {result.reason}"
347	            state.flush()
348	            return None
349	        stl = workdir / "impeller.stl"
350	        d = Design(
351	            trial=tid, params=dict(flat),
352	            objectives={"cfm_free": result.cfm_free, "cfm_load": result.cfm_load,
353	                        "efficiency": result.efficiency},
354	            feasible=True, is_pareto=False,
355	            stl_path=stl if stl.exists() else None,
356	            extra={"n_blades": params.n_blades, "source": "user"},
357	        )
358	        # persist so the design survives a cockpit restart (reloaded by _load_assessed_designs)
359	        try:
360	            (workdir / "design.json").write_text(json.dumps(
361	                {"trial": d.trial, "params": d.params, "objectives": d.objectives,
362	                 "feasible": True, "reason": d.reason, "extra": d.extra}, indent=2))
363	        except Exception:  # noqa: BLE001 - persistence is best-effort; keep the in-memory design
364	            pass
365	        user_designs.append(d)
366	        by_trial[tid] = d
367	        refresh_items()
368	        refresh_figure()
369	        state.flush()
370	        return d
371	
372	    def on_assess():
373	        if state.assess_busy:
374	            return
375	        # store features alongside geometry so an assessed design's settings reload when reselected
376	        params, flat = build_edit_params(), {**edit_flat(), **_feat_dict()}
377	
378	        async def task():
379	            state.assess_busy = True
380	            state.assess_msg = "Running CFD on your design… (~4 min)"
381	            state.flush()
382	            d = await _assess(params, flat, "Assess")
383	            if d:
384	                o = d.objectives
385	                state.assess_msg = (f"Done ◆#{d.trial}: free {o['cfm_free']:.1f}  "
386	                                    f"load {o['cfm_load']:.1f}  eff {o['efficiency']:.1f}%"
387	                                    f"  (added to plot)")

================================================================================
## window @ 2026-08-28T14:38:41  (lines 389-402)

389	        async def task():
390	            state.assess_busy = True
391	            state.assess_msg = "Running CFD on your design… (~4 min)"
392	            state.flush()
393	            d = await _assess(params, flat, "Assess")
394	            if d:
395	                o = d.objectives
396	                state.assess_msg = (f"Done ◆#{d.trial}: free {o['cfm_free']:.1f}  "
397	                                    f"load {o['cfm_load']:.1f}  eff {o['efficiency']:.1f}%"
398	                                    f"  (added to plot)")
399	                state.selected_trial = d.trial
400	            state.assess_busy = False
401	            state.flush()
402

================================================================================
## window @ 2026-08-28T14:39:05  (lines 180-185)

180	    state.selected_trial = None
181	    state.info_lines = ["Select a design (click a point or use the dropdown)."]
182	    state.preview_msg = "Select a design, then edit and press Preview geometry."
183	    state.preview_busy = False
184	    state.assess_msg = ""
185	    state.assess_busy = False

================================================================================
## window @ 2026-08-28T14:39:24  (lines 593-602)

593	                        with v3.VCard(classes="mb-2 pa-3"):
594	                            html.Div("Assess & sweep (runs CFD)",
595	                                     classes="text-subtitle-2 mb-1")
596	                            v3.VBtn("Assess this design", color="success", size="small",
597	                                    block=True, click=(on_assess,),
598	                                    loading=("assess_busy",), disabled=("assess_busy",))
599	                            with v3.VRow(no_gutters=True, classes="mt-2 align-center"):
600	                                with v3.VCol(cols=6, classes="pr-1"):
601	                                    v3.VSelect(label="Sweep", v_model=("sweep_param",),
602	                                               items=("sweep_items",), density="compact",

================================================================================
## window @ 2026-08-28T14:39:51  (lines 489-499)

489	        state.info_lines = [
490	            f"Trial {d.trial}   {d.extra.get('n_blades')} blades"
491	            + ("   ★ Pareto" if d.is_pareto else ""),
492	            f"CFM free {o['cfm_free']:.1f}   CFM load {o['cfm_load']:.1f}"
493	            f"   efficiency {o['efficiency']:.1f}%",
494	            f"stagger r/m/t {p.get('stagger_root',0):.0f}/{p.get('stagger_mid',0):.0f}"
495	            f"/{p.get('stagger_tip',0):.0f}   camber {p.get('max_camber',0):.3f}",
496	            f"chord r/m/t {p.get('chord_root',0):.1f}/{p.get('chord_mid',0):.1f}"
497	            f"/{p.get('chord_tip',0):.1f}   sweep m/t {p.get('sweep_mid',0):.1f}"
498	            f"/{p.get('sweep_tip',0):.1f}",
499	        ]

================================================================================
## window @ 2026-08-28T15:10:16  (lines 625-648)

625	                                with v3.VCol(cols=8, classes="pr-1"):
626	                                    v3.VSelect(label="Fan model", v_model=("fan_model",),
627	                                               items=("fan_models",), density="compact",
628	                                               hide_details=True)
629	                                with v3.VCol(cols=4):
630	                                    v3.VBtn("Reload", size="x-small", variant="tonal",
631	                                            click=(reload_models,))
632	                            html.Div("{{ model_info }}", classes="text-caption my-1")
633	                            html.Div("Leeway — allow exceeding nominal (flagged over-spec):",
634	                                     classes="text-caption mt-1")
635	                            _slider("Tip past frame (mm)", "lee_tip", 0, 10, 0.5)
636	                            _slider("Extra depth Z (mm)", "lee_depth", 0, 12, 0.5)
637	                            _slider("Over-voltage (V)", "lee_overvolt", 0, 12, 0.5)
638	                            _slider("Extra weight (g)", "lee_weight", 0, 40, 1)
639	                        with v3.VCard(classes="mb-2 pa-3"):
640	                            html.Div("Assess & sweep (runs CFD)",
641	                                     classes="text-subtitle-2 mb-1")
642	                            v3.VBtn("Assess this design", color="success", size="small",
643	                                    block=True, click=(on_assess,),
644	                                    loading=("assess_busy",), disabled=("assess_busy",))
645	                            with v3.VRow(no_gutters=True, classes="mt-2 align-center"):
646	                                with v3.VCol(cols=6, classes="pr-1"):
647	                                    v3.VSelect(label="Sweep", v_model=("sweep_param",),
648	                                               items=("sweep_items",), density="compact",

================================================================================
## window @ 2026-08-28T15:10:19  (lines 620-625)

620	                                        click=(select, "[selected_trial]"))
621	                            html.Div("{{ preview_msg }}", classes="text-caption mt-2")
622	                        with v3.VCard(classes="mb-2 pa-3"):
623	                            html.Div("Fan model & leeway", classes="text-subtitle-2 mb-1")
624	                            with v3.VRow(no_gutters=True, classes="align-center"):
625	                                with v3.VCol(cols=8, classes="pr-1"):

================================================================================
## window @ 2026-08-28T15:42:37  (lines 318-333)

318	        featured build can't take down the cockpit server — it surfaces as a caught error)."""
319	        from fansim.geometry.isolated import build_stl_isolated
320	        build_stl_isolated(flat, feat, preview_stl, timeout=120.0)
321	
322	    def do_preview():
323	        # Async so the "Generating…" indicator shows while the (7-35 s) geometry build runs;
324	        # a synchronous build would freeze the UI with no feedback until it finished.
325	        if state.preview_busy or state.assess_busy:
326	            return
327	        params = build_edit_params()
328	        printable = check_printability(params)
329	        if not printable.printable:
330	            state.preview_msg = f"⚠ Not printable: {printable.reason}"
331	            return
332	        flat, feat = edit_flat(), edit_features()  # serializable inputs for the isolated build
333

================================================================================
## window @ 2026-08-28T15:42:39  (lines 348-365)

348	            except Exception as exc:  # loft/boolean failure or isolated native crash — app survives
349	                state.preview_msg = f"⚠ Geometry failed: {type(exc).__name__} (the app is fine)"
350	                state.preview_busy = False
351	                state.flush()
352	                return
353	            plotter.clear_actors()
354	            plotter.add_mesh(pv.read(str(preview_stl)), color="darkorange",
355	                             smooth_shading=True)
356	            plotter.reset_camera()
357	            feats = "features ON" if params.features.active else "smooth"
358	            state.preview_msg = (f"Preview (orange): {params.n_blades} blades, "
359	                                 f"camber {state.e_camber:.3f}, {feats} — geometry only, "
360	                                 f"not yet evaluated. Use 'Assess' to run CFD.")
361	            state.preview_busy = False
362	            try:
363	                ctrl.view_update()
364	            except Exception:
365	                pass

================================================================================
## window @ 2026-08-28T16:11:06  (lines 59-94)

59	)
60	from fansim.geometry import build_impeller, export_stl
61	from fansim.geometry.features import Features
62	from fansim.manufacturability import check_printability
63	from fansim.optimize.objectives import evaluate_candidate
64	from fansim.optimize.search_space import blade_from_flat
65	
66	pv.OFF_SCREEN = True
67	
68	
69	def _slider(label: str, model: str, mn: float, mx: float, step: float):
70	    """Compact labelled slider bound to a state variable (used in the editor panel)."""
71	    v3.VSlider(
72	        v_model=(model,), min=mn, max=mx, step=step, label=label,
73	        thumb_label=True, density="compact", hide_details=True, classes="mb-1",
74	    )
75	
76	
77	# Plain-English "map" of what each control does + its performance effect (shown in a help panel).
78	CONTROL_HELP = [
79	    ("Blades", "How many blades. More = more airflow & pressure, but louder and less efficient."),
80	    ("Camber (curve)", "How curved each blade section is. More camber turns the air harder "
81	                       "(more pressure) but too much hurts efficiency."),
82	    ("Stagger root/mid/tip", "Blade pitch angle at hub / mid / tip. Higher = more axial (flow-through); "
83	                             "lower = blades overlap more (pressure)."),
84	    ("Chord root/mid/tip", "Blade width at hub / mid / tip. Wider = more blade area / solidity "
85	                           "(pressure), but heavier and lower efficiency."),
86	    ("Wrap mid/tip (deg)", "Circumferential lean — wraps the blades around the axis so they overlap "
87	                           "like a real fan (0 = a flat radial paddle)."),
88	    ("Sweep mid/tip", "Axial position of the WHOLE section (forward/back rake of the blade)."),
89	    ("LE curve mid/tip (mm)", "Rakes only the LEADING edge forward/back, curving the leading-edge "
90	                              "line without moving the trailing edge. 0 = the flat default LE."),
91	    ("Hub radius (mm)", "Size of the central hub. Bigger hub = smaller flow annulus (less airflow) "
92	                        "but more room for the motor; must fit the fan model's hub-diameter limits."),
93	    ("Camber position", "Where the max camber sits along the chord (0.2=near LE, 0.6=aft). Shifts "
94	                        "the loading fore/aft."),

================================================================================
## window @ 2026-08-28T16:11:10  (lines 94-111)

94	                        "the loading fore/aft."),
95	    ("Thickness root/mid/tip", "Blade thickness (fraction of chord) at hub/mid/tip. Thicker = stronger "
96	                               "/ more printable but heavier and less efficient; thin tips can drop "
97	                               "below the min printable wall."),
98	    ("Uneven spacing", "Spreads the blades to UNEVEN (but still balanced) angles to smear the "
99	                       "blade-pass tone. 0 = evenly spaced. Higher = more tone-spreading."),
100	    ("Tubercle amp/waves", "Bumpy leading edge (humpback-whale flipper) — delays stall."),
101	    ("Serration amp/teeth", "Sawtooth trailing edge (owl wing) — reduces edge noise."),
102	    ("Dimple depth/rows/cols", "Golf-ball-style surface dimples — texture the blade surface."),
103	]
104	
105	
106	def scatter_figure(study_designs, user_designs=()) -> go.Figure:
107	    def trace(designs, name, symbol_pareto, symbol_plain, line):
108	        return go.Scatter(
109	            x=[d.objectives["cfm_free"] for d in designs],
110	            y=[d.objectives["cfm_load"] for d in designs],
111	            mode="markers", name=name,

================================================================================
## window @ 2026-08-28T16:12:19  (lines 631-646)

631	                            html.Div("Modify design", classes="text-subtitle-2 mb-1")
632	                            with v3.VExpansionPanels(variant="accordion", multiple=True):
633	                                with v3.VExpansionPanel(title="ℹ What these controls do"):
634	                                    with v3.VExpansionPanelText():
635	                                        for _term, _desc in CONTROL_HELP:
636	                                            with v3.VRow(no_gutters=True, classes="mb-1"):
637	                                                with v3.VCol(cols=5):
638	                                                    html.Span(_term,
639	                                                              classes="text-caption font-weight-bold")
640	                                                with v3.VCol(cols=7):
641	                                                    html.Span(_desc, classes="text-caption")
642	                                with v3.VExpansionPanel(title="Geometry"):
643	                                    with v3.VExpansionPanelText():
644	                                        _slider("Blades", "e_n_blades", 5, 11, 1)
645	                                        _slider("Camber (curve)", "e_camber", 0.0, 0.06, 0.005)
646	                                        _slider("Stagger root", "e_stagger_root", 15, 55, 1)

================================================================================
## window @ 2026-08-28T16:52:48  (lines 371-392)

371	            stagger_tip=state.e_stagger_tip, chord_root=state.e_chord_root,
372	            chord_mid=state.e_chord_mid, chord_tip=state.e_chord_tip,
373	            sweep_mid=state.e_sweep_mid, sweep_tip=state.e_sweep_tip,
374	            max_camber=state.e_camber, camber_pos=state.e_camber_pos,
375	            lean_mid=state.e_lean_mid, lean_tip=state.e_lean_tip,
376	            le_sweep_mid=state.e_le_mid, le_sweep_tip=state.e_le_tip,
377	            hub_radius=state.e_hub_radius,
378	            thickness_root=state.e_thick_root, thickness_mid=state.e_thick_mid,
379	            thickness_tip=state.e_thick_tip,
380	            spacing_spread=state.e_spacing, spacing_seed=0,
381	        )
382	
383	    def edit_features() -> Features:
384	        # A feature needs BOTH amplitude and a count to be visible; if the user raises only the
385	        # amplitude slider, auto-fill a sensible count so it actually shows up.
386	        tw = int(state.e_tub_waves) or (6 if state.e_tub_amp > 0 else 0)
387	        sw = int(state.e_ser_waves) or (8 if state.e_ser_amp > 0 else 0)
388	        dr = int(state.e_dim_rows) or (5 if state.e_dim_amp > 0 else 0)
389	        dc = int(state.e_dim_cols) or (5 if state.e_dim_amp > 0 else 0)
390	        return Features(
391	            tubercle_amp=state.e_tub_amp, tubercle_waves=tw,
392	            serration_amp=state.e_ser_amp, serration_waves=sw,

================================================================================
## window @ 2026-08-28T16:52:56  (lines 479-498)

479	    def spec_status(stl_path, params):
480	        """Check the BUILT geometry against the active fan model (envelope/hub/depth/weight) with NO
481	        CFD -- lets us flag an out-of-spec design at Preview instead of after an Assess."""
482	        spec = active_spec()
483	        try:
484	            import trimesh
485	            m = trimesh.load(str(stl_path))
486	            (xmin, ymin, zmin), (xmax, ymax, zmax) = m.bounds
487	            dia = 2.0 * max(abs(xmin), abs(xmax), abs(ymin), abs(ymax))
488	            depth = zmax - zmin
489	            weight = estimate_weight_g(abs(float(m.volume)), spec.material)
490	        except Exception:  # noqa: BLE001 - if we can't measure it, don't block
491	            return True, ""
492	        ok, reason = check_build(spec, dia, 2.0 * params.hub_radius, depth, weight)
493	        if not ok:
494	            return False, f"⚠ Out of spec — Assess will reject: {reason}. {_reject_hint(reason)}"
495	        over = over_spec_flags(spec, dia, depth, weight)
496	        if over:
497	            return True, "⚠ OVER-SPEC (allowed via leeway): " + "; ".join(over)
498	        return True, f"✓ fits {spec.name} (dia {dia:.0f} mm, depth {depth:.0f} mm, {weight:.0f} g)"

================================================================================
## window @ 2026-08-28T17:59:30  (lines 505-634)

505	            return True, ""
506	        ok, reason = check_build(spec, dia, 2.0 * params.hub_radius, depth, weight)
507	        depth_msg = _depth_driver_msg(flat) if (flat and "depth" in reason.lower()) else ""
508	        if not ok:
509	            return False, f"⚠ Out of spec — Assess will reject: {reason}. {_reject_hint(reason)}{depth_msg}"
510	        over = over_spec_flags(spec, dia, depth, weight)
511	        if over:
512	            dm = _depth_driver_msg(flat) if (flat and any("depth" in o for o in over)) else ""
513	            return True, "⚠ OVER-SPEC (allowed via leeway): " + "; ".join(over) + dm
514	        return True, f"✓ fits {spec.name} (dia {dia:.0f} mm, depth {depth:.0f} mm, {weight:.0f} g)"
515	
516	    def _blocking_eval(params, workdir):
517	        return evaluate_candidate(params, workdir, procs=8, base_cell=0.006, iters=500,
518	                                  spec=active_spec())
519	
520	    async def _assess(params, flat, label):
521	        tid = next_id[0]
522	        next_id[0] += 1
523	        workdir = assess_dir / f"design_{tid}"
524	        loop = asyncio.get_running_loop()
525	        result = await loop.run_in_executor(None, _blocking_eval, params, workdir)
526	        if not result.feasible:
527	            hint = _reject_hint(result.reason)
528	            state.assess_msg = f"{label}: rejected — {result.reason}" + (f"\n{hint}" if hint else "")
529	            state.flush()
530	            return None
531	        stl = workdir / "impeller.stl"
532	        d = Design(
533	            trial=tid, params=dict(flat),
534	            objectives={"cfm_free": result.cfm_free, "cfm_load": result.cfm_load,
535	                        "efficiency": result.efficiency},
536	            feasible=True, is_pareto=False,
537	            stl_path=stl if stl.exists() else None,
538	            extra={"n_blades": params.n_blades, "source": "user",
539	                   "over_spec": list(result.over_spec), "fan_model": state.fan_model,
540	                   "actual_rpm": round(result.actual_rpm)},
541	        )
542	        # persist so the design survives a cockpit restart (reloaded by _load_assessed_designs)
543	        try:
544	            (workdir / "design.json").write_text(json.dumps(
545	                {"trial": d.trial, "params": d.params, "objectives": d.objectives,
546	                 "feasible": True, "reason": d.reason, "extra": d.extra}, indent=2))
547	        except Exception:  # noqa: BLE001 - persistence is best-effort; keep the in-memory design
548	            pass
549	        user_designs.append(d)
550	        by_trial[tid] = d
551	        refresh_items()
552	        refresh_figure()
553	        state.flush()
554	        return d
555	
556	    def on_assess():
557	        if state.assess_busy:
558	            return
559	        # store features alongside geometry so an assessed design's settings reload when reselected
560	        params, flat = build_edit_params(), {**edit_flat(), **_feat_dict()}
561	
562	        async def task():
563	            state.assess_busy = True
564	            state.assess_msg = "Running CFD on your design… (~4 min)"
565	            state.flush()
566	            d = await _assess(params, flat, "Assess")
567	            if d:
568	                o = d.objectives
569	                over = d.extra.get("over_spec") or []
570	                tag = ("  ⚠ OVER-SPEC: " + "; ".join(over)) if over else ""
571	                spec = get_fan_spec(d.extra.get("fan_model", "a12x25"))
572	                rpm = d.extra.get("actual_rpm", 0)
573	                rpm_tag = (f"  ⚙ motor-limited: {rpm:.0f} RPM ({100*rpm/spec.rpm:.0f}%)"
574	                           if rpm and rpm < spec.rpm * 0.995 else "")
575	                state.assess_msg = (f"Done ◆#{d.trial}: free {o['cfm_free']:.1f}  "
576	                                    f"load {o['cfm_load']:.1f}  eff {o['efficiency']:.1f}%"
577	                                    f"  (added to plot){rpm_tag}{tag}")
578	                state.selected_trial = d.trial
579	            state.assess_busy = False
580	            state.flush()
581	
582	        asynchronous.create_task(task())
583	
584	    def on_sweep():
585	        if state.assess_busy:
586	            return
587	        import numpy as np
588	
589	        opt = next((o for o in SWEEP_OPTIONS if o[0] == state.sweep_param), SWEEP_OPTIONS[0])
590	        label, kind, field, mn, mx = opt
591	        base_flat, base_feat = edit_flat(), _feat_dict()
592	        steps = max(2, int(state.sweep_steps))
593	        raw = list(np.linspace(mn, mx, steps))
594	        values = sorted(set(int(round(v)) for v in raw)) if field == "n_blades" else raw
595	
596	        async def task():
597	            state.assess_busy = True
598	            done = 0
599	            for i, val in enumerate(values):
600	                flat, feat = dict(base_flat), dict(base_feat)
601	                if kind == "flat":
602	                    flat[field] = int(val) if field == "n_blades" else float(val)
603	                else:
604	                    feat[field] = float(val)
605	                    if kind == "tub" and feat["tubercle_waves"] == 0:
606	                        feat["tubercle_waves"] = 6
607	                    if kind == "ser" and feat["serration_waves"] == 0:
608	                        feat["serration_waves"] = 8
609	                    if kind == "dim":
610	                        feat["dimple_rows"] = feat["dimple_rows"] or 5
611	                        feat["dimple_cols"] = feat["dimple_cols"] or 5
612	                params = blade_from_flat(flat, Features(**feat))
613	                state.assess_msg = f"Sweep {label} {i+1}/{len(values)} = {val:g}: running CFD…"
614	                state.flush()
615	                if not check_printability(params).printable:
616	                    continue
617	                if await _assess(params, flat, f"sweep {label}={val:g}"):
618	                    done += 1
619	            state.assess_msg = f"Sweep of {label} done: {done} ◆ runs added to the plot."
620	            state.assess_busy = False
621	            state.flush()
622	
623	        asynchronous.create_task(task())
624	
625	    def select(trial: int | None):
626	        print(f"[cockpit] select({trial!r})", flush=True)
627	        if trial is None:
628	            return
629	        d = by_trial.get(int(trial))
630	        if d is None:
631	            return
632	        plotter.clear_actors()
633	        if d.has_model:
634	            plotter.add_mesh(pv.read(str(d.stl_path)), color="lightsteelblue",

================================================================================
## window @ 2026-08-28T18:03:36  (lines 60-67)

60	from fansim.geometry import build_impeller, export_stl
61	from fansim.geometry.features import Features
62	from fansim.manufacturability import check_printability
63	from fansim.optimize.objectives import evaluate_candidate
64	from fansim.optimize.search_space import blade_from_flat
65	
66	pv.OFF_SCREEN = True
67

================================================================================
## window @ 2026-08-28T18:53:45  (lines 333-412)

333	    def _init_editor(p: dict, feat: Features | None = None):
334	        """Load the parameter-editor sliders from a design's params + features."""
335	        feat = feat or Features()
336	        state.e_n_blades = int(p.get("n_blades", 7))
337	        state.e_stagger_root = float(p.get("stagger_root", 26.0))
338	        state.e_stagger_mid = float(p.get("stagger_mid", 26.0))
339	        state.e_stagger_tip = float(p.get("stagger_tip", 22.0))
340	        state.e_chord_root = float(p.get("chord_root", 34.0))
341	        state.e_chord_mid = float(p.get("chord_mid", 44.0))
342	        state.e_chord_tip = float(p.get("chord_tip", 38.0))
343	        state.e_camber = float(p.get("max_camber", 0.05))
344	        state.e_sweep_mid = float(p.get("sweep_mid", 3.0))
345	        state.e_sweep_tip = float(p.get("sweep_tip", 5.0))
346	        state.e_lean_mid = float(p.get("lean_mid", 14.0))  # circumferential WRAP (deg)
347	        state.e_lean_tip = float(p.get("lean_tip", 26.0))
348	        state.e_le_mid = float(p.get("le_sweep_mid", 0.0))  # leading-edge curve (mm)
349	        state.e_le_tip = float(p.get("le_sweep_tip", 0.0))
350	        state.e_hub_radius = float(p.get("hub_radius", 21.5))       # hub radius (mm)
351	        state.e_tip_radius = float(p.get("tip_radius", 56.5))       # tip radius = blade length (mm)
352	        state.e_thick_root = float(p.get("thickness_root", 0.10))   # blade thickness (frac chord)
353	        state.e_thick_mid = float(p.get("thickness_mid", 0.08))
354	        state.e_thick_tip = float(p.get("thickness_tip", 0.06))
355	        state.e_camber_pos = float(p.get("camber_pos", 0.4))        # max-camber chordwise position
356	        state.e_spacing = float(p.get("spacing_spread", 0.0))       # uneven-spacing spread (0=even)
357	        # Load feature sliders from the design's params (feature-enabled runs + assessed designs
358	        # store them there), falling back to the passed Features. This is why selecting a featured
359	        # result now shows its bio-feature settings instead of resetting them to zero.
360	        state.e_tub_amp = float(p.get("tubercle_amp", feat.tubercle_amp))
361	        state.e_tub_waves = int(p.get("tubercle_waves", feat.tubercle_waves))
362	        state.e_ser_amp = float(p.get("serration_amp", feat.serration_amp))
363	        state.e_ser_waves = int(p.get("serration_waves", feat.serration_waves))
364	        state.e_dim_amp = float(p.get("dimple_amp", feat.dimple_amp))
365	        state.e_dim_rows = int(p.get("dimple_rows", feat.dimple_rows))
366	        state.e_dim_cols = int(p.get("dimple_cols", feat.dimple_cols))
367	
368	    _init_editor({})
369	
370	    def edit_flat() -> dict:
371	        return dict(
372	            n_blades=int(state.e_n_blades),
373	            stagger_root=state.e_stagger_root, stagger_mid=state.e_stagger_mid,
374	            stagger_tip=state.e_stagger_tip, chord_root=state.e_chord_root,
375	            chord_mid=state.e_chord_mid, chord_tip=state.e_chord_tip,
376	            sweep_mid=state.e_sweep_mid, sweep_tip=state.e_sweep_tip,
377	            max_camber=state.e_camber, camber_pos=state.e_camber_pos,
378	            lean_mid=state.e_lean_mid, lean_tip=state.e_lean_tip,
379	            le_sweep_mid=state.e_le_mid, le_sweep_tip=state.e_le_tip,
380	            hub_radius=state.e_hub_radius, tip_radius=state.e_tip_radius,
381	            thickness_root=state.e_thick_root, thickness_mid=state.e_thick_mid,
382	            thickness_tip=state.e_thick_tip,
383	            spacing_spread=state.e_spacing, spacing_seed=0,
384	        )
385	
386	    def edit_features() -> Features:
387	        # A feature needs BOTH amplitude and a count to be visible; if the user raises only the
388	        # amplitude slider, auto-fill a sensible count so it actually shows up.
389	        tw = int(state.e_tub_waves) or (6 if state.e_tub_amp > 0 else 0)
390	        sw = int(state.e_ser_waves) or (8 if state.e_ser_amp > 0 else 0)
391	        dr = int(state.e_dim_rows) or (5 if state.e_dim_amp > 0 else 0)
392	        dc = int(state.e_dim_cols) or (5 if state.e_dim_amp > 0 else 0)
393	        return Features(
394	            tubercle_amp=state.e_tub_amp, tubercle_waves=tw,
395	            serration_amp=state.e_ser_amp, serration_waves=sw,
396	            dimple_amp=state.e_dim_amp, dimple_rows=dr, dimple_cols=dc,
397	        )
398	
399	    def build_edit_params():
400	        return blade_from_flat(edit_flat(), edit_features())
401	
402	    def _build_preview_stl(flat, feat):
403	        """Blocking geometry build in an ISOLATED subprocess (a native OCP crash or a runaway
404	        featured build can't take down the cockpit server — it surfaces as a caught error)."""
405	        from fansim.geometry.isolated import build_stl_isolated
406	        build_stl_isolated(flat, feat, preview_stl, timeout=120.0)
407	
408	    def do_preview():
409	        # Async so the "Generating…" indicator shows while the (7-35 s) geometry build runs;
410	        # a synchronous build would freeze the UI with no feedback until it finished.
411	        if state.preview_busy or state.assess_busy:
412	            return

================================================================================
## window @ 2026-08-28T18:54:15  (lines 240-334)

240	def _load_assessed_designs(assess_dir: Path) -> list[Design]:
241	    """Reload designs the user assessed in earlier cockpit sessions (persisted as design.json)."""
242	    out: list[Design] = []
243	    if not assess_dir.exists():
244	        return out
245	    for jf in sorted(assess_dir.glob("design_*/design.json")):
246	        try:
247	            d = json.loads(jf.read_text())
248	            stl = jf.parent / "impeller.stl"
249	            out.append(Design(
250	                trial=int(d["trial"]), params=d.get("params", {}),
251	                objectives=d["objectives"], feasible=d.get("feasible", True), is_pareto=False,
252	                stl_path=stl if stl.exists() else None,
253	                reason=d.get("reason", ""), extra=d.get("extra", {})))
254	        except Exception:  # noqa: BLE001 - skip a corrupt/partial assess dir
255	            continue
256	    return out
257	
258	
259	def build_server(run_dir: str | Path, study_name: str | None = None):
260	    run_dir = Path(run_dir)
261	    study_designs = feasible_designs(load_designs(run_dir, study_name))
262	    if not study_designs:
263	        raise SystemExit(f"No feasible designs found in {run_dir}")
264	    assess_dir = run_dir / "cockpit_assess"
265	    # Reload previously assessed designs from disk so they SURVIVE a cockpit restart (they used to
266	    # live only in memory and vanished on restart).
267	    user_designs: list[Design] = _load_assessed_designs(assess_dir)
268	    by_trial = {d.trial: d for d in study_designs}
269	    by_trial.update({d.trial: d for d in user_designs})
270	    next_id = [max([9000] + [d.trial + 1 for d in user_designs])]  # continue past reloaded ids
271	
272	    server = get_server(client_type="vue3")
273	    state, ctrl = server.state, server.controller
274	    _quiet_connection_reset(server)
275	
276	    plotter = pv.Plotter()
277	    plotter.background_color = "white"
278	    plotter.add_axes()
279	
280	    def _label(d):
281	        tag = "  ★" if d.is_pareto else ("  ◆" if d.trial >= 9000 else "")
282	        return {"title": f"#{d.trial}{tag}", "value": d.trial}
283	
284	    def refresh_items():
285	        alld = sorted(study_designs + user_designs,
286	                      key=lambda d: -d.objectives["cfm_load"])
287	        state.trial_items = [_label(d) for d in alld]
288	
289	    state.selected_trial = None
290	    state.info_lines = ["Select a design (click a point or use the dropdown)."]
291	    state.preview_msg = "Select a design, then edit and press Preview geometry."
292	    state.preview_busy = False
293	    state.assess_msg = ""
294	    state.assess_busy = False
295	    # fan-model constraints + leeway (applied when you Assess). Nominal is never changed; leeway lets
296	    # a design exceed it (flagged over-spec). Import new models by dropping YAML in config/fan_models/.
297	    state.fan_model = "a12x25"
298	    state.fan_models = fan_spec_names()
299	    state.lee_tip = 0.0
300	    state.lee_depth = 0.0
301	    state.lee_overvolt = 0.0
302	    state.lee_weight = 0.0
303	
304	    def _model_readout():
305	        s = get_fan_spec(state.fan_model)
306	        state.model_info = (f"{s.name}: tip ≤{s.tip_dia_mm[1]:.0f} mm, depth ≤{s.depth_mm[1]:.0f} mm, "
307	                            f"hub {s.hub_dia_mm[0]:.0f}-{s.hub_dia_mm[1]:.0f} mm, "
308	                            f"{s.max_shaft_power_w:.2f} W shaft ({s.voltage_v:.0f} V×{s.max_current_a:.2f} A), "
309	                            f"≤{s.max_weight_g:.0f} g. Published {s.ref_cfm:.0f} CFM / "
310	                            f"{s.ref_static_pa:.0f} Pa / {s.ref_noise_dba:.0f} dBA.")
311	    _model_readout()
312	
313	    def reload_models():
314	        load_fan_models_dir()
315	        state.fan_models = fan_spec_names()
316	        _model_readout()
317	        state.flush()
318	
319	    @state.change("fan_model")
320	    def _on_model(**_):
321	        _model_readout()
322	    state.sweep_param = "max_camber"
323	    state.sweep_steps = 3
324	    refresh_items()
325	
326	    preview_stl = Path(tempfile.gettempdir()) / "fansim_cockpit_preview.stl"
327	
328	    def refresh_figure():
329	        fig = scatter_figure(study_designs, user_designs)
330	        if hasattr(ctrl, "figure_update"):
331	            ctrl.figure_update(fig)
332	
333	    def _init_editor(p: dict, feat: Features | None = None):
334	        """Load the parameter-editor sliders from a design's params + features."""

================================================================================
## window @ 2026-08-28T18:55:00  (lines 468-481)

468	    def _feat_dict() -> dict:
469	        f = edit_features()
470	        return dict(tubercle_amp=f.tubercle_amp, tubercle_waves=f.tubercle_waves,
471	                    serration_amp=f.serration_amp, serration_waves=f.serration_waves,
472	                    dimple_amp=f.dimple_amp, dimple_rows=f.dimple_rows,
473	                    dimple_cols=f.dimple_cols)
474	
475	    def active_spec():
476	        """The selected fan model with the current leeway margins applied (nominal untouched)."""
477	        return dataclasses.replace(
478	            get_fan_spec(state.fan_model),
479	            leeway_tip_dia_mm=float(state.lee_tip), leeway_depth_mm=float(state.lee_depth),
480	            leeway_weight_g=float(state.lee_weight), over_voltage_v=float(state.lee_overvolt))
481

================================================================================
## window @ 2026-08-28T18:57:49  (lines 648-717)

648	                for i, val in enumerate(values):
649	                    flat, feat = dict(base_flat), dict(base_feat)
650	                    if kind == "flat":
651	                        flat[field] = int(val) if field == "n_blades" else float(val)
652	                    else:
653	                        feat[field] = float(val)
654	                        if kind == "tub" and feat["tubercle_waves"] == 0:
655	                            feat["tubercle_waves"] = 6
656	                        if kind == "ser" and feat["serration_waves"] == 0:
657	                            feat["serration_waves"] = 8
658	                        if kind == "dim":
659	                            feat["dimple_rows"] = feat["dimple_rows"] or 5
660	                            feat["dimple_cols"] = feat["dimple_cols"] or 5
661	                    params = blade_from_flat(flat, Features(**feat))
662	                    state.assess_msg = f"Sweep {label} {i+1}/{len(values)} = {val:g}: running CFD…"
663	                    state.flush()
664	                    if not check_printability(params).printable:
665	                        continue
666	                    try:  # one design failing shouldn't abort the whole sweep
667	                        if await _assess(params, flat, f"sweep {label}={val:g}"):
668	                            done += 1
669	                    except Exception as exc:  # noqa: BLE001
670	                        state.assess_msg = f"Sweep {label}={val:g} failed: {type(exc).__name__}: {exc}"
671	                        state.flush()
672	                state.assess_msg = f"Sweep of {label} done: {done} ◆ runs added to the plot."
673	            finally:
674	                state.assess_busy = False
675	                state.flush()
676	
677	        asynchronous.create_task(task())
678	
679	    def select(trial: int | None):
680	        print(f"[cockpit] select({trial!r})", flush=True)
681	        if trial is None:
682	            return
683	        d = by_trial.get(int(trial))
684	        if d is None:
685	            return
686	        plotter.clear_actors()
687	        if d.has_model:
688	            plotter.add_mesh(pv.read(str(d.stl_path)), color="lightsteelblue",
689	                             smooth_shading=True)
690	            plotter.reset_camera()
691	        o, p = d.objectives, d.params
692	        state.selected_trial = int(trial)
693	        state.info_lines = [
694	            f"Trial {d.trial}   {d.extra.get('n_blades')} blades"
695	            + ("   ★ Pareto" if d.is_pareto else ""),
696	            f"CFM free {o['cfm_free']:.1f}   CFM load {o['cfm_load']:.1f}"
697	            f"   efficiency {o['efficiency']:.1f}%",
698	            f"stagger r/m/t {p.get('stagger_root',0):.0f}/{p.get('stagger_mid',0):.0f}"
699	            f"/{p.get('stagger_tip',0):.0f}   camber {p.get('max_camber',0):.3f}",
700	            f"chord r/m/t {p.get('chord_root',0):.1f}/{p.get('chord_mid',0):.1f}"
701	            f"/{p.get('chord_tip',0):.1f}   sweep m/t {p.get('sweep_mid',0):.1f}"
702	            f"/{p.get('sweep_tip',0):.1f}",
703	        ]
704	        rpm = d.extra.get("actual_rpm", 0)
705	        spec = get_fan_spec(d.extra.get("fan_model", "a12x25"))
706	        if rpm and rpm < spec.rpm * 0.995:
707	            state.info_lines.append(f"⚙ motor-limited: runs at {rpm:.0f} RPM "
708	                                    f"({100*rpm/spec.rpm:.0f}% of {spec.rpm:.0f}) — flow already derated")
709	        if d.extra.get("over_spec"):
710	            state.info_lines.append("⚠ OVER-SPEC: " + "; ".join(d.extra["over_spec"]))
711	        _init_editor(p)  # load the editor sliders from the selected design
712	        state.preview_msg = "Edit the sliders below, then press Preview geometry."
713	        try:
714	            ctrl.view_update()
715	        except Exception:
716	            pass
717

================================================================================
## window @ 2026-08-28T18:58:39  (lines 857-880)

857	                                                _slider("Extra weight (g)", "lee_weight", 0, 40, 1)
858	                        with v3.VCard(classes="mb-2 pa-3"):
859	                            html.Div("Assess & sweep (runs CFD)",
860	                                     classes="text-subtitle-2 mb-1")
861	                            v3.VBtn("Assess this design", color="success", size="small",
862	                                    block=True, click=(on_assess,),
863	                                    loading=("assess_busy",), disabled=("assess_busy",))
864	                            with v3.VRow(no_gutters=True, classes="mt-2 align-center"):
865	                                with v3.VCol(cols=6, classes="pr-1"):
866	                                    v3.VSelect(label="Sweep", v_model=("sweep_param",),
867	                                               items=("sweep_items",), density="compact",
868	                                               variant="outlined", hide_details=True)
869	                                with v3.VCol(cols=3, classes="px-1"):
870	                                    v3.VTextField(label="steps", v_model=("sweep_steps",),
871	                                                  type="number", density="compact",
872	                                                  variant="outlined", hide_details=True)
873	                                with v3.VCol(cols=3, classes="pl-1"):
874	                                    v3.VBtn("Run", size="small", color="success",
875	                                            variant="tonal", click=(on_sweep,),
876	                                            disabled=("assess_busy",))
877	                            html.Div("{{ assess_msg }}", classes="text-caption mt-2",
878	                                     style="white-space: pre-line")
879	                        with v3.VCard(style="height:420px;"):
880	                            view = plotter_ui(plotter)

================================================================================
## window @ 2026-08-28T19:07:08  (lines 452-501)

452	        build_stl_isolated(flat, feat, preview_stl, timeout=120.0)
453	
454	    def do_preview():
455	        # Async so the "Generating…" indicator shows while the (7-35 s) geometry build runs;
456	        # a synchronous build would freeze the UI with no feedback until it finished.
457	        if state.preview_busy or state.assess_busy:
458	            return
459	        params = build_edit_params()
460	        printable = check_printability(params)
461	        if not printable.printable:
462	            state.preview_msg = f"⚠ Not printable: {printable.reason}"
463	            return
464	        flat, feat = edit_flat(), edit_features()  # serializable inputs for the isolated build
465	
466	        async def task():
467	            state.preview_busy = True
468	            heavy = " (features are heavy — up to ~2 min)" if params.features.active else ""
469	            state.preview_msg = f"⏳ Generating geometry…{heavy}"
470	            state.flush()
471	            loop = asyncio.get_running_loop()
472	            try:
473	                await loop.run_in_executor(None, _build_preview_stl, flat, feat)
474	            except TimeoutError:
475	                state.preview_msg = ("⚠ Geometry build timed out — featured blades are heavy; "
476	                                     "try a lower serration/dimple count (the app is fine).")
477	                state.preview_busy = False
478	                state.flush()
479	                return
480	            except Exception as exc:  # loft/boolean failure or isolated native crash — app survives
481	                state.preview_msg = f"⚠ Geometry failed: {type(exc).__name__} (the app is fine)"
482	                state.preview_busy = False
483	                state.flush()
484	                return
485	            plotter.clear_actors()
486	            plotter.add_mesh(pv.read(str(preview_stl)), color="darkorange",
487	                             smooth_shading=True)
488	            plotter.reset_camera()
489	            feats = "features ON" if params.features.active else "smooth"
490	            _, status = spec_status(preview_stl, params, flat)   # spec check now, before any CFD
491	            state.preview_msg = (f"Preview (orange): {params.n_blades} blades, "
492	                                 f"camber {state.e_camber:.3f}, {feats}.\n{status}")
493	            state.preview_busy = False
494	            try:
495	                ctrl.view_update()
496	            except Exception:
497	                pass
498	            state.flush()
499	
500	        asynchronous.create_task(task())
501

================================================================================
## window @ 2026-08-28T19:07:12  (lines 572-616)

572	    def spec_status(stl_path, params, flat=None):
573	        """Check the BUILT geometry against the active fan model (envelope/hub/depth/weight) with NO
574	        CFD -- lets us flag an out-of-spec design at Preview instead of after an Assess. On a depth
575	        issue, names the specific sliders driving it for THIS design."""
576	        spec = active_spec()
577	        try:
578	            import trimesh
579	            m = trimesh.load(str(stl_path))
580	            (xmin, ymin, zmin), (xmax, ymax, zmax) = m.bounds
581	            dia = 2.0 * max(abs(xmin), abs(xmax), abs(ymin), abs(ymax))
582	            depth = zmax - zmin
583	            weight = estimate_weight_g(abs(float(m.volume)), spec.material)
584	        except Exception:  # noqa: BLE001 - if we can't measure it, don't block
585	            return True, ""
586	        ok, reason = check_build(spec, dia, 2.0 * params.hub_radius, depth, weight)
587	        depth_msg = _depth_driver_msg(flat) if (flat and "depth" in reason.lower()) else ""
588	        if not ok:
589	            return False, f"⚠ Out of spec — Assess will reject: {reason}. {_reject_hint(reason)}{depth_msg}"
590	        over = over_spec_flags(spec, dia, depth, weight)
591	        if over:
592	            dm = _depth_driver_msg(flat) if (flat and any("depth" in o for o in over)) else ""
593	            return True, "⚠ OVER-SPEC (allowed via leeway): " + "; ".join(over) + dm
594	        return True, f"✓ fits {spec.name} (dia {dia:.0f} mm, depth {depth:.0f} mm, {weight:.0f} g)"
595	
596	    def _blocking_eval(flat, features, workdir):
597	        # Isolated subprocess: an OCP native crash / OpenFOAM hang can't take the cockpit down.
598	        return evaluate_candidate_isolated(flat, features, workdir, spec=active_spec(),
599	                                           procs=8, base_cell=0.006, iters=500)
600	
601	    async def _assess(params, flat, label):
602	        tid = next_id[0]
603	        next_id[0] += 1
604	        workdir = assess_dir / f"design_{tid}"
605	        loop = asyncio.get_running_loop()
606	        result = await loop.run_in_executor(None, _blocking_eval, flat, params.features, workdir)
607	        if not result.feasible:
608	            hint = _reject_hint(result.reason)
609	            state.assess_msg = f"{label}: rejected — {result.reason}" + (f"\n{hint}" if hint else "")
610	            state.flush()
611	            return None
612	        stl = workdir / "impeller.stl"
613	        d = Design(
614	            trial=tid, params=dict(flat),
615	            objectives={"cfm_free": result.cfm_free, "cfm_load": result.cfm_load,
616	                        "efficiency": result.efficiency},

================================================================================
## window @ 2026-08-28T19:08:55  (lines 948-961)

948	                                                  type="number", density="compact",
949	                                                  variant="outlined", hide_details=True)
950	                                with v3.VCol(cols=3, classes="pl-1"):
951	                                    v3.VBtn("Run", size="small", color="success",
952	                                            variant="tonal", click=(on_sweep,),
953	                                            disabled=("assess_busy",))
954	                            html.Div("{{ assess_msg }}", classes="text-caption mt-2",
955	                                     style="white-space: pre-line")
956	                        with v3.VCard(style="height:420px;"):
957	                            view = plotter_ui(plotter)
958	    ctrl.view_update = view.update
959	    ctrl.figure_update = fig_widget.update
960	    return server
961

================================================================================
## window @ 2026-08-28T20:08:13  (lines 423-440)

423	    _init_editor({})
424	
425	    def edit_flat() -> dict:
426	        return dict(
427	            n_blades=int(state.e_n_blades),
428	            stagger_root=state.e_stagger_root, stagger_mid=state.e_stagger_mid,
429	            stagger_tip=state.e_stagger_tip, chord_root=state.e_chord_root,
430	            chord_mid=state.e_chord_mid, chord_tip=state.e_chord_tip,
431	            sweep_mid=state.e_sweep_mid, sweep_tip=state.e_sweep_tip,
432	            max_camber=state.e_camber, camber_pos=state.e_camber_pos,
433	            lean_mid=state.e_lean_mid, lean_tip=state.e_lean_tip,
434	            le_sweep_mid=state.e_le_mid, le_sweep_tip=state.e_le_tip,
435	            hub_radius=state.e_hub_radius, tip_radius=state.e_tip_radius,
436	            thickness_root=state.e_thick_root, thickness_mid=state.e_thick_mid,
437	            thickness_tip=state.e_thick_tip,
438	            spacing_spread=state.e_spacing, spacing_seed=0,
439	        )
440

================================================================================
## window @ 2026-08-28T20:08:25  (lines 888-899)

888	                                        _slider("Chord tip", "e_chord_tip", 14, 42, 0.5)
889	                                        _slider("Wrap mid (deg)", "e_lean_mid", 0, 30, 1)
890	                                        _slider("Wrap tip (deg)", "e_lean_tip", 0, 45, 1)
891	                                        _slider("Sweep mid", "e_sweep_mid", -3, 8, 0.5)
892	                                        _slider("Sweep tip", "e_sweep_tip", 0, 15, 0.5)
893	                                        _slider("LE curve mid (mm)", "e_le_mid", -8, 8, 0.5)
894	                                        _slider("LE curve tip (mm)", "e_le_tip", -8, 8, 0.5)
895	                                        _slider("Hub radius (mm)", "e_hub_radius", 15, 35, 0.5)
896	                                        _slider("Tip radius / length (mm)", "e_tip_radius", 45, 59, 0.5)
897	                                        _slider("Camber position", "e_camber_pos", 0.2, 0.6, 0.05)
898	                                        _slider("Thickness root", "e_thick_root", 0.03, 0.15, 0.01)
899	                                        _slider("Thickness mid", "e_thick_mid", 0.03, 0.15, 0.01)

================================================================================
## window @ 2026-08-28T20:08:49  (lines 188-232)

188	def _blade_z_extent(params) -> float:
189	    """Axial (Z) extent of the blade from its section points -- FAST (no CAD-kernel solid)."""
190	    from fansim.geometry.blade import _interp_stations, _section_points_3d
191	    it = _interp_stations(params, params.n_span)
192	    r0 = params.hub_radius - params.root_embed
193	    zs = []
194	    for i in range(params.n_span):
195	        rf = float(it["r_frac"][i]); r = r0 + (params.tip_radius - r0) * rf
196	        pts = _section_points_3d(
197	            r=r, r_frac=rf, chord=float(it["chord"][i]), stagger_deg=float(it["stagger_deg"][i]),
198	            thickness=float(it["thickness"][i]), max_camber=float(it["max_camber"][i]),
199	            camber_pos=float(it["camber_pos"][i]), sweep=float(it["sweep"][i]),
200	            skew=float(it["skew"][i]), le_sweep=float(it["le_sweep"][i]),
201	            lean_deg=float(it["lean_deg"][i]), n_chord=params.n_chord, features=params.features)
202	        zs += [v.z for v in pts]
203	    return max(zs) - min(zs)
204	
205	
206	def _depth_drivers(flat: dict, top: int = 3) -> list[tuple[str, float]]:
207	    """For THIS design, how much each slider would cut the blade's Z-depth -- ranked. Features off
208	    (they barely affect depth) so it's fast. Returns [(label, mm_saved), ...] biggest first."""
209	    from fansim.geometry.features import Features
210	    from fansim.optimize.search_space import blade_from_flat
211	    base = _blade_z_extent(blade_from_flat(flat, Features()))
212	    tests = [("Sweep tip", "sweep_tip", -4.0), ("Sweep mid", "sweep_mid", -4.0),
213	             ("Mid stagger/pitch", "stagger_mid", -6.0), ("Tip stagger/pitch", "stagger_tip", -6.0),
214	             ("Root stagger/pitch", "stagger_root", -6.0), ("Mid chord", "chord_mid", -6.0),
215	             ("Tip chord", "chord_tip", -6.0), ("Root chord", "chord_root", -6.0),
216	             ("LE curve tip", "le_sweep_tip", 0.0), ("LE curve mid", "le_sweep_mid", 0.0),
217	             ("Wrap tip", "lean_tip", -10.0), ("Wrap mid", "lean_mid", -10.0),
218	             ("Tip radius / length", "tip_radius", -5.0)]
219	    out = []
220	    for label, key, delta in tests:
221	        f = dict(flat)
222	        f[key] = 0.0 if delta == 0.0 else f.get(key, 0.0) + delta
223	        try:
224	            saved = base - _blade_z_extent(blade_from_flat(f, Features()))
225	        except Exception:  # noqa: BLE001
226	            continue
227	        if saved > 0.3:
228	            out.append((label, saved))
229	    f = dict(flat)
230	    for k in ("thickness_root", "thickness_mid", "thickness_tip"):
231	        f[k] = max(0.03, f.get(k, 0.08) - 0.02)
232	    try:

================================================================================
## window @ 2026-08-28T20:09:07  (lines 229-258)

229	    f = dict(flat)
230	    for k in ("thickness_root", "thickness_mid", "thickness_tip"):
231	        f[k] = max(0.03, f.get(k, 0.08) - 0.02)
232	    try:
233	        saved = base - _blade_z_extent(blade_from_flat(f, Features()))
234	        if saved > 0.3:
235	            out.append(("Thinner blades", saved))
236	    except Exception:  # noqa: BLE001
237	        pass
238	    out.sort(key=lambda t: -t[1])
239	    return out[:top]
240	
241	
242	def _load_assessed_designs(assess_dirs) -> list[Design]:
243	    """Reload designs the user assessed in earlier cockpit sessions (persisted as design.json).
244	
245	    Accepts a single dir or an iterable of cockpit_assess dirs so a design assessed under ANY run
246	    shows up regardless of which --run is currently open (user designs are the user's own work, not
247	    tied to one optimizer run). Trial ids that collide across runs are re-keyed to a fresh id (the
248	    original is kept in extra['orig_trial']); each design records its source run in extra['source_run'].
249	    """
250	    if isinstance(assess_dirs, (str, Path)):
251	        assess_dirs = [Path(assess_dirs)]
252	    out: list[Design] = []
253	    used: set[int] = set()
254	
255	    def _fresh() -> int:
256	        i = 9000
257	        while i in used:
258	            i += 1

================================================================================
## window @ 2026-08-28T22:01:40  (lines 586-593)

586	            _draw(preview_stl, "darkorange")  # renders with highlight/envelope aids
587	            feats = "features ON" if params.features.active else "smooth"
588	            _, status = spec_status(preview_stl, params, flat)   # spec check now, before any CFD
589	            state.preview_msg = (f"Preview (orange): {params.n_blades} blades, "
590	                                 f"camber {state.e_camber:.3f}, {feats}.\n{status}")
591	            state.preview_busy = False
592	            try:
593	                ctrl.view_update()

================================================================================
## window @ 2026-08-28T22:24:33  (lines 861-890)

861	    @state.change("selected_trial")
862	    def _on_dropdown(selected_trial=None, **_):
863	        select(selected_trial)
864	
865	    def on_plotly_click(event=None):
866	        pts = (event or {}).get("points") or []
867	        if pts and pts[0].get("customdata") is not None:
868	            state.selected_trial = int(pts[0]["customdata"])
869	
870	    with SinglePageLayout(server) as layout:
871	        layout.title.set_text("Fan-simulator Cockpit")
872	        with layout.content:
873	            with v3.VContainer(fluid=True, classes="pa-2"):
874	                with v3.VRow(no_gutters=True):
875	                    with v3.VCol(cols=6, classes="pr-2"):
876	                        fig_widget = plotly_widgets.Figure(
877	                            figure=scatter_figure(study_designs, user_designs),
878	                            click=(on_plotly_click, "[$event]"),
879	                            style="width:100%;",
880	                        )
881	                    with v3.VCol(cols=6):
882	                        with v3.VCard(classes="mb-2 pa-3"):
883	                            v3.VSelect(
884	                                label="Design",
885	                                v_model=("selected_trial",),
886	                                items=("trial_items",),
887	                                density="compact", variant="outlined",
888	                                hide_details=True,
889	                                update_modelValue=(select, "[$event]"),
890	                            )

================================================================================
## window @ 2026-08-28T22:30:54  (lines 930-951)

930	                                with v3.VExpansionPanel(title="Features (bio-inspired)"):
931	                                    with v3.VExpansionPanelText():
932	                                        _slider("Tubercle amp", "e_tub_amp", 0.0, 0.10, 0.01)
933	                                        _slider("Tubercle waves", "e_tub_waves", 0, 8, 1)
934	                                        _slider("Serration amp", "e_ser_amp", 0.0, 0.06, 0.005)
935	                                        _slider("Serration teeth", "e_ser_waves", 0, 12, 1)
936	                                        _slider("Dimple depth", "e_dim_amp", 0.0, 0.35, 0.05)
937	                                        _slider("Dimple rows", "e_dim_rows", 0, 6, 1)
938	                                        _slider("Dimple cols", "e_dim_cols", 0, 6, 1)
939	                            with v3.VRow(no_gutters=True, classes="mt-2"):
940	                                v3.VBtn("Preview geometry", color="primary", size="small",
941	                                        click=(do_preview,), classes="mr-2",
942	                                        loading=("preview_busy",),
943	                                        disabled=("preview_busy || assess_busy",))
944	                                v3.VBtn("Reset", size="small", variant="tonal",
945	                                        click=(select, "[selected_trial]"))
946	                            html.Div("{{ preview_msg }}", classes="text-caption mt-2",
947	                                     style="white-space: pre-line")
948	                        with v3.VExpansionPanels(classes="mb-2"):
949	                            with v3.VExpansionPanel(title="Fan model & leeway"):
950	                                with v3.VExpansionPanelText():
951	                                    with v3.VRow(no_gutters=True, classes="align-center"):

================================================================================
## window @ 2026-08-28T22:31:12  (lines 460-475)

460	    def edit_features() -> Features:
461	        # A feature needs BOTH amplitude and a count to be visible; if the user raises only the
462	        # amplitude slider, auto-fill a sensible count so it actually shows up.
463	        tw = int(state.e_tub_waves) or (6 if state.e_tub_amp > 0 else 0)
464	        sw = int(state.e_ser_waves) or (8 if state.e_ser_amp > 0 else 0)
465	        dr = int(state.e_dim_rows) or (5 if state.e_dim_amp > 0 else 0)
466	        dc = int(state.e_dim_cols) or (5 if state.e_dim_amp > 0 else 0)
467	        return Features(
468	            tubercle_amp=state.e_tub_amp, tubercle_waves=tw,
469	            serration_amp=state.e_ser_amp, serration_waves=sw,
470	            dimple_amp=state.e_dim_amp, dimple_rows=dr, dimple_cols=dc,
471	        )
472	
473	    def build_edit_params():
474	        return blade_from_flat(edit_flat(), edit_features())
475

================================================================================
## window @ 2026-08-28T22:50:50  (lines 840-909)

840	
841	    def select(trial: int | None):
842	        print(f"[cockpit] select({trial!r})", flush=True)
843	        if trial is None:
844	            return
845	        d = by_trial.get(int(trial))
846	        if d is None:
847	            return
848	        if d.has_model:
849	            _draw(d.stl_path, "lightsteelblue")  # renders with highlight/envelope aids
850	        else:
851	            plotter.clear_actors()
852	        o, p = d.objectives, d.params
853	        state.selected_trial = int(trial)
854	        state.info_lines = [
855	            f"Trial {d.trial}   {d.extra.get('n_blades')} blades"
856	            + ("   ★ Pareto" if d.is_pareto else ""),
857	            f"CFM free {o['cfm_free']:.1f}   CFM load {o['cfm_load']:.1f}"
858	            f"   efficiency {o['efficiency']:.1f}%",
859	            f"stagger r/m/t {p.get('stagger_root',0):.0f}/{p.get('stagger_mid',0):.0f}"
860	            f"/{p.get('stagger_tip',0):.0f}   camber {p.get('max_camber',0):.3f}",
861	            f"chord r/m/t {p.get('chord_root',0):.1f}/{p.get('chord_mid',0):.1f}"
862	            f"/{p.get('chord_tip',0):.1f}   sweep m/t {p.get('sweep_mid',0):.1f}"
863	            f"/{p.get('sweep_tip',0):.1f}",
864	        ]
865	        rpm = d.extra.get("actual_rpm", 0)
866	        spec = get_fan_spec(d.extra.get("fan_model", "a12x25"))
867	        if rpm and rpm < spec.rpm * 0.995:
868	            state.info_lines.append(f"⚙ motor-limited: runs at {rpm:.0f} RPM "
869	                                    f"({100*rpm/spec.rpm:.0f}% of {spec.rpm:.0f}) — flow already derated")
870	        if d.extra.get("over_spec"):
871	            state.info_lines.append("⚠ OVER-SPEC: " + "; ".join(d.extra["over_spec"]))
872	        _init_editor(p)  # load the editor sliders from the selected design
873	        _set_baseline()  # editor now matches the assessed design — not stale until edited
874	        state.preview_msg = "Edit the sliders below, then press Preview geometry."
875	        try:
876	            ctrl.view_update()
877	        except Exception:
878	            pass
879	
880	    @state.change("selected_trial")
881	    def _on_dropdown(selected_trial=None, **_):
882	        select(selected_trial)
883	
884	    def on_plotly_click(event=None):
885	        pts = (event or {}).get("points") or []
886	        if pts and pts[0].get("customdata") is not None:
887	            state.selected_trial = int(pts[0]["customdata"])
888	            state.flush()  # push the new selection back so the Design dropdown syncs to the clicked point
889	
890	    with SinglePageLayout(server) as layout:
891	        layout.title.set_text("Fan-simulator Cockpit")
892	        with layout.content:
893	            with v3.VContainer(fluid=True, classes="pa-2"):
894	                with v3.VRow(no_gutters=True):
895	                    with v3.VCol(cols=6, classes="pr-2"):
896	                        fig_widget = plotly_widgets.Figure(
897	                            figure=scatter_figure(study_designs, user_designs),
898	                            click=(on_plotly_click, "[$event]"),
899	                            style="width:100%;",
900	                        )
901	                    with v3.VCol(cols=6):
902	                        with v3.VCard(classes="mb-2 pa-3"):
903	                            v3.VSelect(
904	                                label="Design",
905	                                v_model=("selected_trial",),
906	                                items=("trial_items",),
907	                                density="compact", variant="outlined",
908	                                hide_details=True,
909	                                update_modelValue=(select, "[$event]"),

================================================================================
## window @ 2026-08-28T22:54:44  (lines 139-188)

139	def scatter_figure(study_designs, user_designs=()) -> go.Figure:
140	    def trace(designs, name, symbol_pareto, symbol_plain, line):
141	        return go.Scatter(
142	            x=[d.objectives["cfm_free"] for d in designs],
143	            y=[d.objectives["cfm_load"] for d in designs],
144	            mode="markers", name=name,
145	            marker=dict(
146	                size=[22 if d.is_pareto else 14 for d in designs],
147	                symbol=[symbol_pareto if d.is_pareto else symbol_plain for d in designs],
148	                color=[d.objectives["efficiency"] for d in designs],
149	                colorscale="Viridis", showscale=True, colorbar=dict(title="eff %"),
150	                cmin=0, cmax=22, line=line,
151	            ),
152	            customdata=[d.trial for d in designs],
153	            hovertemplate="#%{customdata}<br>free %{x:.1f} CFM"
154	                          "<br>load %{y:.1f} CFM<extra>" + name + "</extra>",
155	        )
156	
157	    fig = go.Figure()
158	    fig.add_trace(trace(study_designs, "study", "star", "circle",
159	                        dict(width=1, color="rgba(0,0,0,0.4)")))
160	    if user_designs:
161	        fig.add_trace(trace(list(user_designs), "your runs", "diamond", "diamond",
162	                            dict(width=2, color="crimson")))
163	    fig.update_layout(
164	        margin=dict(l=50, r=10, t=30, b=45),
165	        xaxis_title="CFM at free delivery", yaxis_title="CFM at load",
166	        title="Design space (★ Pareto, ◆ your runs)", height=560,
167	        template="plotly_white", showlegend=False,
168	    )
169	    return fig
170	
171	
172	def _reject_hint(reason: str) -> str:
173	    """Turn a gate rejection into an actionable hint about which sliders drive it."""
174	    r = reason.lower()
175	    # (over-power no longer rejects -- it derates RPM; only the hard geometry limits reject)
176	    if "depth" in r:
177	        return ("↳ depth = how far blades reach in Z. Driven by sweep, LE curve, stagger, thickness "
178	                "and wrap. Reduce those (esp. Sweep tip / LE curve tip) — or add Extra-depth leeway.")
179	    if "tip dia" in r:
180	        return "↳ tip diameter too big: reduce Chord tip / stagger — or add Tip-past-frame leeway."
181	    if "hub" in r:
182	        return "↳ hub diameter out of range: adjust the Hub radius slider."
183	    if "weight" in r:
184	        return ("↳ too heavy: thinner blades (Thickness sliders), smaller chord/hub, or fewer blades "
185	                "— or add Extra-weight leeway.")
186	    return ""
187	
188

================================================================================
## window @ 2026-08-28T22:55:40  (lines 922-931)

922	        layout.title.set_text("Fan-simulator Cockpit")
923	        with layout.content:
924	            with v3.VContainer(fluid=True, classes="pa-2"):
925	                with v3.VRow(no_gutters=True):
926	                    with v3.VCol(cols=6, classes="pr-2"):
927	                        fig_widget = plotly_widgets.Figure(
928	                            figure=scatter_figure(study_designs, user_designs),
929	                            click=(on_plotly_click, "[$event]"),
930	                            style="width:100%;",
931	                        )

================================================================================
## window @ 2026-08-28T22:55:43  (lines 944-953)

944	                                v_for="line in info_lines",
945	                                classes="text-body-2 mt-2",
946	                            )
947	                        with v3.VCard(classes="mb-2 pa-3"):
948	                            html.Div("Modify design — hover any slider for a min/max picture + what it does",
949	                                     classes="text-caption mb-1")
950	                            with v3.VExpansionPanels(variant="accordion", multiple=True):
951	                                with v3.VExpansionPanel(title="Geometry"):
952	                                    with v3.VExpansionPanelText():
953	                                        _slider("Blades", "e_n_blades", 5, 11, 1)

================================================================================
## window @ 2026-08-29T02:15:24  (lines 897-910)

897	            + ("   ★ Pareto" if d.is_pareto else ""),
898	            f"CFM free {o['cfm_free']:.1f}   CFM load {o['cfm_load']:.1f}"
899	            f"   efficiency {o['efficiency']:.1f}%",
900	            f"stagger r/m/t {p.get('stagger_root',0):.0f}/{p.get('stagger_mid',0):.0f}"
901	            f"/{p.get('stagger_tip',0):.0f}   camber {p.get('max_camber',0):.3f}",
902	            f"chord r/m/t {p.get('chord_root',0):.1f}/{p.get('chord_mid',0):.1f}"
903	            f"/{p.get('chord_tip',0):.1f}   sweep m/t {p.get('sweep_mid',0):.1f}"
904	            f"/{p.get('sweep_tip',0):.1f}",
905	        ]
906	        rpm = d.extra.get("actual_rpm", 0)
907	        spec = get_fan_spec(d.extra.get("fan_model", "a12x25"))
908	        if rpm and rpm < spec.rpm * 0.995:
909	            state.info_lines.append(f"⚙ motor-limited: runs at {rpm:.0f} RPM "
910	                                    f"({100*rpm/spec.rpm:.0f}% of {spec.rpm:.0f}) — flow already derated")

================================================================================
## window @ 2026-08-29T02:15:28  (lines 911-928)

911	        if d.extra.get("over_spec"):
912	            state.info_lines.append("⚠ OVER-SPEC: " + "; ".join(d.extra["over_spec"]))
913	        _init_editor(p)  # load the editor sliders from the selected design
914	        _set_baseline()  # editor now matches the assessed design — not stale until edited
915	        state.preview_msg = "Edit the sliders below, then press Preview geometry."
916	        try:
917	            ctrl.view_update()
918	        except Exception:
919	            pass
920	
921	    @state.change("selected_trial")
922	    def _on_dropdown(selected_trial=None, **_):
923	        select(selected_trial)
924	
925	    def on_plotly_click(trial=None):
926	        # We receive ONLY the clicked point's customdata (the trial id), not the whole plotly event:
927	        # the full $event contains non-serializable fields (functions/DOM refs) that fail to marshal to
928	        # the server, so the click never arrived. Extracting customdata client-side (see the binding)

================================================================================
## window @ 2026-08-29T02:15:51  (lines 1100-1119)

1100	                                            variant="tonal", click=(on_sweep,),
1101	                                            disabled=("assess_busy",))
1102	                            html.Div("{{ assess_msg }}", classes="text-caption mt-2",
1103	                                     style="white-space: pre-line")
1104	                        with v3.VCard(classes="pa-2"):
1105	                            with v3.VRow(no_gutters=True, classes="align-center"):
1106	                                with v3.VCol(cols=7):
1107	                                    v3.VSwitch(v_model=("highlight_spec",), density="compact",
1108	                                               hide_details=True, color="error", inset=True,
1109	                                               label="Highlight out-of-spec (red)")
1110	                                with v3.VCol(cols=5):
1111	                                    v3.VSwitch(v_model=("show_envelope",), density="compact",
1112	                                               hide_details=True, color="success", inset=True,
1113	                                               label="Case envelope")
1114	                            html.Div("Red = geometry past the fan's nominal tip diameter or depth. "
1115	                                     "Envelope = the max tip-dia × depth the blade must fit inside.",
1116	                                     classes="text-caption text-medium-emphasis")
1117	                        with v3.VCard(style="height:420px;"):
1118	                            view = plotter_ui(plotter)
1119	    ctrl.view_update = view.update

================================================================================
## window @ 2026-08-29T16:27:26  (lines 50-67)

50	from trame.widgets import vuetify3 as v3
51	
52	from fansim.cockpit.data import Design, feasible_designs, load_designs
53	from fansim.fan_spec import (
54	    check_build,
55	    estimate_weight_g,
56	    fan_spec_names,
57	    get_fan_spec,
58	    load_fan_models_dir,
59	    over_spec_flags,
60	)
61	from fansim.geometry import build_impeller, export_stl
62	from fansim.geometry.features import Features
63	from fansim.manufacturability import check_printability
64	from fansim.optimize.isolated_eval import evaluate_candidate_isolated
65	from fansim.optimize.search_space import blade_from_flat
66	from validation.ingest import MeasuredPoint
67	from validation.store import make_design_id, record_measurement, sim_vs_real

================================================================================
## window @ 2026-08-29T16:27:52  (lines 734-737)

734	    state.change(*EDITOR_VARS)(_recompute_stale)
735	
736	    def active_spec():
737	        """The selected fan model with the current leeway margins applied (nominal untouched)."""

================================================================================
## window @ 2026-08-29T16:28:13  (lines 1026-1047)

1026	                            style="width:100%;",
1027	                        )
1028	                    with v3.VCol(cols=6):
1029	                        with v3.VCard(classes="mb-2 pa-3"):
1030	                            v3.VSelect(
1031	                                label="Design",
1032	                                v_model=("selected_trial",),
1033	                                items=("trial_items",),
1034	                                density="compact", variant="outlined",
1035	                                hide_details=True,
1036	                                update_modelValue=(select, "[$event]"),
1037	                            )
1038	                            html.Div(
1039	                                "{{ line }}",
1040	                                v_for="line in info_lines",
1041	                                classes="text-body-2 mt-2",
1042	                            )
1043	                        with v3.VCard(classes="mb-2 pa-3"):
1044	                            html.Div("Modify design — hover any slider for a min/max picture + what it does",
1045	                                     classes="text-caption mb-1")
1046	                            with v3.VExpansionPanels(variant="accordion", multiple=True):
1047	                                with v3.VExpansionPanel(title="Geometry"):

================================================================================
## window @ 2026-08-30T01:07:02  (lines 585-600)

585	        cyl = pv.Cylinder(center=(0, 0, zmid), direction=(0, 0, 1),
586	                          radius=tip_r, height=depth_lim, resolution=64)
587	        plotter.add_mesh(cyl, color="seagreen", opacity=0.10)
588	        try:  # crisp rim/outline so the envelope reads as a box even at low opacity
589	            plotter.add_mesh(cyl.extract_feature_edges(), color="seagreen", line_width=2)
590	        except Exception:  # noqa: BLE001 - edges are cosmetic
591	            pass
592	
593	    def _apply_render(reset: bool = False):
594	        """(Re)draw the current model with the active highlight/envelope options."""
595	        plotter.clear_actors()
596	        p = render_state["path"]
597	        if not p:
598	            return
599	        try:
600	            mesh = pv.read(str(p))

================================================================================
## window @ 2026-08-30T01:07:09  (lines 662-673)

662	                return
663	            _draw(preview_stl, "darkorange")  # renders with highlight/envelope aids
664	            feats = "features ON" if params.features.active else "smooth"
665	            _, status = spec_status(preview_stl, params, flat)   # spec check now, before any CFD
666	            try:
667	                from fansim.manufacturability.printability_score import grade_printability
668	                print_line = "\n🖨 " + grade_printability(params).summary
669	            except Exception:  # noqa: BLE001 - printability grade is informational
670	                print_line = ""
671	            state.preview_msg = (f"Preview (orange): {params.n_blades} blades, "
672	                                 f"camber {state.e_camber:.3f}, {feats}.\n{status}{print_line}")
673	            state.preview_busy = False

================================================================================
## window @ 2026-08-30T01:26:40  (lines 1111-1122)

1111	                                        _slider("Dimple cols", "e_dim_cols", 0, 6, 1)
1112	                            with v3.VRow(no_gutters=True, classes="mt-2"):
1113	                                v3.VBtn("Preview geometry", color="primary", size="small",
1114	                                        click=(do_preview,), classes="mr-2",
1115	                                        loading=("preview_busy",),
1116	                                        disabled=("preview_busy || assess_busy",))
1117	                                v3.VBtn("Reset", size="small", variant="tonal",
1118	                                        click=(select, "[selected_trial]"))
1119	                            html.Div("{{ preview_msg }}", classes="text-caption mt-2",
1120	                                     style="white-space: pre-line")
1121	                        with v3.VExpansionPanels(classes="mb-2"):
1122	                            with v3.VExpansionPanel(title="Fan model & leeway"):

================================================================================
## window @ 2026-08-30T01:33:22  (lines 426-431)

426	    def refresh_figure():
427	        fig = scatter_figure(study_designs, user_designs)
428	        if hasattr(ctrl, "figure_update"):
429	            ctrl.figure_update(fig)
430	
431	    def _init_editor(p: dict, feat: Features | None = None):

================================================================================
## window @ 2026-08-30T01:33:41  (lines 1068-1079)

1068	
1069	    with SinglePageLayout(server) as layout:
1070	        layout.title.set_text("Fan-simulator Cockpit")
1071	        with layout.content:
1072	            with v3.VContainer(fluid=True, classes="pa-2"):
1073	                with v3.VRow(no_gutters=True):
1074	                    with v3.VCol(cols=6, classes="pr-2"):
1075	                        fig_widget = plotly_widgets.Figure(
1076	                            figure=scatter_figure(study_designs, user_designs),
1077	                            # send ONLY the clicked point's customdata (trial id) — the full $event has
1078	                            # non-serializable fields that silently break the round-trip to the server.
1079	                            click=(on_plotly_click, "[$event?.points?.[0]?.customdata]"),

================================================================================
## window @ 2026-08-30T02:22:55  (lines 808-819)

808	            return
809	        _init_editor(e.params)          # params fill the editor sliders (features fall back to 0)
810	        _set_baseline()                 # editor now matches this design — not stale until edited
811	        parts = [f"Loaded {e.design_id}", f"{e.source}"]
812	        if isinstance(e.cfm_free, (int, float)):
813	            parts.append(f"sim {e.cfm_free:.0f}/{e.cfm_load or 0:.0f} CFM  eff {e.efficiency or 0:.0f}%")
814	        if e.has_measurement and e.measured_cfm is not None:
815	            parts.append(f"MEASURED {e.measured_cfm:.0f} CFM (sim {e.cfm_error_pct:+.0f}%)"
816	                         if e.cfm_error_pct is not None else f"MEASURED {e.measured_cfm:.0f} CFM")
817	        state.catalog_info = "  ·  ".join(parts)
818	        state.preview_msg = f"Loaded {e.design_id} from the catalog. Press Preview geometry to see it."
819	        state.flush()

================================================================================
## window @ 2026-08-30T18:46:17  (lines 1-990)

1	"""Trame design cockpit: browse the design space, click/select a design, view its 3D model.
2	
3	Layout: an interactive Plotly scatter of the evaluated designs (left) beside a live PyVista
4	3D view of the selected impeller and its metrics (right). Selecting a point in the plot -- or
5	via the dropdown -- loads that design's model. This is the foundation for the tweak-and-rerun
6	loop (parameter editor + regression sweep) added next.
7	"""
8	
9	from __future__ import annotations
10	
11	import asyncio
12	import base64
13	import dataclasses
14	import json
15	import random
16	import tempfile
17	from pathlib import Path
18	
19	
20	def _quiet_connection_reset(server) -> None:
21	    """Silence the benign Windows proactor ConnectionResetError spam on client disconnect.
22	
23	    On Windows, when a browser tab closes/navigates away, asyncio's ProactorEventLoop tries
24	    to shut down an already-closed socket and logs a full traceback. It is harmless (the
25	    server keeps running); we swallow ONLY ConnectionResetError and pass everything else to
26	    the default handler so real errors still surface.
27	    """
28	    def _ready(**_):
29	        try:
30	            loop = asyncio.get_running_loop()
31	
32	            def handler(loop, context):
33	                if isinstance(context.get("exception"), ConnectionResetError):
34	                    return
35	                loop.default_exception_handler(context)
36	
37	            loop.set_exception_handler(handler)
38	        except Exception:
39	            pass
40	
41	    server.controller.on_server_ready.add(_ready)
42	
43	import plotly.graph_objects as go
44	import pyvista as pv
45	from pyvista.trame.ui import plotter_ui
46	from trame.app import asynchronous, get_server
47	from trame.ui.vuetify3 import SinglePageLayout
48	from trame.widgets import html
49	from trame.widgets import plotly as plotly_widgets
50	from trame.widgets import vuetify3 as v3
51	
52	from fansim.catalog import build_catalog, get_entry, load_catalog
53	from fansim.cockpit.data import Design, feasible_designs, load_designs
54	from fansim.fan_spec import (
55	    check_build,
56	    estimate_weight_g,
57	    fan_spec_names,
58	    get_fan_spec,
59	    load_fan_models_dir,
60	    over_spec_flags,
61	)
62	from fansim.geometry import build_impeller, export_stl
63	from fansim.geometry.features import Features
64	from fansim.manufacturability import check_printability
65	from fansim.optimize.isolated_eval import evaluate_candidate_isolated
66	from fansim.optimize.search_space import blade_from_flat
67	from validation.ingest import MeasuredPoint
68	from validation.store import make_design_id, record_measurement, sim_vs_real
69	
70	pv.OFF_SCREEN = True
71	
72	
73	# Per-slider plain-English descriptions + min/max illustration images (shown as hover tooltips).
74	_CTRL_IMG_DIR = Path(__file__).resolve().parents[2] / "docs" / "control_images"
75	
76	
77	def _load_control_images() -> dict:
78	    uris = {}
79	    if _CTRL_IMG_DIR.exists():
80	        for p in _CTRL_IMG_DIR.glob("e_*.png"):
81	            try:
82	                uris[p.stem] = "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()
83	            except Exception:  # noqa: BLE001
84	                pass
85	    return uris
86	
87	
88	_IMG_URI = _load_control_images()
89	
90	CONTROL_DESC = {
91	    "e_n_blades": "How many blades. More = more airflow & pressure, but louder and less efficient.",
92	    "e_camber": "Blade curvature. More camber turns the air harder (pressure); too much hurts efficiency.",
93	    "e_stagger_root": "Blade PITCH angle at the hub. Higher = more axial (flow); lower = blades overlap (pressure).",
94	    "e_stagger_mid": "Blade PITCH angle at mid-span.",
95	    "e_stagger_tip": "Blade PITCH angle at the tip.",
96	    "e_chord_root": "Blade width at the hub. Wider = more area/solidity (pressure) but heavier, less efficient.",
97	    "e_chord_mid": "Blade width at mid-span.",
98	    "e_chord_tip": "Blade width at the tip.",
99	    "e_lean_mid": "Circumferential WRAP at mid-span — wraps blades so they overlap like a real fan.",
100	    "e_lean_tip": "Circumferential WRAP at the tip (0 = a flat radial paddle).",
101	    "e_sweep_mid": "Axial position of the WHOLE mid section (forward/back rake).",
102	    "e_sweep_tip": "Axial position of the WHOLE tip section.",
103	    "e_le_mid": "Rakes only the LEADING edge at mid-span — curves the LE line, trailing edge unchanged.",
104	    "e_le_tip": "Rakes only the LEADING edge at the tip.",
105	    "e_skew_mid": "Skew (mm) — shifts the whole mid section sideways (tangentially). Fine balance/overlap tweak.",
106	    "e_skew_tip": "Skew (mm) — shifts the whole tip section sideways (tangentially).",
107	    "e_winglet_span": "Where the WINGLET starts (fraction of span). Below this the blade is straight; beyond it the tip curls.",
108	    "e_winglet_sweep": "Winglet AXIAL bend (mm) — curls the tip forward/up out of the rotation plane (a real winglet). 0 = off.",
109	    "e_winglet_lean": "Winglet CIRCUMFERENTIAL curl (deg) — wraps the tip around the axis. 0 = off.",
110	    "e_hub_radius": "Hub size. Smaller hub = bigger flow annulus (more airflow/efficiency); must fit the model's hub limits.",
111	    "e_tip_radius": "Blade LENGTH (outer radius). Shrink it to make an oversized blade fit the frame (tip diameter) or trim depth.",
112	    "e_hub_height": "Hub HEIGHT (mm). 0 = auto (just covers the blade roots — shortest). Raise it for a taller hub; it can't go below root coverage.",
113	    "e_hub_nose": "Nose height (mm) for the cone/dome hub profile. Adds a spinner on the intake side (increases depth — may go over-spec).",
114	    "e_camber_pos": "Where max camber sits along the chord (0.2 = near LE, 0.6 = aft). Shifts loading fore/aft.",
115	    "e_thick_root": "Blade thickness at the hub. Thinner = lighter/more efficient; too thin drops below the min printable wall.",
116	    "e_thick_mid": "Blade thickness at mid-span.",
117	    "e_thick_tip": "Blade thickness at the tip.",
118	    "e_spacing": "Uneven-but-balanced blade spacing to spread the blade-pass tone. 0 = evenly spaced.",
119	    "e_tub_amp": "Tubercle amplitude — bumpy leading edge (whale-fin), delays stall.",
120	    "e_tub_waves": "Number of tubercle bumps along the span.",
121	    "e_ser_amp": "Serration depth — sawtooth trailing edge (owl-wing), cuts edge noise.",
122	    "e_ser_waves": "Number of serration teeth.",
123	    "e_dim_amp": "Dimple depth — golf-ball-style surface texture.",
124	    "e_dim_rows": "Dimples along the chord.",
125	    "e_dim_cols": "Dimples along the span.",
126	}
127	
128	
129	def _slider(label: str, model: str, mn: float, mx: float, step: float):
130	    """A labelled slider with a HOVER TOOLTIP: what it does + a min/max illustration."""
131	    desc, uri = CONTROL_DESC.get(model, ""), _IMG_URI.get(model)
132	    if not desc and not uri:
133	        v3.VSlider(v_model=(model,), min=mn, max=mx, step=step, label=label, thumb_label=True,
134	                   density="compact", hide_details=True, classes="mb-1")
135	        return
136	    with v3.VTooltip(location="end", open_delay=150, max_width=380):
137	        with v3.Template(v_slot_activator="{ props }"):
138	            v3.VSlider(v_bind="props", v_model=(model,), min=mn, max=mx, step=step,
139	                       label=label, thumb_label=True, density="compact", hide_details=True,
140	                       classes="mb-1")
141	        if uri:
142	            html.Img(src=uri, style="width:360px;max-width:100%;display:block;"
143	                                    "margin-bottom:4px;border-radius:4px;")
144	        html.Div(desc, classes="text-caption")
145	
146	
147	def scatter_figure(study_designs, user_designs=()) -> go.Figure:
148	    def trace(designs, name, symbol_pareto, symbol_plain, line):
149	        return go.Scatter(
150	            x=[d.objectives["cfm_free"] for d in designs],
151	            y=[d.objectives["cfm_load"] for d in designs],
152	            mode="markers", name=name,
153	            marker=dict(
154	                # bigger markers = easier click targets (plotly only fires a click on a precise hit)
155	                size=[30 if d.is_pareto else 20 for d in designs],
156	                symbol=[symbol_pareto if d.is_pareto else symbol_plain for d in designs],
157	                color=[d.objectives["efficiency"] for d in designs],
158	                colorscale="Viridis", showscale=True, colorbar=dict(title="eff %"),
159	                cmin=0, cmax=22, line=line,
160	            ),
161	            customdata=[d.trial for d in designs],
162	            hovertemplate="#%{customdata}<br>free %{x:.1f} CFM"
163	                          "<br>load %{y:.1f} CFM<extra>" + name + "</extra>",
164	        )
165	
166	    fig = go.Figure()
167	    fig.add_trace(trace(study_designs, "study", "star", "circle",
168	                        dict(width=1, color="rgba(0,0,0,0.4)")))
169	    if user_designs:
170	        fig.add_trace(trace(list(user_designs), "your runs", "diamond", "diamond",
171	                            dict(width=2, color="crimson")))
172	    fig.update_layout(
173	        margin=dict(l=50, r=10, t=30, b=45),
174	        xaxis_title="CFM at free delivery", yaxis_title="CFM at load",
175	        title="Design space (★ Pareto, ◆ your runs)", height=560,
176	        template="plotly_white", showlegend=False,
177	    )
178	    return fig
179	
180	
181	def _reject_hint(reason: str) -> str:
182	    """Turn a gate rejection into an actionable hint about which sliders drive it."""
183	    r = reason.lower()
184	    # (over-power no longer rejects -- it derates RPM; only the hard geometry limits reject)
185	    if "depth" in r:
186	        return ("↳ depth = how far blades reach in Z. Driven by sweep, LE curve, stagger, thickness "
187	                "and wrap. Reduce those (esp. Sweep tip / LE curve tip) — or add Extra-depth leeway.")
188	    if "tip dia" in r:
189	        return "↳ tip diameter too big: reduce Chord tip / stagger — or add Tip-past-frame leeway."
190	    if "hub" in r:
191	        return "↳ hub diameter out of range: adjust the Hub radius slider."
192	    if "weight" in r:
193	        return ("↳ too heavy: thinner blades (Thickness sliders), smaller chord/hub, or fewer blades "
194	                "— or add Extra-weight leeway.")
195	    return ""
196	
197	
198	def _blade_z_extent(params) -> float:
199	    """Axial (Z) extent of the blade from its section points -- FAST (no CAD-kernel solid)."""
200	    from fansim.geometry.blade import _interp_stations, _section_points_3d
201	    it = _interp_stations(params, params.n_span)
202	    r0 = params.hub_radius - params.root_embed
203	    zs = []
204	    for i in range(params.n_span):
205	        rf = float(it["r_frac"][i]); r = r0 + (params.tip_radius - r0) * rf
206	        pts = _section_points_3d(
207	            r=r, r_frac=rf, chord=float(it["chord"][i]), stagger_deg=float(it["stagger_deg"][i]),
208	            thickness=float(it["thickness"][i]), max_camber=float(it["max_camber"][i]),
209	            camber_pos=float(it["camber_pos"][i]), sweep=float(it["sweep"][i]),
210	            skew=float(it["skew"][i]), le_sweep=float(it["le_sweep"][i]),
211	            lean_deg=float(it["lean_deg"][i]), n_chord=params.n_chord, features=params.features)
212	        zs += [v.z for v in pts]
213	    return max(zs) - min(zs)
214	
215	
216	def _depth_drivers(flat: dict, top: int = 3) -> list[tuple[str, float]]:
217	    """For THIS design, how much each slider would cut the blade's Z-depth -- ranked. Features off
218	    (they barely affect depth) so it's fast. Returns [(label, mm_saved), ...] biggest first."""
219	    from fansim.geometry.features import Features
220	    from fansim.optimize.search_space import blade_from_flat
221	    base = _blade_z_extent(blade_from_flat(flat, Features()))
222	    tests = [("Sweep tip", "sweep_tip", -4.0), ("Sweep mid", "sweep_mid", -4.0),
223	             ("Mid stagger/pitch", "stagger_mid", -6.0), ("Tip stagger/pitch", "stagger_tip", -6.0),
224	             ("Root stagger/pitch", "stagger_root", -6.0), ("Mid chord", "chord_mid", -6.0),
225	             ("Tip chord", "chord_tip", -6.0), ("Root chord", "chord_root", -6.0),
226	             ("LE curve tip", "le_sweep_tip", 0.0), ("LE curve mid", "le_sweep_mid", 0.0),
227	             ("Wrap tip", "lean_tip", -10.0), ("Wrap mid", "lean_mid", -10.0),
228	             ("Tip radius / length", "tip_radius", -5.0)]
229	    out = []
230	    for label, key, delta in tests:
231	        f = dict(flat)
232	        f[key] = 0.0 if delta == 0.0 else f.get(key, 0.0) + delta
233	        try:
234	            saved = base - _blade_z_extent(blade_from_flat(f, Features()))
235	        except Exception:  # noqa: BLE001
236	            continue
237	        if saved > 0.3:
238	            out.append((label, saved))
239	    f = dict(flat)
240	    for k in ("thickness_root", "thickness_mid", "thickness_tip"):
241	        f[k] = max(0.03, f.get(k, 0.08) - 0.02)
242	    try:
243	        saved = base - _blade_z_extent(blade_from_flat(f, Features()))
244	        if saved > 0.3:
245	            out.append(("Thinner blades", saved))
246	    except Exception:  # noqa: BLE001
247	        pass
248	    # Hub contributions to TOTAL depth (the hub, not just the blades, can be the binding element).
249	    nose = float(flat.get("hub_nose", 0.0))
250	    if nose > 0.3 and str(flat.get("hub_profile", "cylinder")).lower() != "cylinder":
251	        out.append(("Hub nose (set profile to cylinder / 0 nose)", nose))
252	    hh = float(flat.get("hub_height", 0.0))
253	    if hh > 0.0:  # explicit hub taller than the auto (root-covering) minimum adds depth
254	        try:
255	            from fansim.geometry.blade import _root_axial_span
256	            p = blade_from_flat(flat, Features())
257	            r_lo, r_hi = _root_axial_span(p)
258	            auto_h = (r_hi - r_lo) + 2.0 * p.hub_axial_margin
259	            if hh - auto_h > 0.3:
260	                out.append(("Hub height above auto (set Hub height to 0)", hh - auto_h))
261	        except Exception:  # noqa: BLE001
262	            pass
263	    out.sort(key=lambda t: -t[1])
264	    return out[:top]
265	
266	
267	def _load_assessed_designs(assess_dirs) -> list[Design]:
268	    """Reload designs the user assessed in earlier cockpit sessions (persisted as design.json).
269	
270	    Accepts a single dir or an iterable of cockpit_assess dirs so a design assessed under ANY run
271	    shows up regardless of which --run is currently open (user designs are the user's own work, not
272	    tied to one optimizer run). Trial ids that collide across runs are re-keyed to a fresh id (the
273	    original is kept in extra['orig_trial']); each design records its source run in extra['source_run'].
274	    """
275	    if isinstance(assess_dirs, (str, Path)):
276	        assess_dirs = [Path(assess_dirs)]
277	    out: list[Design] = []
278	    used: set[int] = set()
279	
280	    def _fresh() -> int:
281	        i = 9000
282	        while i in used:
283	            i += 1
284	        used.add(i)
285	        return i
286	
287	    for assess_dir in assess_dirs:
288	        assess_dir = Path(assess_dir)
289	        if not assess_dir.exists():
290	            continue
291	        run_name = assess_dir.parent.name
292	        for jf in sorted(assess_dir.glob("design_*/design.json")):
293	            try:
294	                d = json.loads(jf.read_text())
295	                stl = jf.parent / "impeller.stl"
296	                orig = int(d["trial"])
297	                if orig in used:
298	                    tid = _fresh()
299	                else:
300	                    tid = orig
301	                    used.add(tid)
302	                extra = dict(d.get("extra", {}))
303	                extra.setdefault("source_run", run_name)
304	                if tid != orig:
305	                    extra["orig_trial"] = orig
306	                out.append(Design(
307	                    trial=tid, params=d.get("params", {}),
308	                    objectives=d["objectives"], feasible=d.get("feasible", True), is_pareto=False,
309	                    stl_path=stl if stl.exists() else None,
310	                    reason=d.get("reason", ""), extra=extra))
311	            except Exception:  # noqa: BLE001 - skip a corrupt/partial assess dir
312	                continue
313	    return out
314	
315	
316	def build_server(run_dir: str | Path, study_name: str | None = None):
317	    run_dir = Path(run_dir)
318	    study_designs = feasible_designs(load_designs(run_dir, study_name))
319	    if not study_designs:
320	        raise SystemExit(f"No feasible designs found in {run_dir}")
321	    assess_dir = run_dir / "cockpit_assess"   # new assessments this session land here
322	    # Reload previously assessed designs from disk so they SURVIVE a cockpit restart (they used to
323	    # live only in memory and vanished on restart). Scan EVERY run's cockpit_assess, not just the
324	    # open --run, so a design you assessed under any run still shows (user designs aren't tied to one
325	    # optimizer run). Falls back to the single dir if the runs root can't be globbed.
326	    runs_root = run_dir.parent
327	    all_assess_dirs = sorted(runs_root.glob("*/cockpit_assess")) if runs_root.exists() else []
328	    if assess_dir not in all_assess_dirs:
329	        all_assess_dirs.append(assess_dir)
330	    user_designs: list[Design] = _load_assessed_designs(all_assess_dirs)
331	    by_trial = {d.trial: d for d in study_designs}
332	    by_trial.update({d.trial: d for d in user_designs})
333	    next_id = [max([9000] + [d.trial + 1 for d in user_designs])]  # continue past reloaded ids
334	
335	    server = get_server(client_type="vue3")
336	    state, ctrl = server.state, server.controller
337	    _quiet_connection_reset(server)
338	
339	    plotter = pv.Plotter()
340	    plotter.background_color = "white"
341	    plotter.add_axes()
342	
343	    def _label(d):
344	        if d.is_pareto:
345	            tag = "  ★"
346	        elif d.trial >= 9000:  # user-assessed; note which run it was assessed under
347	            run = d.extra.get("source_run", "")
348	            tag = f"  ◆ {run}" if run else "  ◆"
349	        else:
350	            tag = ""
351	        return {"title": f"#{d.trial}{tag}", "value": d.trial}
352	
353	    def refresh_items():
354	        alld = sorted(study_designs + user_designs,
355	                      key=lambda d: -d.objectives["cfm_load"])
356	        state.trial_items = [_label(d) for d in alld]
357	
358	    state.selected_trial = None
359	    state.info_lines = ["Select a design (click a point or use the dropdown)."]
360	    state.preview_msg = "Select a design, then edit and press Preview geometry."
361	    state.export_msg = ""
362	    state.preview_busy = False
363	    state.assess_msg = ""
364	    state.assess_busy = False
365	    # staleness: True once the editor diverges from the selected design's assessed config, so the
366	    # shown CFM/eff no longer reflect the edits and a re-Assess is needed (esp. after feature edits).
367	    state.edited_stale = False
368	    state.stale_msg = ""
369	    # 3D-view constraint aids: paint the geometry that pokes past the fan's nominal envelope red, and
370	    # optionally draw the outer-case envelope (max tip diameter x max depth) as a translucent shell.
371	    state.highlight_spec = True
372	    state.show_envelope = False
373	    state.hub_profiles = ["cylinder", "cone", "dome"]  # hub nose-shape options
374	    state.declutter = False   # thin near-duplicate points in the design-space plot (view only)
375	    # physical-measurement recorder (fills validation/measurements/ — the sim-vs-real bridge)
376	    state.meas_cfm = None
377	    state.meas_static = None
378	    state.meas_noise = None
379	    state.meas_rpm = None
380	    state.meas_instrument = ""
381	    state.meas_notes = ""
382	    state.meas_msg = "Select a design, print + test it, then record what you measured."
383	    # unified catalog: every design across ALL runs, so the cockpit isn't limited to the loaded --run
384	    def _catalog_items():
385	        items = []
386	        for e in load_catalog():
387	            star = " ★" if e.is_pareto else ""
388	            meas = "  ✓meas" if e.has_measurement else ""
389	            free = f"{e.cfm_free:.0f}" if isinstance(e.cfm_free, (int, float)) else "?"
390	            items.append({"title": f"{e.design_id}  ·  {free} CFM{star}{meas}", "value": e.design_id})
391	        return items
392	    try:
393	        build_catalog()                     # refresh the index from all runs + measurements (cheap scan)
394	    except Exception:  # noqa: BLE001 - the catalog is a convenience; never block cockpit startup
395	        pass
396	    state.catalog_items = _catalog_items()
397	    state.catalog_sel = None
398	    state.catalog_info = f"{len(state.catalog_items)} designs across all runs. Pick one to load it here."
399	    # fan-model constraints + leeway (applied when you Assess). Nominal is never changed; leeway lets
400	    # a design exceed it (flagged over-spec). Import new models by dropping YAML in config/fan_models/.
401	    state.fan_model = "a12x25"
402	    state.fan_models = fan_spec_names()
403	    state.lee_tip = 0.0
404	    state.lee_depth = 0.0
405	    state.lee_overvolt = 0.0
406	    state.lee_weight = 0.0
407	
408	    def _model_readout():
409	        s = get_fan_spec(state.fan_model)
410	        state.model_info = (f"{s.name}: tip ≤{s.tip_dia_mm[1]:.0f} mm, depth ≤{s.depth_mm[1]:.0f} mm, "
411	                            f"hub {s.hub_dia_mm[0]:.0f}-{s.hub_dia_mm[1]:.0f} mm, "
412	                            f"{s.max_shaft_power_w:.2f} W shaft ({s.voltage_v:.0f} V×{s.max_current_a:.2f} A), "
413	                            f"≤{s.max_weight_g:.0f} g. Published {s.ref_cfm:.0f} CFM / "
414	                            f"{s.ref_static_pa:.0f} Pa / {s.ref_noise_dba:.0f} dBA.")
415	    _model_readout()
416	
417	    def reload_models():
418	        load_fan_models_dir()
419	        state.fan_models = fan_spec_names()
420	        _model_readout()
421	        state.flush()
422	
423	    @state.change("fan_model")
424	    def _on_model(**_):
425	        _model_readout()
426	    state.sweep_param = "max_camber"
427	    state.sweep_steps = 3
428	    refresh_items()
429	
430	    preview_stl = Path(tempfile.gettempdir()) / "fansim_cockpit_preview.stl"
431	
432	    def _thin(designs, cell: float = 2.5):
433	        """Keep one design per ~cell-CFM bucket in (free, load) space — pareto first, then best eff.
434	        Non-destructive: only the PLOTTED set is thinned; nothing is removed from disk or the dropdown."""
435	        best = {}
436	        for d in designs:
437	            key = (round(d.objectives["cfm_free"] / cell), round(d.objectives["cfm_load"] / cell))
438	            cur = best.get(key)
439	            rank = (d.is_pareto, d.objectives.get("efficiency", 0))
440	            if cur is None or rank > (cur.is_pareto, cur.objectives.get("efficiency", 0)):
441	                best[key] = d
442	        return list(best.values())
443	
444	    def refresh_figure():
445	        sd = _thin(study_designs) if state.declutter else study_designs
446	        ud = _thin(list(user_designs)) if state.declutter else user_designs
447	        fig = scatter_figure(sd, ud)
448	        if hasattr(ctrl, "figure_update"):
449	            ctrl.figure_update(fig)
450	
451	    @state.change("declutter")
452	    def _on_declutter(**_):
453	        refresh_figure()
454	
455	    def _init_editor(p: dict, feat: Features | None = None):
456	        """Load the parameter-editor sliders from a design's params + features."""
457	        feat = feat or Features()
458	        state.e_n_blades = int(p.get("n_blades", 7))
459	        state.e_stagger_root = float(p.get("stagger_root", 26.0))
460	        state.e_stagger_mid = float(p.get("stagger_mid", 26.0))
461	        state.e_stagger_tip = float(p.get("stagger_tip", 22.0))
462	        state.e_chord_root = float(p.get("chord_root", 34.0))
463	        state.e_chord_mid = float(p.get("chord_mid", 44.0))
464	        state.e_chord_tip = float(p.get("chord_tip", 38.0))
465	        state.e_camber = float(p.get("max_camber", 0.05))
466	        state.e_sweep_mid = float(p.get("sweep_mid", 3.0))
467	        state.e_sweep_tip = float(p.get("sweep_tip", 5.0))
468	        state.e_lean_mid = float(p.get("lean_mid", 14.0))  # circumferential WRAP (deg)
469	        state.e_lean_tip = float(p.get("lean_tip", 26.0))
470	        state.e_le_mid = float(p.get("le_sweep_mid", 0.0))  # leading-edge curve (mm)
471	        state.e_le_tip = float(p.get("le_sweep_tip", 0.0))
472	        state.e_skew_mid = float(p.get("skew_mid", 0.0))    # tangential fine offset (mm)
473	        state.e_skew_tip = float(p.get("skew_tip", 0.0))
474	        state.e_winglet_span = float(p.get("winglet_span", 0.85))  # where the tip winglet begins
475	        state.e_winglet_sweep = float(p.get("winglet_sweep", 0.0))  # tip axial curl (mm), 0=off
476	        state.e_winglet_lean = float(p.get("winglet_lean", 0.0))   # tip circumferential curl (deg)
477	        state.e_hub_radius = float(p.get("hub_radius", 21.5))       # hub radius (mm)
478	        state.e_tip_radius = float(p.get("tip_radius", 56.5))       # tip radius = blade length (mm)
479	        state.e_hub_height = float(p.get("hub_height", 0.0))        # hub height (0 = auto/cover roots)
480	        state.e_hub_profile = str(p.get("hub_profile", "cylinder"))  # cylinder | cone | dome
481	        state.e_hub_nose = float(p.get("hub_nose", 0.0))            # nose height for cone/dome
482	        state.e_thick_root = float(p.get("thickness_root", 0.10))   # blade thickness (frac chord)
483	        state.e_thick_mid = float(p.get("thickness_mid", 0.08))
484	        state.e_thick_tip = float(p.get("thickness_tip", 0.06))
485	        state.e_camber_pos = float(p.get("camber_pos", 0.4))        # max-camber chordwise position
486	        state.e_spacing = float(p.get("spacing_spread", 0.0))       # uneven-spacing spread (0=even)
487	        # Load feature sliders from the design's params (feature-enabled runs + assessed designs
488	        # store them there), falling back to the passed Features. This is why selecting a featured
489	        # result now shows its bio-feature settings instead of resetting them to zero.
490	        state.e_tub_amp = float(p.get("tubercle_amp", feat.tubercle_amp))
491	        state.e_tub_waves = int(p.get("tubercle_waves", feat.tubercle_waves))
492	        state.e_ser_amp = float(p.get("serration_amp", feat.serration_amp))
493	        state.e_ser_waves = int(p.get("serration_waves", feat.serration_waves))
494	        state.e_dim_amp = float(p.get("dimple_amp", feat.dimple_amp))
495	        state.e_dim_rows = int(p.get("dimple_rows", feat.dimple_rows))
496	        state.e_dim_cols = int(p.get("dimple_cols", feat.dimple_cols))
497	
498	    _init_editor({})
499	
500	    def edit_flat() -> dict:
501	        return dict(
502	            n_blades=int(state.e_n_blades),
503	            stagger_root=state.e_stagger_root, stagger_mid=state.e_stagger_mid,
504	            stagger_tip=state.e_stagger_tip, chord_root=state.e_chord_root,
505	            chord_mid=state.e_chord_mid, chord_tip=state.e_chord_tip,
506	            sweep_mid=state.e_sweep_mid, sweep_tip=state.e_sweep_tip,
507	            max_camber=state.e_camber, camber_pos=state.e_camber_pos,
508	            lean_mid=state.e_lean_mid, lean_tip=state.e_lean_tip,
509	            le_sweep_mid=state.e_le_mid, le_sweep_tip=state.e_le_tip,
510	            skew_mid=state.e_skew_mid, skew_tip=state.e_skew_tip,
511	            winglet_span=state.e_winglet_span, winglet_sweep=state.e_winglet_sweep,
512	            winglet_lean=state.e_winglet_lean,
513	            hub_radius=state.e_hub_radius, tip_radius=state.e_tip_radius,
514	            hub_height=state.e_hub_height, hub_profile=state.e_hub_profile,
515	            hub_nose=state.e_hub_nose,
516	            thickness_root=state.e_thick_root, thickness_mid=state.e_thick_mid,
517	            thickness_tip=state.e_thick_tip,
518	            spacing_spread=state.e_spacing, spacing_seed=0,
519	        )
520	
521	    def edit_features() -> Features:
522	        # A feature needs BOTH amplitude and a count to be visible; if the user raises only the
523	        # amplitude slider, auto-fill a sensible count so it actually shows up.
524	        tw = int(state.e_tub_waves) or (6 if state.e_tub_amp > 0 else 0)
525	        sw = int(state.e_ser_waves) or (8 if state.e_ser_amp > 0 else 0)
526	        dr = int(state.e_dim_rows) or (5 if state.e_dim_amp > 0 else 0)
527	        dc = int(state.e_dim_cols) or (5 if state.e_dim_amp > 0 else 0)
528	        return Features(
529	            tubercle_amp=state.e_tub_amp, tubercle_waves=tw,
530	            serration_amp=state.e_ser_amp, serration_waves=sw,
531	            dimple_amp=state.e_dim_amp, dimple_rows=dr, dimple_cols=dc,
532	        )
533	
534	    def randomize_features():
535	        """Roll a random bio-feature combo on the CURRENT geometry — a creativity seed to preview,
536	        assess, or optimize from. Geometry is untouched, so the result stays buildable. At least one
537	        feature is always turned on (each with its count) so you actually get something 'crazy'."""
538	        on = {k: random.random() < 0.6 for k in ("tub", "ser", "dim")}
539	        if not any(on.values()):
540	            on[random.choice(("tub", "ser", "dim"))] = True
541	        state.e_tub_amp = round(random.uniform(0.02, 0.10), 3) if on["tub"] else 0.0
542	        state.e_tub_waves = random.randint(3, 8) if on["tub"] else 0
543	        state.e_ser_amp = round(random.uniform(0.015, 0.06), 3) if on["ser"] else 0.0
544	        state.e_ser_waves = random.randint(4, 12) if on["ser"] else 0
545	        state.e_dim_amp = round(random.uniform(0.10, 0.35), 2) if on["dim"] else 0.0
546	        state.e_dim_rows = random.randint(2, 6) if on["dim"] else 0
547	        state.e_dim_cols = random.randint(2, 6) if on["dim"] else 0
548	        active = ", ".join(k for k, v in on.items() if v)
549	        state.preview_msg = f"🎲 Randomized features ({active}). Press Preview geometry to see it."
550	        state.flush()
551	
552	    def randomize_geometry():
553	        """Roll a random GEOMETRY (blades/angles/chords/sweep/wrap/hub) — a wild starting point to
554	        preview, assess, or optimize from. May land out-of-spec (Preview shows it); that's fine, it's
555	        a creativity seed. Leaves the feature layer alone (that has its own dice)."""
556	        import random as _r
557	        state.e_n_blades = _r.randint(5, 11)
558	        state.e_stagger_root = round(_r.uniform(18, 48), 1)
559	        state.e_stagger_mid = round(_r.uniform(18, 48), 1)
560	        state.e_stagger_tip = round(_r.uniform(16, 40), 1)
561	        state.e_chord_root = round(_r.uniform(16, 40), 1)
562	        state.e_chord_mid = round(_r.uniform(16, 42), 1)
563	        state.e_chord_tip = round(_r.uniform(16, 40), 1)
564	        state.e_sweep_mid = round(_r.uniform(-3, 8), 1)
565	        state.e_sweep_tip = round(_r.uniform(0, 12), 1)
566	        state.e_camber = round(_r.uniform(0.0, 0.06), 3)
567	        state.e_camber_pos = round(_r.uniform(0.3, 0.5), 2)
568	        state.e_lean_mid = round(_r.uniform(0, 25), 1)
569	        state.e_lean_tip = round(_r.uniform(0, 45), 1)
570	        state.e_le_mid = round(_r.uniform(-8, 8), 1)
571	        state.e_le_tip = round(_r.uniform(-8, 8), 1)
572	        state.e_skew_mid = round(_r.uniform(-4, 4), 1)
573	        state.e_skew_tip = round(_r.uniform(-4, 4), 1)
574	        wl = _r.random() < 0.4   # sometimes throw a winglet on for a wild tip
575	        state.e_winglet_span = round(_r.uniform(0.75, 0.9), 2)
576	        state.e_winglet_sweep = round(_r.uniform(4, 12), 1) if wl else 0.0
577	        state.e_winglet_lean = round(_r.uniform(0, 20), 1) if wl else 0.0
578	        state.e_hub_radius = round(_r.uniform(17, 28), 1)
579	        state.e_tip_radius = round(_r.uniform(48, 58), 1)
580	        state.e_thick_root = round(_r.uniform(0.06, 0.12), 3)
581	        state.e_thick_mid = round(_r.uniform(0.05, 0.10), 3)
582	        state.e_thick_tip = round(_r.uniform(0.04, 0.08), 3)
583	        state.e_hub_profile = _r.choice(["cylinder", "cylinder", "cone", "dome"])  # bias to plain
584	        state.e_hub_nose = round(_r.uniform(3, 12), 1) if state.e_hub_profile != "cylinder" else 0.0
585	        state.preview_msg = "🎲 Randomized geometry. Press Preview geometry to see it (may be out-of-spec)."
586	        state.flush()
587	
588	    def build_edit_params():
589	        return blade_from_flat(edit_flat(), edit_features())
590	
591	    def export_stl_current():
592	        """Save the current design as a print-ready STL (motor-mount cup carved) into exports/."""
593	        from fansim.manufacturability.print_export import export_print_ready
594	        params = build_edit_params()
595	        spec = active_spec()
596	        exports = Path("exports")
597	        exports.mkdir(exist_ok=True)
598	        tid = state.selected_trial
599	        name = f"design_{tid}" if tid is not None else "fan_current"
600	        out = exports / f"{name}.stl"
601	        try:
602	            rep = export_print_ready(params, out, mount=spec.motor_mount)
603	        except Exception as exc:  # noqa: BLE001
604	            state.export_msg = f"⚠ Export failed: {type(exc).__name__}: {exc}"
605	            state.flush()
606	            return
607	        wt = "watertight" if rep.ok else "⚠ NON-manifold"
608	        mnt = ("" if rep.mount_fits is None else
609	               ("· mountable" if rep.mount_fits else "· ⚠ hub too small to mount"))
610	        state.export_msg = f"✓ Saved {out.resolve()}  ({wt} {mnt})"
611	        state.flush()
612	
613	    def _build_preview_stl(flat, feat):
614	        """Blocking geometry build in an ISOLATED subprocess (a native OCP crash or a runaway
615	        featured build can't take down the cockpit server — it surfaces as a caught error)."""
616	        from fansim.geometry.isolated import build_stl_isolated
617	        build_stl_isolated(flat, feat, preview_stl, timeout=120.0)
618	
619	    # --- 3D render with constraint aids -----------------------------------------------------------
620	    # render_state remembers the mesh + base color currently shown so the highlight/envelope toggles
621	    # can redraw the SAME model without a rebuild or a camera reset.
622	    render_state = {"path": None, "color": "lightsteelblue"}
623	
624	    def _spec_limits():
625	        """Nominal outer-case limits of the active fan model: (max tip RADIUS mm, max DEPTH mm).
626	        Uses the nominal spec (not leeway) so red = 'past the real fan's envelope'."""
627	        s = active_spec()
628	        return s.tip_dia_mm[1] / 2.0, s.depth_mm[1]
629	
630	    def _out_of_spec_mask(mesh):
631	        """Per-point 1.0 where the geometry exceeds the nominal tip radius or depth budget, else 0.0.
632	        Depth is measured as distance from the model's own z-midplane (no absolute case datum)."""
633	        import numpy as np
634	        pts = mesh.points
635	        r = np.hypot(pts[:, 0], pts[:, 1])
636	        z = pts[:, 2]
637	        tip_r, depth_lim = _spec_limits()
638	        zmid = 0.5 * (float(z.min()) + float(z.max()))
639	        mask = (r > tip_r) | (np.abs(z - zmid) > depth_lim / 2.0)
640	        return mask.astype(float)
641	
642	    def _add_envelope(mesh):
643	        zc = mesh.points[:, 2]
644	        zmid = 0.5 * (float(zc.min()) + float(zc.max()))
645	        tip_r, depth_lim = _spec_limits()
646	        cyl = pv.Cylinder(center=(0, 0, zmid), direction=(0, 0, 1),
647	                          radius=tip_r, height=depth_lim, resolution=64)
648	        plotter.add_mesh(cyl, color="seagreen", opacity=0.10)
649	        try:  # crisp rim/outline so the envelope reads as a box even at low opacity
650	            plotter.add_mesh(cyl.extract_feature_edges(), color="seagreen", line_width=2)
651	        except Exception:  # noqa: BLE001 - edges are cosmetic
652	            pass
653	
654	    def _apply_render(reset: bool = False):
655	        """(Re)draw the current model with the active highlight/envelope options."""
656	        plotter.clear_actors()
657	        p = render_state["path"]
658	        if not p:
659	            return
660	        try:
661	            mesh = pv.read(str(p))
662	        except Exception:  # noqa: BLE001 - nothing to show
663	            return
664	        base = render_state["color"]
665	        if state.highlight_spec:
666	            mask = _out_of_spec_mask(mesh)
667	            if mask.any():  # 2-color map: base where in-spec, red where it breaks the envelope
668	                mesh["spec"] = mask
669	                plotter.add_mesh(mesh, scalars="spec", cmap=[base, "red"], clim=[0, 1],
670	                                 show_scalar_bar=False, smooth_shading=True)
671	            else:
672	                plotter.add_mesh(mesh, color=base, smooth_shading=True)
673	        else:
674	            plotter.add_mesh(mesh, color=base, smooth_shading=True)
675	        if state.show_envelope:
676	            _add_envelope(mesh)
677	        if reset:
678	            plotter.reset_camera()
679	
680	    def _draw(path, color: str):
681	        render_state["path"] = str(path)
682	        render_state["color"] = color
683	        _apply_render(reset=True)
684	
685	    @state.change("highlight_spec", "show_envelope", "fan_model")
686	    def _on_viz_toggle(**_):
687	        _apply_render(reset=False)  # keep the current camera when just toggling an aid
688	        try:
689	            ctrl.view_update()
690	        except Exception:  # noqa: BLE001
691	            pass
692	
693	    def do_preview():
694	        # Async so the "Generating…" indicator shows while the (7-35 s) geometry build runs;
695	        # a synchronous build would freeze the UI with no feedback until it finished.
696	        if state.preview_busy or state.assess_busy:
697	            return
698	        params = build_edit_params()
699	        printable = check_printability(params)
700	        if not printable.printable:
701	            state.preview_msg = f"⚠ Not printable: {printable.reason}"
702	            return
703	        flat, feat = edit_flat(), edit_features()  # serializable inputs for the isolated build
704	
705	        async def task():
706	            state.preview_busy = True
707	            heavy = " (features are heavy — up to ~2 min)" if params.features.active else ""
708	            state.preview_msg = f"⏳ Generating geometry…{heavy}"
709	            state.flush()
710	            loop = asyncio.get_running_loop()
711	            try:
712	                await loop.run_in_executor(None, _build_preview_stl, flat, feat)
713	            except TimeoutError:
714	                state.preview_msg = ("⚠ Geometry build timed out — featured blades are heavy; "
715	                                     "try a lower serration/dimple count (the app is fine).")
716	                state.preview_busy = False
717	                state.flush()
718	                return
719	            except Exception as exc:  # loft/boolean failure or isolated native crash — app survives
720	                state.preview_msg = f"⚠ Geometry failed: {type(exc).__name__} (the app is fine)"
721	                state.preview_busy = False
722	                state.flush()
723	                return
724	            _draw(preview_stl, "darkorange")  # renders with highlight/envelope aids
725	            feats = "features ON" if params.features.active else "smooth"
726	            _, status = spec_status(preview_stl, params, flat)   # spec check now, before any CFD
727	            try:
728	                from fansim.manufacturability.printability_score import grade_printability
729	                print_line = "\n🖨 " + grade_printability(params).summary
730	            except Exception:  # noqa: BLE001 - printability grade is informational
731	                print_line = ""
732	            # Uneven-spacing tonal readout (CFD-validated: cuts the peak tone ~5-6 dB at its best on odd
733	            # blade counts, for free). Predicted from the balanced-spacing pattern, no GPU needed.
734	            tone_line = ""
735	            if params.blade_angles_deg is not None:
736	                try:
737	                    import numpy as _np
738	                    from fansim.acoustics.tonal import peak_tone_reduction_db
739	                    drop = -peak_tone_reduction_db(_np.radians(_np.asarray(params.blade_angles_deg)))
740	                    odd = "" if params.n_blades % 2 else "  (even blade count — odd counts spread the tone more)"
741	                    tone_line = f"\n🔉 Uneven spacing: predicted peak tone −{drop:.1f} dB, free of any flow cost{odd}"
742	                except Exception:  # noqa: BLE001
743	                    tone_line = ""
744	            state.preview_msg = (f"Preview (orange): {params.n_blades} blades, "
745	                                 f"camber {state.e_camber:.3f}, {feats}.\n{status}{print_line}{tone_line}")
746	            state.preview_busy = False
747	            try:
748	                ctrl.view_update()
749	            except Exception:
750	                pass
751	            state.flush()
752	
753	        asynchronous.create_task(task())
754	
755	    # --- Assess (run CFD) + Sweep (regression over one parameter) ---
756	    SWEEP_OPTIONS = [
757	        ("camber", "flat", "max_camber", 0.0, 0.06),
758	        ("blades", "flat", "n_blades", 5.0, 11.0),
759	        ("stagger tip", "flat", "stagger_tip", 20.0, 50.0),
760	        ("sweep tip", "flat", "sweep_tip", 0.0, 15.0),
761	        ("tubercle amp", "tub", "tubercle_amp", 0.0, 0.10),
762	        ("serration amp", "ser", "serration_amp", 0.0, 0.06),
763	        ("dimple depth", "dim", "dimple_amp", 0.0, 0.35),
764	    ]
765	    state.sweep_items = [o[0] for o in SWEEP_OPTIONS]
766	
767	    def _feat_dict() -> dict:
768	        f = edit_features()
769	        return dict(tubercle_amp=f.tubercle_amp, tubercle_waves=f.tubercle_waves,
770	                    serration_amp=f.serration_amp, serration_waves=f.serration_waves,
771	                    dimple_amp=f.dimple_amp, dimple_rows=f.dimple_rows,
772	                    dimple_cols=f.dimple_cols)
773	
774	    # --- Edited-since-assessment tracking ---------------------------------------------------------
775	    # EDITOR_VARS is every slider that feeds the geometry/CFD, so a change to ANY of them can make a
776	    # prior assessment stale. sel_sig holds the signature of the selected design's assessed config.
777	    EDITOR_VARS = (
778	        "e_n_blades", "e_stagger_root", "e_stagger_mid", "e_stagger_tip",
779	        "e_chord_root", "e_chord_mid", "e_chord_tip", "e_sweep_mid", "e_sweep_tip",
780	        "e_camber", "e_camber_pos", "e_lean_mid", "e_lean_tip", "e_le_mid", "e_le_tip",
781	        "e_skew_mid", "e_skew_tip", "e_winglet_span", "e_winglet_sweep", "e_winglet_lean",
782	        "e_hub_radius", "e_tip_radius", "e_hub_height", "e_hub_profile", "e_hub_nose",
783	        "e_thick_root", "e_thick_mid", "e_thick_tip", "e_spacing",
784	        "e_tub_amp", "e_tub_waves", "e_ser_amp", "e_ser_waves", "e_dim_amp", "e_dim_rows", "e_dim_cols",
785	    )
786	    sel_sig = [None]  # signature of the currently-selected design's assessed geometry+features
787	
788	    def _editor_sig() -> dict:
789	        """Normalized signature of the current editor state (geometry + features), rounded so tiny
790	        float noise doesn't read as an edit."""
791	        s = {**edit_flat(), **_feat_dict()}
792	        return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in s.items()}
793	
794	    def _set_baseline():
795	        """Mark the current editor state as the assessed baseline (not stale)."""
796	        sel_sig[0] = _editor_sig()
797	        state.edited_stale = False
798	        state.stale_msg = ""
799	
800	    def _recompute_stale(**_):
801	        if sel_sig[0] is None:
802	            return
803	        stale = _editor_sig() != sel_sig[0]
804	        state.edited_stale = stale
805	        state.stale_msg = ("⚠ Edited since assessment — the shown CFM/efficiency are for the "
806	                           "un-edited design. Press Assess to evaluate your changes." if stale else "")
807	
808	    state.change(*EDITOR_VARS)(_recompute_stale)
809	
810	    def load_catalog_design(design_id=None, **_):
811	        """Load ANY catalogued design (from any run) into the editor — breaks the single-run limit.
812	        Its params fill the sliders; press Preview to see it. Its sim numbers + any real measurement
813	        are shown so you can compare across runs without relaunching the cockpit."""
814	        if not design_id:
815	            return
816	        e = get_entry(design_id)
817	        if e is None:
818	            state.catalog_info = f"'{design_id}' not in the catalog (rebuild it if it's new)."
819	            state.flush()
820	            return
821	        _init_editor(e.params)          # params fill the editor sliders (features fall back to 0)
822	        _set_baseline()                 # editor now matches this design — not stale until edited
823	        parts = [f"Loaded {e.design_id}", f"{e.source}"]
824	        if isinstance(e.cfm_free, (int, float)):
825	            parts.append(f"sim {e.cfm_free:.0f}/{e.cfm_load or 0:.0f} CFM  eff {e.efficiency or 0:.0f}%")
826	        try:  # mountability + print difficulty for the loaded design (cheap, no CFD)
827	            from fansim.fan_spec import mount_min_hub_radius
828	            from fansim.manufacturability.printability_score import grade_printability
829	            lp = blade_from_flat(e.params)
830	            need = mount_min_hub_radius(active_spec())
831	            parts.append("mountable" if (need is None or lp.hub_radius >= need) else "NOT mountable")
832	            parts.append(f"print {grade_printability(lp).difficulty:.0f}/100")
833	        except Exception:  # noqa: BLE001
834	            pass
835	        if e.has_measurement and e.measured_cfm is not None:
836	            parts.append(f"MEASURED {e.measured_cfm:.0f} CFM (sim {e.cfm_error_pct:+.0f}%)"
837	                         if e.cfm_error_pct is not None else f"MEASURED {e.measured_cfm:.0f} CFM")
838	        state.catalog_info = "  ·  ".join(parts)
839	        state.preview_msg = f"Loaded {e.design_id} from the catalog. Press Preview geometry to see it."
840	        state.flush()
841	
842	    def active_spec():
843	        """The selected fan model with the current leeway margins applied (nominal untouched)."""
844	        return dataclasses.replace(
845	            get_fan_spec(state.fan_model),
846	            leeway_tip_dia_mm=float(state.lee_tip), leeway_depth_mm=float(state.lee_depth),
847	            leeway_weight_g=float(state.lee_weight), over_voltage_v=float(state.lee_overvolt))
848	
849	    def _depth_driver_msg(flat):
850	        """Name the top depth-driving sliders FOR THIS design, with mm each would save."""
851	        try:
852	            drivers = _depth_drivers(flat)
853	        except Exception:  # noqa: BLE001
854	            return ""
855	        if not drivers:
856	            return ""
857	        return "  Top depth drivers here: " + ", ".join(f"{lab} (~{mm:.0f} mm)" for lab, mm in drivers)
858	
859	    def spec_status(stl_path, params, flat=None):
860	        """Check the BUILT geometry against the active fan model (envelope/hub/depth/weight) with NO
861	        CFD -- lets us flag an out-of-spec design at Preview instead of after an Assess. On a depth
862	        issue, names the specific sliders driving it for THIS design."""
863	        spec = active_spec()
864	        try:
865	            import trimesh
866	            m = trimesh.load(str(stl_path))
867	            (xmin, ymin, zmin), (xmax, ymax, zmax) = m.bounds
868	            dia = 2.0 * max(abs(xmin), abs(xmax), abs(ymin), abs(ymax))
869	            depth = zmax - zmin
870	            weight = estimate_weight_g(abs(float(m.volume)), spec.material)
871	        except Exception:  # noqa: BLE001 - if we can't measure it, don't block
872	            return True, ""
873	        ok, reason = check_build(spec, dia, 2.0 * params.hub_radius, depth, weight)
874	        depth_msg = _depth_driver_msg(flat) if (flat and "depth" in reason.lower()) else ""
875	        if not ok:
876	            return False, f"⚠ Out of spec — Assess will reject: {reason}. {_reject_hint(reason)}{depth_msg}"
877	        over = over_spec_flags(spec, dia, depth, weight)
878	        if over:
879	            dm = _depth_driver_msg(flat) if (flat and any("depth" in o for o in over)) else ""
880	            return True, "⚠ OVER-SPEC (allowed via leeway): " + "; ".join(over) + dm
881	        return True, f"✓ fits {spec.name} (dia {dia:.0f} mm, depth {depth:.0f} mm, {weight:.0f} g)"
882	
883	    def _blocking_eval(flat, features, workdir):
884	        # Isolated subprocess: an OCP native crash / OpenFOAM hang can't take the cockpit down.
885	        return evaluate_candidate_isolated(flat, features, workdir, spec=active_spec(),
886	                                           procs=8, base_cell=0.006, iters=500)
887	
888	    async def _assess(params, flat, label):
889	        tid = next_id[0]
890	        next_id[0] += 1
891	        workdir = assess_dir / f"design_{tid}"
892	        loop = asyncio.get_running_loop()
893	        result = await loop.run_in_executor(None, _blocking_eval, flat, params.features, workdir)
894	        if not result.feasible:
895	            hint = _reject_hint(result.reason)
896	            state.assess_msg = f"{label}: rejected — {result.reason}" + (f"\n{hint}" if hint else "")
897	            state.flush()
898	            return None
899	        stl = workdir / "impeller.stl"
900	        d = Design(
901	            trial=tid, params=dict(flat),
902	            objectives={"cfm_free": result.cfm_free, "cfm_load": result.cfm_load,
903	                        "efficiency": result.efficiency},
904	            feasible=True, is_pareto=False,
905	            stl_path=stl if stl.exists() else None,
906	            extra={"n_blades": params.n_blades, "source": "user",
907	                   "source_run": run_dir.name,
908	                   "over_spec": list(result.over_spec), "fan_model": state.fan_model,
909	                   "actual_rpm": round(result.actual_rpm)},
910	        )
911	        # persist so the design survives a cockpit restart (reloaded by _load_assessed_designs)
912	        try:
913	            (workdir / "design.json").write_text(json.dumps(
914	                {"trial": d.trial, "params": d.params, "objectives": d.objectives,
915	                 "feasible": True, "reason": d.reason, "extra": d.extra}, indent=2))
916	        except Exception:  # noqa: BLE001 - persistence is best-effort; keep the in-memory design
917	            pass
918	        user_designs.append(d)
919	        by_trial[tid] = d
920	        refresh_items()
921	        refresh_figure()
922	        state.flush()
923	        return d
924	
925	    def on_assess():
926	        if state.assess_busy:
927	            return
928	        # store features alongside geometry so an assessed design's settings reload when reselected
929	        params, flat = build_edit_params(), {**edit_flat(), **_feat_dict()}
930	
931	        async def task():
932	            state.assess_busy = True
933	            state.assess_msg = "Running CFD on your design… (~4 min)"
934	            state.flush()
935	            try:
936	                d = await _assess(params, flat, "Assess")
937	                if d:
938	                    o = d.objectives
939	                    over = d.extra.get("over_spec") or []
940	                    tag = ("  ⚠ OVER-SPEC: " + "; ".join(over)) if over else ""
941	                    spec = get_fan_spec(d.extra.get("fan_model", "a12x25"))
942	                    rpm = d.extra.get("actual_rpm", 0)
943	                    rpm_tag = (f"  ⚙ motor-limited: {rpm:.0f} RPM ({100*rpm/spec.rpm:.0f}%)"
944	                               if rpm and rpm < spec.rpm * 0.995 else "")
945	                    state.assess_msg = (f"Done ◆#{d.trial}: free {o['cfm_free']:.1f}  "
946	                                        f"load {o['cfm_load']:.1f}  eff {o['efficiency']:.1f}%"
947	                                        f"  (added to plot){rpm_tag}{tag}")
948	                    state.selected_trial = d.trial
949	                    _set_baseline()  # the editor now matches the just-assessed design
950	            except Exception as exc:  # noqa: BLE001 - surface eval errors; never a stuck/dead UI
951	                state.assess_msg = f"Assess failed: {type(exc).__name__}: {exc}"
952	            finally:
953	                state.assess_busy = False
954	                state.flush()
955	
956	        asynchronous.create_task(task())
957	
958	    def on_sweep():
959	        if state.assess_busy:
960	            return
961	        import numpy as np
962	
963	        opt = next((o for o in SWEEP_OPTIONS if o[0] == state.sweep_param), SWEEP_OPTIONS[0])
964	        label, kind, field, mn, mx = opt
965	        base_flat, base_feat = edit_flat(), _feat_dict()
966	        steps = max(2, int(state.sweep_steps))
967	        raw = list(np.linspace(mn, mx, steps))
968	        values = sorted(set(int(round(v)) for v in raw)) if field == "n_blades" else raw
969	
970	        async def task():
971	            state.assess_busy = True
972	            done = 0
973	            try:
974	                for i, val in enumerate(values):
975	                    flat, feat = dict(base_flat), dict(base_feat)
976	                    if kind == "flat":
977	                        flat[field] = int(val) if field == "n_blades" else float(val)
978	                    else:
979	                        feat[field] = float(val)
980	                        if kind == "tub" and feat["tubercle_waves"] == 0:
981	                            feat["tubercle_waves"] = 6
982	                        if kind == "ser" and feat["serration_waves"] == 0:
983	                            feat["serration_waves"] = 8
984	                        if kind == "dim":
985	                            feat["dimple_rows"] = feat["dimple_rows"] or 5
986	                            feat["dimple_cols"] = feat["dimple_cols"] or 5
987	                    params = blade_from_flat(flat, Features(**feat))
988	                    state.assess_msg = f"Sweep {label} {i+1}/{len(values)} = {val:g}: running CFD…"
989	                    state.flush()
990	                    if not check_printability(params).printable:

================================================================================
## window @ 2026-08-30T18:46:20  (lines 991-1305)

991	                        continue
992	                    try:  # one design failing shouldn't abort the whole sweep
993	                        if await _assess(params, flat, f"sweep {label}={val:g}"):
994	                            done += 1
995	                    except Exception as exc:  # noqa: BLE001
996	                        state.assess_msg = f"Sweep {label}={val:g} failed: {type(exc).__name__}: {exc}"
997	                        state.flush()
998	                state.assess_msg = f"Sweep of {label} done: {done} ◆ runs added to the plot."
999	            finally:
1000	                state.assess_busy = False
1001	                state.flush()
1002	
1003	        asynchronous.create_task(task())
1004	
1005	    def select(trial: int | None):
1006	        print(f"[cockpit] select({trial!r})", flush=True)
1007	        if trial is None:
1008	            return
1009	        d = by_trial.get(int(trial))
1010	        if d is None:
1011	            return
1012	        if d.has_model:
1013	            _draw(d.stl_path, "lightsteelblue")  # renders with highlight/envelope aids
1014	        else:
1015	            plotter.clear_actors()
1016	        o, p = d.objectives, d.params
1017	        state.selected_trial = int(trial)
1018	        state.info_lines = [
1019	            f"Trial {d.trial}   {d.extra.get('n_blades')} blades"
1020	            + ("   ★ Pareto" if d.is_pareto else ""),
1021	            f"CFM free {o['cfm_free']:.1f}   CFM load {o['cfm_load']:.1f}"
1022	            f"   efficiency {o['efficiency']:.1f}%",
1023	            f"stagger r/m/t {p.get('stagger_root',0):.0f}/{p.get('stagger_mid',0):.0f}"
1024	            f"/{p.get('stagger_tip',0):.0f}   camber {p.get('max_camber',0):.3f}",
1025	            f"chord r/m/t {p.get('chord_root',0):.1f}/{p.get('chord_mid',0):.1f}"
1026	            f"/{p.get('chord_tip',0):.1f}   sweep m/t {p.get('sweep_mid',0):.1f}"
1027	            f"/{p.get('sweep_tip',0):.1f}",
1028	        ]
1029	        rpm = d.extra.get("actual_rpm", 0)
1030	        spec = get_fan_spec(d.extra.get("fan_model", "a12x25"))
1031	        if rpm and rpm < spec.rpm * 0.995:
1032	            state.info_lines.append(f"⚙ motor-limited: runs at {rpm:.0f} RPM "
1033	                                    f"({100*rpm/spec.rpm:.0f}% of {spec.rpm:.0f}) — flow already derated")
1034	        if d.extra.get("over_spec"):
1035	            state.info_lines.append("⚠ OVER-SPEC: " + "; ".join(d.extra["over_spec"]))
1036	        _init_editor(p)  # load the editor sliders from the selected design
1037	        _set_baseline()  # editor now matches the assessed design — not stale until edited
1038	        state.preview_msg = "Edit the sliders below, then press Preview geometry."
1039	        try:
1040	            ctrl.view_update()
1041	        except Exception:
1042	            pass
1043	
1044	    @state.change("selected_trial")
1045	    def _on_dropdown(selected_trial=None, **_):
1046	        select(selected_trial)
1047	
1048	    def _mf(v):
1049	        """Coerce a text-field value to float or None (blank fields come back as '' / None)."""
1050	        try:
1051	            return float(v) if v not in (None, "", "None") else None
1052	        except (TypeError, ValueError):
1053	            return None
1054	
1055	    def save_measurement():
1056	        """Save what the user physically measured for the selected design, tied to its sim numbers."""
1057	        tid = state.selected_trial
1058	        d = by_trial.get(int(tid)) if tid is not None else None
1059	        if d is None:
1060	            state.meas_msg = "⚠ Select a design first (click a point or use the dropdown)."
1061	            state.flush(); return
1062	        if _mf(state.meas_cfm) is None and _mf(state.meas_static) is None and _mf(state.meas_noise) is None:
1063	            state.meas_msg = "⚠ Enter at least one measured value (CFM / static Pa / dB(A))."
1064	            state.flush(); return
1065	        run = d.extra.get("source_run") or run_dir.name
1066	        design_id = make_design_id(run, d.trial)
1067	        sim = {"cfm_free": d.objectives.get("cfm_free"), "cfm_load": d.objectives.get("cfm_load"),
1068	               "efficiency": d.objectives.get("efficiency"), "actual_rpm": d.extra.get("actual_rpm")}
1069	        rpm = _mf(state.meas_rpm) or d.extra.get("actual_rpm") or active_spec().rpm
1070	        pt = MeasuredPoint(rpm=float(rpm), cfm=_mf(state.meas_cfm),
1071	                           static_pressure_pa=_mf(state.meas_static), noise_dba=_mf(state.meas_noise),
1072	                           source=state.meas_instrument or "")
1073	        rec = record_measurement(design_id, pt, run=run, trial=d.trial,
1074	                                 stl_path=str(d.stl_path) if d.has_model else "",
1075	                                 material=active_spec().material, sim=sim,
1076	                                 instrument=state.meas_instrument, notes=state.meas_notes)
1077	        last = sim_vs_real(rec)[-1]
1078	        parts = []
1079	        if "cfm" in last:
1080	            parts.append(f"CFM {last['cfm']['measured']:.1f} vs sim free {last['cfm']['sim']:.1f} "
1081	                         f"(sim over-reads {last['cfm']['pct_error']:+.0f}%)")
1082	        if "noise_dba" in last:
1083	            parts.append(f"noise {last['noise_dba']['measured']:.1f} dBA "
1084	                         f"(Δ{last['noise_dba']['delta_db']:+.1f} vs sim)")
1085	        state.meas_msg = (f"✓ Saved to validation/measurements/ for {design_id} "
1086	                          f"({len(rec.measured)} point(s)). " + "  ".join(parts))
1087	        state.flush()
1088	
1089	    def on_plotly_click(trial=None):
1090	        # We receive ONLY the clicked point's customdata (the trial id), not the whole plotly event:
1091	        # the full $event contains non-serializable fields (functions/DOM refs) that fail to marshal to
1092	        # the server, so the click never arrived. Extracting customdata client-side (see the binding)
1093	        # sends a plain number that serializes cleanly.
1094	        if trial is not None:
1095	            state.selected_trial = int(trial)
1096	            state.flush()  # push the new selection back so the Design dropdown syncs to the clicked point
1097	
1098	    with SinglePageLayout(server) as layout:
1099	        layout.title.set_text("Fan-simulator Cockpit")
1100	        with layout.content:
1101	            with v3.VContainer(fluid=True, classes="pa-2"):
1102	                with v3.VRow(no_gutters=True):
1103	                    with v3.VCol(cols=6, classes="pr-2"):
1104	                        v3.VSwitch(v_model=("declutter",), density="compact", hide_details=True,
1105	                                   inset=True, color="primary", classes="ml-2",
1106	                                   label="Declutter (hide near-duplicate designs)")
1107	                        fig_widget = plotly_widgets.Figure(
1108	                            figure=scatter_figure(study_designs, user_designs),
1109	                            # send ONLY the clicked point's customdata (trial id) — the full $event has
1110	                            # non-serializable fields that silently break the round-trip to the server.
1111	                            click=(on_plotly_click, "[$event?.points?.[0]?.customdata]"),
1112	                            style="width:100%;",
1113	                        )
1114	                    with v3.VCol(cols=6):
1115	                        with v3.VCard(classes="mb-2 pa-3"):
1116	                            v3.VSelect(
1117	                                label="Design",
1118	                                v_model=("selected_trial",),
1119	                                items=("trial_items",),
1120	                                density="compact", variant="outlined",
1121	                                hide_details=True,
1122	                                update_modelValue=(select, "[$event]"),
1123	                            )
1124	                            html.Div(
1125	                                "{{ line }}",
1126	                                v_for="line in info_lines",
1127	                                classes="text-body-2 mt-2",
1128	                            )
1129	                        with v3.VExpansionPanels(classes="mb-2"):
1130	                            with v3.VExpansionPanel(title="Browse all designs (catalog)"):
1131	                                with v3.VExpansionPanelText():
1132	                                    v3.VSelect(label="Any design, any run", v_model=("catalog_sel",),
1133	                                               items=("catalog_items",), density="compact",
1134	                                               variant="outlined", hide_details=True,
1135	                                               update_modelValue=(load_catalog_design, "[$event]"))
1136	                                    html.Div("{{ catalog_info }}", classes="text-caption mt-2",
1137	                                             style="white-space: pre-line")
1138	                        with v3.VCard(classes="mb-2 pa-3"):
1139	                            html.Div("Modify design — hover any slider for a min/max picture + what it does",
1140	                                     classes="text-caption mb-1")
1141	                            with v3.VExpansionPanels(variant="accordion", multiple=True):
1142	                                with v3.VExpansionPanel(title="Geometry"):
1143	                                    with v3.VExpansionPanelText():
1144	                                        v3.VBtn("🎲 Randomize geometry", size="x-small",
1145	                                                variant="tonal", color="secondary", block=True,
1146	                                                click=(randomize_geometry,), classes="mb-3")
1147	                                        _slider("Blades", "e_n_blades", 5, 11, 1)
1148	                                        _slider("Camber (curve)", "e_camber", 0.0, 0.06, 0.005)
1149	                                        _slider("Stagger root", "e_stagger_root", 15, 55, 1)
1150	                                        _slider("Stagger mid", "e_stagger_mid", 15, 55, 1)
1151	                                        _slider("Stagger tip", "e_stagger_tip", 15, 55, 1)
1152	                                        _slider("Chord root", "e_chord_root", 14, 42, 0.5)
1153	                                        _slider("Chord mid", "e_chord_mid", 14, 42, 0.5)
1154	                                        _slider("Chord tip", "e_chord_tip", 14, 42, 0.5)
1155	                                        _slider("Wrap mid (deg)", "e_lean_mid", 0, 30, 1)
1156	                                        _slider("Wrap tip (deg)", "e_lean_tip", 0, 45, 1)
1157	                                        _slider("Sweep mid", "e_sweep_mid", -3, 8, 0.5)
1158	                                        _slider("Sweep tip", "e_sweep_tip", 0, 15, 0.5)
1159	                                        _slider("LE curve mid (mm)", "e_le_mid", -8, 8, 0.5)
1160	                                        _slider("LE curve tip (mm)", "e_le_tip", -8, 8, 0.5)
1161	                                        _slider("Skew mid (mm)", "e_skew_mid", -6, 6, 0.5)
1162	                                        _slider("Skew tip (mm)", "e_skew_tip", -6, 6, 0.5)
1163	                                        _slider("Winglet start (span)", "e_winglet_span", 0.6, 0.95, 0.05)
1164	                                        _slider("Winglet sweep (mm)", "e_winglet_sweep", 0, 15, 0.5)
1165	                                        _slider("Winglet lean (deg)", "e_winglet_lean", 0, 30, 1)
1166	                                        _slider("Hub radius (mm)", "e_hub_radius", 15, 35, 0.5)
1167	                                        _slider("Tip radius / length (mm)", "e_tip_radius", 45, 59, 0.5)
1168	                                        _slider("Hub height (mm, 0=auto)", "e_hub_height", 0, 30, 0.5)
1169	                                        v3.VSelect(label="Hub profile", v_model=("e_hub_profile",),
1170	                                                   items=("hub_profiles",), density="compact",
1171	                                                   variant="outlined", hide_details=True,
1172	                                                   classes="mb-3")
1173	                                        _slider("Hub nose (mm, cone/dome)", "e_hub_nose", 0, 15, 0.5)
1174	                                        _slider("Camber position", "e_camber_pos", 0.2, 0.6, 0.05)
1175	                                        _slider("Thickness root", "e_thick_root", 0.03, 0.15, 0.01)
1176	                                        _slider("Thickness mid", "e_thick_mid", 0.03, 0.15, 0.01)
1177	                                        _slider("Thickness tip", "e_thick_tip", 0.03, 0.15, 0.01)
1178	                                        _slider("Uneven spacing", "e_spacing", 0.0, 0.6, 0.05)
1179	                                with v3.VExpansionPanel(title="Features (bio-inspired)"):
1180	                                    with v3.VExpansionPanelText():
1181	                                        v3.VBtn("🎲 Randomize features", size="x-small",
1182	                                                variant="tonal", color="secondary", block=True,
1183	                                                click=(randomize_features,), classes="mb-3")
1184	                                        _slider("Tubercle amp", "e_tub_amp", 0.0, 0.10, 0.01)
1185	                                        _slider("Tubercle waves", "e_tub_waves", 0, 8, 1)
1186	                                        _slider("Serration amp", "e_ser_amp", 0.0, 0.06, 0.005)
1187	                                        _slider("Serration teeth", "e_ser_waves", 0, 12, 1)
1188	                                        _slider("Dimple depth", "e_dim_amp", 0.0, 0.35, 0.05)
1189	                                        _slider("Dimple rows", "e_dim_rows", 0, 6, 1)
1190	                                        _slider("Dimple cols", "e_dim_cols", 0, 6, 1)
1191	                            with v3.VRow(no_gutters=True, classes="mt-2"):
1192	                                v3.VBtn("Preview geometry", color="primary", size="small",
1193	                                        click=(do_preview,), classes="mr-2",
1194	                                        loading=("preview_busy",),
1195	                                        disabled=("preview_busy || assess_busy",))
1196	                                v3.VBtn("Reset", size="small", variant="tonal",
1197	                                        click=(select, "[selected_trial]"), classes="mr-2")
1198	                                v3.VBtn("💾 Export STL", size="small", variant="tonal",
1199	                                        color="primary", click=(export_stl_current,))
1200	                            html.Div("{{ preview_msg }}", classes="text-caption mt-2",
1201	                                     style="white-space: pre-line")
1202	                            html.Div("{{ export_msg }}", classes="text-caption mt-1",
1203	                                     style="white-space: pre-line")
1204	                        with v3.VExpansionPanels(classes="mb-2"):
1205	                            with v3.VExpansionPanel(title="Fan model & leeway"):
1206	                                with v3.VExpansionPanelText():
1207	                                    with v3.VRow(no_gutters=True, classes="align-center"):
1208	                                        with v3.VCol(cols=8, classes="pr-1"):
1209	                                            v3.VSelect(label="Fan model", v_model=("fan_model",),
1210	                                                       items=("fan_models",), density="compact",
1211	                                                       hide_details=True)
1212	                                        with v3.VCol(cols=4):
1213	                                            v3.VBtn("Reload", size="x-small", variant="tonal",
1214	                                                    click=(reload_models,))
1215	                                    html.Div("{{ model_info }}", classes="text-caption my-1")
1216	                                    with v3.VExpansionPanels(classes="mt-1"):
1217	                                        with v3.VExpansionPanel(
1218	                                                title="Leeway (allow exceeding nominal → over-spec)"):
1219	                                            with v3.VExpansionPanelText():
1220	                                                _slider("Tip past frame (mm)", "lee_tip", 0, 10, 0.5)
1221	                                                _slider("Extra depth Z (mm)", "lee_depth", 0, 12, 0.5)
1222	                                                _slider("Over-voltage (V)", "lee_overvolt", 0, 12, 0.5)
1223	                                                _slider("Extra weight (g)", "lee_weight", 0, 40, 1)
1224	                        with v3.VCard(classes="mb-2 pa-3"):
1225	                            html.Div("Assess & sweep (runs CFD)",
1226	                                     classes="text-subtitle-2 mb-1")
1227	                            v3.VAlert("{{ stale_msg }}", v_if="edited_stale", type="warning",
1228	                                      density="compact", variant="tonal", classes="mb-2",
1229	                                      style="white-space: pre-line")
1230	                            v3.VBtn("Assess this design", color="success", size="small",
1231	                                    block=True, click=(on_assess,),
1232	                                    loading=("assess_busy",), disabled=("assess_busy",))
1233	                            with v3.VRow(no_gutters=True, classes="mt-2 align-center"):
1234	                                with v3.VCol(cols=6, classes="pr-1"):
1235	                                    v3.VSelect(label="Sweep", v_model=("sweep_param",),
1236	                                               items=("sweep_items",), density="compact",
1237	                                               variant="outlined", hide_details=True)
1238	                                with v3.VCol(cols=3, classes="px-1"):
1239	                                    v3.VTextField(label="steps", v_model=("sweep_steps",),
1240	                                                  type="number", density="compact",
1241	                                                  variant="outlined", hide_details=True)
1242	                                with v3.VCol(cols=3, classes="pl-1"):
1243	                                    v3.VBtn("Run", size="small", color="success",
1244	                                            variant="tonal", click=(on_sweep,),
1245	                                            disabled=("assess_busy",))
1246	                            html.Div("{{ assess_msg }}", classes="text-caption mt-2",
1247	                                     style="white-space: pre-line")
1248	                        with v3.VExpansionPanels(classes="mb-2"):
1249	                            with v3.VExpansionPanel(title="Record measurement (physical)"):
1250	                                with v3.VExpansionPanelText():
1251	                                    html.Div("Printed + tested a design? Enter what you measured — it's "
1252	                                             "saved to validation/measurements/ tied to this design's sim "
1253	                                             "numbers, and compared. (Select the design first.)",
1254	                                             classes="text-caption mb-2")
1255	                                    with v3.VRow(no_gutters=True):
1256	                                        with v3.VCol(cols=6, classes="pr-1"):
1257	                                            v3.VTextField(label="Measured CFM", v_model=("meas_cfm",),
1258	                                                          type="number", density="compact",
1259	                                                          variant="outlined", hide_details=True,
1260	                                                          classes="mb-2")
1261	                                        with v3.VCol(cols=6, classes="pl-1"):
1262	                                            v3.VTextField(label="Static Pa", v_model=("meas_static",),
1263	                                                          type="number", density="compact",
1264	                                                          variant="outlined", hide_details=True,
1265	                                                          classes="mb-2")
1266	                                    with v3.VRow(no_gutters=True):
1267	                                        with v3.VCol(cols=6, classes="pr-1"):
1268	                                            v3.VTextField(label="Noise dB(A)", v_model=("meas_noise",),
1269	                                                          type="number", density="compact",
1270	                                                          variant="outlined", hide_details=True,
1271	                                                          classes="mb-2")
1272	                                        with v3.VCol(cols=6, classes="pl-1"):
1273	                                            v3.VTextField(label="RPM", v_model=("meas_rpm",),
1274	                                                          type="number", density="compact",
1275	                                                          variant="outlined", hide_details=True,
1276	                                                          classes="mb-2")
1277	                                    v3.VTextField(label="Instrument", v_model=("meas_instrument",),
1278	                                                  density="compact", variant="outlined",
1279	                                                  hide_details=True, classes="mb-2")
1280	                                    v3.VTextField(label="Notes", v_model=("meas_notes",),
1281	                                                  density="compact", variant="outlined",
1282	                                                  hide_details=True, classes="mb-2")
1283	                                    v3.VBtn("Save measurement", color="primary", size="small",
1284	                                            block=True, click=(save_measurement,))
1285	                                    html.Div("{{ meas_msg }}", classes="text-caption mt-2",
1286	                                             style="white-space: pre-line")
1287	                        with v3.VCard(classes="pa-2"):
1288	                            with v3.VRow(no_gutters=True, classes="align-center"):
1289	                                with v3.VCol(cols=7):
1290	                                    v3.VSwitch(v_model=("highlight_spec",), density="compact",
1291	                                               hide_details=True, color="error", inset=True,
1292	                                               label="Highlight out-of-spec (red)")
1293	                                with v3.VCol(cols=5):
1294	                                    v3.VSwitch(v_model=("show_envelope",), density="compact",
1295	                                               hide_details=True, color="success", inset=True,
1296	                                               label="Case envelope")
1297	                            html.Div("Red = geometry past the fan's nominal tip diameter or depth. "
1298	                                     "Envelope = the max tip-dia × depth the blade must fit inside.",
1299	                                     classes="text-caption text-medium-emphasis")
1300	                        with v3.VCard(style="height:420px;"):
1301	                            view = plotter_ui(plotter)
1302	    ctrl.view_update = view.update
1303	    ctrl.figure_update = fig_widget.update
1304	    return server
1305

================================================================================
## window @ 2026-08-30T23:04:39  (lines 756-773)

756	        if not printable.printable:
757	            state.preview_msg = f"⚠ Not printable: {printable.reason}"
758	            return
759	        flat, feat = edit_flat(), edit_features()  # serializable inputs for the isolated build
760	
761	        async def task():
762	            state.preview_busy = True
763	            heavy = " (features are heavy — up to ~2 min)" if params.features.active else ""
764	            state.preview_msg = f"⏳ Generating geometry…{heavy}"
765	            state.flush()
766	            loop = asyncio.get_running_loop()
767	            try:
768	                await loop.run_in_executor(None, _build_preview_stl, flat, feat)
769	            except TimeoutError:
770	                state.preview_msg = ("⚠ Geometry build timed out — featured blades are heavy; "
771	                                     "try a lower serration/dimple count (the app is fine).")
772	                state.preview_busy = False
773	                state.flush()

================================================================================
## window @ 2026-08-30T23:30:03  (lines 592-659)

592	        state.e_thick_tip = round(_r.uniform(0.04, 0.08), 3)
593	        state.e_hub_profile = _r.choice(["cylinder", "cylinder", "cone", "dome"])  # bias to plain
594	        state.e_hub_nose = round(_r.uniform(3, 12), 1) if state.e_hub_profile != "cylinder" else 0.0
595	        state.preview_msg = "🎲 Randomized geometry. Press Preview geometry to see it (may be out-of-spec)."
596	        state.flush()
597	
598	    def build_edit_params():
599	        return blade_from_flat(edit_flat(), edit_features())
600	
601	    def export_stl_current():
602	        """Save the current design as a print-ready STL with the motor-mount cup carved into the hub.
603	
604	        Two things the earlier version got wrong (both fixed here):
605	        - Filenames are now TIMESTAMPED (design_<trial>_<YYYYmmdd-HHMMSS>.stl) so each export is its
606	          own file instead of overwriting fan_current.stl every time.
607	        - The motor cup can only be carved when the hub is wide enough to house the motor
608	          (hub_radius >= cavity/2 + wall). Aero-optimized hubs are too narrow, so the export used to
609	          come out as a SOLID hub with no cavity. Now, if the hub is too small, we widen it just enough
610	          to fit the real motor, update the Hub-radius slider to match, and say so — so the exported
611	          part actually slips over the fan's 50 mm motor hub. A companion .md print sheet is written too.
612	        """
613	        from datetime import datetime
614	
615	        from fansim.fan_spec import mount_min_hub_radius
616	        from fansim.manufacturability.print_export import (
617	            balance_summary, export_print_ready, print_readme, recommend_print_settings,
618	        )
619	        spec = active_spec()
620	        # Widen the hub to the minimum mountable radius if it's too narrow, so the cup carves at all.
621	        # Gated by the "Fit hub to motor on export" switch — off = keep the aero hub (cup won't carve
622	        # on a too-small hub, and the message says so) for users mounting the fan a different way.
623	        need = mount_min_hub_radius(spec)
624	        grew_from = None
625	        if state.export_fit_hub and need is not None and float(state.e_hub_radius) < need:
626	            grew_from = float(state.e_hub_radius)
627	            state.e_hub_radius = round(need + 0.05, 2)   # just clears the fit test
628	        params = build_edit_params()                     # rebuilt with the (possibly widened) hub
629	        exports = Path("exports")
630	        exports.mkdir(exist_ok=True)
631	        tid = state.selected_trial
632	        base = f"design_{tid}" if tid is not None else "fan"
633	        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
634	        out = exports / f"{base}_{stamp}.stl"
635	        try:
636	            rep = export_print_ready(params, out, mount=spec.motor_mount)
637	        except Exception as exc:  # noqa: BLE001
638	            state.export_msg = f"⚠ Export failed: {type(exc).__name__}: {exc}"
639	            state.flush()
640	            return
641	        try:  # companion print sheet (documents the cup dimensions, material, balance) — best-effort
642	            settings = recommend_print_settings(spec.material)
643	            bal = balance_summary(params, spec.rpm)
644	            (out.with_suffix(".md")).write_text(
645	                print_readme(out.stem, params, spec.material, rep, bal, settings, None),
646	                encoding="utf-8")
647	        except Exception:  # noqa: BLE001
648	            pass
649	        wt = "watertight" if rep.ok else "⚠ NON-manifold"
650	        if rep.mount_fits is True:
651	            mnt = f" · ✓ motor cup carved ({rep.mount_msg})"
652	        elif rep.mount_fits is False:
653	            mnt = f" · ⚠ {rep.mount_msg}"
654	            if not state.export_fit_hub:   # explain the solid hub + how to get the cup
655	                mnt += " — turn on 'Fit hub to motor on export' to widen it and carve the cup"
656	        else:
657	            mnt = " · (this fan model has no motor-mount defined)"
658	        grew = ""
659	        if grew_from is not None:

================================================================================
## window @ 2026-08-30T23:30:05  (lines 658-669)

658	        grew = ""
659	        if grew_from is not None:
660	            grew = (f"\n↳ Hub widened {grew_from:.1f} → {state.e_hub_radius:.1f} mm to fit the "
661	                    f"{spec.motor_mount.cavity_dia_mm:.0f} mm motor — press Preview to see it. The CFM/eff "
662	                    f"shown were for the narrower hub, so they're now approximate; re-Assess for exact numbers.")
663	        state.export_msg = f"✓ Saved {out.resolve()}  ({wt}{mnt}){grew}"
664	        state.flush()
665	
666	    def _build_preview_stl(flat, feat):
667	        """Blocking geometry build in an ISOLATED subprocess (a native OCP crash or a runaway
668	        featured build can't take down the cockpit server — it surfaces as a caught error).
669

================================================================================
## window @ 2026-08-31T02:46:39  (lines 985-1034)

985	            return True, "⚠ OVER-SPEC (allowed via leeway): " + "; ".join(over) + dm
986	        return True, f"✓ fits {spec.name} (dia {dia:.0f} mm, depth {depth:.0f} mm, {weight:.0f} g)"
987	
988	    def _blocking_eval(flat, features, workdir):
989	        # Isolated subprocess: an OCP native crash / OpenFOAM hang can't take the cockpit down.
990	        return evaluate_candidate_isolated(flat, features, workdir, spec=active_spec(),
991	                                           procs=8, base_cell=0.006, iters=500)
992	
993	    async def _assess(params, flat, label):
994	        tid = next_id[0]
995	        next_id[0] += 1
996	        workdir = assess_dir / f"design_{tid}"
997	        loop = asyncio.get_running_loop()
998	        result = await loop.run_in_executor(None, _blocking_eval, flat, params.features, workdir)
999	        if not result.feasible:
1000	            hint = _reject_hint(result.reason)
1001	            state.assess_msg = f"{label}: rejected — {result.reason}" + (f"\n{hint}" if hint else "")
1002	            state.flush()
1003	            return None
1004	        stl = workdir / "impeller.stl"
1005	        d = Design(
1006	            trial=tid, params=dict(flat),
1007	            objectives={"cfm_free": result.cfm_free, "cfm_load": result.cfm_load,
1008	                        "efficiency": result.efficiency},
1009	            feasible=True, is_pareto=False,
1010	            stl_path=stl if stl.exists() else None,
1011	            extra={"n_blades": params.n_blades, "source": "user",
1012	                   "source_run": run_dir.name,
1013	                   "over_spec": list(result.over_spec), "fan_model": state.fan_model,
1014	                   "actual_rpm": round(result.actual_rpm)},
1015	        )
1016	        # persist so the design survives a cockpit restart (reloaded by _load_assessed_designs)
1017	        try:
1018	            (workdir / "design.json").write_text(json.dumps(
1019	                {"trial": d.trial, "params": d.params, "objectives": d.objectives,
1020	                 "feasible": True, "reason": d.reason, "extra": d.extra}, indent=2))
1021	        except Exception:  # noqa: BLE001 - persistence is best-effort; keep the in-memory design
1022	            pass
1023	        user_designs.append(d)
1024	        by_trial[tid] = d
1025	        refresh_items()
1026	        refresh_figure()
1027	        state.flush()
1028	        return d
1029	
1030	    def on_assess():
1031	        if state.assess_busy:
1032	            return
1033	        # store features alongside geometry so an assessed design's settings reload when reselected
1034	        params, flat = build_edit_params(), {**edit_flat(), **_feat_dict()}

================================================================================
## window @ 2026-08-31T02:46:45  (lines 1063-1110)

1063	    def on_sweep():
1064	        if state.assess_busy:
1065	            return
1066	        import numpy as np
1067	
1068	        opt = next((o for o in SWEEP_OPTIONS if o[0] == state.sweep_param), SWEEP_OPTIONS[0])
1069	        label, kind, field, mn, mx = opt
1070	        base_flat, base_feat = edit_flat(), _feat_dict()
1071	        steps = max(2, int(state.sweep_steps))
1072	        raw = list(np.linspace(mn, mx, steps))
1073	        values = sorted(set(int(round(v)) for v in raw)) if field == "n_blades" else raw
1074	
1075	        async def task():
1076	            state.assess_busy = True
1077	            done = 0
1078	            try:
1079	                for i, val in enumerate(values):
1080	                    flat, feat = dict(base_flat), dict(base_feat)
1081	                    if kind == "flat":
1082	                        flat[field] = int(val) if field == "n_blades" else float(val)
1083	                    else:
1084	                        feat[field] = float(val)
1085	                        if kind == "tub" and feat["tubercle_waves"] == 0:
1086	                            feat["tubercle_waves"] = 6
1087	                        if kind == "ser" and feat["serration_waves"] == 0:
1088	                            feat["serration_waves"] = 8
1089	                        if kind == "dim":
1090	                            feat["dimple_rows"] = feat["dimple_rows"] or 5
1091	                            feat["dimple_cols"] = feat["dimple_cols"] or 5
1092	                    params = blade_from_flat(flat, Features(**feat))
1093	                    state.assess_msg = f"Sweep {label} {i+1}/{len(values)} = {val:g}: running CFD…"
1094	                    state.flush()
1095	                    if not check_printability(params).printable:
1096	                        continue
1097	                    try:  # one design failing shouldn't abort the whole sweep
1098	                        if await _assess(params, flat, f"sweep {label}={val:g}"):
1099	                            done += 1
1100	                    except Exception as exc:  # noqa: BLE001
1101	                        state.assess_msg = f"Sweep {label}={val:g} failed: {type(exc).__name__}: {exc}"
1102	                        state.flush()
1103	                state.assess_msg = f"Sweep of {label} done: {done} ◆ runs added to the plot."
1104	            finally:
1105	                state.assess_busy = False
1106	                state.flush()
1107	
1108	        asynchronous.create_task(task())
1109	
1110	    def select(trial: int | None):

================================================================================
## window @ 2026-08-31T02:46:52  (lines 434-437)

434	    def _on_model(**_):
435	        _model_readout()
436	    state.sweep_param = "stagger mid"   # a valid label (o[0]); the strongest flow/eff lever
437	    state.sweep_steps = 3

================================================================================
## window @ 2026-08-31T02:56:44  (lines 753-774)

753	            if mask.any():  # 2-color map: base where in-spec, red where it breaks the envelope
754	                mesh["spec"] = mask
755	                plotter.add_mesh(mesh, scalars="spec", cmap=[base, "red"], clim=[0, 1],
756	                                 show_scalar_bar=False, smooth_shading=True)
757	            else:
758	                plotter.add_mesh(mesh, color=base, smooth_shading=True)
759	        else:
760	            plotter.add_mesh(mesh, color=base, smooth_shading=True)
761	        if state.show_envelope:
762	            _add_envelope(mesh)
763	        if reset:
764	            plotter.reset_camera()
765	
766	    def _draw(path, color: str):
767	        render_state["path"] = str(path)
768	        render_state["color"] = color
769	        _apply_render(reset=True)
770	
771	    @state.change("highlight_spec", "show_envelope", "fan_model")
772	    def _on_viz_toggle(**_):
773	        _apply_render(reset=False)  # keep the current camera when just toggling an aid
774	        try:

================================================================================
## window @ 2026-08-31T02:56:47  (lines 779-798)

779	    def do_preview():
780	        # Async so the "Generating…" indicator shows while the (7-35 s) geometry build runs;
781	        # a synchronous build would freeze the UI with no feedback until it finished.
782	        if state.preview_busy or state.assess_busy:
783	            return
784	        params = build_edit_params()
785	        printable = check_printability(params)
786	        if not printable.printable:
787	            state.preview_msg = f"⚠ Not printable: {printable.reason}"
788	            return
789	        flat, feat = edit_flat(), edit_features()  # serializable inputs for the isolated build
790	
791	        async def task():
792	            state.preview_busy = True
793	            heavy = " (features are heavy — up to ~2 min)" if params.features.active else ""
794	            state.preview_msg = f"⏳ Generating geometry…{heavy}"
795	            state.flush()
796	            loop = asyncio.get_running_loop()
797	            try:
798	                await loop.run_in_executor(None, _build_preview_stl, flat, feat)

================================================================================
## window @ 2026-08-31T02:57:04  (lines 825-838)

825	                try:
826	                    import numpy as _np
827	                    from fansim.acoustics.tonal import peak_tone_reduction_db
828	                    drop = -peak_tone_reduction_db(_np.radians(_np.asarray(params.blade_angles_deg)))
829	                    odd = "" if params.n_blades % 2 else "  (even blade count — odd counts spread the tone more)"
830	                    tone_line = f"\n🔉 Uneven spacing: predicted peak tone −{drop:.1f} dB, free of any flow cost{odd}"
831	                except Exception:  # noqa: BLE001
832	                    tone_line = ""
833	            state.preview_msg = (f"Preview (orange): {params.n_blades} blades, "
834	                                 f"camber {state.e_camber:.3f}, {feats}.\n{status}{print_line}{tone_line}")
835	            state.preview_busy = False
836	            try:
837	                ctrl.view_update()
838	            except Exception:

================================================================================
## window @ 2026-08-31T15:08:48  (lines 402-431)

402	            items.append({"title": f"{e.design_id}  ·  {free} CFM{star}{meas}", "value": e.design_id})
403	        return items
404	    try:
405	        build_catalog()                     # refresh the index from all runs + measurements (cheap scan)
406	    except Exception:  # noqa: BLE001 - the catalog is a convenience; never block cockpit startup
407	        pass
408	    state.catalog_items = _catalog_items()
409	    state.catalog_sel = None
410	    state.catalog_info = f"{len(state.catalog_items)} designs across all runs. Pick one to load it here."
411	    # fan-model constraints + leeway (applied when you Assess). Nominal is never changed; leeway lets
412	    # a design exceed it (flagged over-spec). Import new models by dropping YAML in config/fan_models/.
413	    state.fan_model = "a12x25"
414	    state.fan_models = fan_spec_names()
415	    state.lee_tip = 0.0
416	    state.lee_depth = 0.0
417	    state.lee_overvolt = 0.0
418	    state.lee_weight = 0.0
419	
420	    def _model_readout():
421	        s = get_fan_spec(state.fan_model)
422	        state.model_info = (f"{s.name}: tip ≤{s.tip_dia_mm[1]:.0f} mm, depth ≤{s.depth_mm[1]:.0f} mm, "
423	                            f"hub {s.hub_dia_mm[0]:.0f}-{s.hub_dia_mm[1]:.0f} mm, "
424	                            f"{s.max_shaft_power_w:.2f} W shaft ({s.voltage_v:.0f} V×{s.max_current_a:.2f} A), "
425	                            f"≤{s.max_weight_g:.0f} g. Published {s.ref_cfm:.0f} CFM / "
426	                            f"{s.ref_static_pa:.0f} Pa / {s.ref_noise_dba:.0f} dBA.")
427	    _model_readout()
428	
429	    def reload_models():
430	        load_fan_models_dir()
431	        state.fan_models = fan_spec_names()

================================================================================
## window @ 2026-08-31T15:08:54  (lines 429-442)

429	    def reload_models():
430	        load_fan_models_dir()
431	        state.fan_models = fan_spec_names()
432	        _model_readout()
433	        state.flush()
434	
435	    @state.change("fan_model")
436	    def _on_model(**_):
437	        _model_readout()
438	    state.sweep_param = "stagger mid"   # a valid label (o[0]); the strongest flow/eff lever
439	    state.sweep_steps = 3
440	    state.sweep_active = False           # a sweep is running -> show progress bar + Cancel
441	    state.sweep_cancel = False           # user asked to stop -> the loop halts after the current design
442	    state.sweep_progress = 0             # 0-100 for the progress bar

================================================================================
## window @ 2026-08-31T15:09:59  (lines 54-65)

54	from fansim.fan_spec import (
55	    check_build,
56	    estimate_weight_g,
57	    fan_spec_names,
58	    get_fan_spec,
59	    load_fan_models_dir,
60	    over_spec_flags,
61	)
62	from fansim.geometry import build_impeller, export_stl
63	from fansim.geometry.features import Features
64	from fansim.manufacturability import check_printability
65	from fansim.optimize.isolated_eval import evaluate_candidate_isolated

================================================================================
## window @ 2026-08-31T15:10:45  (lines 1022-1030)

1022	    def _recompute_stale(**_):
1023	        if sel_sig[0] is None:
1024	            return
1025	        stale = _editor_sig() != sel_sig[0]
1026	        state.edited_stale = stale
1027	        state.stale_msg = ("⚠ Edited since assessment — the shown CFM/efficiency are for the "
1028	                           "un-edited design. Press Assess to evaluate your changes." if stale else "")
1029	
1030	    state.change(*EDITOR_VARS)(_recompute_stale)

================================================================================
## window @ 2026-08-31T15:11:12  (lines 1694-1703)

1694	                                    html.Div("{{ model_info }}", classes="text-caption my-1")
1695	                                    with v3.VExpansionPanels(classes="mt-1"):
1696	                                        with v3.VExpansionPanel(
1697	                                                title="Leeway (allow exceeding nominal → over-spec)"):
1698	                                            with v3.VExpansionPanelText():
1699	                                                _slider("Tip past frame (mm)", "lee_tip", 0, 10, 0.5)
1700	                                                _slider("Extra depth Z (mm)", "lee_depth", 0, 12, 0.5)
1701	                                                _slider("Over-voltage (V)", "lee_overvolt", 0, 12, 0.5)
1702	                                                _slider("Extra weight (g)", "lee_weight", 0, 40, 1)
1703	                        with v3.VCard(classes="mb-2 pa-3"):

================================================================================
## window @ 2026-08-31T20:11:42  (lines 449-458)

449	        state.hub_fit_info = (f"Motor hub {cav:.1f} mm → this hub needs radius ≥ {need:.1f} mm. "
450	                              + (f"Current {cur:.1f} mm ✓ fits — cup will carve." if cur >= need
451	                                 else f"Current {cur:.1f} mm ✗ TOO SMALL, won't fit (Snap, or turn up Hub radius)."))
452	
453	    def snap_hub_to_fit():
454	        """Set the hub radius to the smallest that fits the selected fan's motor (with wall margin)."""
455	        s = get_fan_spec(state.fan_model)
456	        need = mount_min_hub_radius(s)
457	        if need is not None:
458	            state.e_hub_radius = round(need + 0.05, 2)

================================================================================
## window @ 2026-08-31T20:11:45  (lines 458-465)

458	            state.e_hub_radius = round(need + 0.05, 2)
459	            _hub_fit_readout()
460	            state.flush()
461	
462	    state.hub_fit_info = ""
463	    _model_readout(); _hub_fit_readout()
464	
465	    def reload_models():

================================================================================
## window @ 2026-08-31T20:27:50  (lines 203-222)

203	    if "weight" in r:
204	        return ("↳ too heavy: thinner blades (Thickness sliders), smaller chord/hub, or fewer blades "
205	                "— or add Extra-weight leeway.")
206	    return ""
207	
208	
209	def _blade_z_extent(params) -> float:
210	    """Axial (Z) extent of the blade from its section points -- FAST (no CAD-kernel solid)."""
211	    from fansim.geometry.blade import _interp_stations, _section_points_3d
212	    it = _interp_stations(params, params.n_span)
213	    r0 = params.hub_radius - params.root_embed
214	    zs = []
215	    for i in range(params.n_span):
216	        rf = float(it["r_frac"][i]); r = r0 + (params.tip_radius - r0) * rf
217	        pts = _section_points_3d(
218	            r=r, r_frac=rf, chord=float(it["chord"][i]), stagger_deg=float(it["stagger_deg"][i]),
219	            thickness=float(it["thickness"][i]), max_camber=float(it["max_camber"][i]),
220	            camber_pos=float(it["camber_pos"][i]), sweep=float(it["sweep"][i]),
221	            skew=float(it["skew"][i]), le_sweep=float(it["le_sweep"][i]),
222	            lean_deg=float(it["lean_deg"][i]), n_chord=params.n_chord, features=params.features)

================================================================================
## window @ 2026-08-31T20:27:53  (lines 223-227)

223	        zs += [v.z for v in pts]
224	    return max(zs) - min(zs)
225	
226	
227	def _depth_drivers(flat: dict, top: int = 3) -> list[tuple[str, float]]:

================================================================================
## window @ 2026-09-01T02:14:16  (lines 688-711)

688	    def _thin(designs, cell: float = 2.5):
689	        """Keep one design per ~cell-CFM bucket in (free, load) space — pareto first, then best eff.
690	        Non-destructive: only the PLOTTED set is thinned; nothing is removed from disk or the dropdown."""
691	        best = {}
692	        for d in designs:
693	            key = (round(d.objectives["cfm_free"] / cell), round(d.objectives["cfm_load"] / cell))
694	            cur = best.get(key)
695	            rank = (d.is_pareto, d.objectives.get("efficiency", 0))
696	            if cur is None or rank > (cur.is_pareto, cur.objectives.get("efficiency", 0)):
697	                best[key] = d
698	        return list(best.values())
699	
700	    def refresh_figure():
701	        sd = _thin(study_designs) if state.declutter else study_designs
702	        ud = _thin(list(user_designs)) if state.declutter else user_designs
703	        fig = scatter_figure(sd, ud)
704	        if hasattr(ctrl, "figure_update"):
705	            ctrl.figure_update(fig)
706	
707	    @state.change("declutter")
708	    def _on_declutter(**_):
709	        refresh_figure()
710	
711	    def _init_editor(p: dict, feat: Features | None = None):

================================================================================
## window @ 2026-09-01T02:15:09  (lines 1723-1736)

1723	            return
1724	        wt = "watertight" if rep.ok else "⚠ NON-manifold"
1725	        state.prop_export_msg = f"✓ Saved {out.resolve()}  ({wt})"
1726	        state.flush()
1727	
1728	    with SinglePageLayout(server) as layout:
1729	        layout.title.set_text("Fan-simulator Cockpit")
1730	        with layout.content:
1731	            with v3.VContainer(fluid=True, classes="pa-2"):
1732	                with v3.VTabs(v_model=("active_tab",), color="primary", classes="mb-3"):
1733	                    v3.VTab("🌀  Fan — CFD design", value="fan")
1734	                    v3.VTab("🚁  Propeller — instant BEMT design", value="propeller")
1735	                # ---- FAN TAB (existing cockpit) ------------------------------------------------
1736	                with v3.VRow(no_gutters=True, v_show="active_tab === 'fan'"):

================================================================================
## window @ 2026-09-01T02:15:12  (lines 1736-1749)

1736	                with v3.VRow(no_gutters=True, v_show="active_tab === 'fan'"):
1737	                    with v3.VCol(cols=6, classes="pr-2"):
1738	                        v3.VSwitch(v_model=("declutter",), density="compact", hide_details=True,
1739	                                   inset=True, color="primary", classes="ml-2",
1740	                                   label="Declutter (hide near-duplicate designs)")
1741	                        fig_widget = plotly_widgets.Figure(
1742	                            figure=scatter_figure(study_designs, user_designs),
1743	                            # send ONLY the clicked point's customdata (trial id) — the full $event has
1744	                            # non-serializable fields that silently break the round-trip to the server.
1745	                            click=(on_plotly_click, "[$event?.points?.[0]?.customdata]"),
1746	                            style="width:100%;",
1747	                        )
1748	                    with v3.VCol(cols=6):
1749	                        with v3.VCard(classes="mb-2 pa-3"):

================================================================================
## window @ 2026-09-01T19:56:44  (lines 1878-1899)

1878	                state.flush()
1879	                return
1880	            prop_pareto_store.clear()
1881	            prop_pareto_store.extend(pareto)
1882	            rows = []
1883	            for i, r in enumerate(pareto[:14]):
1884	                p = r["params"]
1885	                rows.append({
1886	                    "idx": i, "thrust": f"{r['thrust_g']:.0f}", "eff": f"{r['eff_g_per_w']:.2f}",
1887	                    "power": f"{r['power_w']:.0f}", "fm": f"{r['fm']:.2f}", "nb": r["n_blades"],
1888	                    "pitch": f"{p['pitch_in']:.1f}",
1889	                })
1890	            state.prop_pareto = rows
1891	            cap_txt = f" ≤{cap:.0f} W" if cap else ""
1892	            state.prop_msg = (f"✓ {len(pareto)} designs on the thrust↔efficiency front{cap_txt}. "
1893	                              f"Click a row to load it (top = most thrust, bottom = most efficient).")
1894	            state.prop_busy = False
1895	            state.flush()
1896	
1897	        asynchronous.create_task(task())
1898	
1899	    def load_prop_row(idx=None, **_):

================================================================================
## window @ 2026-09-01T19:57:19  (lines 2336-2357)

2336	                        # RIGHT — performance readout, 3-D prop, optimizer front
2337	                        with v3.VCol(cols=7):
2338	                            with v3.VCard(classes="mb-2 pa-3"):
2339	                                html.Div("{{ line }}", v_for="line in prop_readout",
2340	                                         classes="text-body-2")
2341	                            with v3.VCard(style="height:360px;", classes="mb-2"):
2342	                                prop_view = plotter_ui(prop_plotter)
2343	                            with v3.VCard(classes="pa-2", v_if="prop_pareto.length"):
2344	                                html.Div("Optimizer front — click a design to load it "
2345	                                         "(top = most thrust, bottom = most efficient)",
2346	                                         classes="text-subtitle-2 mb-1")
2347	                                with v3.VList(density="compact", lines=False):
2348	                                    with v3.VListItem(v_for="row in prop_pareto", key="row.idx",
2349	                                                      click=(load_prop_row, "[row.idx]")):
2350	                                        v3.VListItemTitle("{{ row.thrust }} g  ·  {{ row.eff }} g/W  "
2351	                                                          "·  {{ row.power }} W  ·  FM {{ row.fm }}  "
2352	                                                          "·  {{ row.nb }}-blade  {{ row.pitch }}\"")
2353	    ctrl.view_update = view.update
2354	    ctrl.figure_update = fig_widget.update
2355	    ctrl.prop_view_update = prop_view.update
2356	    return server
2357

================================================================================
## window @ 2026-09-01T19:59:06  (lines 1721-1744)

1721	            state.meas_msg = "⚠ Enter at least one measured value (CFM / static Pa / dB(A))."
1722	            state.flush(); return
1723	        run = d.extra.get("source_run") or run_dir.name
1724	        design_id = make_design_id(run, d.trial)
1725	        sim = {"cfm_free": d.objectives.get("cfm_free"), "cfm_load": d.objectives.get("cfm_load"),
1726	               "efficiency": d.objectives.get("efficiency"), "actual_rpm": d.extra.get("actual_rpm")}
1727	        rpm = _mf(state.meas_rpm) or d.extra.get("actual_rpm") or active_spec().rpm
1728	        pt = MeasuredPoint(rpm=float(rpm), cfm=_mf(state.meas_cfm),
1729	                           static_pressure_pa=_mf(state.meas_static), noise_dba=_mf(state.meas_noise),
1730	                           source=state.meas_instrument or "")
1731	        rec = record_measurement(design_id, pt, run=run, trial=d.trial,
1732	                                 stl_path=str(d.stl_path) if d.has_model else "",
1733	                                 material=active_spec().material, sim=sim,
1734	                                 instrument=state.meas_instrument, notes=state.meas_notes)
1735	        last = sim_vs_real(rec)[-1]
1736	        parts = []
1737	        if "cfm" in last:
1738	            parts.append(f"CFM {last['cfm']['measured']:.1f} vs sim free {last['cfm']['sim']:.1f} "
1739	                         f"(sim over-reads {last['cfm']['pct_error']:+.0f}%)")
1740	        if "noise_dba" in last:
1741	            parts.append(f"noise {last['noise_dba']['measured']:.1f} dBA "
1742	                         f"(Δ{last['noise_dba']['delta_db']:+.1f} vs sim)")
1743	        state.meas_msg = (f"✓ Saved to validation/measurements/ for {design_id} "
1744	                          f"({len(rec.measured)} point(s)). " + "  ".join(parts))

================================================================================
## window @ 2026-09-01T19:59:29  (lines 2283-2292)

2283	                                                                      variant="outlined", hide_details=True,
2284	                                                                      classes="mb-2")
2285	                                                v3.VTextField(label="Instrument", v_model=("meas_instrument",),
2286	                                                              density="compact", variant="outlined",
2287	                                                              hide_details=True, classes="mb-2")
2288	                                                v3.VTextField(label="Notes", v_model=("meas_notes",),
2289	                                                              density="compact", variant="outlined",
2290	                                                              hide_details=True, classes="mb-2")
2291	                                                v3.VBtn("Save measurement", color="primary", size="small",
2292	                                                        block=True, click=(save_measurement,))

================================================================================
## window @ 2026-09-01T20:04:58  (lines 2352-2377)

2352	                                                      v_model=("prop_maxpower",), type="number",
2353	                                                      density="compact", variant="outlined",
2354	                                                      hide_details=True)
2355	                                v3.VBtn("Optimize", color="success", size="small", block=True,
2356	                                        click=(optimize_prop,), classes="mt-2",
2357	                                        loading=("prop_busy",), disabled=("prop_busy",))
2358	                        # RIGHT — performance readout, 3-D prop, optimizer front
2359	                        with v3.VCol(cols=7):
2360	                            with v3.VCard(classes="mb-2 pa-3"):
2361	                                html.Div("{{ line }}", v_for="line in prop_readout",
2362	                                         classes="text-body-2")
2363	                            with v3.VCard(style="height:360px;", classes="mb-2"):
2364	                                prop_view = plotter_ui(prop_plotter)
2365	                            with v3.VCard(classes="pa-2 mb-2"):   # always mounted so prop_fig_update lands
2366	                                prop_fig_widget = plotly_widgets.Figure(
2367	                                    figure=prop_scatter_figure([]),
2368	                                    click=(load_prop_row, "[$event?.points?.[0]?.customdata]"),
2369	                                    style="width:100%;")
2370	                            with v3.VCard(classes="pa-2", v_if="prop_pareto.length"):
2371	                                html.Div("Optimizer front — click a point above or a row here "
2372	                                         "(top = most thrust, bottom = most efficient)",
2373	                                         classes="text-subtitle-2 mb-1")
2374	                                with v3.VList(density="compact", lines=False):
2375	                                    with v3.VListItem(v_for="row in prop_pareto", key="row.idx",
2376	                                                      click=(load_prop_row, "[row.idx]")):
2377	                                        v3.VListItemTitle("{{ row.thrust }} g  ·  {{ row.eff }} g/W  "

================================================================================
## window @ 2026-09-01T20:06:46  (lines 2004-2048)

2004	                                                 classes="text-caption text-medium-emphasis")
2005	                                    with v3.VCard(style="height:560px;"):
2006	                                        view = plotter_ui(plotter)
2007	                                with v3.VCol(cols=5):
2008	                                    with v3.VTabs(v_model=("fan_subtab",), color="primary", classes="mb-3"):
2009	                                        v3.VTab("Design", value="design")
2010	                                        v3.VTab("Results", value="results")
2011	                                        v3.VTab("Library", value="library")
2012	
2013	                                    # ---- RESULTS ----------------------------------------------------------
2014	                                    with html.Div(v_show="fan_subtab === 'results'"):
2015	                                        v3.VSwitch(v_model=("declutter",), density="compact", hide_details=True,
2016	                                                   inset=True, color="primary", classes="ml-2 mb-1",
2017	                                                   label="Declutter (hide near-duplicates)")
2018	                                        hub_all = [d for d in _hub_designs() if not d.extra.get("cfd_stale")]
2019	                                        fig_widget = plotly_widgets.Figure(
2020	                                            figure=scatter_figure([d for d in hub_all if d in study_designs],
2021	                                                                  [d for d in hub_all if d in user_designs]),
2022	                                            click=(on_plotly_click, "[$event?.points?.[0]?.customdata]"),
2023	                                            style="width:100%;",
2024	                                        )
2025	                                        with v3.VCard(classes="mb-2 pa-3"):
2026	                                            v3.VSelect(
2027	                                                label="Design",
2028	                                                v_model=("selected_trial",),
2029	                                                items=("trial_items",),
2030	                                                density="compact", variant="outlined",
2031	                                                hide_details=True,
2032	                                                update_modelValue=(select, "[$event]"),
2033	                                            )
2034	                                            html.Div(
2035	                                                "{{ line }}",
2036	                                                v_for="line in info_lines",
2037	                                                classes="text-body-2 mt-2",
2038	                                            )
2039	
2040	                                    # ---- LIBRARY ----------------------------------------------------------
2041	                                    with html.Div(v_show="fan_subtab === 'library'"):
2042	                                        with v3.VCard(classes="mb-2 pa-3"):
2043	                                            html.Div("{{ library_info }}", classes="text-caption mb-2")
2044	                                            html.Div("{{ library_leftover }}", classes="text-caption mb-2",
2045	                                                     v_if="library_leftover")
2046	                                            html.Div("{{ preview_msg }}", classes="text-caption mt-2",
2047	                                                     style="white-space: pre-line")
2048	                                            v3.VBtn("Scale to this hub", color="primary", size="small",

================================================================================
## window @ 2026-09-01T20:32:18  (lines 1817-1832)

1817	                                 chord_frac=(float(state.p_chord_root), float(state.p_chord_mid),
1818	                                             float(state.p_chord_tip)),
1819	                                 camber=float(state.p_camber))
1820	
1821	    def _draw_prop(path):
1822	        prop_plotter.clear_actors()
1823	        try:
1824	            prop_plotter.add_mesh(pv.read(str(path)), color="cadetblue", smooth_shading=True)
1825	            prop_plotter.reset_camera()
1826	        except Exception:  # noqa: BLE001 - nothing to show
1827	            pass
1828	        try:
1829	            ctrl.prop_view_update()
1830	        except Exception:  # noqa: BLE001
1831	            pass
1832

================================================================================
## window @ 2026-09-01T20:32:22  (lines 1833-1850)

1833	    def _prop_perf_lines(spec, params):
1834	        """BEMT readout for the current prop: static hover thrust/eff/FM + a forward-flight note."""
1835	        perf = bemt_analyze(params, rpm=spec.rpm_max)
1836	        lines = [
1837	            f"⚙ {spec.n_blades}-blade  {spec.diameter_in}×{spec.pitch_in:.1f} in  @ {spec.rpm_max:.0f} rpm",
1838	            f"Thrust {perf.thrust_g:.0f} g   ·   {perf.efficiency_g_per_w:.2f} g/W   ·   {perf.power_w:.0f} W",
1839	            f"Figure of merit {perf.figure_of_merit:.2f}   (0.6–0.8 = a good real prop)",
1840	        ]
1841	        fwd = bemt_analyze(params, rpm=spec.rpm_max, v_forward=15.0)
1842	        if fwd.prop_efficiency is not None:
1843	            lines.append(f"At 15 m/s forward: prop efficiency {100*fwd.prop_efficiency:.0f}%")
1844	        return lines
1845	
1846	    def analyze_prop():
1847	        """Instant BEMT readout, then an async 3-D preview build (geometry is the slow part)."""
1848	        if state.prop_busy:
1849	            return
1850	        spec, params = prop_editor_spec(), prop_editor_params()

================================================================================
## window @ 2026-09-01T20:32:32  (lines 1899-1910)

1899	            state.prop_msg = f"⏳ Optimizing {trials} blade designs (BEMT — a second or two)…"
1900	            state.flush()
1901	            loop = asyncio.get_running_loop()
1902	            try:
1903	                _, pareto = await loop.run_in_executor(
1904	                    None, lambda: run_prop_study(base, n_trials=trials, max_power_w=cap))
1905	            except Exception as exc:  # noqa: BLE001
1906	                state.prop_msg = f"⚠ Optimize failed: {type(exc).__name__}: {exc}"
1907	                state.prop_busy = False
1908	                state.flush()
1909	                return
1910	            prop_pareto_store.clear()

================================================================================
## window @ 2026-09-01T20:32:36  (lines 1910-1921)

1910	            prop_pareto_store.clear()
1911	            prop_pareto_store.extend(pareto)
1912	            rows = []
1913	            for i, r in enumerate(pareto[:14]):
1914	                p = r["params"]
1915	                rows.append({
1916	                    "idx": i, "thrust": f"{r['thrust_g']:.0f}", "eff": f"{r['eff_g_per_w']:.2f}",
1917	                    "power": f"{r['power_w']:.0f}", "fm": f"{r['fm']:.2f}", "nb": r["n_blades"],
1918	                    "pitch": f"{p['pitch_in']:.1f}",
1919	                })
1920	            state.prop_pareto = rows
1921	            if hasattr(ctrl, "prop_fig_update"):    # push the thrust-vs-efficiency scatter

================================================================================
## window @ 2026-09-03T14:28:25  (lines 876-905)

876	    def edit_flat() -> dict:
877	        shroud = normalize_shroud_thick_mm(state.e_shroud_thick)
878	        if float(state.e_shroud_thick or 0.0) != shroud:
879	            state.e_shroud_thick = shroud  # snap a 0.2 mm nudge up to a printable wall
880	        return dict(
881	            n_blades=int(state.e_n_blades),
882	            stagger_root=state.e_stagger_root, stagger_mid=state.e_stagger_mid,
883	            stagger_tip=state.e_stagger_tip, chord_root=state.e_chord_root,
884	            chord_mid=state.e_chord_mid, chord_tip=state.e_chord_tip,
885	            sweep_mid=state.e_sweep_mid, sweep_tip=state.e_sweep_tip,
886	            max_camber=state.e_camber, camber_pos=state.e_camber_pos,
887	            lean_mid=state.e_lean_mid, lean_tip=state.e_lean_tip,
888	            le_sweep_mid=state.e_le_mid, le_sweep_tip=state.e_le_tip,
889	            skew_mid=state.e_skew_mid, skew_tip=state.e_skew_tip,
890	            winglet_span=state.e_winglet_span, winglet_sweep=state.e_winglet_sweep,
891	            winglet_lean=state.e_winglet_lean,
892	            shroud_thick_mm=shroud,
893	            shroud_height_frac=min(max(float(state.e_shroud_height or 0.0), 0.0), 1.0),
894	            tip_round=state.e_tip_round, tip_round_start=state.e_tip_start,
895	            hub_radius=state.e_hub_radius, tip_radius=state.e_tip_radius,
896	            hub_height=state.e_hub_height, hub_profile=state.e_hub_profile,
897	            hub_nose=state.e_hub_nose,
898	            thickness_root=state.e_thick_root, thickness_mid=state.e_thick_mid,
899	            thickness_tip=state.e_thick_tip,
900	            spacing_spread=state.e_spacing, spacing_seed=0,
901	        )
902	
903	    def _apply_editor_flat(flat: dict) -> None:
904	        """Apply flat (non-prefixed) geometry fields into the editor sliders (preserve features)."""
905	        mapping = {

================================================================================
## window @ 2026-09-03T15:14:27  (lines 1481-1660)

1481	    def _blocking_eval(flat, features, workdir):
1482	        # Isolated subprocess: an OCP native crash / OpenFOAM hang can't take the cockpit down.
1483	        return evaluate_candidate_isolated(flat, features, workdir, spec=active_spec(),
1484	                                           procs=8, base_cell=0.006, iters=500)
1485	
1486	    async def _assess(params, flat, label):
1487	        tid = next_id[0]
1488	        next_id[0] += 1
1489	        workdir = assess_dir / f"design_{tid}"
1490	        loop = asyncio.get_running_loop()
1491	        result = await loop.run_in_executor(None, _blocking_eval, flat, params.features, workdir)
1492	        if not result.feasible:
1493	            hint = _reject_hint(result.reason)
1494	            state.assess_msg = f"{label}: rejected — {result.reason}" + (f"\n{hint}" if hint else "")
1495	            state.flush()
1496	            return None
1497	        stl = workdir / "impeller.stl"
1498	        extra = {"n_blades": params.n_blades, "source": "user",
1499	                 "source_run": run_dir.name,
1500	                 "over_spec": list(result.over_spec), "fan_model": state.fan_model,
1501	                 "actual_rpm": round(result.actual_rpm)}
1502	        if state.library_parent_id:
1503	            extra["parent_id"] = state.library_parent_id
1504	            extra["place_op"] = state.library_place_op or "fit_envelope"
1505	            extra["placed_on"] = state.fan_model
1506	            extra["cfd_stale"] = False
1507	        d = Design(
1508	            trial=tid, params=dict(flat),
1509	            objectives={"cfm_free": result.cfm_free, "cfm_load": result.cfm_load,
1510	                        "efficiency": result.efficiency},
1511	            feasible=True, is_pareto=False,
1512	            stl_path=stl if stl.exists() else None,
1513	            extra=extra,
1514	        )
1515	        # persist so the design survives a cockpit restart (reloaded by _load_assessed_designs)
1516	        try:
1517	            (workdir / "design.json").write_text(json.dumps(
1518	                {"trial": d.trial, "params": d.params, "objectives": d.objectives,
1519	                 "feasible": True, "reason": d.reason, "extra": d.extra}, indent=2))
1520	        except Exception:  # noqa: BLE001 - persistence is best-effort; keep the in-memory design
1521	            pass
1522	        user_designs.append(d)
1523	        by_trial[tid] = d
1524	        refresh_items()
1525	        refresh_figure()
1526	        state.flush()
1527	        return d
1528	
1529	    async def _assess_existing(d: Design, params, flat, label):
1530	        """Assess into an existing draft row (clears cfd_stale on success)."""
1531	        tid = int(d.trial)
1532	        workdir = assess_dir / f"design_{tid}"
1533	        loop = asyncio.get_running_loop()
1534	        result = await loop.run_in_executor(None, _blocking_eval, flat, params.features, workdir)
1535	        if not result.feasible:
1536	            hint = _reject_hint(result.reason)
1537	            state.assess_msg = f"{label}: rejected — {result.reason}" + (f"\n{hint}" if hint else "")
1538	            state.flush()
1539	            return None
1540	        stl = workdir / "impeller.stl"
1541	        d.params = dict(flat)
1542	        d.objectives = {"cfm_free": result.cfm_free, "cfm_load": result.cfm_load, "efficiency": result.efficiency}
1543	        d.feasible = True
1544	        d.is_pareto = False
1545	        d.stl_path = stl if stl.exists() else None
1546	        d.reason = ""
1547	        d.extra.update({
1548	            "source": d.extra.get("source", "user"),
1549	            "source_run": run_dir.name,
1550	            "over_spec": list(result.over_spec),
1551	            "fan_model": state.fan_model,
1552	            "actual_rpm": round(result.actual_rpm),
1553	            "cfd_stale": False,
1554	        })
1555	        # persist so the design survives a cockpit restart (reloaded by _load_assessed_designs)
1556	        try:
1557	            workdir.mkdir(parents=True, exist_ok=True)
1558	            (workdir / "design.json").write_text(json.dumps(
1559	                {"trial": d.trial, "params": d.params, "objectives": d.objectives,
1560	                 "feasible": True, "reason": d.reason, "extra": d.extra}, indent=2))
1561	        except Exception:  # noqa: BLE001
1562	            pass
1563	        by_trial[tid] = d
1564	        refresh_items()
1565	        refresh_figure()
1566	        state.flush()
1567	        return d
1568	
1569	    def on_assess():
1570	        if state.assess_busy:
1571	            return
1572	        # store features alongside geometry so an assessed design's settings reload when reselected
1573	        params, flat = build_edit_params(), {**edit_flat(), **_feat_dict()}
1574	
1575	        async def task():
1576	            state.assess_busy = True
1577	            state.assess_msg = "Running CFD on your design… (~4 min)"
1578	            state.flush()
1579	            try:
1580	                cur = by_trial.get(int(state.selected_trial)) if state.selected_trial is not None else None
1581	                if cur is not None and cur.extra.get("cfd_stale"):
1582	                    d = await _assess_existing(cur, params, flat, "Assess")
1583	                else:
1584	                    d = await _assess(params, flat, "Assess")
1585	                if d:
1586	                    o = d.objectives
1587	                    over = d.extra.get("over_spec") or []
1588	                    tag = ("  ⚠ OVER-SPEC: " + "; ".join(over)) if over else ""
1589	                    spec = get_fan_spec(d.extra.get("fan_model", "a12x25"))
1590	                    rpm = d.extra.get("actual_rpm", 0)
1591	                    rpm_tag = (f"  ⚙ motor-limited: {rpm:.0f} RPM ({100*rpm/spec.rpm:.0f}%)"
1592	                               if rpm and rpm < spec.rpm * 0.995 else "")
1593	                    state.assess_msg = (f"Done ◆#{d.trial}: free {o['cfm_free']:.1f}  "
1594	                                        f"load {o['cfm_load']:.1f}  eff {o['efficiency']:.1f}%"
1595	                                        f"  (added to plot){rpm_tag}{tag}")
1596	                    state.selected_trial = d.trial
1597	                    _set_baseline()  # the editor now matches the just-assessed design
1598	            except Exception as exc:  # noqa: BLE001 - surface eval errors; never a stuck/dead UI
1599	                state.assess_msg = f"Assess failed: {type(exc).__name__}: {exc}"
1600	            finally:
1601	                state.assess_busy = False
1602	                state.flush()
1603	
1604	        asynchronous.create_task(task())
1605	
1606	    def on_sweep():
1607	        if state.assess_busy:
1608	            return
1609	        import numpy as np
1610	
1611	        opt = next((o for o in SWEEP_OPTIONS if o[0] == state.sweep_param), SWEEP_OPTIONS[0])
1612	        label, kind, field, mn, mx = opt
1613	        base_flat, base_feat = edit_flat(), _feat_dict()
1614	        steps = max(2, int(state.sweep_steps))
1615	        raw = list(np.linspace(mn, mx, steps))
1616	        values = sorted(set(int(round(v)) for v in raw)) if field == "n_blades" else raw
1617	
1618	        async def task():
1619	            state.assess_busy = True
1620	            state.sweep_active = True
1621	            state.sweep_cancel = False
1622	            state.sweep_progress = 0
1623	            done = 0
1624	            n = len(values)
1625	            try:
1626	                for i, val in enumerate(values):
1627	                    if state.sweep_cancel:   # user hit Cancel — stop before starting the next design
1628	                        state.assess_msg = f"Sweep of {label} cancelled: {done}/{n} done ({done} ◆ added)."
1629	                        break
1630	                    flat, feat = dict(base_flat), dict(base_feat)
1631	                    if kind == "flat":
1632	                        flat[field] = int(val) if field == "n_blades" else float(val)
1633	                    else:
1634	                        feat[field] = float(val)
1635	                        if kind == "tub" and feat["tubercle_waves"] == 0:
1636	                            feat["tubercle_waves"] = 6
1637	                        if kind == "ser" and feat["serration_waves"] == 0:
1638	                            feat["serration_waves"] = 8
1639	                        if kind == "dim":
1640	                            feat["dimple_rows"] = feat["dimple_rows"] or 5
1641	                            feat["dimple_cols"] = feat["dimple_cols"] or 5
1642	                    params = blade_from_flat(flat, Features(**feat))
1643	                    state.assess_msg = (f"Sweep {label} {i+1}/{n} = {val:g}: running CFD… "
1644	                                        f"(~4 min/step; {done} added so far)")
1645	                    state.sweep_progress = int(100 * i / n)
1646	                    state.flush()
1647	                    if not check_printability(params).printable:
1648	                        continue
1649	                    try:  # one design failing shouldn't abort the whole sweep
1650	                        if await _assess(params, flat, f"sweep {label}={val:g}"):
1651	                            done += 1
1652	                    except Exception as exc:  # noqa: BLE001
1653	                        state.assess_msg = f"Sweep {label}={val:g} failed: {type(exc).__name__}: {exc}"
1654	                        state.flush()
1655	                else:
1656	                    state.assess_msg = f"Sweep of {label} done: {done} ◆ runs added to the plot."
1657	                state.sweep_progress = 100
1658	            finally:
1659	                state.assess_busy = False
1660	                state.sweep_active = False

================================================================================
## window @ 2026-09-03T15:17:53  (lines 251-290)

251	def _reject_hint(reason: str) -> str:
252	    """Turn a gate rejection into an actionable hint about which sliders drive it."""
253	    r = reason.lower()
254	    # (over-power no longer rejects -- it derates RPM; only the hard geometry limits reject)
255	    if "depth" in r:
256	        return ("↳ depth = how far blades reach in Z. Driven by sweep, LE curve, stagger, thickness "
257	                "and wrap. Reduce those (esp. Sweep tip / LE curve tip) — or add Extra-depth leeway.")
258	    if "tip dia" in r:
259	        return "↳ tip diameter too big: reduce Chord tip / stagger — or add Tip-past-frame leeway."
260	    if "hub" in r:
261	        return "↳ hub diameter out of range: adjust the Hub radius slider."
262	    if "weight" in r:
263	        return ("↳ too heavy: thinner blades (Thickness sliders), smaller chord/hub, or fewer blades "
264	                "— or add Extra-weight leeway.")
265	    return ""
266	
267	
268	def _blade_z_extent(params) -> float:
269	    """Axial (Z) extent of the blade from its section points -- FAST (no CAD-kernel solid)."""
270	    from fansim.geometry.blade import _interp_stations, _section_points_3d
271	    it = _interp_stations(params, params.n_span)
272	    r0 = params.hub_radius - params.root_embed
273	    zs = []
274	    for i in range(params.n_span):
275	        rf = float(it["r_frac"][i]); r = r0 + (params.tip_radius - r0) * rf
276	        pts = _section_points_3d(
277	            r=r, r_frac=rf, chord=float(it["chord"][i]), stagger_deg=float(it["stagger_deg"][i]),
278	            thickness=float(it["thickness"][i]), max_camber=float(it["max_camber"][i]),
279	            camber_pos=float(it["camber_pos"][i]), sweep=float(it["sweep"][i]),
280	            skew=float(it["skew"][i]), le_sweep=float(it["le_sweep"][i]),
281	            lean_deg=float(it["lean_deg"][i]), n_chord=params.n_chord, features=params.features)
282	        zs += [v.z for v in pts]
283	    return max(zs) - min(zs)
284	
285	
286	def _blade_max_dia(params) -> float:
287	    """Max blade DIAMETER (mm) from the section points -- FAST (no CAD solid). The BUILT tip diameter
288	    runs a bit past 2*tip_radius: the wrapped, chord-wide tip section bulges outward radially. This is
289	    the number the frame check must use, not the nominal 2*tip_radius (which reads ~0.5-2 mm small)."""
290	    import math

================================================================================
## window @ 2026-09-03T15:18:15  (lines 1448-1480)

1448	    def spec_status(stl_path, params, flat=None):
1449	        """Check the BUILT geometry against the active fan model (envelope/hub/depth/weight) with NO
1450	        CFD -- lets us flag an out-of-spec design at Preview instead of after an Assess. On a depth
1451	        issue, names the specific sliders driving it for THIS design."""
1452	        spec = active_spec()
1453	        try:
1454	            import trimesh
1455	            m = trimesh.load(str(stl_path))
1456	            (xmin, ymin, zmin), (xmax, ymax, zmax) = m.bounds
1457	            dia = 2.0 * max(abs(xmin), abs(xmax), abs(ymin), abs(ymax))
1458	            depth = zmax - zmin
1459	            # The fast preview mesh is non-fused (blades overlap the hub), so its own volume is wrong;
1460	            # prefer the accurate volume the preview worker wrote to a <stl>.meta.json sidecar.
1461	            vol = abs(float(m.volume))
1462	            meta = Path(str(stl_path) + ".meta.json")
1463	            if meta.exists():
1464	                try:
1465	                    vol = float(json.loads(meta.read_text()).get("volume_mm3", vol))
1466	                except Exception:  # noqa: BLE001 - fall back to the mesh volume
1467	                    pass
1468	            weight = estimate_weight_g(vol, spec.material)
1469	        except Exception:  # noqa: BLE001 - if we can't measure it, don't block
1470	            return True, ""
1471	        ok, reason = check_build(spec, dia, 2.0 * params.hub_radius, depth, weight)
1472	        depth_msg = _depth_driver_msg(flat) if (flat and "depth" in reason.lower()) else ""
1473	        if not ok:
1474	            return False, f"⚠ Out of spec — Assess will reject: {reason}. {_reject_hint(reason)}{depth_msg}"
1475	        over = over_spec_flags(spec, dia, depth, weight)
1476	        if over:
1477	            dm = _depth_driver_msg(flat) if (flat and any("depth" in o for o in over)) else ""
1478	            return True, "⚠ OVER-SPEC (allowed via leeway): " + "; ".join(over) + dm
1479	        return True, f"✓ fits {spec.name} (dia {dia:.0f} mm, depth {depth:.0f} mm, {weight:.0f} g)"
1480
