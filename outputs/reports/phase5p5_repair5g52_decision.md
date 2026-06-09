# Phase5.5 Repair5G.5.2 Decision

Decision: `runtime_updatepolicy_equivalence_failed`.

G5.2 fixed the candidate registry and UpdateParams hash story, and the full policy-closure sweep now passes. It did not clear the main runtime equivalence gate: on the required observed sweep over maps `random-32-32-20`, `maze-32-32-4`, `warehouse-10-20-10-2-1`, agents `50,100`, and IDs `146..155`, the runtime exact/shadow selector paths still do not reproduce the fixed static/map-agent baselines under the 3s closed-loop budget.

Key gate results:

```text
row_count = 1080
update_log_rows = 1058
runtime_always_static_exact_matches_static = false
runtime_always_static_max_regret_vs_static = 0.08146453089000016
runtime_always_map_agent_exact_matches_map_agent = false
runtime_always_map_agent_max_regret_vs_map_agent = 0.06535141799999988
selector_shadow_static_matches_static = false
semantic_parity_mismatch_count = 0
selected_params_hash_matches_expected = true
force_additive_policy_compliant = true
disable_policy_compliant = true
policy_closure_passed = true
checkpoint_export_passed = false
counterfactual_labels_passed = false
```

Interpretation:

```text
The remaining mismatch is not an unsupported-candidate or UpdateParams hash mismatch.
The mismatches are classified as time_budget_sensitivity, with no semantic parity mismatches.
Runtime selector plumbing still changes enough closed-loop behavior under the 3s budget that learned runtime selection remains blocked.
```

Required answers:

```text
1. Did runtime always-static reproduce static baseline?
   No. Max regret vs static = 0.08146453089000016.

2. Did runtime always-map-agent reproduce map-agent baseline?
   No. Max regret vs map-agent = 0.06535141799999988.

3. Did selector shadow mode reproduce static while logging decisions?
   No. Shadow-static exact matching failed under the required sweep.

4. Is force-additive policy fixed?
   Yes for G5.2 exact closure. Full policy-closure sweep passed.

5. Is disable policy fixed?
   Yes. Full policy-closure sweep passed.

6. Are UpdateParams hashes consistent?
   Yes. Candidate registry and selected runtime hash checks passed.

7. Are replayable traffic_before + trace checkpoints available?
   Not as an allowed G5.2 learning artifact. Checkpoint export is blocked because UpdatePolicy equivalence failed.

8. Are true counterfactual labels available?
   No. Counterfactual labels remain unavailable because replayability is blocked by UpdatePolicy equivalence failure.

9. Is G6 learned mixture/residual policy justified?
   No. Runtime equivalence and counterfactual labels have not passed.

10. Are IDs 166..205 still untouched?
   Yes. G5.2 used observed IDs 146..155 only.
```

Promotion state:

```text
phase5p5_allowed = false
phase6_allowed = false
aaai_ready = false
```

Next allowed work is to reduce or isolate the runtime selector overhead/timing divergence so exact/shadow runtime paths are policy-equivalent to fixed baselines under the required time budget. Do not train a learned selector and do not run IDs `166..205` until that gate passes.
