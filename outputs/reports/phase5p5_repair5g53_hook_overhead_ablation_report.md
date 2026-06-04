# Phase5.5 Repair5G.5.3 Hook Overhead Ablation

- minimal_hook_static_matches_static: `False`
- minimal_hook_map_agent_matches_map_agent: `False`
- shadow_noop_minimal_matches_static: `False`
- minimal_hook_failure_class: `minimal_hook_time_budget_sensitivity`
- minimal_hook_time_budget_sensitivity_count: `10`
- true_semantic_mismatch_count: `0`
- dominant_overhead_component: `repair5g53_cost_audit_ms`
- decision: `minimal_hook_semantic_bug`

This is diagnostic-only; performance claims must use `--repair5g-runtime-audit-mode perf`.
