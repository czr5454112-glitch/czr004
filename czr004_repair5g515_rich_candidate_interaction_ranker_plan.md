# Repair5G.5.15 Rich Candidate Interaction Ranker Plan

Generated: 2026-06-07

## Objective

Implement the local Repair5G.5.15 execution round from the existing G5.14 v4 table:

```text
rich context features
-> rich x candidate-parameter interactions
-> within-context pairwise ranking
-> safety-calibrated nonstatic gate
-> hard controls, OOF calibration, false-positive autopsy, and final decision
```

This is an offline table-only diagnostic. It does not run the solver, does not change C++ or solver semantics, and does not export a runtime policy.

## Constraints

- Do not modify `external/lacam2/lacam2/**`.
- Do not change PIBT, LaCAM*, candidate generation, conflicts, pruning, OPEN/EXPLORED, rewrite, incumbent, or restart semantics.
- Do not introduce action prediction, priority prediction, learned restart, h-values, candidate deletion, MAPF action logits, or learned solver control.
- Do not inspect or run IDs `166..205`.
- Start from `outputs/tables/phase5p5_repair5g514_candidate_feature_matrix_v4.csv`.
- Keep `phase5p5_allowed=false`, `phase6_allowed=false`, `aaai_ready=false`, `runtime_claim_allowed=false`, and `learned_runtime_policy_validated=false`.
- Leave unrelated dirty/untracked files untouched.

## Planned Artifacts

- `scripts/repair5g515_common.py`
- `scripts/verify_repair5g515_g514_artifacts.py`
- `scripts/analyze_repair5g515_v4_context_only_feature_blocker.py`
- `scripts/create_repair5g515_candidate_feature_matrix_v5_interactions.py`
- `scripts/train_repair5g515_two_stage_safety_ranker.py`
- `scripts/train_repair5g515_pairwise_context_ranker.py`
- `scripts/eval_repair5g515_calibrated_interaction_rankers.py`
- `scripts/analyze_repair5g515_false_positive_autopsy.py`
- `scripts/analyze_repair5g515_static_abstention_safety_update.py`
- `scripts/write_repair5g515_decision.py`
- `outputs/tables/phase5p5_repair5g515_*`
- `outputs/reports/phase5p5_repair5g515_*`
- `outputs/reports/phase5p5_repair5g514_final_interpretation.md`

## Validation

- `python -m py_compile` for all G5.15 scripts.
- G5.14 artifact verifier passes.
- JSON summaries parse.
- CSV row-count sanity passes.
- Leakage scan reports `forbidden_feature_count=0`.
- Reserved-ID guard rejects `166`.
- Grouped OOF/dev sanity: exactly 14 candidate rows per context.
- `git diff --check`.

## Commit

```text
repair5g: add rich candidate interaction ranker diagnostics
```
