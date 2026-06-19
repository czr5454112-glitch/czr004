# Repair5G.5.61 Failure Attribution

- g560_replay_truth: `failed_materialization_gate` (exact_materialization_actor_rows=165/300; fallback_additive_executed=135)
- canonical_theta_schema: `implemented` (src/gcst/theta_schema.py is the canonical solver-facing schema; label_v4 actor bounds now use solver bounds.)
- valid_scenario_bank: `expanded_component_aware` (valid_scenarios=2600 target=2600; physical_map_hashes=56; map_families=12; regimes=8; density_bins=6; budget_profiles=8)
- materialization_contract: `passed` (planned=85; executed=85; candidate=1.0; fingerprint=1.0; scenario=1.0; identity=1.0)
- goal_aware_representation: `smoke_completed` (variants=F1,F2,F4,F6,F7; causal_sensitivity_passed=True)
- replay_ladder: `executed_exact_materialization` (corrected=g561_corrected_g560_scalar_replay_executed_exact_materialization; architecture=g561_architecture_replay_executed_exact_materialization; corrected_actor_rows=200; architecture_actor_rows=400)
