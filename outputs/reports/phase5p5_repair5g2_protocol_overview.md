# Phase5.5 Repair5G.2 Protocol Overview

Repair5G.2 tested whether the G1 flow-shield headroom survives a frozen selector protocol and untouched final validation.

Data policy:

```text
support IDs: 1..25
development validation IDs: 26..45
fresh final IDs: 46..65
```

Protocol sequence:

```text
1. Audit G1 parity and determinism.
2. Build a restricted G2 candidate subset from controls, C-equivalent baselines, flow-shield candidates, agent-progress diagnostics, and synthetic diagnostics.
3. Run support probe on IDs 1..25.
4. Build selector training contexts from support IDs 1..25 plus observed G1 dev IDs 26..45.
5. Tune deterministic selectors using development data only.
6. Freeze the selector before evaluating IDs 46..65.
7. Run fresh final validation on IDs 46..65.
8. Write a decision report without promoting Phase5.5 or Phase6.
```

Important audit result:

```text
G1 parity audit true semantic mismatches = 0
G2 support rows = 9000 / 9000
G2 support strict parity mismatches = 85
G2 support true semantic parity mismatches = 0
G2 support mismatch classification = time_budget_sensitivity only
G2 fresh-final strict required controls passed exactly
```

Frozen selector:

```text
selected_selector_type = map_agent_group_static_selector
selected_static_candidate = repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75
final_ids_used_for_tuning = false
```

Fresh final result:

```text
rows = 2520 / 2520
missing_rows = 0
schema_errors = 0
solver_crash_count = 0
protocol_gates_passed = true
selected better / equal / worse = 62 / 44 / 14
selected mean_delta_ratio_vs_ltm = -0.020112979571774988
selected bootstrap probability mean < 0 = 1.0
selected ratio_worse_than_ltm_groups = 0
selected success_worse_than_ltm_groups = 0
```

Decision:

```text
continue_repair5g3_broader_validation
```

Interpretation:

```text
G0 global flow bonus failed.
G1 flow-shield produced strong development headroom.
G1 top candidates were diagnostic-only until G2.
G2 used a non-leaky frozen protocol and fresh IDs 46..65.
Fresh final IDs support broader G3 validation.
phase5p5_allowed=false
phase6_allowed=false
```
