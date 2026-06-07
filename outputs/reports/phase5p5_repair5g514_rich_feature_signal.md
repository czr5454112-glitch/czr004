# Phase5.5 Repair5G.5.14 Rich Feature Signal

- decision: `rich_feature_signal_analyzed_continue_v4_ranker`
- candidate_rows: `840`
- rich_feature_count: `19`
- missing_rich_contexts: `0`
- forbidden_feature_count: `0`
- map_agent_leakage_suspicion: `{'map_agent_groups': 6, 'groups_with_one_rich_signature': 0, 'note': 'A single signature per map-agent would be suspicious; multiple signatures per group indicate the recovered rich fields vary by context.'}`
- runtime_claim_allowed: `false`

## Top Rich Feature Correlations

- `feature_rich_blocked_per_committed`: corr_delta=0.2030, corr_harm=0.1136
- `feature_rich_wait_per_committed`: corr_delta=0.1983, corr_harm=0.1168
- `feature_rich_committed_per_agent`: corr_delta=-0.1256, corr_harm=-0.0699
- `feature_rich_nonprogress_committed_count`: corr_delta=-0.0906, corr_harm=-0.0728
- `feature_rich_blocked_count`: corr_delta=0.0865, corr_harm=0.0333

The correlations are diagnostic only; the grouped hard-control evaluation decides whether v4 actually beats simple priors.
