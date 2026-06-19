# Repair5G.5.61 Scenario Generator Repair

- decision: `g561_valid_scenario_bank_underpowered_continue_generation`
- retained valid G5.60 scenarios: `1203`
- target valid independent instances: `2500`
- generator code path no longer uses modulo cell cycling; over-capacity assignments are marked invalid instead of duplicating vertices.
- next required work: component-aware replacement generation until the valid bank reaches at least 2,500 independent instances.
