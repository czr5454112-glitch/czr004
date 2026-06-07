# czr004 Repair5G.5.13 Hard-Controlled Ranker and Safety Preflight Plan

Date: 2026-06-07
Branch: `phase4f5p5-stable-attention-lau`

## Objective

Repair5G.5.13 is a local execution round after the G5.12 offline candidate-level ranker diagnostic. It hard-controls the G5.12 result, audits the actual selected candidates, reports bootstrap uncertainty, checks whether richer runtime-safe context features already exist in tracked artifacts, and starts the static/abstention/budget/OOD safety preflight.

This is not a runtime integration round. It does not open Phase5.5, Phase6, or AAAI-ready claims.

## Carry-Forward Interpretation

G5.12 passed as a positive offline diagnostic:

```text
contexts = 60
candidates = 14
candidate_level_rows = 840
train/dev rows = 420/420
primary dev mean_delta_vs_static = -0.010423295036333333
primary dev mean_delta_vs_additive = -0.09984319068166667
harmful_vs_static_rate = 0.03333333333333333
coverage = 0.2
fallback_rate = 0.8
```

The working interpretation is intentionally conservative: G5.12 is likely a safe-gated `slow_decay_high_shield` specialist rather than a broad learned runtime parameter policy.

## Constraints

- Do not modify `external/lacam2/lacam2/**`.
- Do not change PIBT, LaCAM*, candidate generation, conflicts, pruning, OPEN/EXPLORED, rewrite, incumbent, or restart semantics.
- Do not introduce action prediction, priority prediction, learned restart, h-values, candidate deletion, MAPF action logits, or learned solver control.
- Do not run or inspect IDs `166..205`.
- If IDs `156..165` are considered, prove they are already approved observed IDs from existing artifacts first.
- Keep `phase5p5_allowed=false`, `phase6_allowed=false`, `aaai_ready=false`, `runtime_claim_allowed=false`, and `learned_runtime_policy_validated=false`.
- Use local PC artifacts by default. Use `--max-workers 1` for any later local probe.
- Leave unrelated dirty and untracked files untouched.

## Implementation

1. Reproduce G5.12 from tracked artifacts:
   - verify G5.11 artifacts;
   - rebuild candidate regret targets;
   - rebuild candidate feature matrix v3;
   - retrain the ranker;
   - rerun grouped context evaluation;
   - rewrite the G5.12 decision.

2. Add selection audit:
   - `scripts/analyze_repair5g513_g512_selection_audit.py`
   - reports selected candidate distribution, map/agent selections, oracle capture, regret to oracle, missed helpful contexts, harmful selected contexts, and whether the policy is broad or specialist.

3. Add hard controls:
   - `scripts/eval_repair5g513_hard_controls.py`
   - includes static, additive, fixed slow decay, train-only safe gates, candidate-only prior, candidate-parameter-only ranker, map-agent-only gate, feature ablations, random-feature, shuffled-label, random-candidate, and oracle controls.

4. Add bootstrap uncertainty:
   - `scripts/analyze_repair5g513_bootstrap_uncertainty.py`
   - bootstraps dev contexts for primary metrics and mean-delta differences versus safe train-only controls.

5. Add rich runtime-safe feature detection:
   - `scripts/create_repair5g513_rich_context_feature_matrix.py`
   - `scripts/analyze_repair5g513_rich_feature_signal.py`
   - if tracked artifacts lack allowed rich pre-choice fields, write `rich_context_features_missing_requires_local_feature_probe`.

6. Add static/abstention safety preflight:
   - `scripts/analyze_repair5g513_static_abstention_safety_preflight.py`
   - reports static wins, static-near-oracle contexts, harmful false positives, uncertainty, budget-sensitive contexts, infeasible cells, and observed-bank holdout coverage.

7. Add final decision:
   - `scripts/write_repair5g513_decision.py`
   - if G5.12 does not beat safe train-only controls, report `candidate_ranker_signal_reduced_to_simple_prior_continue_rich_features` rather than hiding the downgrade.

## Validation

- `python -m py_compile` on all new G5.13 scripts and modified G5.12-facing scripts.
- Run the full G5.12 reproduction sequence.
- Run all G5.13 scripts.
- Parse JSON summaries.
- Check CSV row counts.
- Confirm leakage scanners report zero forbidden feature columns.
- Confirm the reserved-ID guard rejects `166`.
- Confirm grouped-context evaluation rows exist.
- Run `git diff --check`.

## Expected Decision Semantics

Best case:

```text
hard_controlled_ranker_passed_continue_rich_safety_preflight
```

Expected conservative case:

```text
candidate_ranker_signal_reduced_to_simple_prior_continue_rich_features
```

This is not a direction failure. It means the current G5.12 signal is not yet enough to claim a robust learned bounded dual-channel UpdateLTM parameter policy, and the next useful work is richer runtime-safe trace features plus safety boundary data.
