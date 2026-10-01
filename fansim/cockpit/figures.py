"""Plotly design-space figures and pure filter/hint helpers (no Trame/VTK)."""

from __future__ import annotations

import plotly.graph_objects as go

from fansim.cockpit.placement import nominal_fits_spec


def prop_scatter_figure(pareto, user_points=()) -> go.Figure:
    """Propeller optimizer front: THRUST vs NOISE (the relative noise proxy), colored by efficiency —
    so you can pick a design that's punchy AND quiet. customdata = the row index (into
    prop_pareto_store) so a click loads that design. (Noise is a relative ranking score, not dB(A).)

    ``user_points`` are Analyze saves (diamonds); Optimize front uses circles. Indices in
    customdata address the concatenated store: study rows first, then user rows.
    """
    fig = go.Figure()
    study = [r for r in (pareto or []) if r.get("rel_dba") is not None and r.get("thrust_g") is not None]
    users = [r for r in (user_points or []) if r.get("rel_dba") is not None and r.get("thrust_g") is not None]
    if study:
        fig.add_trace(go.Scatter(
            x=[r["thrust_g"] for r in study], y=[r["rel_dba"] for r in study], mode="markers",
            name="optimize",
            marker=dict(size=14, color=[r["eff_g_per_w"] for r in study], colorscale="Viridis",
                        showscale=True, colorbar=dict(title="g/W"),
                        line=dict(width=1, color="rgba(0,0,0,0.4)")),
            customdata=list(range(len(study))),
            hovertemplate="%{x:.0f} g thrust<br>noise %{y:.0f} (rel)<br>%{marker.color:.2f} g/W<extra>opt</extra>"))
    if users:
        off = len(study)
        fig.add_trace(go.Scatter(
            x=[r["thrust_g"] for r in users], y=[r["rel_dba"] for r in users], mode="markers",
            name="analyze",
            marker=dict(size=16, symbol="diamond", color=[r["eff_g_per_w"] for r in users],
                        colorscale="Viridis", showscale=not study, colorbar=dict(title="g/W"),
                        line=dict(width=2, color="crimson")),
            customdata=list(range(off, off + len(users))),
            hovertemplate="%{x:.0f} g thrust<br>noise %{y:.0f} (rel)<br>%{marker.color:.2f} g/W<extra>analyze</extra>"))
    fig.update_layout(margin=dict(l=55, r=10, t=32, b=42), xaxis_title="thrust (g)",
                      yaxis_title="noise (relative — lower is quieter)",
                      title="Thrust vs noise — click a point (★ opt / ◆ analyze; color = g/W)",
                      height=340, template="plotly_white", showlegend=False)
    return fig


def prop_mission_figure(pareto, user_points=(), *, y_key: str, y_title: str) -> go.Figure:
    """Mission front: thrust vs ``y_key`` (hover minutes or range), colored by g/W."""
    fig = go.Figure()
    study_all = list(pareto or [])
    users_all = list(user_points or [])
    off = len(study_all)

    def _hover(r, y_val: float) -> str:
        thrust = float(r.get("thrust_g") or 0)
        rel = float(r.get("rel_dba") or 0)
        power = float(r.get("power_w") or 0)
        return (
            f"{thrust:.0f} g thrust<br>{y_val:.2f}<br>noise {rel:.0f} (rel)<br>{power:.0f} W"
        )

    sx, sy, sc, sh, si = [], [], [], [], []
    for i, r in enumerate(study_all):
        y_val = r.get(y_key)
        if y_val is None:
            continue
        y_val = float(y_val)
        sx.append(float(r.get("thrust_g") or 0))
        sy.append(y_val)
        sc.append(float(r.get("eff_g_per_w") or 0))
        sh.append(_hover(r, y_val))
        si.append(i)
    if sx:
        fig.add_trace(go.Scatter(
            x=sx, y=sy, mode="markers", name="optimize",
            marker=dict(size=14, color=sc, colorscale="Viridis",
                        showscale=True, colorbar=dict(title="g/W"),
                        line=dict(width=1, color="rgba(0,0,0,0.4)")),
            customdata=si, hovertext=sh, hoverinfo="text"))

    ux, uy, uc, uh, ui = [], [], [], [], []
    for j, r in enumerate(users_all):
        y_val = r.get(y_key)
        if y_val is None:
            continue
        y_val = float(y_val)
        ux.append(float(r.get("thrust_g") or 0))
        uy.append(y_val)
        uc.append(float(r.get("eff_g_per_w") or 0))
        uh.append(_hover(r, y_val))
        ui.append(off + j)
    if ux:
        fig.add_trace(go.Scatter(
            x=ux, y=uy, mode="markers", name="analyze",
            marker=dict(size=16, symbol="diamond", color=uc,
                        colorscale="Viridis", showscale=not sx, colorbar=dict(title="g/W"),
                        line=dict(width=2, color="crimson")),
            customdata=ui, hovertext=uh, hoverinfo="text"))

    fig.update_layout(margin=dict(l=55, r=10, t=32, b=42), xaxis_title="thrust (g)",
                      yaxis_title=y_title, height=340, template="plotly_white", showlegend=False)
    return fig


def cror_scatter_figure(rows) -> go.Figure:
    """CROR BEMT-proxy front: thrust vs relative noise (● Optimize)."""
    fig = go.Figure()
    if not rows:
        fig.update_layout(
            title="CROR — run Optimize (BEMT proxy)",
            xaxis_title="thrust (g)",
            yaxis_title="noise (relative)",
            margin=dict(l=40, r=20, t=40, b=40), height=340,
            template="plotly_white",
        )
        return fig
    xs = [float(r.get("thrust_g") or 0) for r in rows]
    ys = [float(r.get("rel_dba") or 0) for r in rows]
    cs = [float(r.get("eff_g_per_w") or 0) for r in rows]
    cds = list(range(len(rows)))
    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode="markers", customdata=cds,
        marker=dict(size=10, color=cs, colorscale="Viridis",
                    colorbar=dict(title="g/W", thickness=12),
                    line=dict(width=0.5, color="#333")),
        hovertemplate="%{x:.0f} g<br>noise %{y:.0f}<br>%{marker.color:.2f} g/W<extra></extra>"))
    fig.update_layout(
        xaxis_title="thrust (g)",
        yaxis_title="noise (relative — lower quieter)",
        title="CROR proxy — click a point (color = g/W)",
        margin=dict(l=40, r=20, t=40, b=40), height=340,
        template="plotly_white", showlegend=False,
    )
    return fig


def mf_scatter_figure(designs) -> go.Figure:
    """Mixed-flow scatter: CFM_free vs CFM_load (§8.6). ◆ Assess CFD; ● BEM Optimize."""
    fig = go.Figure()
    rows = [d for d in (designs or []) if d.get("objectives")]
    opt = [d for d in rows if str((d.get("extra") or {}).get("source", "")) == "mixed_optimize"]
    assess = [d for d in rows if d not in opt]
    if opt:
        fig.add_trace(go.Scatter(
            x=[d["objectives"]["cfm_free"] for d in opt],
            y=[d["objectives"]["cfm_load"] for d in opt],
            mode="markers",
            name="optimize (BEM)",
            marker=dict(
                size=14, symbol="circle",
                color=[d["objectives"]["efficiency"] for d in opt],
                colorscale="Viridis", showscale=True, colorbar=dict(title="eff %"),
                line=dict(width=1, color="rgba(0,0,0,0.4)"),
            ),
            customdata=[d["trial"] for d in opt],
            hovertemplate="#%{customdata}<br>free %{x:.1f} CFM<br>load %{y:.1f} CFM"
                          "<br>η %{marker.color:.1f}% (BEM)<extra>opt</extra>",
        ))
    if assess:
        fig.add_trace(go.Scatter(
            x=[d["objectives"]["cfm_free"] for d in assess],
            y=[d["objectives"]["cfm_load"] for d in assess],
            mode="markers",
            name="assess (CFD)",
            marker=dict(
                size=22, symbol="diamond",
                color=[d["objectives"]["efficiency"] for d in assess],
                colorscale="Viridis", showscale=not opt, colorbar=dict(title="eff %"),
                line=dict(width=2, color="crimson"),
            ),
            customdata=[d["trial"] for d in assess],
            hovertemplate="#%{customdata}<br>free %{x:.1f} CFM<br>load %{y:.1f} CFM"
                          "<br>η %{marker.color:.1f}%<extra>assess</extra>",
        ))
    fig.update_layout(
        margin=dict(l=50, r=10, t=30, b=45),
        xaxis_title="CFM at free delivery", yaxis_title="CFM at load",
        title="Mixed-flow — ● BEM Optimize / ◆ Assess CFD — click a point",
        height=340, template="plotly_white", showlegend=False,
    )
    return fig


def volute_scatter_figure(designs) -> go.Figure:
    """Volute Optimize scatter: capacity_proxy vs head_proxy (§14.4b). Ranking-only."""
    fig = go.Figure()
    rows = [d for d in (designs or []) if d.get("objectives")]
    if not rows:
        fig.update_layout(
            title="Volute — run Optimize (geometry proxy)",
            xaxis_title="capacity proxy",
            yaxis_title="head proxy",
            margin=dict(l=50, r=10, t=30, b=45), height=340,
            template="plotly_white",
        )
        return fig
    fig.add_trace(go.Scatter(
        x=[float(d["objectives"]["capacity_proxy"]) for d in rows],
        y=[float(d["objectives"]["head_proxy"]) for d in rows],
        mode="markers",
        name="optimize (proxy)",
        marker=dict(
            size=14, symbol="circle",
            color=[float(d["objectives"]["capacity_proxy"]) for d in rows],
            colorscale="Viridis", showscale=True, colorbar=dict(title="cap"),
            line=dict(width=1, color="rgba(0,0,0,0.4)"),
        ),
        customdata=[d["trial"] for d in rows],
        hovertemplate="#%{customdata}<br>cap %{x:.1f}<br>head %{y:.2f}"
                      "<extra>proxy</extra>",
    ))
    fig.update_layout(
        margin=dict(l=50, r=10, t=30, b=45),
        xaxis_title="capacity proxy (relative)",
        yaxis_title="head proxy (relative)",
        title="Volute — ● geometry proxy Optimize — click a point (not CFM)",
        height=340, template="plotly_white", showlegend=False,
    )
    return fig


FAN_OBJECTIVES = ("cfm_free", "cfm_load", "efficiency")
# One marker shape per cockpit Optimize run (color stays = efficiency).
OPT_RUN_SYMBOLS = ("square", "triangle-up", "pentagon", "hexagon", "triangle-down",
                   "cross", "star-diamond", "hourglass")


def pareto_front(designs, keys=FAN_OBJECTIVES) -> set[int]:
    """``id()`` of designs no other design beats on every objective (all maximised)."""
    pts = []
    for d in designs:
        try:
            pts.append((d, tuple(float(d.objectives[k]) for k in keys)))
        except (KeyError, TypeError, ValueError):
            continue
    front = set()
    for d, a in pts:
        dominated = any(
            all(bk >= ak for ak, bk in zip(a, b)) and any(bk > ak for ak, bk in zip(a, b))
            for _, b in pts
        )
        if not dominated:
            front.add(id(d))
    return front


def design_group(d, opened_run: str = "") -> tuple[str, str]:
    """(group key, legend label) for a fan design: opened study, one Optimize run, or Assessed."""
    from fansim.cockpit.labels import run_label

    extra = getattr(d, "extra", None) or {}
    if extra.get("source") == "cockpit_opt":
        run = str(extra.get("source_run") or "")
        return f"opt:{run}", run_label(run)
    if int(getattr(d, "trial", 0)) >= 9000:
        return "assessed", "Assessed by you"
    label = run_label(opened_run) if opened_run else "study"
    return "study", f"{label} (opened run)"


def design_provenance(d, opened_run: str = "") -> str:
    """One-line 'where/when' for hover text and the design dropdown."""
    extra = getattr(d, "extra", None) or {}
    _, label = design_group(d, opened_run)
    when = str(extra.get("completed") or "")
    if label == "Assessed by you" and extra.get("source_run"):
        label = f"Assessed under {extra['source_run']}"
    if when and when[:10] in label:          # same day as the run's start stamp
        when = f"done {when[11:]}"
    return f"{label} · {when}" if when else label


def scatter_figure(study_designs, user_designs=(), stock_ref: dict | None = None,
                   opened_run: str = "") -> go.Figure:
    study_designs, user_designs = list(study_designs), list(user_designs)
    everything = study_designs + user_designs
    effs = [d.objectives["efficiency"] for d in everything]
    cmax = max([45.0] + [e for e in effs if e is not None])
    best = pareto_front(everything)
    colorbar_shown = [False]

    def trace(designs, name, symbol_pareto, symbol_plain, line):
        show_scale = not colorbar_shown[0]
        colorbar_shown[0] = True
        return go.Scatter(
            x=[d.objectives["cfm_free"] for d in designs],
            y=[d.objectives["cfm_load"] for d in designs],
            mode="markers", name=name,
            marker=dict(
                # bigger markers = easier click targets (plotly only fires a click on a precise hit)
                size=[30 if d.is_pareto else 20 for d in designs],
                symbol=[symbol_pareto if d.is_pareto else symbol_plain for d in designs],
                color=[d.objectives["efficiency"] for d in designs],
                colorscale="Viridis", showscale=show_scale, colorbar=dict(title="eff %"),
                cmin=0, cmax=cmax, line=line,
            ),
            customdata=[d.trial for d in designs],
            text=[design_provenance(d, opened_run) for d in designs],
            hovertemplate="#%{customdata} · %{text}<br>free %{x:.1f} CFM"
                          "<br>load %{y:.1f} CFM<br>eff %{marker.color:.1f} %<extra></extra>",
        )

    fig = go.Figure()
    _, study_label = design_group(study_designs[0], opened_run) if study_designs else ("", "study")
    if study_designs:
        fig.add_trace(trace(study_designs, study_label, "star", "circle",
                            dict(width=1, color="rgba(0,0,0,0.4)")))
    groups: dict[str, tuple[str, list]] = {}
    for d in user_designs:
        key, label = design_group(d, opened_run)
        groups.setdefault(key, (label, []))[1].append(d)
    if "assessed" in groups:
        label, ds = groups.pop("assessed")
        fig.add_trace(trace(ds, label, "diamond", "diamond", dict(width=2, color="crimson")))
    for k, key in enumerate(sorted(groups)):     # Optimize runs, oldest first (stamped names)
        label, ds = groups[key]
        sym = OPT_RUN_SYMBOLS[k % len(OPT_RUN_SYMBOLS)]
        fig.add_trace(trace(ds, label, sym, sym, dict(width=1.5, color="rgba(0,0,0,0.7)")))
    ringed = [d for d in everything if id(d) in best]
    if ringed:
        fig.add_trace(go.Scatter(
            x=[d.objectives["cfm_free"] for d in ringed],
            y=[d.objectives["cfm_load"] for d in ringed],
            mode="markers", name="Best overall (nothing beats it on all 3)",
            marker=dict(size=40, symbol="circle-open", color="gold", line=dict(width=3)),
            customdata=[d.trial for d in ringed],
            text=[design_provenance(d, opened_run) for d in ringed],
            hovertemplate="#%{customdata} · %{text}<br>best overall: no design beats it on "
                          "free, load and efficiency at once<extra></extra>",
        ))
    if stock_ref and stock_ref.get("cfm_free") is not None and stock_ref.get("cfm_load") is not None:
        label = str(stock_ref.get("name") or "stock")
        noise = stock_ref.get("noise_dba")
        noise_bit = f"<br>noise {noise:.1f} dB(A)" if noise is not None else ""
        fig.add_trace(go.Scatter(
            x=[float(stock_ref["cfm_free"])],
            y=[float(stock_ref["cfm_load"])],
            mode="markers",
            name=f"{label} (published)",
            marker=dict(
                size=22,
                symbol="x",
                color="gold",
                line=dict(width=3, color="black"),
            ),
            customdata=["stock"],
            hovertemplate=(
                f"<b>{label}</b> (published)<br>"
                "free %{x:.1f} CFM<br>load %{y:.1f} CFM (hose est.)"
                f"{noise_bit}<br>click → load parametric stock"
                f"<extra>stock</extra>"
            ),
        ))
    fig.update_layout(
        margin=dict(l=50, r=10, t=40, b=45),
        xaxis_title="CFM at free delivery", yaxis_title="CFM at load",
        title="Design space (shape = run · gold ring = best)",
        height=580, template="plotly_white", showlegend=True,
        # Top-left is always empty (load CFM ≤ free CFM), so the legend never covers points.
        legend=dict(x=0.01, y=0.99, xanchor="left", yanchor="top", font=dict(size=11),
                    bgcolor="rgba(255,255,255,0.85)", bordercolor="rgba(0,0,0,0.15)",
                    borderwidth=1),
    )
    return fig


def filter_fitting_designs(designs, spec) -> list:
    """Keep designs whose built tip / depth / hub fit ``spec`` (Library nominal gate).

    Used by the Results scatter when **Fits this fan only** is on, so oversize
    opened-run / Optimize points drop off the graph for the selected fan model.
    """
    out = []
    for d in designs:
        params = getattr(d, "params", None) or {}
        if not params:
            continue
        if nominal_fits_spec(params, spec):
            out.append(d)
    return out


def reject_hint(reason: str) -> str:
    """Turn a gate rejection into an actionable hint about which sliders drive it."""
    r = reason.lower()
    # (over-power no longer rejects -- it derates RPM; only the hard geometry limits reject)
    if "vibration" in r or "resonance" in r or "blade-pass" in r or "bpf" in r:
        return (
            "↳ Plain English: blades whoosh past a fixed point at the blade-pass rate (BPF). "
            "If that rate is too close to how the blade likes to flex, it can buzz. "
            "This check runs before CFD. Fastest fix: fewer Blades. Next: Thickness mid up, "
            "or Tip radius down. (Not a full FEA — just a cheap safety gate.)"
        )
    if "stalls at this hose" in r:
        return ("↳ the fan's CFD static-pressure ceiling is below this hose, so the loaded solve "
                "reverses (CFD also under-predicts static ~2×). Pick a lighter **Application** "
                "preset (Case 8 → try a lower load), or read the free-air delivery above.")
    if "tip gap" in r or "frame gap" in r:
        return ("↳ too close to the frame: a real fan needs ≥0.5 mm tip clearance, and CFD won't run "
                "without it. Click **Fit envelope** (now leaves that clearance) or lower Tip radius.")
    if "depth" in r:
        return ("↳ depth = how far blades reach in Z. Driven by sweep, LE curve, stagger, thickness "
                "and wrap. Reduce those (esp. Sweep tip / LE curve tip) — or add Extra-depth leeway.")
    if "tip dia" in r:
        return "↳ tip diameter too big: reduce Chord tip / stagger — or add Tip-past-frame leeway."
    if "hub" in r:
        return "↳ hub diameter out of range: adjust the Hub radius slider."
    if "weight" in r:
        return ("↳ too heavy: thinner blades (Thickness sliders), smaller chord/hub, or fewer blades "
                "— or add Extra-weight leeway.")
    return ""
