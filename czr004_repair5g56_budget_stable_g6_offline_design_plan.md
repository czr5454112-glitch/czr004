# czr004 Repair5G.5.6 Plan: Budget-Stable Scaled Counterfactual Labels and Offline G6 Safe-Mixture Prototype

**Branch:** `phase4f5p5-stable-attention-lau`
**Start after commit:** `930cbf3 repair5g: scale counterfactual labels and prepare g6 design`
**Status:** proposed next diagnostic/research wave after G5.5 produced scaled same-context labels and a strong adaptive oracle-gap signal
**Promotion status:** `phase5p5_allowed=false`, `phase6_allowed=false`
**AAAI status:** `aaai_ready=false`
**Main project objective:** use learning-enhanced `UpdateLTM` to replace the coarse additive update in the LTM paper and eventually beat `LaCAM*+plain additive LTM` under closed-loop solver metrics, without changing LaCAM*/PIBT semantics.

---

## 0. Executive interpretation

G5.5 is the first result that looks like a real bridge from validated goal-aware dual-channel LTM toward learned bounded `UpdateLTM` dynamics.

Preserve the key facts:

```text
decision:
  scaled_labels_passed_adaptive_gap_strong_continue_g6_design

context_count:
  60

label_rows:
  420

candidate_count:
  7

scaled_label_smoke_passed:
  true

scaled_label_target_passed:
  false

oracle_beats_static_fraction:
  0.4166666666666667

mean_oracle_gap_over_static:
  -0.014675222527750003

feature_audit_passed:
  true

probe_budget_stability_measured:
  true

g6_training_allowed:
  false

ids_166_205_untouched:
  true

phase5p5_allowed:
  false

phase6_allowed:
  false

aaai_ready:
  false
```

Correct interpretation:

```text
Good:
  The adaptive oracle gap survived scaling from G5.4 smoke to 60 contexts.
  Static flow-shield does not dominate all contexts.
  A non-default flow-shield expert wins often enough to justify G6 design.
  Same-context counterfactual label infrastructure is working.
  Feature leakage and runtime availability audits passed.
  Candidate registry supports a small local flow-shield lattice.

Not enough yet:
  The 120-context target did not pass.
  Probe-budget stability was measured on only 6 contexts, with only 3 stable.
  Labels still need a training-eligible stable subset.
  Current labels are observed-ID diagnostic evidence only.
  No G6 learned model is trained or allowed yet.
  No runtime learned-performance claim is allowed.
```

Do not interpret G5.5 as proof that the final learned method works. Interpret it as proof that the learning problem is now real and worth the next step.

---

## 1. Why this is aligned with the grand plan

The grand plan says the project should learn `UpdateLTM` dynamics, not MAPF actions.

The intended G6 method remains:

```text
pre-update context / trace / C-F traffic summary
  -> safe learned mixture over validated UpdateLTM experts
  -> optional abstention / fallback to static flow-shield
  -> later bounded residual over flow-shield parameters only after gates pass
```

Allowed outputs:

```text
mixture weights over safe UpdateLTM experts
abstention probability
confidence / risk score
optional bounded residuals after a later gate
```

Forbidden outputs:

```text
agent actions
PIBT priorities
restart nodes
h_i(v)
action logits
candidate deletion
collision decisions
OPEN / EXPLORED / rewrite / incumbent decisions
```

G5.5 supports this direction because the oracle does not always select the same expert:

```text
repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p75:
  oracle_win_rate = 0.35

repair5g2_best_frozen_static_candidate:
  oracle_win_rate = 0.25

repair5g2_frozen_static_or_selector:
  oracle_win_rate = 0.06666666666666667
```

This is exactly the signature that a safe mixture / abstention policy might add value over static flow-shield.

---

## 2. Main failure / blocker after G5.5

G5.5 did not fail scientifically. It failed the *training-permission* threshold.

Blockers:

```text
B1. Scaled-label target not met:
    context_count = 60
    target >= 120 was not reached

B2. Probe-budget stability too small:
    measured_contexts = 6
    training_eligible_stable_contexts = 3
    unstable_contexts = 3

B3. Labels appear concentrated in first-update contexts:
    current oracle-gap table reports iteration = 0 groups only.
    G6 needs later traffic-state contexts where C/F history exists.

B4. Warehouse labels are weak/empty under current probe setup:
    warehouse groups reported 0 oracle wins and blank gap values.
    This must be classified as no-solution / probe-budget / map-specific difficulty,
    not silently ignored.

B5. Runtime feature set still includes expensive audit-style cost features:
    cost_min, cost_max, cost_span appear in the feature table,
    but earlier G5.3 showed cost_audit is a dominant overhead component.
    G6 runtime-performance mode should use a cheap feature allowlist first.
```

Therefore G5.6 must turn "G6 design allowed" into either:

```text
G6 offline diagnostic training allowed
```

or:

```text
candidate/label/probe stability insufficient; collect more labels before training
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
- train a runtime learned model in C++ in this round
- use warehouse failures to cherry-pick maps away
- use audit-only expensive cost_audit features in a performance-runtime feature set
```

Allowed:

```text
- observed-ID counterfactual label expansion
- observed-ID offline G6 diagnostic training only if P1-P5 gates pass
- train/dev split using observed IDs only
- small calibrated linear / MLP safe-mixture prototype
- random-feature and shuffled-label controls
- static-flow-shield fallback and abstention policy design
- runtime feature allowlist refinement
- budget stability and no-solution classification
```

---

## 4. Split policy

Observed IDs may be used for diagnostics and training-development only:

```text
1..25      support/training, observed
26..45     G1/G2 development, observed
46..65     G2 final, now observed
66..105    G3 broader/protocol, observed
106..115   possible G3.1 sentinel; audit before reuse
126..165   G4/G5/G5.1/G5.2/G5.3/G5.4/G5.5 observed
146..165   current primary extension window
```

Reserved IDs:

```text
166..205:
  remain untouched for later learned-runtime fresh validation.
  They must not be used for label collection, model training, hyperparameter selection, diagnostics, debugging, or peeking.
```

Recommended G5.6 splits:

```text
observed_train:
  IDs 146..155, plus optionally observed IDs <=145 after split audit

observed_dev:
  IDs 156..165, if not already used for label target completion

strict rule:
  no split may contain IDs >=166
```

If compute only permits one pass, prioritize:

```text
1. completing IDs 156..165 label coverage
2. collecting later-iteration contexts
3. probe-budget stability on a stratified subset
```

---

## 5. Required work

### P0. Documentation and decision hygiene

Add this plan to repo root:

```text
czr004_repair5g56_budget_stable_g6_offline_design_plan.md
```

Update:

```text
docs/codex-worklog.md
```

Write:

```text
outputs/reports/phase5p5_repair5g55_final_interpretation.md
outputs/reports/phase5p5_repair5g56_protocol_overview.md
```

Required interpretation:

```text
G5.5 is a strong positive diagnostic result.
G5.5 confirms adaptive oracle gap over static flow-shield in 25 / 60 contexts.
G5.5 does not train G6 and does not allow runtime claims.
The main blocker is not direction failure, but insufficient target coverage and label stability.
Goal-aware dual-channel LTM remains valid.
```

---

### P1. Complete and diversify scaled labels

Implement or update:

```text
scripts/run_repair5g56_counterfactual_label_completion.py
scripts/analyze_repair5g56_counterfactual_label_completion.py
```

Goal:

```text
context_count >= 120
label_rows = context_count * candidate_count
map/agent coverage complete
IDs 166..205 untouched
```

Required extension:

```text
maps:
  random-32-32-20
  maze-32-32-4
  warehouse-10-20-10-2-1

agents:
  50
  100

observed IDs:
  primary 146..165
  optional observed expansion <=165 only after split audit

iterations:
  do not stop at iteration 0
  collect contexts from iteration 0,1,2,3 when trace_events and traffic_before are available
  explicitly report iteration coverage
```

Outputs:

```text
outputs/tables/phase5p5_repair5g56_counterfactual_update_labels.csv
outputs/tables/phase5p5_repair5g56_counterfactual_contexts.csv
outputs/reports/phase5p5_repair5g56_counterfactual_label_completion.md
outputs/reports/phase5p5_repair5g56_counterfactual_label_completion_summary.json
```

Gates:

```text
context_count_ge_120 = true
label_rows_equal_context_count_times_candidate_count = true
same_context_labels_exist_for_all_candidates = true
checkpoint_replayability_still_passes = true
map_agent_coverage_complete = true
iteration_coverage_reported = true
later_iteration_context_count_gt_0 = true
observed_ids_only = true
ids_166_205_untouched = true
```

If later-iteration contexts are unavailable, classify exactly why:

```text
not enough iterations
no trace events
time-budget stops
checkpoint callback not retaining later traffic
runner max_contexts bug
```

---

### P2. Warehouse and no-solution probe classification

Implement:

```text
scripts/analyze_repair5g56_warehouse_probe_failures.py
scripts/run_repair5g56_warehouse_probe_budget_sentinel.py
```

Purpose:

```text
Do not let warehouse rows silently become NaN.
Classify warehouse/100 and warehouse/50 probe gaps.
```

Budgets:

```text
1000 ms primary
2000 ms sentinel
5000 ms sentinel if needed and compute allows
```

Outputs:

```text
outputs/reports/phase5p5_repair5g56_warehouse_probe_failure_analysis.md
outputs/reports/phase5p5_repair5g56_warehouse_probe_failure_summary.json
outputs/tables/phase5p5_repair5g56_warehouse_probe_failure_cases.csv
```

Classifications:

```text
no_solution_all_candidates
static_only_solution
oracle_nonstatic_solution
budget_sensitive_solution
candidate_specific_failure
valid_flat_no_gap
```

Gate:

```text
warehouse_contexts_classified = true
warehouse_nan_gap_rows_explained = true
```

---

### P3. Probe-budget stability expansion

Implement:

```text
scripts/run_repair5g56_probe_budget_stability_expanded.py
scripts/analyze_repair5g56_probe_budget_stability_expanded.py
```

Budget grid:

```text
250 ms
500 ms
1000 ms
2000 ms
```

Minimum stratified subset:

```text
>= 30 contexts
cover all maps
cover agents 50 and 100
cover static-win and nonstatic-win contexts
cover no-solution warehouse cases if present
```

Outputs:

```text
outputs/reports/phase5p5_repair5g56_probe_budget_stability.md
outputs/reports/phase5p5_repair5g56_probe_budget_stability_summary.json
outputs/tables/phase5p5_repair5g56_probe_budget_rank_stability.csv
outputs/tables/phase5p5_repair5g56_training_eligible_stable_contexts.csv
```

Gates:

```text
budget_stability_measured_contexts_ge_30 = true
training_eligible_stable_contexts_ge_30 = true
unstable_labels_separated = true
oracle_static_sign_stability_reported = true
candidate_rank_stability_reported = true
```

---

### P4. Performance-safe G6 feature allowlist

Implement:

```text
scripts/create_repair5g56_g6_perf_feature_table.py
scripts/analyze_repair5g56_perf_feature_allowlist.py
```

Important:

Earlier G5.3 showed `cost_audit` can dominate runtime overhead. Therefore split feature sets:

```text
perf_safe_features:
  cheap features computed from context stats, trace counts, and cached traffic summaries

audit_only_features:
  cost_min
  cost_max
  cost_span
  any feature requiring full graph cost_audit
```

Initial G6 should train/evaluate both:

```text
A. perf_safe_only
B. audit_plus_perf diagnostic only
```

But only A may be used for runtime-performance claims later.

Outputs:

```text
outputs/tables/phase5p5_repair5g56_g6_perf_feature_table.csv
outputs/reports/phase5p5_repair5g56_perf_feature_allowlist.md
outputs/reports/phase5p5_repair5g56_perf_feature_allowlist_summary.json
outputs/reports/phase5p5_repair5g56_g6_feature_schema.json
```

Gates:

```text
no_forbidden_features = true
no_future_outcome_leakage = true
perf_safe_feature_count_gt_0 = true
audit_only_features_separated = true
cost_audit_features_not_in_perf_safe_runtime_set = true
```

---

### P5. Oracle target construction for safe mixture

Implement:

```text
scripts/create_repair5g56_g6_safe_mixture_targets.py
```

Targets:

```text
oracle_candidate_id
delta_vs_static
delta_vs_additive
candidate_regret
harmful_vs_static label
stable_label flag
abstain_to_static label
train_weight based on margin and budget stability
```

Rules:

```text
If oracle margin over static is below epsilon:
  label = static fallback / abstain

If label is budget unstable:
  mark training_eligible = false, keep for diagnostics

If any candidate is worse than static by safety margin:
  mark harmful candidate for safety head

If all candidates fail:
  mark no-solution context, exclude from training target but keep in report
```

Outputs:

```text
outputs/tables/phase5p5_repair5g56_g6_safe_mixture_targets.csv
outputs/reports/phase5p5_repair5g56_g6_target_construction.md
outputs/reports/phase5p5_repair5g56_g6_target_construction_summary.json
```

Gates:

```text
training_eligible_contexts_ge_30 = true
nonstatic_training_eligible_contexts_gt_0 = true
static_fallback_contexts_gt_0 = true
harmful_candidate_labels_available = true
```

---

### P6. Optional offline G6 safe-mixture prototype only if P1-P5 pass

Do not run this step if the gates above fail.

Implement:

```text
scripts/train_repair5g56_offline_safe_mixture.py
scripts/eval_repair5g56_offline_safe_mixture.py
```

Allowed models:

```text
calibrated multinomial logistic regression
small MLP with <= 64 hidden units
temperature-scaled probabilities
abstention threshold
```

Forbidden:

```text
GNN / Transformer in this round
runtime C++ integration
fresh IDs
actions / priorities / restarts
```

Splits:

```text
observed_train: observed IDs only, no 166..205
observed_dev: observed IDs only, no 166..205
grouped by context_id, not by label row
```

Baselines:

```text
static flow-shield fallback
map-agent selector
always additive
oracle upper bound
random features
shuffled labels
majority expert
```

Outputs:

```text
artifacts/models/laur_ltm/repair5g56_offline_safe_mixture/
outputs/reports/phase5p5_repair5g56_offline_safe_mixture_train.md
outputs/reports/phase5p5_repair5g56_offline_safe_mixture_eval.md
outputs/reports/phase5p5_repair5g56_offline_safe_mixture_summary.json
outputs/tables/phase5p5_repair5g56_offline_safe_mixture_eval.csv
```

Required offline diagnostic gates:

```text
beats_static_on_dev_expected_utility = true
beats_majority_expert = true
beats_random_features = true
beats_shuffled_labels = true
abstention_rate_reported = true
unsafe_candidate_rate_bounded = true
calibration_reported = true
```

If gates fail, decision must be:

```text
continue_label_scaling_or_feature_design
```

not runtime promotion.

---

### P7. Final decision

Write:

```text
outputs/reports/phase5p5_repair5g56_decision.md
outputs/reports/phase5p5_repair5g56_decision_summary.json
```

Decision options:

```text
scaled_target_failed_continue_label_collection
later_iteration_contexts_missing
warehouse_probe_failure_blocks_training
probe_budget_instability_blocks_training
perf_feature_allowlist_failed
g6_targets_ready_no_training_run
offline_g6_safe_mixture_failed
offline_g6_safe_mixture_passed_continue_runtime_preflight_design
candidate_space_too_small_expand_before_training
stop_for_protocol_or_semantic_bug
```

Promotion status must remain:

```text
phase5p5_allowed=false
phase6_allowed=false
aaai_ready=false
ids_166_205_untouched=true
```

Only if offline G6 passes may the next step be a separate G6.1 runtime preflight design. Do not run fresh IDs in G5.6.

---

## 6. Validation

Required:

```text
python -m py_compile all new/modified Python scripts
if C++ changed, run scripts/build_phase1a_batch.ps1
pytest focused tests if available; otherwise manual fallback harness
reserved-ID guard rejects 166
JSON summaries validate
git diff --check
commit and push only G5.6-related tracked files/reports
leave unrelated dirty/untracked files untouched
```

Suggested tests:

```text
tests/test_repair5g56_budget_stable_labels.py
tests/test_repair5g56_feature_allowlist.py
tests/test_repair5g56_safe_mixture_targets.py
```

Commit message:

```text
repair5g: prepare budget-stable g6 safe mixture prototype
```
