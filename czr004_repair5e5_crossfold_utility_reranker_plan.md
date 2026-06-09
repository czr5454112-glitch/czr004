# czr004 Repair5E.5 Plan: Cross-Fold Utility Reranker and False-Positive Suppression

**Branch:** `phase4f5p5-stable-attention-lau`
**Latest pushed commit:** `db0f494509f1f19035f1e9d2e177f3126a9c2c10`
**Latest commit message:** `Implement Repair5E.4 closed-loop utility calibration`

## 0. Current Position After Repair5E.4

Repair5E.4 is a valid negative / weak-signal result. It is **not promotable**, but it is not a reason to abandon the Repair5 main line.

The project goal remains:

```text
Use learning-enhanced UpdateLTM to replace the coarse additive LTM update,
so LaCAM* + learned UpdateLTM beats LaCAM* + plain additive LTM.
```

Stay inside LAUR / UpdateLTM. Do not change PIBT, LaCAM*, candidate generation, pruning, conflict semantics, action prediction, learned restart, richer LTM representation, or bounded delta UpdateParams in this step.

## 1. Evidence From E4

Final E4 held-out preflight:

```text
repair5e4_closed_loop_utility_selector:
  better / equal / worse = 3 / 53 / 4
  mean_delta_ratio_vs_ltm = -0.0008248539980000043
  ratio_worse_than_ltm_groups = 1
  success_worse_than_ltm_groups = 0
  zero_nonadditive_groups = 4

repair5e4_closed_loop_utility_selector_force_additive_parity:
  better / equal / worse = 0 / 60 / 0
  mean_delta_ratio_vs_ltm = 0.0

oracle_teacher_forced_best_safe_update_static_proxy:
  better / equal / worse = 29 / 28 / 3
  mean_delta_ratio_vs_ltm = -0.014011226436383337
```

OOD calibration improved materially:

```text
feature_stats_valid = true
learned_choices_all_blocked_by_ood = false
E3 committed_count max |z| = 126300.0
E4 committed_count max |z| = 8.191661429636884
E4 top OOD trigger concentration = 0.0
```

Leakage/provenance evidence:

```text
leakage_detected = false
support/eval instance overlap = 0
phase5p5_allowed = false
phase6_allowed = false
```

Closed-loop utility table:

```text
contexts = 210
positive non-additive contexts = 24
label distribution = {'additive_ltm': 186, 'block_heavy': 20, 'decay_090': 4}
positive labels only appear in:
  random-32-32-20:100 -> 20
  random-32-32-20:50  -> 4
```

Ablation warning:

```text
repair5e4_closed_loop_utility_selector:
  3 / 53 / 4, mean -0.000824853998

no_ood_guard_diagnostic:
  3 / 53 / 4, mean -0.000824853998

shuffled_labels_diagnostic:
  3 / 53 / 4, mean -0.000353012293
```

This means the guard is no longer the main bottleneck. The bottleneck is the weakness and instability of the utility labels / selector.

## 2. Diagnosis

E4 fixed the measurement problem but exposed the learning problem.

### 2.1 E4 is not purely additive anymore

`zero_nonadditive_groups = 4`, not 6. It selected non-additive updates in some groups, and the force-additive parity control remained exact. That means the runtime path is meaningful.

### 2.2 The selector has poor precision

The selected non-additive choices give only:

```text
3 better / 53 equal / 4 worse
```

The mean is slightly negative, but `better <= worse`, so it fails the promotion criterion. This is a weak signal, not a pass.

### 2.3 The utility labels are too sparse and too concentrated

Only 24 / 210 train contexts are positive, all on `random-32-32-20`, and only two rules survive: `block_heavy` and `decay_090`.

This creates two failure modes:

```text
false positives:
  random-like contexts where the selector fires but the held-out outcome is worse.

false negatives:
  maze / warehouse contexts where oracle/static still has headroom,
  but the learned selector has no positive support and falls back to additive.
```

### 2.4 Shuffled-label ablation is too close

The shuffled-label diagnostic is close to the real E4 selector. That means the current label/neighbor structure is not discriminative enough. The next step must prove that learned utility ordering, not accidental group bias, is producing the gain.

## 3. Repair5E.5 Objective

Call the next step:

```text
Repair5E.5: Cross-Fold Utility Reranker and False-Positive Suppression
```

Primary question:

```text
Can a cross-fold, risk-calibrated utility reranker recover oracle/static headroom
while suppressing E4's false-positive non-additive choices?
```

E5 remains diagnostic-only. It must not claim Phase5.5 or Phase6.

## 4. Key Strategy

Do **not** add more LTM information.
Do **not** split the 8 preset rules into finer rules.
Do **not** implement bounded delta UpdateParams.

Instead:

```text
1. Use more reliable out-of-fold closed-loop utility evidence.
2. Replace sparse hard labels with soft/listwise utility margins.
3. Add risk calibration so non-additive updates fire only when the expected utility is robust.
4. Analyze false positives and false negatives explicitly.
```

The output space stays:

```text
existing 8 preset UpdateLTM rules + additive/defer fallback
```

## 5. Required E5 Work

## P0-A. E4 Failure Autopsy

Implement:

```text
scripts/analyze_repair5e4_failure_modes.py
```

Inputs:

```text
outputs/tables/phase5p5_repair5e4_preflight_paired.csv
outputs/logs/phase5p5_repair5e4_preflight/phase5p5_repair5e4_preflight_laur_updates.jsonl
outputs/tables/phase5p5_repair5e4_closed_loop_rule_utility_train.csv
outputs/reports/phase5p5_repair5e4_ablation_summary.json
```

Write:

```text
outputs/reports/phase5p5_repair5e5_e4_failure_autopsy_report.md
outputs/reports/phase5p5_repair5e5_e4_failure_autopsy_summary.json
outputs/tables/phase5p5_repair5e5_false_positive_contexts.csv
outputs/tables/phase5p5_repair5e5_false_negative_oracle_contexts.csv
```

Required analysis:

```text
- where E4 fires non-additive and gets worse
- where oracle/static is positive but E4 defers to additive
- selected rule distribution by map/agents/iteration
- predicted margin vs realized delta
- support count vs realized delta
- neighbor distance vs realized delta
- rule-specific precision/recall for block_heavy and decay_090
- whether random-32-32-20:100 is the main false-positive source
- whether maze/warehouse are false-negative sources due to no positive train support
```

## P0-B. Cross-Fold Utility Evidence Over Available Instances

Local scenario IDs appear limited to `1..25`, so use cross-fold diagnostics rather than pretending there is a large clean holdout.

Create fold blocks:

```text
fold_0_eval = [1, 2, 3, 4, 5]
fold_1_eval = [6, 7, 8, 9, 10]
fold_2_eval = [11, 12, 13, 14, 15]
fold_3_eval = [16, 17, 18, 19, 20]
fold_4_eval = [21, 22, 23, 24, 25]
```

For each fold:

```text
train/support instances = all other available IDs
eval instances = fold_eval
```

Generate support logs for all preset static probes and additive baseline.

Write:

```text
outputs/logs/phase5p5_repair5e5_crossfold_support/fold_*/...
outputs/reports/phase5p5_repair5e5_crossfold_support_report.md
outputs/reports/phase5p5_repair5e5_crossfold_support_summary.json
```

Include methods:

```text
lacam_star_ltm
always_additive_defer
oracle_probe_static_block_heavy
oracle_probe_static_block_light
oracle_probe_static_commit_heavy
oracle_probe_static_decay_090
oracle_probe_static_decay_095
oracle_probe_static_wait_heavy
oracle_probe_static_wait_light
oracle_teacher_forced_best_safe_update_static_proxy
```

## P0-C. Build Soft/Listwise Utility Tables

Implement:

```text
scripts/create_repair5e5_crossfold_utility_tables.py
```

Do not keep only hard top-1 labels. For every context, preserve:

```text
utility_delta_ratio_by_rule
utility_delta_expanded_by_rule
utility_delta_pibt_by_rule
utility_delta_ttfs_by_rule
success_by_rule
safe_by_rule
rank_by_rule
margin_to_additive_by_rule
margin_to_second_best
fold_id
support_count
context_feature_vector
context_hash
```

Write:

```text
outputs/tables/phase5p5_repair5e5_crossfold_utility_long.csv
outputs/tables/phase5p5_repair5e5_crossfold_utility_wide.csv
outputs/reports/phase5p5_repair5e5_crossfold_utility_report.md
outputs/reports/phase5p5_repair5e5_crossfold_utility_summary.json
```

Required diagnostics:

```text
- positive-context count by map/agents/rule/fold
- stable-positive count by rule
- false-positive risk by rule
- how often each rule beats additive by more than epsilon
- utility margin histogram
- whether positive labels remain only random-map labels
- whether maze/warehouse have weak but consistent non-ratio benefits
```

## P0-D. Threshold and Risk Calibration

Implement:

```text
scripts/tune_repair5e5_utility_thresholds.py
```

Sweep:

```text
min_predicted_margin
min_support_count
max_neighbor_distance
min_fold_agreement
rule-specific risk caps
non_additive_budget
commit_heavy exclusion/cap
```

Write:

```text
outputs/reports/phase5p5_repair5e5_threshold_sweep_report.md
outputs/reports/phase5p5_repair5e5_threshold_sweep_summary.json
outputs/tables/phase5p5_repair5e5_threshold_sweep.csv
```

Primary tuning goal:

```text
better > worse
mean_delta_ratio_vs_ltm < 0
ratio_worse_than_ltm_groups <= 1
success_worse_than_ltm_groups = 0
zero_nonadditive_groups < total_groups
```

Secondary goal:

```text
shuffled-label diagnostic must not match the real selector.
```

## P0-E. Implement One E5 Candidate

Implement:

```text
repair5e5_crossfold_utility_reranker
```

Runtime dir:

```text
artifacts/models/laur_ltm/repair5e5_crossfold_utility_reranker/
```

Artifact script:

```text
scripts/create_repair5e5_crossfold_utility_reranker_runtime.py
```

Acceptable implementation:

```text
Option 1:
  deterministic KNN / radius-neighbor utility reranker over calibrated runtime features

Option 2:
  small neural utility model with rule utility heads and safety heads
```

Requirements:

```text
- output space = existing 8 preset rules plus additive/defer fallback
- no bounded delta UpdateParams
- no richer LTM representation
- no solver semantic changes
- no action prediction
- no exact map/agent recovery table as the primary decision mechanism
- use cross-fold train evidence only
- selected non-additive rule must have positive utility margin and enough support
- suppress E4 false positives, especially random-32-32-20:100 if confirmed
- recover E4 false negatives where oracle/static headroom is stable
- keep calibrated OOD/defer guard
- force-additive parity path must remain exact
```

Manifest must record:

```text
fold definitions
train/support logs
forbidden eval logs
feature stats hash
utility table hash
threshold sweep hash
selected thresholds
rule-specific risk caps
script hashes
git provenance
```

Write:

```text
outputs/reports/phase5p5_repair5e5_selector_artifact_report.md
outputs/reports/phase5p5_repair5e5_selector_artifact_summary.json
```

## P0-F. E5 Ablations

Run:

```text
repair5e5_crossfold_utility_reranker
repair5e5_crossfold_utility_reranker_force_additive_parity
repair5e5_crossfold_utility_reranker_recovery_disabled_parity
repair5e5_crossfold_utility_reranker_no_ood_guard_diagnostic
repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic
repair5e5_crossfold_utility_reranker_loose_threshold_diagnostic
repair5e5_crossfold_utility_reranker_strict_threshold_diagnostic
repair5e4_closed_loop_utility_selector
repair5e4_calibrated_guard_only_on_e3_split
```

Write:

```text
outputs/reports/phase5p5_repair5e5_ablation_report.md
outputs/reports/phase5p5_repair5e5_ablation_summary.json
outputs/tables/phase5p5_repair5e5_ablation_paired.csv
```

Ablation interpretation:

```text
If no_ood_guard == normal:
  guard is not the bottleneck.

If shuffled_labels ~= real selector:
  utility model is still not learning meaningful structure.

If loose threshold wins mean but has many worse:
  false-positive control is insufficient.

If strict threshold is parity:
  selector is too conservative.

If calibrated guard only beats E5:
  E5 selector still fails; inspect label model.
```

## P0-G. Final E5 Evaluation

Because local instances are limited, run two diagnostic views.

### View 1: Five-fold out-of-fold evaluation

Each fold's selector/runtime must be built without using that fold's eval logs.

Write:

```text
outputs/reports/phase5p5_repair5e5_oof_preflight_report.md
outputs/reports/phase5p5_repair5e5_oof_preflight_summary.json
outputs/tables/phase5p5_repair5e5_oof_preflight_summary.csv
outputs/tables/phase5p5_repair5e5_oof_preflight_paired.csv
outputs/logs/phase5p5_repair5e5_oof_preflight/*.jsonl
```

### View 2: Small final holdout

If feasible:

```text
train/support = 1..20
eval = 21..25
```

If some scenario IDs are missing, use the largest disjoint final block and record exact IDs.

Write:

```text
outputs/reports/phase5p5_repair5e5_preflight_report.md
outputs/reports/phase5p5_repair5e5_preflight_summary.json
outputs/tables/phase5p5_repair5e5_preflight_summary.csv
outputs/tables/phase5p5_repair5e5_preflight_paired.csv
outputs/logs/phase5p5_repair5e5_preflight/*.jsonl
```

Required methods:

```text
lacam_star
lacam_star_ltm
always_additive_defer
repair5d_composite_diagnostic_distilled
repair5e_caseb_ood_guard_distilled
repair5e3_split_guarded_selector
repair5e4_closed_loop_utility_selector
repair5e5_crossfold_utility_reranker
repair5e5_crossfold_utility_reranker_force_additive_parity
oracle_teacher_forced_best_safe_update_static_proxy
```

## 6. E5 Diagnostic Pass Criteria

E5 is still diagnostic-only. It passes as a stronger Repair5 candidate only if:

```text
success_worse_than_ltm_groups = 0
ratio_worse_than_ltm_groups <= 1
mean_delta_ratio_vs_ltm < 0.0
better > worse
zero_nonadditive_groups < total_groups
force-additive parity = exact LTM parity
recovery-disabled parity = exact LTM parity
no support/eval leakage
feature_stats_valid = true
learned_choices_all_blocked_by_ood = false
shuffled-label diagnostic is not as good as real selector
phase5p5_allowed = false
phase6_allowed = false
```

Stronger target:

```text
better - worse >= 3
mean_delta_ratio_vs_ltm <= -0.002
```

## 7. When To Stop Repair5E

If E5 still fails after:

```text
- cross-fold support generation
- soft/listwise utility labels
- threshold/risk calibration
- false-positive suppression
- false-negative recovery
```

then the next formal branch should be Repair5F, but only as a controlled side branch:

```text
Repair5F bounded delta UpdateParams
or richer LTM representation
```

Do not jump to Repair5F before completing E5, because E4 showed oracle/static headroom still exists inside the current preset-rule space.

## 8. Codex Prompt

```text
Continue czr004 on branch phase4f5p5-stable-attention-lau after commit db0f494509f1f19035f1e9d2e177f3126a9c2c10.

Goal:
  Implement Repair5E.5: cross-fold utility reranker and false-positive suppression for learned UpdateLTM.

Main objective:
  Keep the czr004 main line: use learning-enhanced UpdateLTM to beat LaCAM*+plain additive LTM.
  Stay inside LAUR/UpdateLTM.
  Do not predict agent actions, replace PIBT/LaCAM*, change candidate generation/pruning/conflict semantics, add learned restart, lower gates, implement bounded delta UpdateParams, or introduce richer LTM representation as the main branch.
  Do not claim Phase5.5 or Phase6.

Current evidence after Repair5E.4:
  - repair5e4_closed_loop_utility_selector:
      better/equal/worse = 3/53/4
      mean_delta_ratio_vs_ltm = -0.0008248539980000043
      ratio_worse_than_ltm_groups = 1
      success_worse_than_ltm_groups = 0
      zero_nonadditive_groups = 4
  - force-additive parity:
      0/60/0, mean 0.0
  - oracle/static proxy remains strong:
      29/28/3, mean_delta_ratio_vs_ltm = -0.014011226436383337
  - OOD calibration is much better:
      feature_stats_valid = true
      learned_choices_all_blocked_by_ood = false
      E3 committed_count max |z| = 126300.0
      E4 committed_count max |z| = 8.191661429636884
  - closed-loop utility labels are sparse and concentrated:
      contexts = 210
      positive non-additive contexts = 24
      label distribution = {'additive_ltm': 186, 'block_heavy': 20, 'decay_090': 4}
      positive labels only in random-32-32-20 groups
  - shuffled-label diagnostic is too close:
      real selector = 3/53/4, mean -0.000824853998
      shuffled labels = 3/53/4, mean -0.000353012293
  - Therefore E4 is a weak-signal negative result: measurement is fixed enough, but utility labels/selector are not discriminative enough.

Tasks:
  1. Implement scripts/analyze_repair5e4_failure_modes.py.
     Write:
       outputs/reports/phase5p5_repair5e5_e4_failure_autopsy_report.md
       outputs/reports/phase5p5_repair5e5_e4_failure_autopsy_summary.json
       outputs/tables/phase5p5_repair5e5_false_positive_contexts.csv
       outputs/tables/phase5p5_repair5e5_false_negative_oracle_contexts.csv
     Analyze false positives, false negatives, predicted margin vs realized delta, support count vs realized delta, neighbor distance vs realized delta, and rule precision/recall.

  2. Generate cross-fold utility support over available instance IDs 1..25.
     Use fold eval blocks:
       [1,2,3,4,5]
       [6,7,8,9,10]
       [11,12,13,14,15]
       [16,17,18,19,20]
       [21,22,23,24,25]
     For each fold, train/support must exclude that fold's eval IDs.
     Write:
       outputs/logs/phase5p5_repair5e5_crossfold_support/fold_*/...
       outputs/reports/phase5p5_repair5e5_crossfold_support_report.md
       outputs/reports/phase5p5_repair5e5_crossfold_support_summary.json

  3. Build soft/listwise cross-fold utility tables.
     Implement scripts/create_repair5e5_crossfold_utility_tables.py.
     Preserve utility deltas for every rule, not only hard top-1 labels.
     Write:
       outputs/tables/phase5p5_repair5e5_crossfold_utility_long.csv
       outputs/tables/phase5p5_repair5e5_crossfold_utility_wide.csv
       outputs/reports/phase5p5_repair5e5_crossfold_utility_report.md
       outputs/reports/phase5p5_repair5e5_crossfold_utility_summary.json

  4. Tune risk thresholds.
     Implement scripts/tune_repair5e5_utility_thresholds.py.
     Sweep min predicted margin, min support count, max neighbor distance, min fold agreement, rule-specific risk caps, non-additive budget, and commit_heavy exclusion/cap.
     Write:
       outputs/reports/phase5p5_repair5e5_threshold_sweep_report.md
       outputs/reports/phase5p5_repair5e5_threshold_sweep_summary.json
       outputs/tables/phase5p5_repair5e5_threshold_sweep.csv

  5. Implement one E5 runtime candidate:
       repair5e5_crossfold_utility_reranker
     Runtime dir:
       artifacts/models/laur_ltm/repair5e5_crossfold_utility_reranker/
     Implement:
       scripts/create_repair5e5_crossfold_utility_reranker_runtime.py
     Requirements:
       output space remains existing 8 preset UpdateLTM rules plus additive/defer fallback;
       calibrated OOD/defer guard remains active;
       no exact map/agent recovery table as the main decision mechanism;
       no bounded delta UpdateParams;
       no richer LTM representation;
       no solver semantic changes;
       selected non-additive rule must have positive utility margin and enough support;
       suppress E4 false positives and recover stable false negatives when supported;
       force-additive parity must remain exact.

  6. Run E5 ablations:
       repair5e5_crossfold_utility_reranker
       repair5e5_crossfold_utility_reranker_force_additive_parity
       repair5e5_crossfold_utility_reranker_recovery_disabled_parity
       repair5e5_crossfold_utility_reranker_no_ood_guard_diagnostic
       repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic
       repair5e5_crossfold_utility_reranker_loose_threshold_diagnostic
       repair5e5_crossfold_utility_reranker_strict_threshold_diagnostic
       repair5e4_closed_loop_utility_selector
       repair5e4_calibrated_guard_only_on_e3_split
     Write:
       outputs/reports/phase5p5_repair5e5_ablation_report.md
       outputs/reports/phase5p5_repair5e5_ablation_summary.json
       outputs/tables/phase5p5_repair5e5_ablation_paired.csv

  7. Run E5 evaluations:
     A. Five-fold out-of-fold evaluation:
        outputs/reports/phase5p5_repair5e5_oof_preflight_report.md
        outputs/reports/phase5p5_repair5e5_oof_preflight_summary.json
        outputs/tables/phase5p5_repair5e5_oof_preflight_summary.csv
        outputs/tables/phase5p5_repair5e5_oof_preflight_paired.csv
        outputs/logs/phase5p5_repair5e5_oof_preflight/*.jsonl

     B. Small final holdout if feasible:
        train/support = 1..20
        eval = 21..25
        outputs/reports/phase5p5_repair5e5_preflight_report.md
        outputs/reports/phase5p5_repair5e5_preflight_summary.json
        outputs/tables/phase5p5_repair5e5_preflight_summary.csv
        outputs/tables/phase5p5_repair5e5_preflight_paired.csv
        outputs/logs/phase5p5_repair5e5_preflight/*.jsonl

     Required comparison methods:
       lacam_star
       lacam_star_ltm
       always_additive_defer
       repair5d_composite_diagnostic_distilled
       repair5e_caseb_ood_guard_distilled
       repair5e3_split_guarded_selector
       repair5e4_closed_loop_utility_selector
       repair5e5_crossfold_utility_reranker
       repair5e5_crossfold_utility_reranker_force_additive_parity
       oracle_teacher_forced_best_safe_update_static_proxy

Diagnostic pass criteria:
  - success_worse_than_ltm_groups = 0
  - ratio_worse_than_ltm_groups <= 1
  - mean_delta_ratio_vs_ltm < 0.0
  - better > worse
  - zero_nonadditive_groups < total_groups
  - force-additive parity remains exact LTM parity
  - recovery-disabled parity remains exact LTM parity
  - no support/eval leakage detected
  - feature_stats_valid = true
  - learned_choices_all_blocked_by_ood = false
  - shuffled-label diagnostic is not as good as real selector
  - phase5p5_allowed = false
  - phase6_allowed = false

Verification:
  - scripts/build_phase1a_batch.ps1
  - python -m pytest tests/test_repair5e_composite_preflight.py
  - python -m pytest
  If pytest is unavailable in the local Python environment, record that explicitly and run py_compile for all new/modified Python scripts; do not claim pytest passed unless it actually ran.

Commit only Repair5E.5 scoped changes. Leave unrelated dirty/untracked work untouched.
```
