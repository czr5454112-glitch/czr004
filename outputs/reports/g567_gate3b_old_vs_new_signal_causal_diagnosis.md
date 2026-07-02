# Gate-3B Old-vs-New Signal Causal Diagnosis

## Answer

The old 10%+ signal did not transfer cleanly because the earlier signal and Gate-3B are not the same statistical unit, and strict static-flow shield is much stronger than the older additive/static floor comparison.

## Evidence

### A. Candidate pool still contains same-context safe oracle signal

Best primary-safe oracle median relative improvement:

- vs additive/LTM: `0.01772616137102189`
- vs static-flow: `0.009994739606717385`

This answers whether high-safe-gain theta still exists in the existing candidate replay rows.

### B. Label-v5.4 target selection

Selected Label-v5.4 representative target median relative improvement:

- vs additive/LTM: `0.01772616137102189`
- vs static-flow: `0.009994739606717385`

Label-v5.3 proxy positives: `12308`

Label-v5.4 positives: `3447`

v5.3-proxy positive but not v5.4 target: `11209`

### C. A5 prediction fit

Existing artifacts do not contain trained Gate-3B A5 predictions on the same LABEL_TRAIN candidate-pool contexts, so actor-vs-target L1 cannot be computed without new inference. Development replay proves the trained actor itself only reached:

- vs additive/LTM median: `0.010401758575756127`
- vs static-flow median: `0.0`

### D. Static-flow shield absorbs much of the old additive advantage

Old strict G5.66 development three-tier median vs static-flow was `0.03541315345929518`, while Gate-3B one-primary A5 vs static-flow was `0.0` and the clustered LCB was `-0.024142784246652928`.

### E. Old pooled checkpoint-context unit effect

The G5.65 13-15% numbers were pooled checkpoint-context rows against additive/static floor. The old direct static-flow shield comparison is absent in those G5.65 pasted results. See `g567_gate3b_old_signal_rebased_to_gate3b_units.csv`.

## Most Likely Blocker

Current ranking:

1. Static-flow barrier and old-unit mismatch: high.
2. Label-v5.4 target conservatism / target-set collapse: medium to high; inspect same-context target-vs-oracle gap.
3. Candidate acquisition ceiling: depends on safe-oracle medians above; if static-flow oracle is low, this is high.
4. Actor fitting: unresolved from existing artifacts because trained A5 was not inferred on LABEL_TRAIN contexts.
5. Solver/timing noise: low; development replay completed with zero hard timeouts.

No full campaign should be launched from this result.
