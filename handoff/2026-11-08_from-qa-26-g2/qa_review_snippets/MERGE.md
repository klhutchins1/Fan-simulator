# QA_REVIEW.md merge instructions (append-only)

**Base:** master 83681c2's `docs/QA_REVIEW.md`. It is 1107 lines, ends with "## Round 26 (grok, 2026-11-04)…", and is byte-identical to 419df2e's copy.

`docs/QA_REVIEW.md` in this zip is that base with exactly two sections appended, in this order:
1. `1_r26-qa68-followup.md`: the QA-68 re-check on 419df2e. It is not committed on master and was placed separately, uncommitted; it is preserved here verbatim from `r26_qa68_out.zip`.
2. `2_r26-g2-followup.md`: this G2 re-check.

No existing line is changed.

**If the working tree already has snippet 1:** append only snippet 2. Don't add snippet 1 a second time; check for "## Round 26 follow-up (grok, 2026-11-08): QA-68".

If master's QA_REVIEW.md has moved on, append both snippets at the end in the same order.
