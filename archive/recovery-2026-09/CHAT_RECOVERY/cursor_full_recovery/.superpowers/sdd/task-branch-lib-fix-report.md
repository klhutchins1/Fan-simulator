# Branch lib-fix report (`library-browse-preview`)

## Tests

Command:

```bash
uv run python -m pytest tests/test_library_view.py tests/test_cockpit_view.py -q --tb=short
```

Output:

```text
...........                                                              [100%]
11 passed in 3.61s
```

## Commit

Command:

```bash
git commit -m "Clear library provenance off-list and show preview status on Library."
```

Output:

```text
[library-browse-preview 33af2ef] Clear library provenance off-list and show preview status on Library.
 2 files changed, 47 insertions(+)
```
