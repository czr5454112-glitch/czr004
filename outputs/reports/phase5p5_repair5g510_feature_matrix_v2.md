# Phase5.5 Repair5G.5.10 Feature Matrix v2

- rows: `60`
- feature_count: `64`
- checkpoint_rows_used: `3`
- rows_with_traffic_snapshot_values: `0`
- runtime_safe_pre_update_only: `True`
- forbidden_outcome_features_excluded: `True`

The v2 matrix keeps G5.8 perf-safe context features and adds pre-update C/F traffic summaries, normalized event features, wait/block burst indicators, progress/nonprogress ratios, later-iteration flags, and a static-boundary proxy that uses only pre-update state.
