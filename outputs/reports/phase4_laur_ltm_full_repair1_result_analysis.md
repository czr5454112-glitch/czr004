# Phase4F Full Repair1 Result Analysis

Date: 2026-05-27

## Summary

Phase4F `full_repair1` completed operationally on the old server (`ackcs-00gjgxxy`) after resuming from the completed probe stage with `--steps dataset,train,eval`.

The run improved substantially over the first full baseline and fixed the safety gates, but it still does not pass the Phase4F performance gate because held-out validation exact rule top1/top3 remain below threshold.

## Run Scope

- server workspace: `/root/shared-nvme/czr004_phase4_repair1_43633e7`
- code commit used on server: `43633e7`
- mode: `phase4-full-repair1`
- record runs: `765 / 765`
- probe runs: `765 / 765`
- dataset rows: `2985`
- train rows: `2526`
- validation rows: `459`
- validation non-neutral checkpoints: `359`
- raw trace compression: zstd
- compressed trace sha256: `0dc42e4e9f6bf8d40642371897b208c2ce3c5901a4576687d11c5f48647a2ccc`

## Gate Result

Operational gate passed:

- record completed: `true`
- probe completed: `true`
- dataset completed: `true`
- train completed: `true`
- eval completed: `true`

Performance gate failed:

- validation top1: `0.3072` vs required `0.35` -> fail
- validation top3: `0.6427` vs required `0.70` -> fail
- harmful recall: `0.9538` vs required `0.80` -> pass
- harmful precision: `0.4015` vs required `0.30` -> pass
- predicted-rule mean delta: `0.0110` vs required `> 0.0` -> pass
- validation non-neutral count: `359` vs required `50` -> pass

## Comparison To Previous Full Baseline

The first full run had validation top1/top3 around `0.1943 / 0.4716` and harmful recall around `0.5525`.

Repair1 improved validation top1/top3 to `0.3072 / 0.6427` and harmful recall to `0.9538`.

This is a meaningful repair, not a dead end, but exact rule ranking is still short of the Phase4F gate. The model is now good enough at safety fallback but not yet good enough at exact update-rule selection on held-out maps.

## Interpretation

The added training coverage, feature-drop configuration, soft labels, and lower harmful threshold did the intended safety work. The remaining problem is exact rule ambiguity and generalization across held-out validation maps, especially where several non-additive rules have very close counterfactual deltas.

This result should not advance into Phase5 learned runtime. Runtime integration would be premature because the Phase4F exact top1/top3 gates still fail.

## Current Decision

Per the user instruction "continue trying the old server; if old does not work, pause", this repair1 full attempt should pause after backup and documentation. Do not start a new full experiment until the next repair idea is explicitly selected.

Likely next directions, if continuing later:

- Diagnose repair1 validation confusions against the new larger dataset.
- Separate safety classifier from exact rule ranker.
- Try pairwise/listwise ranking over rule deltas rather than single-label classification.
- Consider family-level action selection plus within-family conservative defaults.
