# G5.33 G5.32 Leakage And Gold Audit

- verdict: `g532_models_partly_inflated_continue_with_stricter_g533`
- corrected safe-positive count: `308`
- corrected candidate-induced count: `277`
- corrected teacher-selection count: `120`
- leakage finding: G5.32 risk diagnostics are partly inflated because direct failure-density and target-proxy fields are too close to the target.
- action: continue G5.33 with stricter solver-facing labels, strict splits, and negative controls.
