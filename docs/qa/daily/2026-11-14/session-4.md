# 2026-11-14 session 4 — re-derive the outline audits

Write this session into `docs/qa/rounds/r30.md`, then stop. Do not open a fifth session. Do not refit. Do not edit `config/problems/a12x25_reference.yaml`. Do not start a solve.

The branch is `stock-outline`. These audits are already filled in. Check that the tests and the written rules agree with the recorded verdict. Do not treat a failure as a license to try again.

| audit | recorded verdict | tests |
|---|---|---|
| `docs/validation/audits/2026-11-13-stock-outline-prereg.md` | FAIL. O3 hub band 1.102 mm. | `tests/test_outline_match.py` |
| `docs/validation/audits/2026-11-13-stock-hub-wall-prereg.md` | PASS at hub 26.0 mm, root embed 6.5 mm, root radius held at 19.5 mm. | `tests/test_outline_hub.py` |
| `docs/validation/audits/2026-11-13-stock-z-edge-prereg.md` | FAIL. Extent came inside 0.40 mm. Stagger and camber did not. Mean distance with no axial slide was 0.365 mm. | `tests/test_outline_z.py` |

Run those three test files. Then answer one question in a sentence: can the z-edge `le_sweep` step pass the camber tolerance of 0.005 while also passing the extent bar? Use the recorded station residuals. Do not propose a new recipe.
