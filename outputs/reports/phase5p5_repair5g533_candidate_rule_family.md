# G5.33 Candidate Rule Family

- decision: `bounded_candidate_rule_family_created`
- candidate count: `11`
- new G5.33 aliases: `none`; existing `repair5g59_*` project-owned aliases cover the bounded family without adapter edits.

- `repair5g59_additive_fallback`: additive LTM baseline
- `repair5g59_static_flow_shield`: validated static flow-shield baseline
- `repair5g59_c_only_f_disabled`: C-channel-only control
- `repair5g59_light_cong_light_flow`: light C/F pressure
- `repair5g59_block_heavy_flow_guard`: blockage-heavy guard
- `repair5g59_commit_heavy_flow_guard`: committed-flow emphasis
- `repair5g59_wait_conservative`: suppresses nonprogress waits
- `repair5g59_wait_aggressive`: penalizes waits aggressively
- `repair5g59_flow_decay`: decays F-channel demand
- `repair5g59_high_beta_cap_safe`: stronger bounded flow shield
- `repair5g59_low_beta_high_cap`: lower beta with higher cap
