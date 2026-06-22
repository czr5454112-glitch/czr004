# Repair5G.5.67 Stage-2A Diagnostic A5 Training

- decision: `stage2a_diagnostic_a5_checkpoint_ready`
- checkpoint: `/root/shared-nvme/g567_stage2a_direct_exact_ea2cb71b_tmux/models/gcst/phase5p5_repair5g567_a5_hierarchical_od_perceiver_actor_seed567.pt`
- checkpoint sha256: `054df49ca406dca3b922f6055a75a93cd7b684154ec1299a4a4e9f2ce6ea26b3`
- source state: `g567_source_state_clean`
- label-train contexts: `64`
- candidate rows: `64`
- replay decision: `g567_three_tier_replay_materialized`
- replay hard-timeout rows: `0`
- CUDA BF16 training: `True`
- diagnostic_only: `True`

This artifact is diagnostic-only and makes no performance claim. It is only intended to prove the A5 checkpoint -> inference -> continuous theta -> registry -> C++ UpdateLTM path used by Gate-3A.
