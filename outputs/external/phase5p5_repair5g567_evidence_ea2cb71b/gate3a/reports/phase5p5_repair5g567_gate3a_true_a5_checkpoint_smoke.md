# Repair5G.5.67 Gate-3A True A5 Checkpoint Smoke

- decision: `gate3a_true_a5_checkpoint_smoke_pass`
- source state: `g567_source_state_clean`
- checkpoint: `/root/shared-nvme/g567_stage2a_direct_exact_ea2cb71b_tmux/models/gcst/phase5p5_repair5g567_a5_hierarchical_od_perceiver_actor_seed567.pt`
- checkpoint variant: `A5`
- selected contexts: `32`
- selected agent tiers: `[32, 256, 1000, 3000]`
- selected map families: `{'chambers': 5, 'city': 3, 'empty': 4, 'game': 4, 'cross': 1, 'islands': 4, 'large_connector': 3, 'maze': 6, 'public_other': 1, 'warehouse': 1}`
- selected map source types: `{'synthetic_stress_map': 13, 'canonical_public_benchmark_map': 19}`
- selected scenario source types: `{'czr004_synthetic_derived_scenario': 13, 'czr004_derived_on_public_parent_map': 19}`
- A5 theta rows: `32`
- replay decision: `g567_three_tier_replay_materialized`
- process hard timeout rows: `0`

This Gate-3A preflight does not construct or access the final blind panel and does not unlock full-scale generation, million-row acquisition, or 48h training.
