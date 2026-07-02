# Phase 5.5 Repair5G567 Gate-3B Research Signal Review

Date: 2026-07-02

Commit: `4b786766da4625b315c281c1b89e7ffd6cbfa591`

Remote stage: `/root/shared-nvme/g567_gate3b_bounded_2d334c79_tmux_r13_pool20000`

Local evidence bundle: `outputs/reports/g567_gate3b_final_20260702_085215_reports/`

## Decision

Gate-3B stopped correctly at:

`gate3b_research_signal_failed`

This is not an infrastructure failure and not a timeout failure. The bounded pipeline completed, but the final development-set research signal did not clear the additive/LTM and static-flow comparison gates.

## Machine-Checked Facts

- `gate3b_pipeline_pass`: `true`
- `gate3b_research_signal_positive`: `false`
- `gate3b_ready_for_full_review`: `false`
- `phase5p5_allowed`: `false`
- `phase6_allowed`: `false`
- Total solver rows: `63027`
- Scientific valid solver rows: `63003`
- Excluded infrastructure hard-timeout rows: `24`
- Unexcluded hard-timeout rows: `0`
- Development replay rows: `3000/3000`
- Development replay hard timeouts: `0`
- Label-train unique exact-labeled contexts: `2000`
- GPU-active training hours: `4.0000057585581414`
- Parent-map split leakage: `0`

## Development Comparison

Primary actor:

`A5::/root/shared-nvme/g567_gate3b_bounded_2d334c79_tmux_r13_pool20000/models/gcst/phase5p5_repair5g567_a5_hierarchical_od_perceiver_actor_seed568.pt`

Development replay:

- Contexts: `500`
- Executed rows: `3000`
- Additive rows: `500`
- Static-flow rows: `500`
- G556 rows: `500`
- Actor candidate rows: `1000`
- Exact execution mode: `direct_exact_solver_row`
- Counterfactual probe callback enabled: `false`
- Exact materialization rate: `1.0`

Measured deltas:

- Median relative improvement vs additive/LTM: `+0.010401758575756127`
- Parent-cluster bootstrap LCB05 vs additive/LTM: `+0.004003184406547981`
- Median relative improvement vs static-flow: `0.0`
- Parent-cluster bootstrap LCB05 vs static-flow: `-0.024142784246652928`
- Q95 harmful delta vs static-flow: `0.21588373910299968`

Gate blockers:

- `tier_A_additive_signal_missing`
- `tier_B_static_flow_signal_missing`

## Interpretation

The actor did show a weak positive median signal against additive/LTM on the development replay, but the signal was not strong enough to satisfy the Gate-3B supported-evidence rule.

Against static-flow, the result is not positive: the median relative improvement is exactly `0.0`, the cluster bootstrap lower bound is negative, and the tail-harm metric is nontrivial. This is why full campaign unlock is blocked.

## Why Earlier Gates Looked Better

Earlier gates mainly proved that the implementation direction was mechanically valid:

- direct exact rows terminate under the repaired timeout contract;
- Label-v5.4 materialization and replicate preservation work;
- A5 inference can produce continuous theta and feed the C++ UpdateLTM path;
- 3000-agent BF16 memory is within contract;
- the actor can be trained for the bounded GPU-hour target.

Those gates did not prove out-of-sample dominance over static-flow on the final Gate-3B development replay.

The label replay also had a weaker and more favorable signal:

- Label replay median relative improvement vs additive/LTM: `+0.007592495895814381`
- Label replay median relative improvement vs static-flow: `+0.00044446604649572667`
- Label replay better-outside-margin rows vs additive: `10580`
- Label replay better-outside-margin rows vs static-flow: `4437`

That is enough to justify running Gate-3B, but not enough to claim the trained actor generalizes. Gate-3B used held-out development contexts and the one-primary-actor selection rule, so the weak label-domain signal did not survive as a robust development-set result.

## Most Likely Causes To Audit Next

These are hypotheses, not proven root causes:

- Static-flow is already a strong baseline on the selected development mix, leaving little margin for A5.
- The actor may be learning safe/near-identity behavior rather than a utility-improving theta policy.
- The critic was not calibrated and was not used for actor training selection, so the actor did not have a reliable tail-risk filter.
- The selected primary actor optimized the required additive/static-flow safety rule, but not enough utility under the public/synthetic development distribution.
- The Gate-3B data scale is bounded; 2000 labeled training contexts and 4 GPU-active hours may be insufficient for stable utility gains, especially under high map-family diversity.

## Current Action

Do not launch full G5.67.

The correct state is:

`g567_full_campaign_waiting_for_manual_gptpro_review`

The completed Gate-3B artifacts are being preserved for GPT-Pro review and next-iteration diagnosis.
