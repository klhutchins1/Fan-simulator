# Round 14, Task A: re-verify QA-35, QA-36 / 24.4, QA-37, 27.3b (master 9562574)

Prereg: `qa_r14/PREREG_R14.md`, branch `prereg/round14`, commit `586bbe9` (sha256 `0ce049ca…16adc`),
committed 14:34 MDT 2026-10-17, before any data. Run clone `/workspace/fansim/qa/run_r14` (9562574).
Scripts and raw data: `handoff/2026-10-16_from-qa-14/`.

## A1: QA-35 (Linux open-build memory ask): **PASS**
- I rebuilt the same 28 ids as r9/r12 (14 shrouded and their 14 open twins, plus controls). The ids match r9.
- 26 pairs ran OK; 0 went over the ask. The ratio is remaining growth ÷ (1.15 × estimate) and passes at ≤ 1.0.
- Worst open build: control S5_0223 at **0.85**. Worst twin: S7_0172_twin at **0.826** (it was 1.03 in r12).
  Worst shrouded: S7_0188 at 0.70.
- S7_0097 and its twin were refused by the hang check before the build, so they are excluded as the prereg allowed.
- QA-35 is verified.
- Data: `data/a1_results.jsonl`, `data/a1_analysis.json`.

## A2a: QA-36 code tests: **PASS**
- `tests/test_ui_says_what_it_does.py`: 6 passed.
- The r12 proposal tests (from-qa-12/tests) pass 4/4 when copied to /tmp.
- Run in place under repo-r13 they fail 2, because pytest's rootdir path insertion imports repo-r13's old
  `fansim`. That is a harness artefact, not a code fault. See `data/a2a_pytest.txt`.

## A2b1: PLA+ through a real browser Preview → Export: **PASS for Export; Preview clause FAILS as registered**
Setup: the cockpit was cold-opened with PETG in Simple mode, then PLA+ was picked. The UI `select` was not found
within 2 s (it sits in a collapsed panel), so the pick went through the trame state (`state.material = "PLA+"`),
which is the same v-model change. I recorded this rather than clicking. Next: Preview, then Export (print id XNRNM).

| check (registered) | result |
|---|---|
| Export README names PLA+ | ✓ `Material: **PLA+** (nozzle 215 °C, bed 60 °C …)` |
| nozzle/bed equal the PLA+ values | ✓ 215/60 = `PRINT_TEMPS_C["PLA+"]`. These temps live in `print_export.py`, not `materials.py` as the prereg said. |
| `_print_fit.json` `material` | ✓ `"PLA+"` |
| `index.jsonl` line `material` | ✓ `"PLA+"` |
| Preview weight line names PLA+ | ✗ `✓ fits Noctua NF-A12x25 (dia 109 mm, depth 16 mm, 11 g)`: no material named |
| Preview grams = volume × 1240 kg/m³ (±1 g or 2 %) | ✗ as registered. The preview solid is 43 818 mm³ → 54.3 g solid. The line shows 11 g because `estimate_weight_g` multiplies by `DEFAULT_PRINT_INFILL = 0.20` (roadmap 2.4, by design). With infill: PLA+ 10.87 g → "11 g" ✓. My prereg left out the infill factor. |

- Discriminating power: PETG at 20 % gives 11.13 g, which also rounds to "11 g". So the Preview line cannot show
  which material it weighed. → **QA-42 (LOW, new)**.
- Observation (no QA id): the 20 % factor treats the whole solid as sparse infill. Thin FDM blades print almost
  entirely from perimeters, so the real printed mass is probably well above 11 g. That is a model limit, worth a
  doc line next to the weight.

## A2b2: switch material while Preview is busy: **INCONCLUSIVE**
- Busy was true when I switched to PLA+ and still true straight after. The finished line read 11 g.
- PETG and PLA+ both show "11 g" and the line names no material, so the observation cannot separate the two
  outcomes. INCONCLUSIVE, not a pass (AGENTS.md rule 1).
- 24.4 still needs a check that can tell them apart. Making QA-42 name the material, or adding one more decimal,
  would allow that.

## A3: QA-37 (kill the cockpit mid-Export): **PASS (run 2); run 1 exposed a hardening gap → QA-41**
- **Run 2** (harness reaps the killed launcher):
  - export worker 446719 was busy when the cockpit 446433 was SIGKILLed;
  - the worker was gone **0.75 s** later;
  - only `.partial-52346_…` was left, with no bare `{id}_….stl`;
  - `index.jsonl` stayed at 2 lines.
- **Run 1** (harness did not reap the launcher):
  - the launcher stayed a **zombie**;
  - `watch_parent` polls `parent_alive(pid)` = `os.kill(pid, 0)`, which **succeeds on a zombie**;
  - so the worker kept running for ≥ 30 s;
  - files were still safe: only `.partial-YD5PD…` was left and no index line was added.
- Probe: `data/a3_zombie_probe.txt`. A killed, unreaped child gives `parent_alive → True`; after reaping it gives
  `False`.
- In the real app, the launcher's parent is a shell or service manager that usually reaps it, but nothing
  guarantees that (for example, a parent that is stopped or busy).
- **QA-41 (LOW, new):** also exit when `os.getppid()` changes, or when `/proc/<pid>/stat` shows state `Z`.

## A4: 27.3b flow card in Simple mode: **FAIL → QA-40 (LOW, new)**
- Pass: s1 (compared + hint), s2 (compared, SWL only) and s4 (no SWL). Noise does not show in Simple mode, and the
  overall line has no noise words.
- Fail: s3 (design with SWL, no Stock reference) shows **"No Stock comparison for noise."** in Simple mode.
  The prereg said no noise text in Simple mode in any case.
- Data: `data/a4_flowcard.json`.
