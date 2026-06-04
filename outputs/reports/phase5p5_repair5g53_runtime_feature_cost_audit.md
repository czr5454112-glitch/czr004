# Phase5.5 Repair5G.5.3 Runtime Feature Cost Audit

The runtime/audit split is necessary. Primary 3s evidence shows that full audit features and cost audit are far too expensive to use inside a closed-loop performance runtime.

## Primary 3s Observed Matrix

- Component rows: 840 G5.3 hook rows.
- Mean positive `repair5g53_update_policy_total_ms`: 582.7920456416465 ms.
- Mean positive `repair5g53_feature_build_ms`: 1271.620347457627 ms.
- Mean positive `repair5g53_cost_audit_ms`: 1607.4005457627118 ms.
- Mean positive `repair5g53_traffic_hash_ms`: 173.12367966101695 ms.
- Mean positive `repair5g53_json_write_ms`: 6.4949841807909605 ms.
- Mean positive `repair5g53_params_hash_ms`: 0.6596593220338983 ms.
- Mean positive candidate select and alias resolve were negligible relative to cost audit.

The dominant measured component is `repair5g53_cost_audit_ms`.

## Targeted Warehouse/100 Sensitivity

- At 5s, targeted warehouse/100 budget sensitivity passed with 0 minimal-hook mismatches; dominant component remained `repair5g53_cost_audit_ms`, mean 2861.07076 ms.
- At 10s, targeted warehouse/100 budget sensitivity passed with 0 minimal-hook mismatches; dominant component remained `repair5g53_cost_audit_ms`, mean 5949.77552 ms.

## Interpretation

`repair5g5_build_features_perf(...)` must remain the performance path. It avoids synchronous JSONL writes, traffic hashes, checkpoint copying, and full graph cost audits. `repair5g5_build_features_audit(...)` remains useful for diagnosis, but it is not performance evidence.

Future learned runtime claims must report perf-mode overhead separately from audit-mode overhead and must not compare audit-mode runs as if they were performance runtime.
