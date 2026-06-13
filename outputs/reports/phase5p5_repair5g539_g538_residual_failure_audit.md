# G5.39 Audit of G5.38 Residual Failure

- decision: `g538_verified_global_residual_failed_continue_param_optimization`
- screening looked positive because it found a low-margin residual opportunity on a limited context slice.
- blind replay failed because the policy collapsed to one global residual candidate instead of stratum-specific parameters.
- selected candidates in blind replay: `['repair5g538_random_bridge_c_light']`
- success regressions vs static_flow / best_static: `2` / `5`
- top failure cluster: `{'paired_against_role': 'best_static_posthoc_diagnostic', 'map_family': 'random', 'agents': '100', 'budget_ms': '500', 'failure_rows': 3, 'success_regressions': 3, 'quality_worse_rows': 0, 'mean_quality_delta': '0', 'phase5p5_allowed': False, 'phase6_allowed': False, 'runtime_claim_allowed': False, 'learned_runtime_policy_validated': False, 'aaai_ready': False}`
- deployable static baselines are separated from posthoc/oracle static diagnostics.
