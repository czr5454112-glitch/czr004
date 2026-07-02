# Gate-3B Same-Context Oracle Audit

This audit uses only completed Gate-3B artifacts. No solver, training, or full-campaign command was run.

## Data Scope

- `LABEL_TRAIN_candidate_pool`: `g567_gate3b_same_context_oracle_by_context.csv`, 2500 contexts with candidate replay rows and same-context baseline ratios.
- `DEVELOPMENT_trained_A5_primary_no_candidate_pool`: included in `g567_gate3b_target_vs_oracle_vs_actor_by_context.csv`; these rows have trained A5 and baselines, but no full candidate pool or Label-v5.4 target set in existing artifacts.

## Same-Context Candidate-Pool Oracle

- Best primary-safe oracle median relative improvement vs additive/LTM: `0.01772616137102189`
- Best primary-safe oracle median relative improvement vs static-flow: `0.009994739606717385`
- Contexts with best-safe oracle >=10% vs additive/LTM: `185`
- Contexts with best-safe oracle >=10% vs static-flow: `62`

## Selected Label-v5.4 Target

- Selected target median relative improvement vs additive/LTM: `0.01772616137102189`
- Selected target median relative improvement vs static-flow: `0.009994739606717385`
- Contexts with selected target >=10% vs additive/LTM: `185`
- Contexts with selected target >=10% vs static-flow: `62`

The Label-v5.4 training target is set-valued: the pipeline first selects the Pareto-safe AB set, then picks a representative target for each training example using joint-positive preference, gain-minus-harm, and medoid penalty. This audit outputs the representative target and the target-set count.

## Development Trained A5

- Gate-3B development median relative improvement vs additive/LTM: `0.010401758575756127`
- Gate-3B development median relative improvement vs static-flow: `0.0`
- Research blockers: `tier_A_additive_signal_missing, tier_B_static_flow_signal_missing`

Important limitation: existing artifacts do not contain trained Gate-3B A5 inference on the LABEL_TRAIN candidate-pool contexts, so actor-to-target L1 is unavailable for those same contexts without running new inference.
