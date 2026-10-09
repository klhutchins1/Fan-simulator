# Cursor → Claude handoff fill (2026-09-12)

**Deadlock broken.** Cursor was last on the live tree (09-04 / 09-11). Claude held
the Aug26–Sep03 transcript dump. This file is Cursor's fill of
`HANDOFF_TO_CURSOR.md`.

**Workspace now:** `T:\Projects\Fan Simulator` (agent root moved here).

## Source of Cursor bytes

Not inventing from memory alone. Recovered from Cursor agent transcript:

`C:\Users\Kimball\.cursor\projects\e-Projects-programming-2-Fan-simulator\agent-transcripts\9f43d5b7-f2a4-41f9-9a46-42b198823724\9f43d5b7-f2a4-41f9-9a46-42b198823724.jsonl`

(~4.9 MB). Staging copies also under `CHAT_RECOVERY/cursor_transcript_extract/`.

## Installed into the live tree (NEW paths only — no overwrite of Claude files)

| Path | Provenance |
|------|------------|
| `fansim/optimize/system_curve.py` | **Rebuilt** from `2026-09-02-system-curve-design.md` + transcript StrReplace patches (initial Write was subagent-only). Includes `derated_probe_pa`, `probe_flow_cfm`, `bem_screen_cfm`, `bem_load_cfm`, eta clamp. |
| `fansim/optimize/presets.py` | Transcript Write + later `assess_load` / `assess_preset_items` |
| `fansim/optimize/design.py` | Transcript Write — **canonical `Design`** |
| `fansim/cfd/frame.py` | Transcript Write — four-bar `export_frame_stl` |
| `fansim/cfd/stator.py` | Transcript Write (+1 replace) |
| `fansim/acoustics/fwh.py` | Transcript Write (+8 replaces) — verify Farassat 1/c vs physics review |
| `fansim/isolated_job.py` | Transcript Write — `run_worker_module`, `load_objective_result` |
| `fansim/cockpit/fan_session.py` | Transcript Write (+2 replaces) |
| `fansim/cockpit/fan_copy.py` | Transcript Write |
| `fansim/cockpit/fan_widgets.py` | Transcript Write |
| `fansim/cockpit/score_caption.py` | Transcript Write (+1 replace) |
| `tests/test_presets.py` | Transcript Write |
| Specs under `docs/superpowers/specs/` | 09-02 system-curve, 09-04 boost + cockpit-opt-live-resume, 09-11 fan-tab + wind-turbine |

Also: `fansim/cockpit/data.py` now **re-exports** `Design` from `fansim.optimize.design` (Cursor 09-11 rule: optimize owns Design; cockpit does not duplicate).

## Still MISSING (no full Write in transcript — only patches / Task subagent)

Claude should **not** wait on Cursor for these unless more transcript archaeology is requested:

| Gap | Notes |
|-----|--------|
| `fansim/cockpit/fan_tab.py` | 15 StrReplace only — body lived in Task worker; not in parent Write |
| `fansim/cockpit/fan_ui.py` | 4 StrReplace only |
| `fansim/cockpit/fan_models.py` | 1 StrReplace only |
| `fansim/cockpit/fan_assess.py` | no Write |
| `fansim/cockpit/fan_optimize.py` | no Write |
| `fansim/cockpit/fan_viz.py` | no Write |
| `fansim/cockpit/library_view.py` | no Write |
| `fansim/cockpit/busy.py` | no Write |
| `fansim/cockpit/app.py` full post-extract | Claude has 990-line base + fragments + 223 edits — **Claude continues that path** |
| `fansim/centrifugal/`, `volute/`, `cror/`, `wind_turbine/` | inventories only in CHAT_RECOVERY |
| `tests/test_system_curve.py` | 12 StrReplace only — recreate from design spec fixtures |
| `uv.lock` | regenerate with `uv lock` |

## Design source of truth

**`fansim.optimize.design.Design`** is canonical.  
`fansim.cockpit.data` re-exports it. Do not keep a second dataclass.

## Blocking imports Claude listed — status

- [x] `system_curve.py` — landed (reconstructed; run tests next)
- [x] `cfd/frame.py` — landed (transcript)
- [x] `presets.py` — landed
- [x] `design.py` — landed
- [x] `stator.py`, `fwh.py`, `isolated_job.py` — landed
- [ ] fan-tab extract remainder — **Claude rebuild from specs + fragments**, or ask Cursor to dig Task tool-result blobs next

## Suggested next steps (Claude or either)

1. ~~Smoke system_curve~~ — **done:** `tests/test_system_curve.py` + `test_presets.py` → **12 passed**
2. Wire `scripts/run_optimization.py` `--preset` / `resolve_load` (Claude's recovered script is older — missing preset CLI)
3. Commit batch: `Cursor transcript fill: system_curve/presets/design/frame/stator/fwh/isolated + fan_* partial`
4. Continue app.py / fan_tab from Claude fragments — Cursor does not have a newer full app.py byte dump beyond what Claude already has
5. Domain skew note: Claude `domain.py` lacks `OPTIMIZER_TIP_GAP_MM` / `remaining_tip_gap_mm` / `casing_id_mm` that Cursor-era `objectives.py` imports — next Cursor/Claude batch should port those from the ring-to-frame-gap / honest-cfd specs in the transcript

## Opt / session memory Cursor still holds (no source needed)

- Commits on lost E: `b360dde`, `a110f76` (not on this T: repo)
- `runs/opt_cfm_compact_3h`: best trial 35 ≈ 47.1 free / **33.0 load** / 20.8% eff (case, guided, mountable) — weaker than `opt_run1` ~66 load
- Continuity errors ~1e-3 mid-solve are OK for this screening CFD
- Glyph tip spike ≠ broken CFM

## Rule reminder

Where Cursor installed a file above, it is the **newer** copy for that path (Claude had zero bytes).  
Where Claude already had `RECOVERED-FROM-CHAT` and Cursor did **not** overwrite — Claude keeps it until a real newer Cursor copy appears.
