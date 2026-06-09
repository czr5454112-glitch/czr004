# czr004 Repair5G.5.14 Rich Trace Feature Probe and V4 Ranker Plan

Date: 2026-06-07
Branch: `phase4f5p5-stable-attention-lau`

## Objective

Repair5G.5.14 recovers runtime-safe rich pre-choice trace features from existing checkpoint JSONL artifacts, joins them onto the G5.12 candidate-level matrix, and reruns grouped hard-controlled candidate ranking as feature matrix v4.

This is an execution round. It is not a runtime integration round and it does not open Phase5.5, Phase6, runtime learned-policy, or AAAI-ready claims.

## Carry-Forward Interpretation

G5.13 kept the G5.12 offline diagnostic positive but downgraded the learned signal:

```text
decision = candidate_ranker_signal_reduced_to_simple_prior_continue_rich_features
```

The bottleneck is feature/data richness, not the bounded dual-channel UpdateLTM direction. The next test is whether allowed pre-choice rich trace aggregates can beat the simple train-only safe priors that G5.13 exposed.

## Constraints

- Do not modify `external/lacam2/lacam2/**`.
- Do not change PIBT, LaCAM*, candidate generation, conflicts, pruning, OPEN/EXPLORED, rewrite, incumbent, or restart semantics.
- Do not introduce action prediction, priority prediction, learned restart, h-values, candidate deletion, MAPF action logits, or learned solver control.
- Do not run or inspect IDs `166..205`.
- Use existing checkpoint JSONL before any solver run.
- If a local probe is needed later, use observed IDs `146..155`, `--max-workers 1`, and no shared concurrent JSONL append.
- Keep `phase5p5_allowed=false`, `phase6_allowed=false`, `aaai_ready=false`, `runtime_claim_allowed=false`, and `learned_runtime_policy_validated=false`.
- Leave unrelated dirty and untracked files untouched.

## Implementation Steps

1. Verify required G5.12/G5.13 summaries and tables, stopping with `missing_g513_artifacts_stop` if they are absent or malformed.
2. Search existing local and server checkpoint JSONL artifacts for rows with `feature_names`, `feature_values`, `traffic_before_hash_full`, `map`, `agents`, `seed`, and `iteration`.
3. Parse usable checkpoint rows into one rich context row per G5.12 context, expanding the allowed feature vector fields only.
4. Join rich context features onto the 840-row G5.12 candidate feature matrix v3 to build candidate feature matrix v4.
5. Audit rich feature signal, leakage, map-agent prior suspicion, and v3 versus v4 feature inventory.
6. Train a deterministic v4 ridge delta/risk ranker and evaluate grouped dev context decisions against hard controls, ablations, random/shuffled controls, and oracle upper bound.
7. Continue the static/abstention safety preflight using G5.13 boundary data plus G5.14 decisions.
8. Write a final conservative decision report.

## Expected Outputs

- `scripts/repair5g514_common.py`
- `scripts/verify_repair5g514_g513_artifacts.py`
- `scripts/find_repair5g514_existing_rich_checkpoint_artifacts.py`
- `scripts/create_repair5g514_rich_context_features_from_checkpoints.py`
- `scripts/run_repair5g514_rich_feature_probe_local.py`
- `scripts/create_repair5g514_candidate_feature_matrix_v4.py`
- `scripts/analyze_repair5g514_rich_feature_signal.py`
- `scripts/train_repair5g514_candidate_regret_ranker_v4.py`
- `scripts/eval_repair5g514_candidate_regret_ranker_v4.py`
- `scripts/analyze_repair5g514_static_abstention_boundary_targets.py`
- `scripts/write_repair5g514_decision.py`
- `outputs/tables/phase5p5_repair5g514_*`
- `outputs/reports/phase5p5_repair5g514_*`

## Validation

- `python -m py_compile` on all G5.14 Python scripts.
- Run the full G5.14 local script sequence.
- Parse generated JSON summaries.
- Check CSV row counts.
- Confirm leakage scanner reports `forbidden_feature_count == 0`.
- Confirm reserved-ID guard rejects `166`.
- Confirm grouped dev sanity: `30` dev contexts and `14` candidates per context.
- Run `git diff --check`.
