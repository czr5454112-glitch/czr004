# Phase5.5 Repair5G.5.13 Rich Feature Signal

- decision: `rich_context_features_missing_requires_local_feature_probe`
- rows: `1`
- feature_count: `0`
- rich_feature_count: `0`
- forbidden_feature_count: `0`
- rich_vs_g512_ranker_rerun: `not_run_missing_rich_features`
- runtime_claim_allowed: `false`

The tracked artifacts do not provide enough rich pre-choice wait/block/progress fields for a valid rich-feature rerun when the decision is `rich_context_features_missing_requires_local_feature_probe`. The correct next step is a local observed-ID trace-feature probe with `--max-workers 1`, not a runtime-policy claim.
