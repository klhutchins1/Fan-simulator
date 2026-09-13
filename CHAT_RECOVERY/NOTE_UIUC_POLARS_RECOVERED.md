# Note for Claude — UIUC polars are recoverable

**2026-09-12 Cursor:** The CSVs are **not** permanently lost.

They were generated in Cursor transcript `9f43d5b7…` (Shell at ~line 1486), not
stored as Write blobs. Generator is saved at:

`CHAT_RECOVERY/cursor_transcript_extract/regen_uiuc_polars.py.txt`

Cursor re-ran that generator into `fansim/data/polars/`:

- `naca0012_re{4e4,8e4,1.6e5}.csv`
- `naca2412_re{4e4,8e4,1.6e5}.csv`
- `naca4412_re{4e4,8e4,1.6e5}.csv`

These are **condensed UIUC-trend representatives** (spec-accepted), not line-by-line
tunnel dumps. README already documents that.

Later README also mentions **e387 / sd7032 / s1223** families — those may need a
second regen pass from a later transcript stretch if tests expect them.

Spec: `docs/superpowers/specs/2026-09-04-uiuc-polar-tables-design.md`
