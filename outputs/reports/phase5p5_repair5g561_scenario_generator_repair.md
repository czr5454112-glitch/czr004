# Repair5G.5.61 Scenario Generator Repair

- decision: `g561_valid_scenario_bank_expanded_component_aware`
- valid scenarios: `2600`
- retained G5.60 valid scenarios: `1203`
- generated G5.61 valid scenarios: `1397`
- target valid independent instances: `2600`
- physical map hashes: `56`
- map families: `12`
- start-goal regimes: `8`
- density bins: `6`
- budget profiles: `8`
- raw materialization root: `C:/PROGRAMING/czr004/outputs/tmp/phase5p5_repair5g561_valid_scenario_bank`

The generated G5.61 rows use component-aware sampling without modulo reuse. Starts and goals are sampled without replacement, each paired start-goal is in the same connected component, and raw map/scenario files are materialized under `outputs/tmp` for reproducible hash checks.

Raw generated files are intentionally not tracked in Git; the committed manifest records hashes, row counts, source command, and the ignored raw root.

Claims remain closed until materialization, replay, and solver-performance gates pass.
