# czr004 Repair5G.5.12 Lattice Regret Ranking Execution Plan

Date: 2026-06-07
Branch: `phase4f5p5-stable-attention-lau`

## Objective

This is an implementation and execution round, not another handoff-prompt round.

G5.12 converts the G5.11 full observed-ID lattice from context-level oracle-class labels into candidate-level regret, ranking, and harmful-risk diagnostics:

```text
60 contexts x 14 candidates = 840 candidate-level rows
primary budgets = 1000ms and 2000ms
split = train seeds 146..150, dev seeds 151..155
```

The purpose is to test whether runtime-safe context metadata plus candidate parameter features can score bounded dual-channel UpdateLTM candidates offline. It does not validate a learned runtime policy.

## Constraints

- Do not modify `external/lacam2/lacam2/**`.
- Do not change PIBT, LaCAM*, candidate generation, conflicts, pruning, OPEN/EXPLORED, rewrite, incumbent, or restart semantics.
- Do not introduce action prediction, priority prediction, learned restart, h-values, candidate deletion, or MAPF action logits.
- Do not run or inspect IDs `166..205`.
- Keep Phase5.5, Phase6, runtime learned-policy, and AAAI-ready claims closed.
- Leave unrelated dirty and untracked files untouched.

## Implementation Steps

1. Verify required G5.11 artifacts and stop with `missing_g511_artifacts_stop` if any required table or summary is missing or malformed.
2. Build candidate-level regret/ranking targets from the G5.11 full lattice and the 14-candidate G5.9 lattice definition.
3. Analyze why G5.11 context-level v5 labels were too coarse and record the target-redesign decision.
4. Build a leakage-clean candidate feature matrix v3 with seed-based train/dev split.
5. Train a small deterministic ridge ranker and true random-feature/shuffled-label controls only after target and feature gates pass.
6. Evaluate grouped context decisions against static, additive, fixed-candidate, train prior, random, random-feature, shuffled-label, and oracle baselines.
7. Write the final G5.12 decision while keeping runtime and paper claims closed.

## Expected Outputs

- `scripts/repair5g512_common.py`
- `scripts/verify_repair5g512_g511_artifacts.py`
- `scripts/create_repair5g512_candidate_regret_targets.py`
- `scripts/analyze_repair5g512_candidate_regret_targets.py`
- `scripts/analyze_repair5g512_context_vs_candidate_target_gap.py`
- `scripts/create_repair5g512_candidate_feature_matrix_v3.py`
- `scripts/analyze_repair5g512_candidate_feature_signal_v3.py`
- `scripts/train_repair5g512_candidate_regret_ranker.py`
- `scripts/eval_repair5g512_candidate_regret_ranker.py`
- `scripts/write_repair5g512_decision.py`
- `outputs/tables/phase5p5_repair5g512_candidate_regret_targets.csv`
- `outputs/tables/phase5p5_repair5g512_candidate_feature_matrix_v3.csv`
- `outputs/tables/phase5p5_repair5g512_candidate_ranker_eval.csv`
- `outputs/tables/phase5p5_repair5g512_candidate_ranker_context_decisions.csv`
- `outputs/reports/phase5p5_repair5g512_*`

## Validation

- `python -m py_compile` on all G5.12 scripts.
- Run the full local G5.12 script sequence.
- Parse generated JSON summaries.
- Check CSV row counts.
- Confirm reserved-ID guard rejects `166`.
- Confirm leakage scanner reports `forbidden_feature_count == 0`.
- Run `git diff --check`.
- Commit and push only G5.12-related files.

