# CFM_PER_M3S single source (#49) — 2026-11-25

`fansim.optimize.meanline` and `fansim.optimize.multi_point` now import `CFM_PER_M3S`
from `fansim.cfd.metrics` instead of carrying a second literal `2118.882`.

`tests/test_math_consistency.py::test_cfm_factor_is_single_source` asserts identity for
meanline/multi_point. That test is a registered check for `cfd.cfm_from_outlet_flow`,
`cfd.duct_area`, and `fan.bem_prescreen`, so those units were re-proven after the test edit
(checks green; fingerprints updated). No physics number change — same constant, one definition.
