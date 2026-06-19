# Repair5G.5.60 G5.59 Truth Audit

G5.59 produced real solver rows and real candidate-vs-g556 pair outcomes, but the learnability experiment did not train a real GCST critic.

## Main Findings

- Pair rows: 128000.
- Instance manifest rows: 2000; unique SHA instance_uids: 1762.
- Original pair-row uid join to split manifest: 0/128000.
- Original heldout examples after that join: 0.
- The legacy runner overwrote `instance_uid` with context-horizon keys, so heldout-map splits were present but unreachable.
- G5.59 training wrapper scripts route to evaluator/synthetic planning functions rather than real training functions.

## Decision

`g559_failed_identity_and_training_entrypoints_not_gcst_learnability`
