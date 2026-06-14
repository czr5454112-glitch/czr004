# G5.49 Audit of G5.48 Calibration Semantics

- decision: `g548_calibration_semantics_audited_for_g549`
- selected evaluable horizon rows: `12`
- unique evaluable strata: `4`
- evaluable families: `maze, random`
- warehouse entirely non-evaluable: `True`

G5.49 treats selected horizon rows and unique strata as separate metrics. A horizon-row count cannot silently satisfy a unique-stratum gate.
