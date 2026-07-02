# G5.67 Gate-3B Failure Diagnosis Summary

Decision: `gate3b_research_signal_failed`

Pipeline pass: `True`

Research signal positive: `False`

Primary actor: `A5::/root/shared-nvme/g567_gate3b_bounded_2d334c79_tmux_r13_pool20000/models/gcst/phase5p5_repair5g567_a5_hierarchical_od_perceiver_actor_seed568.pt`

## Important Unit Separation

The previous G5.65 note reported a pooled checkpoint-context discovery signal against an additive/static floor. It did not contain a strict replay against `repair5g59_static_flow_shield`.

Gate-3B is different: it uses one selected A5 actor on held-out development contexts, with direct exact rows for additive/LTM, static-flow shield, g556, and the trained actor.

## Old Pasted G5.65 Signal

- Fresh rich-only E0/E1/E2 vs additive/static floor: median quality improvement `13.72%`, mean `14.44%`, success gains/regressions `464/3`, pair rows `10514`, pooled over checkpoint-context rows.
- Expanded vs additive/static floor: median quality improvement `14.62%`, mean `18.70%`, success gains/regressions `146/12`, pair rows `3000`, pooled over checkpoint-context rows.
- Strict old `repair5g59_static_flow_shield` replay: not present in the pasted note.

## Gate-3B Label Replay

- Rows: `60000`
- Contexts: `2500`
- Median relative improvement vs additive/LTM: `0.007592495895814381`
- Median relative improvement vs static-flow: `0.00044446604649572667`
- Median relative improvement vs g556: `0.0`

## Gate-3B One-Primary A5 Development Replay

- Contexts: `500`
- Actor pairs: `500`
- Median relative improvement vs additive/LTM: `0.010034757202263999`
- Median relative improvement vs static-flow: `0.0`
- Median relative improvement vs g556: `-0.00101919031419325`

## Gate Blockers

- `tier_A_additive_signal_missing, tier_B_static_flow_signal_missing`

The short version: the old discovery signal was real against an additive/static floor, but Gate-3B asked a stricter question: can one trained A5 actor generalize to held-out development contexts and beat both additive/LTM and direct static-flow shield robustly? The answer from this run is no.
