# UIUC Propeller Data Site — vendored vol-1 files

Source: UIUC Propeller Data Site, Volume 1
<https://m-selig.ae.illinois.edu/props/volume-1/propDB-volume-1.html> (files under `.../volume-1/data/`).
Downloaded 2026-09-29. Data credit: UIUC Propeller Data Site (Selig, Brandt, Deters et al.);
published for public use with citation. Plain-text tables, a few hundred bytes each.

| prop | geometry (r/R, c/R, beta deg) | static (RPM, CT, CP) | advancing flow (J, CT, CP, eta) |
|---|---|---|---|
| APC Slow Flyer 9x4.7 | `apcsf_9x4.7_geom.txt` | `apcsf_9x4.7_static_kt1032.txt` | `apcsf_9x4.7_kt1033_4008`, `kt1034_5013`, `kt1036_6004`, `kt1035_6029`, `kt1037_6815`, `kt1038_6819` |
| APC Thin Electric 9x6 | `apce_9x6_geom.txt` | `apce_9x6_static_rd0987.txt` | `apce_9x6_rd0988_4003`, `rd0990_5000`, `rd0989_5013`, `rd0992_6015`, `rd0991_6038`, `rd0993_6701`, `rd0994_6715` |

`apcsf_9x4.7_static.json` is the earlier single-row fixture (retrieved 2026-09-21).
Used by `tests/audit/test_prop_bemt_audit.py` and `fansim/propeller/bemt_catalog.py`
(`load_uiuc_geometry_blade`, `load_uiuc_performance`). Audit: `docs/validation/audits/2026-09-29-audit-03-prop-bemt-uiuc.md`.
