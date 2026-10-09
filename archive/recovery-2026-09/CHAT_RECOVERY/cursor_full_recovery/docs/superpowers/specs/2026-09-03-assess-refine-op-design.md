# Assess opt-in refine-op

**Date:** 2026-09-03  
**Status:** accepted  
**Approach:** A switch on the Assess card, same plumbing as the Application picker. When on, pass `refine_op=True` through the isolated worker into existing `evaluate_candidate`. Default **off**. Stamp `op_cfd` on extra and add it to `score_caption`. Not a new third-solve implementation. Not fan Optimize.  
**Roadmap:** §8.2. Amends `2026-09-03-refine-op-cfd-design.md` non-goal “A cockpit checkbox this cycle.” Not §8.3.

## Plain language

`--refine-op` already exists: a third RANS at the hose operating pressure instead of the 2-point line. Assess always does two solves. A switch, off by default, is the same flag the CLI uses. It costs ~50% more time. The caption says whether the extra solve ran, was reused, or failed.

## Problem

```text
evaluate_candidate_isolated(..., load_pa=…)   # no refine_op
_eval_worker → evaluate_candidate(..., refine_op=False)
```

`evaluate_candidate` already implements the third solve. The worker never turns it on.

## Goal

1. **Switch** on the Assess card, under Application, above **Assess this design**:

```text
Third CFD at operating point (~50% longer; replaces the 2-point hose estimate)
```

State: `assess_refine_op: bool = False`. Changing it after a scored design is selected marks `edited_stale` the same way the hose picker does (load CFM is for the previous setting).

2. **Plumbing** — extend the job the same way as `load_pa`:

```text
eval_job_dict(..., refine_op: bool = False)
eval_kwargs_from_job → refine_op=bool(job.get("refine_op", False))
evaluate_candidate_isolated(..., refine_op=False)
_blocking_eval passes bool(state.assess_refine_op)
```

Default **False** so existing callers stay two-solve. Sweep uses the current switch.

3. **Stamp extra** (in `stamp_score_extra`):

```text
extra["refine_op"] = refine_op
# from result.raw when present:
extra["op_cfd"]        # "solved" | "reused-probe" | "failed"
extra["cfm_op_alg"]    # algebraic Q_op, when refine ran
```

Do not invent `op_cfd` when refine is off.

4. **`score_caption`**: if `op_cfd` is set, append `op CFD: solved` (or reused-probe / failed). If refine is off, omit — don’t print “2-point” on every legacy row.

5. Prop tab unchanged. No CLI change. No change to `refine_operating_metrics`. No catalog rewrite.

## Non-goals

- Default-on
- §8.3 fan Optimize
- Changing when the third solve is skipped (still 0.05 Pa / failed-keeps-algebraic)
- Print-penalty or circular-duct toggles
- A fourth Newton solve on the hose

## Tests (no Docker, no Trame, no CFD)

- `eval_job_dict(..., refine_op=True)` stamps `"refine_op": True`; default omitted-or-false is False
- `eval_kwargs_from_job` passes `refine_op` through (default False)
- `score_caption` with `op_cfd="solved"` contains `op CFD: solved`; empty extra still does not claim circular
- `stamp_score_extra(..., refine_op=True, raw={op_cfd: "solved"})` copies both
- `app.py` contains `assess_refine_op`, `state.assess_refine_op = False`, and the switch label; `_blocking_eval` mentions `refine_op`

## Files

| Path | Responsibility |
|---|---|
| `fansim/optimize/isolated_eval.py` | `refine_op` on job / isolated call |
| `fansim/optimize/_eval_worker.py` | `eval_kwargs_from_job` |
| `fansim/cockpit/score_caption.py` | stamp + caption clause |
| `fansim/cockpit/app.py` | switch, stale-on-change, `_blocking_eval` |
| `tests/test_isolated_eval.py` | job + kwargs |
| `tests/test_score_caption.py` | caption / stamp |
| `tests/test_cockpit_view.py` | switch copy |
| `docs/roadmap.md` | §8.2 done |

Do not add Python dependencies. Do not commit `catalog/catalog.db`.
