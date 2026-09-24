# fpv_5inch BEMT datasheet check Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record the existing `fpv_5inch` static BEMT point against its own datasheet, and print shaft power on the CLI line.

**Architecture:** `bemt_datasheet_report` already returns thrust, power, and both ratios. This plan does not change that function or the blade model. Task 1 makes the CLI print line show the power fields the JSON already has. Task 2 writes the measured ratios onto roadmap §4.3.

**Tech Stack:** Python 3.12, `uv run`, pytest, PowerShell here-strings for commits.

## Global Constraints

- Point is `fpv_5inch` at `ref_rpm` 30000. Datasheet is 1850 g and 650 W. Measured BEMT is 1654 g (ratio 0.894) and 572.6 W (ratio 0.881). Figure of merit is 0.648.
- `within_2x` stays a thrust-only flag.
- Do not retune camber, pitch, stall, or compressibility.
- No obj_2 CFD, mesh, or AMI. Do not edit smoke, refine, GCI, or wall JSON.
- Do not check §4.3 or §4.4.
- No Docker.
- On Windows, pytest may exit `-1073741819`, `-1073740940`, or `3221226356` after a printed pass line. Treat the pass line as success.
- PowerShell: do not chain commands with `&&`.
- Commit only the files a task lists. Do not stage `.superpowers/sdd/progress.md`, `catalog/catalog.db`, or `runs/`.

---

## File map

| File | Responsibility |
|---|---|
| `scripts/calibrate_prop_datasheet.py` | Print thrust and shaft power on one line |
| `tests/test_prop_calibrate.py` | Assert the printed line contains power and `power_ratio` |
| `docs/roadmap.md` | One §4.3 sentence with the two ratios and the spec/plan paths |

---

### Task 1: Print shaft power on the datasheet line

**Files:**
- Modify: `scripts/calibrate_prop_datasheet.py` (the `print` in `main`)
- Test: `tests/test_prop_calibrate.py`

**Interfaces:**
- Consumes: `bemt_datasheet_report` → dict with `thrust_g`, `power_w`, `rpm`, and `datasheet["thrust_ratio"]`, `datasheet["power_ratio"]`, `datasheet["thrust_ref_scaled_g"]`, `datasheet["power_ref_scaled_w"]`, `datasheet["within_2x"]`.
- Produces: stdout line for `fpv_5inch` containing `1654 g`, `572.6 W`, `power_ratio 0.881`, and `within_2x=True`.

- [ ] **Step 1: Write the failing test**

Add this test to `tests/test_prop_calibrate.py`:

```python
import subprocess
import sys
from pathlib import Path


def test_datasheet_cli_prints_power():
    script = Path(__file__).resolve().parents[1] / "scripts" / "calibrate_prop_datasheet.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--spec", "fpv_5inch"],
        check=True,
        capture_output=True,
        text=True,
    )
    line = proc.stdout.splitlines()[0]
    assert line == (
        "fpv_5inch: BEMT 1654 g, 572.6 W @ 30000 RPM | "
        "ref_scaled 1850.0 g, 650.0 W | "
        "thrust_ratio 0.894 | power_ratio 0.881 | within_2x=True"
    )
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run python -m pytest tests/test_prop_calibrate.py::test_datasheet_cli_prints_power -q --tb=line`

Expected: FAIL. The current first line has thrust and `within_2x` and does not contain `572.6 W` or `power_ratio`.

- [ ] **Step 3: Print power and power_ratio**

In `scripts/calibrate_prop_datasheet.py`, replace the existing `ratio = d.get("thrust_ratio")` line and the `print(...)` call that follows it with:

```python
        ratio = d.get("thrust_ratio")
        p_ratio = d.get("power_ratio")
        print(
            f"{key}: BEMT {rep['thrust_g']:.0f} g, {rep['power_w']:.1f} W @ {rep['rpm']:.0f} RPM | "
            f"ref_scaled {d.get('thrust_ref_scaled_g')} g, {d.get('power_ref_scaled_w')} W | "
            f"thrust_ratio {ratio if ratio is None else round(ratio, 3)} | "
            f"power_ratio {p_ratio if p_ratio is None else round(p_ratio, 3)} | "
            f"within_2x={d.get('within_2x')}"
        )
```

Leave the JSON payload as it is. Do not change `bemt_datasheet_report`.

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run python -m pytest tests/test_prop_calibrate.py::test_datasheet_cli_prints_power -q --tb=line`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add -- scripts/calibrate_prop_datasheet.py tests/test_prop_calibrate.py
git commit -m @"
feat(prop): print shaft power on the datasheet check

"@
```

---

### Task 2: Record the ratios on §4.3

**Files:**
- Modify: `docs/roadmap.md` (the §4.3 paragraph that starts with `**§4.3 screening stages**`)

**Interfaces:**
- Consumes: the measured ratios from the spec. No code from Task 1.
- Produces: a roadmap sentence. The §4.3 checkbox stays `- [ ]`.

- [ ] **Step 1: Add the sentence**

After the sentence that ends `GCI remains a screening stamp only.` and before the §4.4 checkbox, add:

```markdown
  **fpv_5inch BEMT datasheet (2026-09-23):** static check at 30000 rpm is 1654 g (ratio 0.894) and 572.6 W (ratio 0.881) versus 1850 g and 650 W. Figure of merit 0.648. `within_2x` is thrust only. Spec/plan:
  `docs/superpowers/specs/2026-09-23-prop-fpv-datasheet-design.md`,
  `docs/superpowers/plans/2026-09-23-prop-fpv-datasheet.md`.
```

Do not change `- [ ] **4.3` or `- [ ] **4.4`.

- [ ] **Step 2: Commit**

```powershell
git add -- docs/roadmap.md
git commit -m @"
docs(prop): record the fpv_5inch BEMT datasheet ratios

"@
```

---
