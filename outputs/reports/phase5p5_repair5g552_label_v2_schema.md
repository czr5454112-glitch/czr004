# G5.52 Label-v2 Schema

Training unit: same context, same checkpoint, same traffic_before, same trace_window, same horizon, same short probe budget.

Allowed policy actions are exactly `ABSTAIN_TO_STATIC_FLOW` or `ALLOW_THETA(theta_id)`. Utility labels are only valid after safety labels pass.
