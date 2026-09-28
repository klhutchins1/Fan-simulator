# FAN-01 benchmark (low-pressure axial fan in a short duct)

External CFD-method benchmark with exact published geometry and a measured fan characteristic.

**Source:** Zenodo record 10787093, "FAN-01 Benchmark: Low pressure Axial Fan in a short Duct", v4 (2024-03-06),
<https://zenodo.org/records/10787093>. Authors: Krömer, Junger, Becker, Kaltenbacher, Czwielong, Schoder
(FAU Erlangen-Nürnberg, TU Wien, TU Graz). Dataset paper: <https://arxiv.org/abs/2211.12014>.

**License:** Creative Commons Attribution 4.0 International (CC-BY-4.0). Files here are unmodified copies
(`cad_model.zip`, `characteristic.zip`) plus a derived CSV.

## Design parameters (dataset paper, Table 2)

| | |
|---|---|
| fan diameter | 495 mm |
| hub diameter | 248 mm |
| tip clearance | 2.5 mm |
| blades | 9 |
| design volume flow | 1.4 m³/s |
| design total-to-static pressure | 150 Pa |
| rotational speed | 1486 rpm |
| test rig | ISO 5801 inlet test chamber |

## Files

- `cad_model.zip`: IGES + Parasolid of the rig assembly (rotor, duct, rig parts). IGES is surfaces only;
  the rotor must be isolated and sewn (see `fansim/validation/fan01.py` once written).
- `characteristic.zip`: measured characteristic (`characteristic_n1ug.h5` / `.mat`, `annotations.txt`,
  `pressure_sensors.pdf`). The chamber static pressure is measured against ambient.
- `characteristic.csv`: 20-point extract. Columns: volume flow (m³/s), chamber static pressure (Pa),
  and shaft power as stored under the dataset key `P_shaft_in_Nm` (values ~235–347; units to be confirmed
  from the dataset docs before use).

Extracted folders (`cad_model/`, `characteristic/`) are not committed.
