# delta-afb1212sh: Delta AFB1212SH, 120 mm, 12 V (curve_only)

- **Source:** Delta Electronics, "Specification for Approval" AFB1212SH, sample issue date APR.19.2004. https://www.delta-fan.com/Download/Spec/AFB1212SH.pdf (scanned PDF, page 1 table).
- **Measured:** rated speed 3400 rpm (REF.), rated input 6.36 W at 12 V. The datasheet gives max airflow at zero static pressure and max static pressure at zero airflow; curve.csv holds those two endpoints, converted from CFM and mmH2O.
- **How measured:** the rig and standard are not stated on page 1. The sheet says readings are taken after a 10-minute warm-up. It also gives MIN limits (lot tolerance), which are not stored.
- **Not used:** the datasheet's P–Q curve figure (not digitised; quality over volume). No blade geometry is published, so BEM is not run.
- **Licence:** manufacturer document with no licence stated. Numbers are cited only; no figure or text is copied. MIT: a handful of cited spec values is a factual statement, but the document itself is Delta's.
