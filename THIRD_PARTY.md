# Third-party data and models

Fan Simulator's own code is MIT-licensed (`LICENSE`). The files below come from other people and
keep **their own licences**. Credit them as shown when you reuse them.

| What | Where in this repo | Source and author | Licence | Notes |
|---|---|---|---|---|
| A12x25 impeller model (the "Stock" reference shape) | `validation/reference/a12x25_impeller.stl`; also the Stock recipe fitted to it (`config/problems/a12x25_reference.yaml`) | "A12x25" by **MajorHardware**, Thingiverse thing 5893432: <https://www.thingiverse.com/thing:5893432> | **CC BY 4.0** (<https://creativecommons.org/licenses/by/4.0/>) | A close community model of the Noctua NF-A12x25 impeller, not Noctua CAD. Reoriented and centred for CFD (see `validation/reference/README.md`) |
| FAN-01 benchmark fan (geometry + measured curve) | `validation/reference/fan01/` | Krömer, Junger, Becker, Kaltenbacher, Czwielong, Schoder, Zenodo 10787093: <https://zenodo.org/records/10787093> | **CC BY 4.0** | Unmodified copies plus a derived CSV |
| UIUC propeller data | `validation/reference/uiuc_propdb/`, `tests/data/uiuc_gws_5x4.3/` | UIUC Propeller Data Site (Selig, Brandt, Deters et al.): <https://m-selig.ae.illinois.edu/props/propDB.html> | Public use with citation | |
| lt120 benchmark fan (geometry table, 5 digitised points) | `docs/qa/benchmarks/lt120/` | Tutar & Cam (2025), *Int. J. Turbomach. Propuls. Power* 10(1):1 (CC BY 4.0), re-plotting Lin & Tsai (2011) | **CC BY 4.0** for the geometry numbers; the points are cited from Lin & Tsai | See its `source.md` |
| nv150 benchmark fan (geometry + digitised curve) | `docs/qa/benchmarks/nv150/` | See its `source.md` | **CC BY-NC-ND 4.0: NOT compatible with MIT** | **Exclude from any public release** (non-commercial + no-derivatives) |
| Fan datasheet numbers (Noctua, Delta) | `docs/qa/benchmarks/*/curve.csv`, `fansim/fan_spec.py` | Manufacturer spec pages (links in each `source.md`) | Facts cited with links | Only the numbers, never copied pages |
| Cybenetics NF-A12x25 test report | cited only | <https://www.cybenetics.com/evaluations/fans/4/de/pdf/> | No reuse terms found | **Never stored here**; derived comparisons only |
| Drone radial / impeller STLs | `validation/reference/drone_radial/` | Downloaded batch, `radial+impeller_stls` | **Unknown: confirm the source before release** | |
