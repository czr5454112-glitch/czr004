# Phase5.5 Repair5G.5.4 Semantic vs Budget Gate Policy

G5.4 separates hard semantic replay correctness from runtime budget stress. A classified 3s deadline flip does not block observed-ID diagnostic checkpoint/probe label construction after UpdateLTM transform equivalence passes.

## Hard Semantic Gate

- UpdateLTM transform equivalence must pass.
- UpdateParams hashes, traffic-after hashes, and C/F update stats must match.
- Force-additive and disable controls remain mandatory policy controls.

## Budget-Stress Gate

- 3s exact minimal-hook reproduction is reported as a runtime stress gate.
- 5s and 10s targeted checks distinguish semantic harm from deadline sensitivity.
- Overhead attribution is diagnostic and does not imply traffic-map corruption.

## Learning-Label Gate

- Labels require replayable observed-ID contexts, same-context candidate probes, leakage audit, and oracle-gap measurement.
- Labels are diagnostic-only and cannot be used for Phase5.5, Phase6, AAAI-ready, or learned-runtime claims in G5.4.
- IDs 166..205 remain untouched.

## Gate Values

- `hard_semantic_update_transform_equivalence`: `True`
- `hard_semantic_updateparams_hash_equivalence`: `True`
- `hard_semantic_traffic_after_hash_equivalence`: `True`
- `hard_semantic_cf_update_stat_equivalence`: `True`
- `hard_semantic_force_additive_disable_controls`: `True`
- `budget_stress_3s_exact_minimal_hook`: `False`
- `budget_stress_failure_classified`: `True`
- `budget_stress_5s_targeted`: `True`
- `budget_stress_10s_targeted`: `True`
- `learning_label_replayable_context_gate`: `True`
- `learning_label_same_context_candidate_probe_gate`: `True`
- `learning_label_leakage_audit_required`: `True`
- `observed_id_diagnostic_labels_reopened`: `True`
- `ids_166_205_reserved`: `True`
- `semantic_vs_budget_policy_passed`: `True`

`phase5p5_allowed=false`, `phase6_allowed=false`, and `aaai_ready=false` remain mandatory.
