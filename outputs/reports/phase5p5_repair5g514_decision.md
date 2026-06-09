# Phase5.5 Repair5G.5.14 Decision

- decision: `rich_trace_features_insufficient_continue_probe_or_lattice`
- rich_feature_source: `existing_checkpoint`
- existing_checkpoint_artifact_decision: `existing_rich_checkpoint_artifacts_found_parse_without_solver`
- rich_contexts: `60` / `60`
- v4_candidate_rows: `840`
- v4_rich_feature_count: `19`
- v4_beat_hard_controls: `True`
- g513_simple_prior_downgrade_resolved: `False`
- safety_package_complete: `False`
- phase5p5_allowed: `false`
- phase6_allowed: `false`
- runtime_claim_allowed: `false`
- learned_runtime_policy_validated: `false`
- aaai_ready: `false`

## Policy Snapshot

- `v4_ranker`: mean_delta_vs_static=-0.010721, harmful=0.067, coverage=0.267, rau_0.10=-0.004055
- `v3_g512_ranker_reproduced`: mean_delta_vs_static=-0.010423, harmful=0.033, coverage=0.200, rau_0.10=-0.007090
- `safe_slow_decay_train_gate`: mean_delta_vs_static=-0.007964, harmful=0.033, coverage=0.167, rau_0.10=-0.004631
- `safe_train_only_map_agent_gate`: mean_delta_vs_static=-0.013731, harmful=0.233, coverage=0.667, rau_0.10=0.009603
- `no_rich_feature_ablation`: mean_delta_vs_static=-0.010423, harmful=0.033, coverage=0.200, rau_0.10=-0.007090
- `rich_only_ranker`: mean_delta_vs_static=0.000000, harmful=0.000, coverage=0.000, rau_0.10=0.000000
- `oracle_upper_bound`: mean_delta_vs_static=-0.037934, harmful=0.000, coverage=1.000, rau_0.10=-0.037934

## Interpretation

G5.14 recovered rich pre-choice trace features from existing checkpoint JSONL artifacts and joined them into a v4 candidate matrix without rerunning solver work. The grouped hard-control evaluation decides whether those rich features resolve the G5.13 simple-prior downgrade. Regardless of the offline result, runtime, Phase5.5, Phase6, and AAAI claims remain closed because the static/abstention/no-solution/budget/OOD safety package is still incomplete.
