# czr004 Repair5G.5.8 Plan: Targeted Confidence Expansion, Abstention Label Bank, and Offline G6 Gate

**Branch:** `phase4f5p5-stable-attention-lau`
**Start after commit:** `d992770 repair5g: add budget-aware label confidence and offline g6 gate`
**Status:** proposed next diagnostic/research wave after G5.7 produced budget-aware confidence labels but did not pass the offline G6 training gate
**Promotion status:** `phase5p5_allowed=false`, `phase6_allowed=false`
**AAAI status:** `aaai_ready=false`
**Main project objective:** use learning-enhanced `UpdateLTM` to replace the coarse additive update in the LTM paper and eventually beat `LaCAM*+plain additive LTM` under closed-loop solver metrics, without changing LaCAM*/PIBT semantics.

---

## 0. Executive interpretation

G5.7 is a **good diagnostic result** and a useful training-gate failure.

It does **not** show that the goal-aware dual-channel LTM direction is wrong. It shows that the label-confidence bank is close to, but still below, the minimum safe threshold for even an offline diagnostic G6 model.

Preserve the key G5.7 facts:

```text
decision:
  confidence_labels_insufficient_continue_probe_design

context_count:
  140

label_rows:
  980

primary_1000_2000_stable_contexts:
  20

training_eligible_contexts:
  20

stable_high_confidence_nonstatic_count:
  11

stable_static_or_abstain_count:
  9

warehouse_policy:
  no_solution_abstain = 35
  longer_budget_needed = 5

offline_training_run:
  false

offline_g6_passed:
  false

ids_166_205_untouched:
  true

phase5p5_allowed:
  false

phase6_allowed:
  false

aaai_ready:
  false

runtime_claim_allowed:
  false
```

The key interpretation is:

```text
Good:
  1000/2000 ms primary-pair stability exists in 20 / 30 measured contexts.
  Stable high-confidence nonstatic contexts already pass the >=10 minimum.
  250 ms is confirmed to be a stress budget, with 16 / 30 disagreement.
  Feature matrices are clean and perf-safe vs audit-only split is correct.
  Warehouse contexts are explicitly classified instead of hidden.
  Offline G6 was correctly blocked because the confidence gate did not pass.

Bad / blocker:
  training_eligible_contexts = 20 < 30
  stable_static_or_abstain_count = 9 < 10
  abstain_to_static_count is 0 in the current confidence label construction
  only 30 budget-tier contexts were analyzed
  warehouse no-solution abstention is not yet integrated into a balanced G6 target bank
```

Scientific conclusion:

```text
The direction is still goal-aware dual-channel LTM + learned bounded UpdateLTM dynamics.
The blocker is not representation failure.
The blocker is insufficient confidence-balanced labels for offline G6.
```

G5.8 must now do targeted confidence expansion, not broad unstructured sweeps.

---

## 1. Why G5.7 does not contradict the project direction

The project's intended learned component is:

```text
pre-update context / trace / C-F traffic summary
  -> safe learned mixture or abstention over validated UpdateLTM experts
  -> bounded C/F-channel UpdateParams
  -> DirectedTrafficMap
  -> WeightedDistanceTable
  -> original LaCAM*/PIBT semantics unchanged
```

G5.7 stayed within that scope. It did not introduce MAPF actions, priorities, restarts, h-values, candidate deletion, or collision decisions.

G5.7's failure is a **training-permission failure**:

```text
confidence labels are not yet sufficiently numerous and class-balanced
```

not a **method-direction failure**:

```text
goal-aware dual-channel LTM is not useful
```

This matters because G5.6 already showed meaningful adaptive oracle gap over static flow-shield:

```text
oracle_beats_static_contexts = 54 / 140
oracle_beats_static_fraction = 0.38571428571428573
mean_oracle_gap_over_static = -0.01113516710276
```

G5.7 adds that 1000/2000 ms primary-pair stability exists, but only in 20 contexts so far. The correct next move is to expand high-confidence labels and abstention examples.

---

## 2. Main research questions for G5.8

G5.8 must answer:

```text
Q1. Can primary-pair 1000/2000 ms stable contexts be expanded from 20 to >=30?

Q2. Can stable_static_or_abstain be raised from 9 to >=10 without weakening label quality?

Q3. Can warehouse no_solution_abstain and longer_budget_needed contexts be turned into useful abstention/fallback training examples?

Q4. Does a balanced confidence label bank exist with:
    stable_high_confidence_nonstatic >= 10
    stable_static_or_abstain >= 10
    no_solution_or_budget_abstain examples present
    training_eligible_contexts >= 30

Q5. Does the perf-safe feature set remain clean after expansion?

Q6. If the label gate passes, can a tiny offline diagnostic G6 safe-mixture / abstention model beat strong observed-ID baselines and controls?
```

---

## 3. Non-negotiable constraints

Do not:

```text
- modify external/lacam2/lacam2/**
- change PIBT legality, priority inheritance, backtracking, vertex conflict, or swap conflict semantics
- change LaCAM* candidate generation, child pruning, OPEN/EXPLORED, rewrite, incumbent pruning, or restart semantics
- introduce action prediction
- introduce learned restart
- output learned h_i(v)
- output learned edge action logits
- output learned priority overrides
- delete legal candidates
- claim Phase5.5 or Phase6
- claim AAAI-ready
- run IDs 166..205
- use final full-run outcomes as per-update labels
- integrate learned G6 into runtime C++
- train on unstable, unknown-confidence, or unclassified labels as gold labels
- use audit-only cost_audit features in a performance-safe model
- hide warehouse/no-solution contexts
```

Allowed:

```text
- observed-ID counterfactual probe expansion
- budget-aware label-confidence modeling
- 1000/2000 ms primary-pair stability expansion
- 250 ms stress analysis only
- warehouse abstention/static-fallback label construction
- tiny offline diagnostic G6 training only if all gates pass
- random-feature and shuffled-label controls
- runtime-preflight design only if offline G6 passes
```

---

## 4. Split policy

Observed IDs may be used only for diagnostics and training-development:

```text
1..25      observed support/training
26..45     observed G1/G2 development
46..65     observed G2 final, now observed
66..105    observed G3 diagnostics
106..115   possible observed sentinel; audit before reuse
126..165   observed G4/G5/G5.1/G5.2/G5.3/G5.4/G5.5/G5.6/G5.7
```

Reserved:

```text
166..205:
  remain untouched for later learned-runtime fresh validation.
  do not use for labels, model training, hyperparameter selection, debugging, command dry-runs, or peeking.
```

Recommended G5.8 extension:

```text
Primary:
  use existing G5.6/G5.7 contexts first
  expand observed confidence labels within IDs 146..165

Optional only if needed and documented:
  use observed IDs <=145 after split audit

No fresh holdout:
  G5.8 is not fresh validation.
```

---

## 5. Required work

### P0. Documentation and decision hygiene

Add this plan to repo root:

```text
czr004_repair5g58_targeted_confidence_expansion_offline_g6_plan.md
```

Update:

```text
docs/codex-worklog.md
```

Write:

```text
outputs/reports/phase5p5_repair5g57_final_interpretation.md
outputs/reports/phase5p5_repair5g58_protocol_overview.md
```

Required interpretation:

```text
G5.7 is a close-but-insufficient confidence-label result.
G5.7 did not fail the goal-aware dual-channel LTM direction.
G5.7 confirms that 250 ms is stress-sensitive and should not be the hard training label gate.
The next target is expanding primary-pair 1000/2000 ms confidence labels and balancing static/abstention examples.
```

---

### P1. Verify G5.7 artifacts

Before any new run, verify:

```text
outputs/reports/phase5p5_repair5g57_decision.md
outputs/reports/phase5p5_repair5g57_decision_summary.json
outputs/reports/phase5p5_repair5g57_budget_tier_stability_summary.json
outputs/reports/phase5p5_repair5g57_confidence_weighted_label_summary.json
outputs/reports/phase5p5_repair5g57_warehouse_no_solution_policy_summary.json
outputs/reports/phase5p5_repair5g57_g6_feature_matrix_summary.json
```

If any are missing:

```text
decision = missing_g57_artifacts_stop
write outputs/reports/phase5p5_repair5g58_missing_g57_artifacts.md
do not run new experiments
do not touch IDs 166..205
```

---

### P2. Targeted primary-pair confidence expansion

Implement:

```text
scripts/run_repair5g58_primary_pair_confidence_expansion.py
scripts/analyze_repair5g58_primary_pair_confidence_expansion.py
```

Primary budgets:

```text
1000 ms
2000 ms
```

Stress / optional budgets:

```text
250 ms = stress diagnostic only
500 ms = optional confidence bonus, not hard gate
```

Sampling priority:

```text
1. contexts likely to become stable_static or abstain_to_static
2. near-boundary static/nonstatic contexts
3. warehouse no_solution / longer_budget contexts
4. later-iteration contexts
5. under-covered map/agent groups
6. contexts where 1000/2000 is likely feasible but 250 disagrees
```

Target gates:

```text
measured_confidence_contexts >= 60
primary_1000_2000_stable_contexts >= 30
training_eligible_contexts >= 30
stable_high_confidence_nonstatic_count >= 10
stable_static_or_abstain_count >= 10
no_solution_or_budget_abstain_count > 0
observed_ids_only = true
ids_166_205_untouched = true
```

Outputs:

```text
outputs/reports/phase5p5_repair5g58_primary_pair_confidence_expansion.md
outputs/reports/phase5p5_repair5g58_primary_pair_confidence_expansion_summary.json
outputs/tables/phase5p5_repair5g58_primary_pair_confidence_by_context.csv
outputs/tables/phase5p5_repair5g58_primary_pair_confidence_by_map_agent.csv
```

---

### P3. Confidence labels v2

Implement:

```text
scripts/create_repair5g58_confidence_weighted_targets.py
scripts/analyze_repair5g58_confidence_weighted_targets.py
```

Label classes:

```text
stable_high_confidence_nonstatic
stable_static
abstain_to_static
no_solution_abstain
longer_budget_needed
budget_sensitive_exclude
exclude_from_training
```

Margin sweep:

```text
0.0025
0.005
0.010
```

Choose a threshold before any offline training and write:

```text
outputs/reports/phase5p5_repair5g58_training_label_threshold_decision.md
outputs/reports/phase5p5_repair5g58_training_label_threshold_decision_summary.json
```

Gate:

```text
confidence_labels_v2_created = true
training_eligible_contexts >= 30
stable_high_confidence_nonstatic_count >= 10
stable_static_or_abstain_count >= 10
budget_sensitive_excluded_or_downweighted = true
no_solution_abstain_present = true
```

If this gate fails, do not train.

---

### P4. Warehouse abstention policy v2

Implement:

```text
scripts/analyze_repair5g58_warehouse_abstention_policy.py
```

Warehouse contexts must not be dropped. They may become:

```text
no_solution_abstain
longer_budget_needed
static_default
candidate_space_gap
warehouse_specialist_later
```

Outputs:

```text
outputs/reports/phase5p5_repair5g58_warehouse_abstention_policy.md
outputs/reports/phase5p5_repair5g58_warehouse_abstention_policy_summary.json
outputs/tables/phase5p5_repair5g58_warehouse_abstention_policy.csv
```

Gate:

```text
warehouse_contexts_classified = true
warehouse_contexts_used_or_explained = true
warehouse_no_solution_not_silently_dropped = true
```

---

### P5. G6 feature matrices v2

Implement:

```text
scripts/create_repair5g58_g6_feature_matrices.py
scripts/analyze_repair5g58_g6_feature_matrix_quality.py
```

Feature sets:

```text
perf_safe_only:
  runtime-eligible features only

audit_plus_perf:
  diagnostic only; never for runtime performance claims
```

Forbidden model features:

```text
future outcome
probe result
oracle score
candidate label
traffic_after
actions
priorities
restart
h-values
candidate deletion
```

Outputs:

```text
outputs/tables/phase5p5_repair5g58_g6_features_perf_safe.csv
outputs/tables/phase5p5_repair5g58_g6_features_audit_plus_perf.csv
outputs/reports/phase5p5_repair5g58_g6_feature_matrix_quality.md
outputs/reports/phase5p5_repair5g58_g6_feature_matrix_summary.json
```

Gate:

```text
perf_safe_rows >= training_eligible_contexts
forbidden_feature_count = 0
audit_only_features_not_in_perf_safe = true
```

---

### P6. Offline diagnostic G6 only if gates pass

Only if P2/P3/P4/P5 gates pass, implement and run:

```text
scripts/train_repair5g58_offline_safe_mixture.py
scripts/eval_repair5g58_offline_safe_mixture.py
```

Allowed models:

```text
calibrated binary classifier:
  choose_nonstatic_vs_static_or_abstain

calibrated multinomial logistic regression:
  choose among stable experts + abstain/static

tiny MLP:
  <=64 hidden units
```

Required baselines:

```text
static flow-shield
map-agent selector
always additive
majority class
random features
shuffled labels
oracle upper bound
```

Required evaluation:

```text
observed-ID train/dev split only
no IDs 166..205
perf_safe_only primary model
audit_plus_perf diagnostic-only model
calibration / confidence analysis
abstention behavior
selected-vs-static estimated label utility
harmful-vs-static rate
random/shuffled controls
```

Outputs:

```text
outputs/reports/phase5p5_repair5g58_offline_safe_mixture_train.md
outputs/reports/phase5p5_repair5g58_offline_safe_mixture_train_summary.json
outputs/reports/phase5p5_repair5g58_offline_safe_mixture_eval.md
outputs/reports/phase5p5_repair5g58_offline_safe_mixture_eval_summary.json
artifacts/models/laur_ltm/repair5g58_offline_safe_mixture/
```

This is offline diagnostic only:

```text
runtime_claim_allowed = false
phase5p5_allowed = false
phase6_allowed = false
aaai_ready = false
```

---

### P7. If local compute is insufficient

Do not fake success. Write:

```text
outputs/reports/phase5p5_repair5g58_local_limit_report.md
outputs/reports/phase5p5_repair5g58_server_command_plan.md
outputs/reports/phase5p5_repair5g58_server_command_plan_summary.json
```

Decision should be:

```text
server_required_for_confidence_label_expansion
```

or:

```text
server_required_for_offline_g6_training_gate
```

---

### P8. Final decision

Write:

```text
outputs/reports/phase5p5_repair5g58_decision.md
outputs/reports/phase5p5_repair5g58_decision_summary.json
```

Decision options:

```text
missing_g57_artifacts_stop
confidence_expansion_failed_continue_probe_design
confidence_labels_sufficient_training_gate_passed
warehouse_abstention_policy_failed
perf_feature_matrix_failed
offline_g6_not_run_training_gate_failed
offline_g6_safe_mixture_failed_continue_labels_or_candidate_space
offline_g6_safe_mixture_passed_continue_runtime_preflight_design
candidate_space_gap_expand_flow_shield_lattice
server_required_for_confidence_label_expansion
server_required_for_offline_g6_training_gate
stop_for_protocol_or_semantic_bug
```

---

## Validation

Required:

```text
python -m py_compile all new/modified Python scripts
if C++ changed, run scripts/build_phase1a_batch.ps1
pytest focused tests if available; otherwise manual fallback harness
reserved-ID guard rejects 166
JSON summaries parse
CSV row-count sanity checks pass
git diff --check
commit and push only G5.8-related tracked files/reports
leave unrelated dirty/untracked files untouched
```

Commit message:

```text
repair5g: expand confidence labels and gate offline g6
```

---

## Codex prompt

```text
Continue czr004 on branch phase4f5p5-stable-attention-lau after commit d992770 repair5g: add budget-aware label confidence and offline g6 gate.

Goal:
Implement Repair5G.5.8: verify G5.7 artifacts, expand primary-pair 1000/2000 ms confidence labels over observed IDs, balance stable nonstatic and static/abstain classes, refine warehouse abstention examples, and only if all training gates pass, train a tiny offline diagnostic G6 safe-mixture model. Do not run IDs 166..205. Do not claim Phase5.5/Phase6/AAAI-ready. Do not integrate learned runtime G6 in this round.

Main project objective:
Use learning-enhanced UpdateLTM to replace the coarse additive update in the LTM paper and eventually beat LaCAM*+plain additive LTM under closed-loop solver metrics, without changing LaCAM*/PIBT semantics.

Read first:
  deep-research-report.md
  phase4_6_laur_ltm_codex_execution_plan.md
  docs/aaai_quality_requirements.md
  czr004_repair5g57_budget_aware_label_confidence_offline_g6_plan.md
  outputs/reports/phase5p5_repair5g57_decision.md
  outputs/reports/phase5p5_repair5g57_decision_summary.json
  outputs/reports/phase5p5_repair5g57_budget_tier_stability_summary.json
  outputs/reports/phase5p5_repair5g57_confidence_weighted_label_summary.json
  outputs/reports/phase5p5_repair5g57_warehouse_no_solution_policy_summary.json
  outputs/reports/phase5p5_repair5g57_g6_feature_matrix_summary.json
  outputs/reports/phase5p5_repair5g57_offline_safe_mixture_summary.json

Preserve this interpretation:
  - G5.7 decision = confidence_labels_insufficient_continue_probe_design.
  - G5.7 is a close-but-insufficient confidence-label result, not a direction failure.
  - context_count = 140, label_rows = 980.
  - primary_1000_2000_stable_contexts = 20.
  - training_eligible_contexts = 20.
  - stable_high_confidence_nonstatic_count = 11.
  - stable_static_or_abstain_count = 9.
  - 250 ms stress disagreement rate = 0.5333333333333333.
  - Warehouse policy: no_solution_abstain = 35, longer_budget_needed = 5.
  - Feature matrices passed: perf_safe_rows = 30, audit_plus_perf_rows = 30, forbidden feature count = 0.
  - Offline training was correctly blocked and no model was trained.
  - IDs 166..205 remain untouched.
  - phase5p5_allowed=false, phase6_allowed=false, aaai_ready=false, runtime_claim_allowed=false.
  - The project direction remains goal-aware dual-channel LTM + learned bounded UpdateLTM dynamics, not MAPF action learning.

Do not:
  - modify external/lacam2/lacam2/**
  - change PIBT, LaCAM*, candidate generation, conflict, pruning, OPEN/EXPLORED, rewrite, incumbent, or restart semantics
  - introduce action prediction
  - introduce learned restart
  - output h_i(v), action logits, priority overrides, or candidate deletion
  - claim Phase5.5 or Phase6
  - claim AAAI-ready
  - run IDs 166..205
  - use final full-run outcomes as per-update labels
  - integrate learned G6 into runtime C++
  - train on unstable, unknown-confidence, or unclassified labels as gold labels
  - use audit-only cost_audit features in a performance-safe model
  - hide warehouse/no-solution contexts

Tasks:
  1. Add czr004_repair5g58_targeted_confidence_expansion_offline_g6_plan.md to repo root and update docs/codex-worklog.md.

  2. Verify G5.7 artifacts. If missing, stop with missing_g57_artifacts_stop.

  3. Write:
     outputs/reports/phase5p5_repair5g57_final_interpretation.md
     outputs/reports/phase5p5_repair5g58_protocol_overview.md

  4. Implement and run targeted primary-pair confidence expansion:
     scripts/run_repair5g58_primary_pair_confidence_expansion.py
     scripts/analyze_repair5g58_primary_pair_confidence_expansion.py

     Use 1000 and 2000 ms as the primary training-label stability pair.
     Treat 250 ms as stress-only.
     Treat 500 ms as optional confidence bonus.

     Gates:
       measured_confidence_contexts >= 60
       primary_1000_2000_stable_contexts >= 30
       training_eligible_contexts >= 30
       stable_high_confidence_nonstatic_count >= 10
       stable_static_or_abstain_count >= 10
       no_solution_or_budget_abstain_count > 0
       observed_ids_only = true
       ids_166_205_untouched = true

  5. Construct confidence-weighted targets v2:
     scripts/create_repair5g58_confidence_weighted_targets.py
     scripts/analyze_repair5g58_confidence_weighted_targets.py

     Label classes:
       stable_high_confidence_nonstatic
       stable_static
       abstain_to_static
       no_solution_abstain
       longer_budget_needed
       budget_sensitive_exclude
       exclude_from_training

     Sweep margins:
       0.0025
       0.005
       0.010

     Choose one threshold before offline training and write:
       outputs/reports/phase5p5_repair5g58_training_label_threshold_decision.md
       outputs/reports/phase5p5_repair5g58_training_label_threshold_decision_summary.json

  6. Refine warehouse abstention policy:
     scripts/analyze_repair5g58_warehouse_abstention_policy.py

     Warehouse no-solution contexts may be used as abstention/fallback examples, not as expert-selection positives.

  7. Build G6 feature matrices v2:
     scripts/create_repair5g58_g6_feature_matrices.py
     scripts/analyze_repair5g58_g6_feature_matrix_quality.py

     Feature sets:
       perf_safe_only
       audit_plus_perf diagnostic only

     Forbidden model features:
       future outcome
       probe result
       oracle score
       candidate label
       traffic_after
       actions
       priorities
       restart
       h-values
       candidate deletion

  8. Only if training gates pass, train tiny offline diagnostic G6:
     scripts/train_repair5g58_offline_safe_mixture.py
     scripts/eval_repair5g58_offline_safe_mixture.py

     Allowed models:
       calibrated logistic regression
       calibrated multinomial logistic regression
       tiny MLP <=64 hidden units

     Baselines:
       static flow-shield
       map-agent selector
       always additive
       majority class
       random features
       shuffled labels
       oracle upper bound

     This is offline observed-ID diagnostic only:
       runtime_claim_allowed=false
       phase5p5_allowed=false
       phase6_allowed=false
       aaai_ready=false

  9. If local compute cannot reach target:
     do not fake success
     do not train
     write:
       outputs/reports/phase5p5_repair5g58_local_limit_report.md
       outputs/reports/phase5p5_repair5g58_server_command_plan.md
       outputs/reports/phase5p5_repair5g58_server_command_plan_summary.json

  10. Write:
      outputs/reports/phase5p5_repair5g58_decision.md
      outputs/reports/phase5p5_repair5g58_decision_summary.json

Decision options:
  missing_g57_artifacts_stop
  confidence_expansion_failed_continue_probe_design
  confidence_labels_sufficient_training_gate_passed
  warehouse_abstention_policy_failed
  perf_feature_matrix_failed
  offline_g6_not_run_training_gate_failed
  offline_g6_safe_mixture_failed_continue_labels_or_candidate_space
  offline_g6_safe_mixture_passed_continue_runtime_preflight_design
  candidate_space_gap_expand_flow_shield_lattice
  server_required_for_confidence_label_expansion
  server_required_for_offline_g6_training_gate
  stop_for_protocol_or_semantic_bug

Validation:
  python -m py_compile all new/modified Python scripts
  if C++ changed, run scripts/build_phase1a_batch.ps1
  pytest focused tests if available; otherwise manual fallback harness
  reserved-ID guard rejects 166
  JSON summaries parse
  CSV row-count sanity checks pass
  git diff --check
  commit and push only G5.8-related tracked files/reports
  leave unrelated dirty/untracked files untouched

Commit message:
  repair5g: expand confidence labels and gate offline g6
```
