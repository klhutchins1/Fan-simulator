"""User-facing BEMT / prop-CFD honesty lines (R1.10 G5). Keep this module import-light."""

PROP_CFD_HONESTY = (
    "Experimental: not validated against published data — "
    "not a performance predictor: thrust reads 40–60 % low in validation; "
    "use it for direction and flow pictures only"
)
PROP_BEMT_HONESTY = (
    "±15 % on thrust at static; worse toward zero-thrust J; "
    "validated on a known-section prop (TU Delft) within 7 %; "
    "power (C_P) can read ~21 % low on slow-flyer props"
)
