# Phase5.5 Repair5G.5 Protocol Overview

Repair5G.5 keeps LaCAM*/PIBT semantics fixed and restricts learning to pre-update selection among bounded UpdateLTM candidates.

- observed_id_ranges: `1..165`
- development_id_ranges: `1..165 only`
- learned_runtime_fresh_holdout: `166..205 primary, 206..245 fallback if touched`
- parity_policy: `semantic_parity_plus_time_budget_equivalence_required`
- final tuning on fresh holdout: `forbidden`
